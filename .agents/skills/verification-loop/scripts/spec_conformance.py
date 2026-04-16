#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""
Stream Coding — Spec Conformance Checker
==========================================

Detects drift between specification documents and code by comparing
exported symbols, function signatures, API routes, and module structure
against what the spec describes.

This is a heuristic tool — it flags POTENTIAL divergence for human review.
It cannot prove conformance, only surface likely mismatches.

Usage:
    python spec_conformance.py <project_path>                           # Auto-detect
    python spec_conformance.py <project_path> --spec docs/spec.md       # Explicit spec
    python spec_conformance.py <project_path> --check exports           # Exports only
    python spec_conformance.py <project_path> --check routes            # Routes only
    python spec_conformance.py <project_path> --check files             # File presence only
    python spec_conformance.py <project_path> --json                    # JSON output
    python spec_conformance.py --help

Check Types:
    all       — Run all conformance checks (default)
    exports   — Verify exported symbols mentioned in spec exist in code
    routes    — Verify API routes mentioned in spec exist in code
    files     — Verify files/modules referenced in spec exist on disk

Exit Codes:
    0 — No divergence detected
    1 — Divergence detected (potential drift)
    2 — Invalid arguments or no spec found

Output: JSON to stdout when --json is used, human-readable otherwise.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# =============================================================================
#  CONFIGURATION
# =============================================================================

SKIP_DIRS = frozenset({
    "node_modules", ".git", "dist", "build", "__pycache__", ".venv", "venv",
    ".next", ".terraform", "vendor", "target", ".agents", ".agent",
    "coverage", ".nyc_output",
})

CODE_EXTENSIONS = frozenset({
    ".go", ".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".java",
    ".kt", ".kts", ".swift", ".php",
})

SPEC_EXTENSIONS = frozenset({".md", ".mdx"})
SPEC_DIRS = ["docs", "spec", "specs", "documentation"]


# =============================================================================
#  SPEC DISCOVERY
# =============================================================================

def find_spec_files(project_path: Path, explicit_spec: Optional[str] = None) -> List[Path]:
    """Find specification documents in the project."""
    if explicit_spec:
        spec_path = project_path / explicit_spec
        if spec_path.exists():
            return [spec_path]
        return []

    specs: List[Path] = []

    # Check known spec directories
    for spec_dir in SPEC_DIRS:
        d = project_path / spec_dir
        if d.is_dir():
            for f in d.rglob("*.md"):
                if f.name.startswith("."):
                    continue
                specs.append(f)

    # Check root-level spec-like files
    spec_names = {"SPEC.md", "SPECIFICATION.md", "DESIGN.md", "ARCHITECTURE.md", "API.md"}
    for f in project_path.iterdir():
        if f.name in spec_names or f.name.upper() in spec_names:
            specs.append(f)

    return specs


def read_spec_content(spec_files: List[Path]) -> str:
    """Read and concatenate all spec file contents."""
    parts = []
    for f in spec_files:
        try:
            parts.append(f.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return "\n\n".join(parts)


# =============================================================================
#  EXTRACTION: What the spec says should exist
# =============================================================================

def extract_spec_exports(spec_content: str) -> Set[str]:
    """Extract function/type/class names mentioned in spec as expected exports."""
    exports: Set[str] = set()

    # Patterns that suggest a symbol is being specified
    # func/function/def/class/type/interface/struct followed by name
    patterns = [
        r"(?:func|function|def|class|type|interface|struct|enum)\s+([A-Z][a-zA-Z0-9_]*)",
        # Backtick-quoted identifiers in markdown
        r"`([A-Z][a-zA-Z0-9_]*(?:\.[A-Z][a-zA-Z0-9_]*)?)`",
        # Table cells with PascalCase identifiers (likely type/function references)
        r"\|\s*`?([A-Z][a-zA-Z0-9_]+)`?\s*\|",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, spec_content):
            name = match.group(1)
            # Filter out common markdown/English words that happen to be PascalCase
            if name not in {"The", "This", "That", "When", "Where", "What", "How", "Why",
                           "Each", "Every", "Some", "None", "True", "False", "Yes", "No",
                           "API", "URL", "HTTP", "JSON", "SQL", "HTML", "CSS", "SDK",
                           "TODO", "FIXME", "NOTE", "IMPORTANT", "WARNING", "CAUTION",
                           "ERROR", "FAIL", "PASS", "SKIP", "OK"}:
                exports.add(name)

    return exports


def extract_spec_routes(spec_content: str) -> Set[str]:
    """Extract API routes mentioned in spec."""
    routes: Set[str] = set()

    # HTTP method + path patterns
    patterns = [
        r"(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(/[a-zA-Z0-9/_\-{}\.:]+)",
        r"`(?:GET|POST|PUT|PATCH|DELETE)\s+(/[a-zA-Z0-9/_\-{}\.:]+)`",
        r"(?:endpoint|route|path).*?(/[a-zA-Z0-9/_\-{}\.:]+)",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, spec_content, re.IGNORECASE):
            route = match.group(1).rstrip(".")
            if len(route) > 1:  # Skip bare "/"
                routes.add(route)

    return routes


def extract_spec_files(spec_content: str, project_path: Path) -> Set[str]:
    """Extract file paths mentioned in spec."""
    files: Set[str] = set()

    # File path patterns in backticks or after keywords
    patterns = [
        r"`([a-zA-Z0-9_\-./]+\.[a-z]{1,4})`",  # `path/to/file.ext`
        r"(?:file|module|source).*?([a-zA-Z0-9_\-./]+\.[a-z]{1,4})",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, spec_content):
            fpath = match.group(1)
            # Basic sanity: must have at least one letter and a dot
            if re.match(r"^[a-zA-Z].*\.[a-z]+$", fpath):
                # Skip common non-file references
                if not any(fpath.endswith(ext) for ext in [".com", ".org", ".io", ".dev", ".app"]):
                    files.add(fpath)

    return files


# =============================================================================
#  EXTRACTION: What the code actually has
# =============================================================================

def extract_code_exports(project_path: Path) -> Set[str]:
    """Extract exported symbols from code files."""
    exports: Set[str] = set()

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext not in CODE_EXTENSIONS:
                continue

            filepath = Path(root) / fname
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            # Language-specific export patterns
            if ext == ".go":
                # Go: exported = starts with uppercase
                for m in re.finditer(r"(?:func|type|var|const)\s+([A-Z][a-zA-Z0-9_]*)", content):
                    exports.add(m.group(1))
            elif ext in {".ts", ".tsx", ".js", ".jsx"}:
                # TypeScript/JavaScript: export keyword
                for m in re.finditer(r"export\s+(?:default\s+)?(?:function|class|const|let|var|type|interface|enum)\s+([a-zA-Z_][a-zA-Z0-9_]*)", content):
                    exports.add(m.group(1))
            elif ext == ".py":
                # Python: top-level functions and classes
                for m in re.finditer(r"^(?:def|class)\s+([a-zA-Z_][a-zA-Z0-9_]*)", content, re.MULTILINE):
                    exports.add(m.group(1))
            elif ext == ".rs":
                # Rust: pub items
                for m in re.finditer(r"pub\s+(?:fn|struct|enum|trait|type|const)\s+([a-zA-Z_][a-zA-Z0-9_]*)", content):
                    exports.add(m.group(1))
            elif ext == ".java":
                # Java: public classes and methods
                for m in re.finditer(r"public\s+(?:static\s+)?(?:class|interface|enum|[\w<>]+)\s+([A-Z][a-zA-Z0-9_]*)", content):
                    exports.add(m.group(1))

    return exports


def extract_code_routes(project_path: Path) -> Set[str]:
    """Extract API routes from code files."""
    routes: Set[str] = set()

    route_patterns = [
        # Express.js / Koa / Hono
        r'\.(?:get|post|put|patch|delete|all|use)\s*\(\s*["\'](/[^"\']*)["\']',
        # Go (Gin, Chi, mux)
        r'\.(?:GET|POST|PUT|PATCH|DELETE|Handle|HandleFunc)\s*\(\s*["\'](/[^"\']*)["\']',
        # Python (Flask, FastAPI)
        r'@(?:app|router|api)\.(?:get|post|put|patch|delete|route)\s*\(\s*["\'](/[^"\']*)["\']',
        # Generic path registration
        r'(?:route|path|endpoint)\s*[=:]\s*["\'](/[a-zA-Z0-9/_\-{}\.:]+)["\']',
    ]

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext not in CODE_EXTENSIONS:
                continue

            filepath = Path(root) / fname
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            for pattern in route_patterns:
                for m in re.finditer(pattern, content):
                    routes.add(m.group(1))

    return routes


# =============================================================================
#  CONFORMANCE CHECKS
# =============================================================================

def check_exports(spec_exports: Set[str], code_exports: Set[str]) -> Dict[str, Any]:
    """Check if exports mentioned in spec exist in code."""
    missing = spec_exports - code_exports
    extra = code_exports - spec_exports

    # Filter: only report missing spec exports (extra exports are OK — code can have more)
    findings = [{"symbol": s, "status": "missing_in_code"} for s in sorted(missing)]

    return {
        "check": "exports",
        "spec_count": len(spec_exports),
        "code_count": len(code_exports),
        "missing_in_code": len(missing),
        "divergence": len(missing) > 0,
        "findings": findings[:30],
    }


def check_routes(spec_routes: Set[str], code_routes: Set[str]) -> Dict[str, Any]:
    """Check if routes mentioned in spec exist in code."""
    # Normalize routes for comparison (strip trailing slashes, lowercase)
    normalize = lambda r: r.rstrip("/").lower()
    spec_norm = {normalize(r): r for r in spec_routes}
    code_norm = {normalize(r): r for r in code_routes}

    missing = set(spec_norm.keys()) - set(code_norm.keys())
    findings = [{"route": spec_norm[r], "status": "missing_in_code"} for r in sorted(missing)]

    return {
        "check": "routes",
        "spec_count": len(spec_routes),
        "code_count": len(code_routes),
        "missing_in_code": len(missing),
        "divergence": len(missing) > 0,
        "findings": findings[:20],
    }


def check_files(spec_files: Set[str], project_path: Path) -> Dict[str, Any]:
    """Check if files mentioned in spec exist on disk."""
    findings = []
    for f in sorted(spec_files):
        exists = (project_path / f).exists()
        if not exists:
            findings.append({"file": f, "status": "missing"})

    return {
        "check": "files",
        "spec_count": len(spec_files),
        "missing": len(findings),
        "divergence": len(findings) > 0,
        "findings": findings[:20],
    }


# =============================================================================
#  MAIN
# =============================================================================

def run_conformance(project_path: Path, spec_path: Optional[str] = None,
                    check_type: str = "all") -> Dict[str, Any]:
    """Run spec conformance checks."""
    # Find specs
    spec_files = find_spec_files(project_path, spec_path)
    if not spec_files:
        return {
            "project": str(project_path),
            "status": "NO_SPEC",
            "message": "No specification files found. Checked: docs/, spec/, SPEC.md, DESIGN.md, etc.",
            "checks": {},
        }

    spec_content = read_spec_content(spec_files)
    if len(spec_content.strip()) < 100:
        return {
            "project": str(project_path),
            "status": "EMPTY_SPEC",
            "message": "Specification files found but contain insufficient content",
            "spec_files": [str(f.relative_to(project_path)) for f in spec_files],
            "checks": {},
        }

    report: Dict[str, Any] = {
        "project": str(project_path),
        "spec_files": [str(f.relative_to(project_path)) for f in spec_files],
        "checks": {},
        "divergence_detected": False,
    }

    # Run requested checks
    if check_type in ("all", "exports"):
        spec_exports = extract_spec_exports(spec_content)
        code_exports = extract_code_exports(project_path)
        result = check_exports(spec_exports, code_exports)
        report["checks"]["exports"] = result
        if result["divergence"]:
            report["divergence_detected"] = True

    if check_type in ("all", "routes"):
        spec_routes = extract_spec_routes(spec_content)
        code_routes = extract_code_routes(project_path)
        result = check_routes(spec_routes, code_routes)
        report["checks"]["routes"] = result
        if result["divergence"]:
            report["divergence_detected"] = True

    if check_type in ("all", "files"):
        spec_files_refs = extract_spec_files(spec_content, project_path)
        result = check_files(spec_files_refs, project_path)
        report["checks"]["files"] = result
        if result["divergence"]:
            report["divergence_detected"] = True

    report["status"] = "DIVERGENCE" if report["divergence_detected"] else "CONFORMS"

    return report


def format_human(report: Dict[str, Any]) -> str:
    """Format report as human-readable text."""
    lines = [
        "",
        "=" * 60,
        "SPEC CONFORMANCE REPORT".center(60),
        "=" * 60,
        "",
        f"Project: {report['project']}",
        f"Status:  {report['status']}",
    ]

    if "spec_files" in report:
        lines.append(f"Specs:   {', '.join(report['spec_files'])}")

    if "message" in report:
        lines.append(f"Note:    {report['message']}")

    lines.append("")

    for check_name, check_result in report.get("checks", {}).items():
        diverges = check_result.get("divergence", False)
        icon = "❌" if diverges else "✅"
        lines.append(f"{icon} {check_name.upper()}")

        if check_name == "exports":
            lines.append(f"    Spec mentions: {check_result['spec_count']} symbols")
            lines.append(f"    Code exports:  {check_result['code_count']} symbols")
            lines.append(f"    Missing:       {check_result['missing_in_code']}")
        elif check_name == "routes":
            lines.append(f"    Spec routes:   {check_result['spec_count']}")
            lines.append(f"    Code routes:   {check_result['code_count']}")
            lines.append(f"    Missing:       {check_result['missing_in_code']}")
        elif check_name == "files":
            lines.append(f"    Spec refs:     {check_result['spec_count']}")
            lines.append(f"    Missing:       {check_result['missing']}")

        for finding in check_result.get("findings", [])[:10]:
            if "symbol" in finding:
                lines.append(f"    ⚠️  {finding['symbol']} — {finding['status']}")
            elif "route" in finding:
                lines.append(f"    ⚠️  {finding['route']} — {finding['status']}")
            elif "file" in finding:
                lines.append(f"    ⚠️  {finding['file']} — {finding['status']}")

        lines.append("")

    lines.extend(["=" * 60, ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stream Coding — Spec Conformance Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Check types:
  all       Run all conformance checks (default)
  exports   Verify exported symbols from spec exist in code
  routes    Verify API routes from spec exist in code
  files     Verify files referenced in spec exist on disk

Examples:
  python spec_conformance.py .                              # Auto-detect specs
  python spec_conformance.py . --spec docs/api-spec.md      # Explicit spec
  python spec_conformance.py . --check routes --json        # Routes only, JSON
""",
    )
    parser.add_argument("project", help="Project path to validate")
    parser.add_argument("--spec", default=None, help="Explicit path to spec file (relative to project)")
    parser.add_argument(
        "--check",
        choices=["all", "exports", "routes", "files"],
        default="all",
        help="Type of conformance check (default: all)",
    )
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")

    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    if not project_path.is_dir():
        msg = f"Error: Not a directory: {project_path}"
        if args.json_output:
            print(json.dumps({"error": msg}))
        else:
            print(msg, file=sys.stderr)
        return 2

    report = run_conformance(project_path, args.spec, args.check)

    if args.json_output:
        print(json.dumps(report, indent=2))
    else:
        print(format_human(report))

    # Exit code
    if report["status"] == "DIVERGENCE":
        return 1
    if report["status"] in ("NO_SPEC", "EMPTY_SPEC"):
        return 0  # Not a failure — just nothing to check
    return 0


if __name__ == "__main__":
    sys.exit(main())
