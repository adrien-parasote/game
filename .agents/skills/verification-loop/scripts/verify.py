#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""
Stream Coding — Master Verification Runner
===========================================

Priority-ordered validation runner for the verification-loop skill.
Orchestrates build, lint, type-check, test, and security scans.
Stops on first CRITICAL failure.

Usage:
    python verify.py <project_path>                    # Auto-detect and run
    python verify.py <project_path> --priority P0      # Security only
    python verify.py <project_path> --priority P0,P1   # Security + Lint
    python verify.py <project_path> --json             # JSON output
    python verify.py <project_path> --stop-on-fail     # Stop on first failure
    python verify.py --help

Priority Order:
    P0: Security Scan (secrets, dangerous patterns)     — CRITICAL
    P1: Build Verification (compile/build)              — CRITICAL
    P2: Type Check (static analysis)                    — HIGH
    P3: Lint Check (code style/quality)                 — HIGH
    P4: Test Suite (unit + integration)                 — HIGH
    P5: Debug Artifacts (console.log, print, TODO)      — MEDIUM

Exit Codes:
    0 — All checks passed
    1 — One or more checks failed
    2 — Invalid arguments or project path

Output: JSON to stdout when --json is used, human-readable otherwise.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
#  CONFIGURATION
# =============================================================================

SKIP_DIRS = frozenset({
    "node_modules", ".git", "dist", "build", "__pycache__", ".venv", "venv",
    ".next", ".terraform", "vendor", "target", ".agents", ".agent",
    "coverage", ".nyc_output", ".pytest_cache", ".mypy_cache",
})

CODE_EXTENSIONS = frozenset({
    ".go", ".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".java",
    ".kt", ".kts", ".swift", ".php", ".cpp", ".cc", ".c", ".h",
    ".tf", ".hcl",
})

SECRET_PATTERNS: List[Tuple[str, str, str]] = [
    # Cloud credentials
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key", "critical"),
    (r"-----BEGIN\s+(RSA|PRIVATE|EC|OPENSSH)\s+KEY-----", "Private Key", "critical"),
    (r"(mongodb|postgres|mysql|redis):\/\/[^\s\"']+", "Database URI", "critical"),

    # API keys and tokens
    (r"(?:api[_-]?key|apikey)\s*[=:]\s*[\"'][^\"']{10,}[\"']", "API Key", "high"),
    (r"(?:secret|password|passwd)\s*[=:]\s*[\"'][^\"']{4,}[\"']", "Hardcoded Secret", "high"),
    (r"bearer\s+[a-zA-Z0-9\-_.]{20,}", "Bearer Token", "high"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub PAT", "critical"),
    (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth Token", "critical"),
    (r"sk-[a-zA-Z0-9]{32,}", "OpenAI/Stripe Key", "critical"),

    # SSH / JWT
    (r"ssh-rsa\s+[A-Za-z0-9+/]{100,}", "SSH Public Key (embedded)", "medium"),
    (r"eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+", "JWT Token", "high"),
]

DANGEROUS_CODE_PATTERNS: List[Tuple[str, str, str, str]] = [
    # Injection risks
    (r"\beval\s*\(", "eval()", "critical", "Code injection"),
    (r"\bexec\s*\(", "exec()", "high", "Code injection"),
    (r"child_process\.exec\s*\(", "child_process.exec", "high", "Command injection"),
    (r"subprocess\.call\s*\([^)]*shell\s*=\s*True", "subprocess shell=True", "high", "Command injection"),

    # XSS
    (r"dangerouslySetInnerHTML", "dangerouslySetInnerHTML", "high", "XSS"),
    (r"\.innerHTML\s*=", "innerHTML assignment", "medium", "XSS"),

    # SQL injection
    (r"""[\"'][^\"']*\+\s*\w+\s*\+\s*[\"'].*(?:SELECT|INSERT|UPDATE|DELETE)""",
     "SQL string concat", "critical", "SQL injection"),
    (r'f"[^"]*(?:SELECT|INSERT|UPDATE|DELETE)[^"]*\{', "SQL f-string", "critical", "SQL injection"),

    # Unsafe config
    (r"verify\s*=\s*False", "SSL verify disabled", "high", "MITM"),
    (r"pickle\.loads?\s*\(", "pickle usage", "high", "Deserialization"),
    (r"yaml\.load\s*\([^)]*\)(?!\s*,\s*Loader)", "Unsafe YAML load", "high", "Deserialization"),
]

DEBUG_PATTERNS: List[Tuple[str, str]] = [
    (r"\bconsole\.log\s*\(", "console.log"),
    (r"\bprint\s*\((?!.*#\s*noqa)", "print()"),
    (r"\bfmt\.Print(?:ln|f)?\s*\(", "fmt.Print"),
    (r"\bSystem\.out\.print", "System.out.print"),
    (r"\b(?:TODO|FIXME|HACK|XXX)\b(?!\s*[\(#]?\s*[A-Z]+-\d+)", "TODO/FIXME without ticket"),
]


# =============================================================================
#  BUILD SYSTEM DETECTION
# =============================================================================

BUILD_SYSTEMS: List[Dict[str, Any]] = [
    {
        "name": "Go",
        "indicator": "go.mod",
        "build_cmd": ["go", "build", "./..."],
        "type_cmd": ["go", "vet", "./..."],
        "lint_cmd": ["golangci-lint", "run", "--timeout", "2m"],
        "test_cmd": ["go", "test", "./...", "-count=1", "-timeout", "2m"],
    },
    {
        "name": "Node.js (npm)",
        "indicator": "package.json",
        "build_cmd_script": "build",
        "type_cmd_script": "typecheck",
        "type_cmd_fallback": ["npx", "tsc", "--noEmit"],
        "lint_cmd_script": "lint",
        "test_cmd_script": "test",
    },
    {
        "name": "Python",
        "indicator": "pyproject.toml",
        "type_cmd": ["mypy", "."],
        "type_cmd_fallback": ["pyright", "."],
        "lint_cmd": ["ruff", "check", "."],
        "test_cmd": ["pytest", "--tb=short", "-q"],
    },
    {
        "name": "Python (requirements)",
        "indicator": "requirements.txt",
        "type_cmd": ["mypy", "."],
        "lint_cmd": ["ruff", "check", "."],
        "test_cmd": ["pytest", "--tb=short", "-q"],
    },
    {
        "name": "Rust",
        "indicator": "Cargo.toml",
        "build_cmd": ["cargo", "build"],
        "type_cmd": ["cargo", "check"],
        "lint_cmd": ["cargo", "clippy"],
        "test_cmd": ["cargo", "test"],
    },
    {
        "name": "Terraform",
        "indicator": "*.tf",
        "build_cmd": ["terraform", "validate"],
        "lint_cmd": ["tflint", "--recursive"],
    },
    {
        "name": "Java (Maven)",
        "indicator": "pom.xml",
        "build_cmd": ["mvn", "compile", "-q"],
        "test_cmd": ["mvn", "test", "-q"],
    },
    {
        "name": "Java (Gradle)",
        "indicator": "build.gradle",
        "build_cmd": ["./gradlew", "compileJava"],
        "test_cmd": ["./gradlew", "test"],
    },
]


def detect_build_system(project_path: Path) -> Optional[Dict[str, Any]]:
    """Auto-detect the project's build system."""
    for bs in BUILD_SYSTEMS:
        indicator = bs["indicator"]
        if "*" in indicator:
            # Glob match
            if list(project_path.glob(indicator)):
                return bs
        elif (project_path / indicator).exists():
            return bs
    return None


def get_npm_script_cmd(project_path: Path, script_name: str) -> Optional[List[str]]:
    """Check if an npm script exists and return the command."""
    pkg_path = project_path / "package.json"
    if not pkg_path.exists():
        return None
    try:
        with open(pkg_path, "r") as f:
            pkg = json.load(f)
        if script_name in pkg.get("scripts", {}):
            return ["npm", "run", script_name, "--", "--if-present"]
        return None
    except (json.JSONDecodeError, OSError):
        return None


# =============================================================================
#  CHECK RUNNERS
# =============================================================================

def run_cmd(cmd: List[str], cwd: str, timeout: int = 120) -> Dict[str, Any]:
    """Run a command and return structured result."""
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "PAGER": "cat", "FORCE_COLOR": "0", "NO_COLOR": "1"},
        )
        duration = round(time.monotonic() - start, 1)
        return {
            "passed": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
            "duration_s": duration,
            "command": " ".join(cmd),
        }
    except FileNotFoundError:
        return {
            "passed": None,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Command not found: {cmd[0]}",
            "duration_s": 0,
            "command": " ".join(cmd),
            "skipped": True,
        }
    except subprocess.TimeoutExpired:
        duration = round(time.monotonic() - start, 1)
        return {
            "passed": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Timeout after {timeout}s",
            "duration_s": duration,
            "command": " ".join(cmd),
        }


def check_p0_security(project_path: Path) -> Dict[str, Any]:
    """P0: Security scan — secrets and dangerous patterns."""
    findings: List[Dict[str, str]] = []
    scanned = 0

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext not in CODE_EXTENSIONS and fname not in {".env", ".env.local", ".env.development"}:
                continue
            filepath = Path(root) / fname
            scanned += 1
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            relpath = str(filepath.relative_to(project_path))

            # Secrets
            for pattern, name, severity in SECRET_PATTERNS:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_num = content[:match.start()].count("\n") + 1
                    findings.append({
                        "file": relpath,
                        "line": str(line_num),
                        "type": "secret",
                        "name": name,
                        "severity": severity,
                    })

            # Dangerous code patterns
            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern, name, severity, category in DANGEROUS_CODE_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append({
                            "file": relpath,
                            "line": str(line_num),
                            "type": "dangerous_pattern",
                            "name": name,
                            "severity": severity,
                            "category": category,
                            "snippet": line.strip()[:100],
                        })

    critical = sum(1 for f in findings if f["severity"] == "critical")
    high = sum(1 for f in findings if f["severity"] == "high")

    return {
        "check": "P0_Security",
        "priority": "P0",
        "passed": critical == 0,
        "scanned_files": scanned,
        "findings_count": len(findings),
        "critical": critical,
        "high": high,
        "findings": findings[:30],  # Cap output
    }


def check_p1_build(project_path: Path, bs: Optional[Dict]) -> Dict[str, Any]:
    """P1: Build verification."""
    if not bs:
        return {"check": "P1_Build", "priority": "P1", "passed": None, "skipped": True,
                "reason": "No build system detected"}

    cmd = None
    if "build_cmd" in bs:
        cmd = bs["build_cmd"]
    elif "build_cmd_script" in bs:
        cmd = get_npm_script_cmd(project_path, bs["build_cmd_script"])

    if not cmd:
        return {"check": "P1_Build", "priority": "P1", "passed": None, "skipped": True,
                "reason": f"No build command for {bs['name']}"}

    result = run_cmd(cmd, str(project_path), timeout=180)
    return {"check": "P1_Build", "priority": "P1", "build_system": bs["name"], **result}


def check_p2_types(project_path: Path, bs: Optional[Dict]) -> Dict[str, Any]:
    """P2: Type checking."""
    if not bs:
        return {"check": "P2_Types", "priority": "P2", "passed": None, "skipped": True,
                "reason": "No build system detected"}

    cmd = None
    if "type_cmd" in bs:
        cmd = bs["type_cmd"]
    elif "type_cmd_script" in bs:
        cmd = get_npm_script_cmd(project_path, bs["type_cmd_script"])
        if not cmd and "type_cmd_fallback" in bs:
            cmd = bs["type_cmd_fallback"]
    elif "type_cmd_fallback" in bs:
        cmd = bs["type_cmd_fallback"]

    if not cmd:
        return {"check": "P2_Types", "priority": "P2", "passed": None, "skipped": True,
                "reason": f"No type check command for {bs['name']}"}

    result = run_cmd(cmd, str(project_path), timeout=120)
    # Try fallback if primary failed due to missing command
    if result.get("skipped") and "type_cmd_fallback" in bs:
        result = run_cmd(bs["type_cmd_fallback"], str(project_path), timeout=120)

    return {"check": "P2_Types", "priority": "P2", "build_system": bs["name"], **result}


def check_p3_lint(project_path: Path, bs: Optional[Dict]) -> Dict[str, Any]:
    """P3: Lint check."""
    if not bs:
        return {"check": "P3_Lint", "priority": "P3", "passed": None, "skipped": True,
                "reason": "No build system detected"}

    cmd = None
    if "lint_cmd" in bs:
        cmd = bs["lint_cmd"]
    elif "lint_cmd_script" in bs:
        cmd = get_npm_script_cmd(project_path, bs["lint_cmd_script"])

    if not cmd:
        return {"check": "P3_Lint", "priority": "P3", "passed": None, "skipped": True,
                "reason": f"No lint command for {bs['name']}"}

    result = run_cmd(cmd, str(project_path), timeout=120)
    return {"check": "P3_Lint", "priority": "P3", "build_system": bs["name"], **result}


def check_p4_tests(project_path: Path, bs: Optional[Dict]) -> Dict[str, Any]:
    """P4: Test suite."""
    if not bs:
        return {"check": "P4_Tests", "priority": "P4", "passed": None, "skipped": True,
                "reason": "No build system detected"}

    cmd = None
    if "test_cmd" in bs:
        cmd = bs["test_cmd"]
    elif "test_cmd_script" in bs:
        cmd = get_npm_script_cmd(project_path, bs["test_cmd_script"])

    if not cmd:
        return {"check": "P4_Tests", "priority": "P4", "passed": None, "skipped": True,
                "reason": f"No test command for {bs['name']}"}

    result = run_cmd(cmd, str(project_path), timeout=300)
    return {"check": "P4_Tests", "priority": "P4", "build_system": bs["name"], **result}


def check_p5_debug_artifacts(project_path: Path) -> Dict[str, Any]:
    """P5: Debug artifacts scan — console.log, print, TODO without ticket."""
    findings: List[Dict[str, str]] = []
    scanned = 0

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext not in CODE_EXTENSIONS:
                continue
            # Skip test files for debug artifact scanning
            if "test" in fname.lower() or "spec" in fname.lower():
                continue
            filepath = Path(root) / fname
            scanned += 1
            try:
                lines = filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue

            relpath = str(filepath.relative_to(project_path))
            for line_num, line in enumerate(lines, 1):
                for pattern, name in DEBUG_PATTERNS:
                    if re.search(pattern, line):
                        findings.append({
                            "file": relpath,
                            "line": str(line_num),
                            "type": "debug_artifact",
                            "name": name,
                            "severity": "medium",
                            "snippet": line.strip()[:100],
                        })

    return {
        "check": "P5_DebugArtifacts",
        "priority": "P5",
        "passed": len(findings) == 0,
        "scanned_files": scanned,
        "findings_count": len(findings),
        "findings": findings[:30],
    }


# =============================================================================
#  REPORT
# =============================================================================

def format_human_report(results: List[Dict], total_duration: float) -> str:
    """Format results as a human-readable report."""
    lines = [
        "",
        "=" * 60,
        "VERIFICATION REPORT".center(60),
        "=" * 60,
        "",
    ]

    # Summary table
    passed = sum(1 for r in results if r.get("passed") is True)
    failed = sum(1 for r in results if r.get("passed") is False)
    skipped = sum(1 for r in results if r.get("passed") is None or r.get("skipped"))

    lines.append(f"Total Duration: {total_duration:.1f}s")
    lines.append(f"Checks: {len(results)} total, {passed} passed, {failed} failed, {skipped} skipped")
    lines.append("")

    # Per-check details
    for r in results:
        if r.get("skipped") or r.get("passed") is None:
            icon = "⏭️ "
            label = "SKIP"
        elif r["passed"]:
            icon = "✅"
            label = "PASS"
        else:
            icon = "❌"
            label = "FAIL"

        duration = f" ({r.get('duration_s', 0):.1f}s)" if "duration_s" in r else ""
        check_name = r.get("check", "Unknown")
        lines.append(f"  {icon} [{label}] {check_name}{duration}")

        # Show failure details
        if r.get("passed") is False:
            if r.get("findings_count"):
                lines.append(f"       Findings: {r['findings_count']} (critical: {r.get('critical', 0)}, high: {r.get('high', 0)})")
            if r.get("stderr"):
                for err_line in r["stderr"].strip().splitlines()[:5]:
                    lines.append(f"       {err_line}")
        elif r.get("skipped"):
            lines.append(f"       Reason: {r.get('reason', 'N/A')}")

    lines.append("")

    # Verdict
    if failed > 0:
        lines.append(f"❌ VERIFICATION FAILED — {failed} check(s) need attention")
    else:
        lines.append("✅ ALL CHECKS PASSED — Ready for PR")

    lines.append("=" * 60)
    lines.append("")

    return "\n".join(lines)


# =============================================================================
#  MAIN
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stream Coding — Master Verification Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Priority levels:
  P0  Security scan (secrets, dangerous patterns)    — CRITICAL
  P1  Build verification                             — CRITICAL
  P2  Type check                                     — HIGH
  P3  Lint check                                     — HIGH
  P4  Test suite                                     — HIGH
  P5  Debug artifacts (console.log, TODO, print)     — MEDIUM

Examples:
  python verify.py .                          # Run all checks
  python verify.py . --priority P0            # Security only
  python verify.py . --priority P0,P1,P3      # Security + Build + Lint
  python verify.py . --json                   # JSON output
  python verify.py . --stop-on-fail           # Stop on first CRITICAL failure
""",
    )
    parser.add_argument("project", help="Project path to validate")
    parser.add_argument(
        "--priority", default="P0,P1,P2,P3,P4,P5",
        help="Comma-separated priority levels to run (default: all)",
    )
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")
    parser.add_argument("--stop-on-fail", action="store_true", help="Stop on first CRITICAL failure (P0/P1)")

    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    if not project_path.is_dir():
        msg = f"Error: Not a directory: {project_path}"
        if args.json_output:
            print(json.dumps({"error": msg}))
        else:
            print(msg, file=sys.stderr)
        return 2

    priorities = {p.strip().upper() for p in args.priority.split(",")}
    bs = detect_build_system(project_path)

    start = time.monotonic()
    results: List[Dict[str, Any]] = []

    checks = [
        ("P0", lambda: check_p0_security(project_path)),
        ("P1", lambda: check_p1_build(project_path, bs)),
        ("P2", lambda: check_p2_types(project_path, bs)),
        ("P3", lambda: check_p3_lint(project_path, bs)),
        ("P4", lambda: check_p4_tests(project_path, bs)),
        ("P5", lambda: check_p5_debug_artifacts(project_path)),
    ]

    for priority, check_fn in checks:
        if priority not in priorities:
            continue

        result = check_fn()
        results.append(result)

        # Stop on CRITICAL failure if requested
        if args.stop_on_fail and priority in ("P0", "P1") and result.get("passed") is False:
            break

    total_duration = round(time.monotonic() - start, 1)

    # Output
    if args.json_output:
        report = {
            "project": str(project_path),
            "build_system": bs["name"] if bs else None,
            "total_duration_s": total_duration,
            "results": results,
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.get("passed") is True),
                "failed": sum(1 for r in results if r.get("passed") is False),
                "skipped": sum(1 for r in results if r.get("passed") is None or r.get("skipped")),
            },
            "verdict": "PASS" if all(r.get("passed") is not False for r in results) else "FAIL",
        }
        print(json.dumps(report, indent=2))
    else:
        print(format_human_report(results, total_duration))

    # Exit code
    if any(r.get("passed") is False for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
