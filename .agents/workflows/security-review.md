---
description: Full security audit. OWASP Top 10, secrets detection, input validation, dependency analysis. Blocks deployment if CRITICAL found.
---

# /security-review — Security Audit

## When to Use

- Before any production deployment
- When code touches authentication, authorization, or sensitive data
- When adding API endpoints
- Third-party service integration
- Periodic security review

## Stream Coding Integration

- **Stage:** 📋 SPEC (security requirements MUST be IN the spec) + ⚡ BUILD (verify code matches security spec)
- **Principle:** Security is specified in the Error Handling Matrix and Anti-Patterns of the spec. This workflow verifies conformance.
- **Golden Rule:** If a vulnerability stems from a spec gap → fix the spec, not just the code

## Pipeline

```
Phase IDENTIFY (parallel scans) → Phase FILTER (exclusions + scoring) → Phase REPORT (format + gate)
```

---

## Phase IDENTIFY — Scan for Raw Findings

Run all 4 scans. Steps 1-3 can run in parallel. Step 4 runs independently.

**Gate:** Collect ALL raw findings without filtering. Output: `Raw findings: [N] total`

### 1. Secrets scan

```bash
# Hardcoded secrets
rg -n "sk-|api_key|password|secret|token|apikey|api-key" \
  --include="*.ts" --include="*.js" --include="*.py" \
  --include="*.go" --include="*.java" --include="*.rs" \
  --include="*.kt" --include="*.swift" --include="*.php"

# Committed .env files
git ls-files | grep -E '\.env$|\.env\.local$|\.env\.prod'

# Private keys
rg -n "BEGIN (RSA |EC |DSA )?PRIVATE KEY"

# Tokens in URLs
rg -n "https?://[^/]*:[^@]*@"
```

### 2. Unicode and hidden payloads

```bash
# Zero-width Unicode characters (invisible injection)
rg -nP '[\x{200B}\x{200C}\x{200D}\x{2060}\x{FEFF}\x{202A}-\x{202E}]'

# Suspicious HTML comments
rg -n '<!--|<script|data:text/html|base64,' --include="*.md" --include="*.html"

# Homoglyphs in identifiers
rg -nP '[^\x00-\x7F]' --include="*.ts" --include="*.js" --include="*.py"
```

### 3. OWASP Top 10 Detection

| # | Risk | Detection Command |
|---|------|-------------------|
| 1 | SQL Injection | `rg -n "query\(.*\+\|query\(.*\$\{" --include="*.ts"` |
| 2 | Broken Auth | Verify JWT validation, session expiry, password hashing |
| 3 | Sensitive Data | `rg -n "console.log.*password\|console.log.*token"` |
| 4 | XXE | `rg -n "parseXML\|DOMParser\|xml2js"` |
| 5 | Broken Access | Verify auth middleware on every route |
| 6 | Misconfig | `rg -n "debug.*true\|DEBUG.*True"` in prod |
| 7 | XSS | `rg -n "innerHTML\|dangerouslySetInnerHTML\|v-html"` |
| 8 | Deserialization | `rg -n "JSON.parse\|pickle.loads\|yaml.load\b"` |
| 9 | Known Vulns | `npm audit` / `cargo audit` / `pip-audit` |
| 10 | Logging | Verify auth events are logged and alerts configured |

### 4. Dependency analysis

```bash
# Node.js
npm audit
npm outdated

# Python
pip-audit
safety check

# Go
govulncheck ./...

# Rust
cargo audit

# Java
./gradlew dependencyCheckAnalyze
```

---

## Phase FILTER — Eliminate Noise

Apply filters to every raw finding. Only findings with confidence ≥ 8/10 pass to Phase REPORT.

**Gate:** Output: `Filtered: [N] raw → [M] confirmed (confidence ≥ 8)`

### Hard Exclusions — Automatically exclude findings matching these patterns

| # | Exclusion | Rationale |
|---|-----------|-----------|
| 1 | Denial of Service (DoS) or resource exhaustion | Managed separately, not a code-level vuln |
| 2 | Secrets or credentials stored on disk if otherwise secured | Not actionable in code review |
| 3 | Rate limiting concerns or service overload | Infrastructure concern, not code |
| 4 | Memory consumption or CPU exhaustion | Performance, not security |
| 5 | Lack of input validation on non-security-critical fields without proven impact | Too speculative |
| 6 | GitHub Action workflow issues unless clearly triggerable via untrusted input | Most are not exploitable |
| 7 | Lack of hardening measures without concrete vulnerability | Not an actionable finding |
| 8 | Race conditions that are theoretical, not concretely problematic | Only report if concretely exploitable |
| 9 | Outdated third-party libraries | Managed by dependency audit (step 4) |
| 10 | Memory safety issues in memory-safe languages (Rust, Go, etc.) | Impossible by design |
| 11 | Findings in files that are only unit tests or test fixtures | Not production code |
| 12 | Log spoofing — outputting unsanitized user input to logs | Not a code vulnerability |
| 13 | SSRF where attacker only controls the path, not host or protocol | Not exploitable |
| 14 | User-controlled content in AI system prompts | By design, not a vuln |
| 15 | Regex injection — injecting untrusted content into a regex | Not a vulnerability |
| 16 | Regex DoS (ReDoS) | Covered by exclusion #1 |
| 17 | Findings in documentation files (markdown, etc.) | Not executable code |

### Precedents — Judgment rules for ambiguous cases

| # | Precedent |
|---|-----------|
| 1 | Logging high-value secrets in plaintext IS a vulnerability. Logging URLs is safe. |
| 2 | UUIDs are unguessable — no need to validate for brute-force risk. |
| 3 | Environment variables and CLI flags are trusted values. Attacks requiring control of env vars are invalid. |
| 4 | Resource management issues (memory/FD leaks) are not security vulnerabilities. |
| 5 | Subtle web vulns (tabnabbing, XS-Leaks, prototype pollution, open redirects) — only report if extremely high confidence. |
| 6 | React/Angular are generally safe from XSS. Only flag `dangerouslySetInnerHTML`, `bypassSecurityTrustHtml`, or equivalent. |
| 7 | Client-side JS/TS code does not need permission checks — the server is responsible for auth. |

### Confidence scoring

Assign a confidence score (1-10) to each finding:

| Score | Meaning | Action |
|-------|---------|--------|
| 9-10 | Certain exploit path identified | **Report** |
| 8 | Clear vulnerability pattern with known exploitation methods | **Report** |
| 7 | Suspicious pattern requiring specific conditions | **Do not report** (too speculative) |
| < 7 | Theoretical or speculative | **Do not report** |

### Signal quality — ask for each finding

1. Is there a concrete, exploitable vulnerability with a clear attack path?
2. Does this represent a real security risk vs theoretical best practice?
3. Are there specific code locations and reproduction steps?
4. Would this finding be actionable for a security team?

If ANY answer is "no" → exclude the finding.

---

## Phase REPORT — Format and Gate

Only confirmed findings (confidence ≥ 8) reach this phase.

### Security report

```
SECURITY REVIEW REPORT
======================

Phase IDENTIFY:
  Secrets:        [PASS/FAIL] (X found)
  Unicode:        [PASS/FAIL] (X suspicious)
  OWASP Checks:   [X/10 passed]
  Dependencies:   [PASS/FAIL] (X vulnerabilities)

Phase FILTER:
  Raw findings:   [N]
  Filtered out:   [M] (false positives, low confidence)
  Confirmed:      [N-M]

CRITICAL Issues:
1. [description, file:line, confidence: X/10, fix]

HIGH Issues:
1. [description, file:line, confidence: X/10, fix]

Spec Conformance: [Are specified protections implemented?]
Missing from Spec: [Risks detected but not specified]

Gate: [DEPLOY / BLOCK DEPLOY]
```

### Deployment gate

- **BLOCK** if: secrets found, CRITICAL vulnerabilities, injection detected
- **DEPLOY WITH NOTES** if: HIGH issues documented with accept/defer decision
- **DEPLOY** if: all checks pass
