#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""
Stream Coding — Security Scanner
==================================

Validates security principles from the security-review skill.
Scans for secrets, dangerous code patterns, configuration issues,
and supply chain risks.

Usage:
    python security_scan.py <project_path>                            # Full scan
    python security_scan.py <project_path> --scan-type secrets        # Secrets only
    python security_scan.py <project_path> --scan-type patterns       # Dangerous code only
    python security_scan.py <project_path> --scan-type config         # Config issues only
    python security_scan.py <project_path> --scan-type deps           # Dependency audit
    python security_scan.py <project_path> --output summary           # Human-readable
    python security_scan.py --help

Scan Types:
    all       — Run every scanner (default)
    secrets   — Hardcoded credentials, API keys, tokens (OWASP A04)
    patterns  — Dangerous code patterns, injection vectors (OWASP A03/A05)
    config    — Insecure configuration, debug modes (OWASP A02)
    deps      — Dependency audit, lock file verification (OWASP A06)

Exit Codes:
    0 — No critical or high findings
    1 — Critical or high findings detected
    2 — Invalid arguments

Output: JSON to stdout by default.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


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
    ".tf", ".hcl", ".rb",
})

CONFIG_EXTENSIONS = frozenset({
    ".json", ".yaml", ".yml", ".toml", ".env", ".ini", ".cfg",
})

CONFIG_FILENAMES = frozenset({
    ".env", ".env.local", ".env.development", ".env.production",
    ".env.staging", ".env.test",
})


# --- Secrets (OWASP A04: Insecure Design / A07: Identification Failures) ---

SECRET_PATTERNS: List[Tuple[str, str, str]] = [
    # Cloud Credentials
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID", "critical"),
    (r"(?:aws[_-]?)?secret[_-]?access[_-]?key\s*[=:]\s*[\"'][^\"']{10,}[\"']",
     "AWS Secret Access Key", "critical"),
    (r"-----BEGIN\s+(?:RSA|PRIVATE|EC|OPENSSH)\s+KEY-----", "Private Key", "critical"),
    (r"(?:mongodb|postgres(?:ql)?|mysql|redis|amqp):\/\/[^\s\"']+",
     "Database Connection String", "critical"),

    # Platform tokens
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token", "critical"),
    (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth Token", "critical"),
    (r"ghs_[a-zA-Z0-9]{36}", "GitHub Server Token", "critical"),
    (r"glpat-[a-zA-Z0-9\-_]{20,}", "GitLab PAT", "critical"),
    (r"sk-[a-zA-Z0-9]{32,}", "OpenAI/Stripe Secret Key", "critical"),
    (r"xox[bpsa]-[a-zA-Z0-9\-]+", "Slack Token", "critical"),
    (r"SG\.[a-zA-Z0-9\-_]{22}\.[a-zA-Z0-9\-_]{43}", "SendGrid API Key", "critical"),

    # GCP
    (r"\"type\"\s*:\s*\"service_account\"", "GCP Service Account Key File", "critical"),
    (r"AIza[0-9A-Za-z\-_]{35}", "Google API Key", "high"),

    # Generic secrets
    (r"(?:api[_-]?key|apikey)\s*[=:]\s*[\"'][^\"']{10,}[\"']", "API Key", "high"),
    (r"(?:secret|password|passwd|pwd)\s*[=:]\s*[\"'][^\"']{4,}[\"']",
     "Hardcoded Secret/Password", "high"),
    (r"bearer\s+[a-zA-Z0-9\-_.]{20,}", "Bearer Token", "high"),

    # JWT
    (r"eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+", "JWT Token", "high"),

    # SSH
    (r"ssh-(?:rsa|ed25519|ecdsa)\s+[A-Za-z0-9+/]{100,}", "SSH Key (embedded)", "medium"),
]


# --- Dangerous Code Patterns (OWASP A03: Injection / A05: Security Misconfiguration) ---

DANGEROUS_PATTERNS: List[Tuple[str, str, str, str]] = [
    # Code injection
    (r"\beval\s*\(", "eval() usage", "critical", "Code Injection (OWASP A03)"),
    (r"\bexec\s*\((?!ute)", "exec() usage", "high", "Code Injection (OWASP A03)"),
    (r"new\s+Function\s*\(", "Function constructor", "high", "Code Injection (OWASP A03)"),

    # Command injection
    (r"child_process\.exec\s*\(", "child_process.exec()", "high", "Command Injection (OWASP A03)"),
    (r"subprocess\.(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True",
     "subprocess with shell=True", "high", "Command Injection (OWASP A03)"),
    (r"os\.system\s*\(", "os.system()", "high", "Command Injection (OWASP A03)"),

    # XSS
    (r"dangerouslySetInnerHTML", "dangerouslySetInnerHTML", "high", "XSS (OWASP A03)"),
    (r"\.innerHTML\s*=", "innerHTML assignment", "medium", "XSS (OWASP A03)"),
    (r"document\.write\s*\(", "document.write()", "medium", "XSS (OWASP A03)"),

    # SQL injection
    (r"""[\"'][^\"']*\+\s*\w+\s*\+\s*[\"'].*(?:SELECT|INSERT|UPDATE|DELETE)""",
     "SQL String Concatenation", "critical", "SQL Injection (OWASP A03)"),
    (r'f"[^"]*(?:SELECT|INSERT|UPDATE|DELETE)[^"]*\{',
     "SQL f-string interpolation", "critical", "SQL Injection (OWASP A03)"),
    (r"fmt\.Sprintf\s*\([^)]*(?:SELECT|INSERT|UPDATE|DELETE)",
     "SQL Sprintf (Go)", "critical", "SQL Injection (OWASP A03)"),

    # Unsafe deserialization (OWASP A08)
    (r"pickle\.loads?\s*\(", "pickle deserialization", "high", "Deserialization (OWASP A08)"),
    (r"yaml\.load\s*\([^)]*\)(?!\s*,\s*Loader)", "Unsafe YAML load", "high", "Deserialization (OWASP A08)"),
    (r"marshal\.Unmarshal\s*\([^)]*interface\{\}", "Unsafe Go unmarshal to interface{}",
     "medium", "Deserialization (OWASP A08)"),

    # TLS/SSL
    (r"verify\s*=\s*False", "SSL verification disabled", "high", "MITM (OWASP A02)"),
    (r"InsecureSkipVerify\s*:\s*true", "Go TLS skip verify", "high", "MITM (OWASP A02)"),
    (r"--insecure\b", "Insecure flag in use", "medium", "Security Disabled (OWASP A02)"),
    (r"disable[_-]?ssl", "SSL disabled", "high", "MITM (OWASP A02)"),

    # Path traversal
    (r"os\.path\.join\s*\([^)]*request\.", "Path join with user input", "high",
     "Path Traversal (OWASP A01)"),
    (r"filepath\.Join\s*\([^)]*r\.\w+", "Go filepath with request input", "high",
     "Path Traversal (OWASP A01)"),
]


# --- Configuration Issues (OWASP A05: Security Misconfiguration) ---

CONFIG_ISSUES: List[Tuple[str, str, str]] = [
    (r'"DEBUG"\s*:\s*true', "Debug mode enabled in config", "high"),
    (r"debug\s*=\s*True", "Python debug mode enabled", "high"),
    (r"NODE_ENV.*development", "Development mode in config", "medium"),
    (r'"Access-Control-Allow-Origin"\s*:\s*"\*"', "CORS wildcard origin", "high"),
    (r"CORS_ALLOW_ALL.*true", "CORS allow all origins", "high"),
    (r"AllowAllOrigins\s*:\s*true", "Go CORS allow all", "high"),
    (r"allowCredentials.*true.*origin.*\*", "Dangerous CORS combo (credentials + wildcard)", "critical"),
    (r"GIN_MODE.*debug", "Gin debug mode in config", "medium"),
]


# =============================================================================
#  SCANNERS
# =============================================================================

def _walk_files(project_path: Path, extensions: frozenset, include_filenames: frozenset = frozenset()):
    """Yield (filepath, relpath) for matching files, skipping excluded dirs."""
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext in extensions or fname in include_filenames:
                filepath = Path(root) / fname
                yield filepath, str(filepath.relative_to(project_path))


def scan_secrets(project_path: Path) -> Dict[str, Any]:
    """Scan for hardcoded secrets (OWASP A04/A07)."""
    findings: List[Dict] = []
    scanned = 0
    severity_counts = {"critical": 0, "high": 0, "medium": 0}

    for filepath, relpath in _walk_files(project_path, CODE_EXTENSIONS | CONFIG_EXTENSIONS, CONFIG_FILENAMES):
        scanned += 1
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for pattern, name, severity in SECRET_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[:match.start()].count("\n") + 1
                findings.append({
                    "file": relpath,
                    "line": line_num,
                    "type": name,
                    "severity": severity,
                    "match_preview": match.group(0)[:30] + "..." if len(match.group(0)) > 30 else match.group(0),
                })
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

    status = "PASS"
    if severity_counts["critical"] > 0:
        status = "CRITICAL"
    elif severity_counts["high"] > 0:
        status = "HIGH"
    elif sum(severity_counts.values()) > 0:
        status = "REVIEW"

    return {
        "scanner": "secrets",
        "owasp": "A04/A07",
        "status": status,
        "scanned_files": scanned,
        "findings_count": len(findings),
        "by_severity": severity_counts,
        "findings": findings[:20],
    }


def scan_patterns(project_path: Path) -> Dict[str, Any]:
    """Scan for dangerous code patterns (OWASP A03/A05)."""
    findings: List[Dict] = []
    scanned = 0
    by_category: Dict[str, int] = {}

    for filepath, relpath in _walk_files(project_path, CODE_EXTENSIONS):
        scanned += 1
        try:
            lines = filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for line_num, line in enumerate(lines, 1):
            for pattern, name, severity, category in DANGEROUS_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append({
                        "file": relpath,
                        "line": line_num,
                        "pattern": name,
                        "severity": severity,
                        "category": category,
                        "snippet": line.strip()[:100],
                    })
                    by_category[category] = by_category.get(category, 0) + 1

    critical = sum(1 for f in findings if f["severity"] == "critical")
    high = sum(1 for f in findings if f["severity"] == "high")

    status = "PASS"
    if critical > 0:
        status = "CRITICAL"
    elif high > 0:
        status = "HIGH"
    elif findings:
        status = "REVIEW"

    return {
        "scanner": "patterns",
        "owasp": "A03/A05/A08",
        "status": status,
        "scanned_files": scanned,
        "findings_count": len(findings),
        "critical": critical,
        "high": high,
        "by_category": by_category,
        "findings": findings[:25],
    }


def scan_config(project_path: Path) -> Dict[str, Any]:
    """Scan for insecure configurations (OWASP A02/A05)."""
    findings: List[Dict] = []

    for filepath, relpath in _walk_files(project_path, CONFIG_EXTENSIONS, CONFIG_FILENAMES):
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for pattern, issue, severity in CONFIG_ISSUES:
            if re.search(pattern, content, re.IGNORECASE):
                findings.append({
                    "file": relpath,
                    "issue": issue,
                    "severity": severity,
                })

    critical = sum(1 for f in findings if f["severity"] == "critical")
    high = sum(1 for f in findings if f["severity"] == "high")

    status = "PASS"
    if critical > 0:
        status = "CRITICAL"
    elif high > 0:
        status = "HIGH"
    elif findings:
        status = "REVIEW"

    return {
        "scanner": "config",
        "owasp": "A02/A05",
        "status": status,
        "findings_count": len(findings),
        "critical": critical,
        "high": high,
        "findings": findings,
    }


def scan_deps(project_path: Path) -> Dict[str, Any]:
    """Scan for dependency/supply chain issues (OWASP A06)."""
    findings: List[Dict] = []
    checks: Dict[str, Any] = {}

    # Check lock files
    lock_map = {
        "package.json": {"npm": ["package-lock.json", "npm-shrinkwrap.json"],
                          "yarn": ["yarn.lock"], "pnpm": ["pnpm-lock.yaml"]},
        "go.mod": {"go": ["go.sum"]},
        "Cargo.toml": {"cargo": ["Cargo.lock"]},
        "pyproject.toml": {"python": ["poetry.lock", "uv.lock", "pdm.lock"]},
        "requirements.txt": {"pip": ["requirements.txt"]},  # Self-locks
    }

    for pkg_file, managers in lock_map.items():
        if (project_path / pkg_file).exists():
            for manager, lock_files in managers.items():
                has_lock = any((project_path / lf).exists() for lf in lock_files)
                checks[f"{manager}_lock_file"] = has_lock
                if not has_lock:
                    findings.append({
                        "type": "missing_lock_file",
                        "manager": manager,
                        "severity": "high",
                        "message": f"{manager}: No lock file found — supply chain integrity at risk",
                    })

    # Run npm audit if applicable
    if (project_path / "package.json").exists():
        try:
            result = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=str(project_path),
                capture_output=True,
                text=True,
                timeout=60,
            )
            try:
                audit = json.loads(result.stdout)
                vulns = audit.get("vulnerabilities", {})
                sev_counts = {"critical": 0, "high": 0, "moderate": 0, "low": 0}
                for v in vulns.values():
                    s = v.get("severity", "low").lower()
                    if s in sev_counts:
                        sev_counts[s] += 1

                checks["npm_audit"] = sev_counts
                if sev_counts["critical"] > 0:
                    findings.append({
                        "type": "npm_audit",
                        "severity": "critical",
                        "message": f"{sev_counts['critical']} critical vulnerabilities in npm dependencies",
                    })
                elif sev_counts["high"] > 0:
                    findings.append({
                        "type": "npm_audit",
                        "severity": "high",
                        "message": f"{sev_counts['high']} high severity vulnerabilities",
                    })
            except json.JSONDecodeError:
                checks["npm_audit"] = "parse_error"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            checks["npm_audit"] = "not_available"

    # Run go vuln check if applicable
    if (project_path / "go.mod").exists():
        try:
            result = subprocess.run(
                ["govulncheck", "./..."],
                cwd=str(project_path),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0 and "Vulnerability" in result.stdout:
                findings.append({
                    "type": "govulncheck",
                    "severity": "high",
                    "message": "Go vulnerability check found issues",
                    "details": result.stdout[:500],
                })
            checks["govulncheck"] = "passed" if result.returncode == 0 else "issues_found"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            checks["govulncheck"] = "not_available"

    critical = sum(1 for f in findings if f["severity"] == "critical")
    high = sum(1 for f in findings if f["severity"] == "high")

    status = "PASS"
    if critical > 0:
        status = "CRITICAL"
    elif high > 0:
        status = "HIGH"
    elif findings:
        status = "REVIEW"

    return {
        "scanner": "deps",
        "owasp": "A06",
        "status": status,
        "findings_count": len(findings),
        "critical": critical,
        "high": high,
        "checks": checks,
        "findings": findings,
    }


# =============================================================================
#  MAIN
# =============================================================================

def run_full_scan(project_path: Path, scan_type: str = "all") -> Dict[str, Any]:
    """Execute the requested security scans and produce a unified report."""
    report: Dict[str, Any] = {
        "project": str(project_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scan_type": scan_type,
        "scans": {},
        "summary": {
            "total_findings": 0,
            "critical": 0,
            "high": 0,
            "status": "PASS",
        },
    }

    scanners = {
        "secrets": scan_secrets,
        "patterns": scan_patterns,
        "config": scan_config,
        "deps": scan_deps,
    }

    for key, scanner_fn in scanners.items():
        if scan_type == "all" or scan_type == key:
            result = scanner_fn(project_path)
            report["scans"][key] = result

            report["summary"]["total_findings"] += result.get("findings_count", 0)
            report["summary"]["critical"] += result.get("critical", 0)
            report["summary"]["high"] += result.get("high", 0)

            # For secrets scanner, use by_severity counts
            if key == "secrets" and "by_severity" in result:
                report["summary"]["critical"] += result["by_severity"].get("critical", 0)
                report["summary"]["high"] += result["by_severity"].get("high", 0)
                # Avoid double-counting
                report["summary"]["critical"] -= result.get("critical", 0)
                report["summary"]["high"] -= result.get("high", 0)

    # Overall status
    if report["summary"]["critical"] > 0:
        report["summary"]["status"] = "CRITICAL"
    elif report["summary"]["high"] > 0:
        report["summary"]["status"] = "HIGH"
    elif report["summary"]["total_findings"] > 0:
        report["summary"]["status"] = "REVIEW"

    return report


def format_summary(report: Dict[str, Any]) -> str:
    """Format report as human-readable summary."""
    lines = [
        "",
        "=" * 60,
        "SECURITY SCAN REPORT".center(60),
        "=" * 60,
        "",
        f"Project:  {report['project']}",
        f"Time:     {report['timestamp']}",
        f"Scope:    {report['scan_type']}",
        "",
        f"Status:   {report['summary']['status']}",
        f"Findings: {report['summary']['total_findings']} total",
        f"  Critical: {report['summary']['critical']}",
        f"  High:     {report['summary']['high']}",
        "",
    ]

    for scan_name, scan_result in report["scans"].items():
        icon = "✅" if scan_result["status"] == "PASS" else "❌"
        lines.append(f"{icon} {scan_name.upper()} [{scan_result.get('owasp', '')}]: {scan_result['status']}")
        for finding in scan_result.get("findings", [])[:5]:
            if "file" in finding:
                lines.append(f"    - [{finding.get('severity', '?')}] {finding['file']}:{finding.get('line', '?')} — {finding.get('type', finding.get('pattern', finding.get('issue', '?')))}")
            else:
                lines.append(f"    - [{finding.get('severity', '?')}] {finding.get('message', finding.get('type', '?'))}")
        remaining = scan_result.get("findings_count", 0) - 5
        if remaining > 0:
            lines.append(f"    ... and {remaining} more")

    lines.extend(["", "=" * 60, ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stream Coding — Security Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scan types:
  all       Run all scanners (default)
  secrets   Hardcoded credentials, API keys, tokens     (OWASP A04/A07)
  patterns  Dangerous code patterns, injection vectors   (OWASP A03/A05/A08)
  config    Insecure configuration, debug modes          (OWASP A02/A05)
  deps      Dependency audit, lock file verification     (OWASP A06)

Examples:
  python security_scan.py .                       # Full scan, JSON output
  python security_scan.py . --output summary      # Human-readable
  python security_scan.py . --scan-type secrets   # Secrets only
""",
    )
    parser.add_argument("project_path", nargs="?", default=".", help="Project directory to scan")
    parser.add_argument(
        "--scan-type",
        choices=["all", "secrets", "patterns", "config", "deps"],
        default="all",
        help="Type of scan to run (default: all)",
    )
    parser.add_argument(
        "--output",
        choices=["json", "summary"],
        default="json",
        help="Output format (default: json)",
    )

    args = parser.parse_args()

    project_path = Path(args.project_path).resolve()
    if not project_path.is_dir():
        error = {"error": f"Not a directory: {project_path}"}
        if args.output == "json":
            print(json.dumps(error))
        else:
            print(f"Error: {error['error']}", file=sys.stderr)
        return 2

    report = run_full_scan(project_path, args.scan_type)

    if args.output == "summary":
        print(format_summary(report))
    else:
        print(json.dumps(report, indent=2))

    # Exit code: 1 if any critical or high findings
    if report["summary"]["critical"] > 0 or report["summary"]["high"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
