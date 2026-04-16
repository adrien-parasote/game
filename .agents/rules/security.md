# Security — Rules and Response Protocol

> Implementation specs touching auth, APIs, or sensitive data MUST pass this checklist. Referenced by `/code-review`, `/security-review` and integrated into the Spec Gate.

## Mandatory Pre-Commit Checklist

Before **every** commit:

- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs validated
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (HTML sanitized)
- [ ] CSRF protection enabled
- [ ] Authentication/authorization verified
- [ ] Rate limiting on all endpoints
- [ ] Error messages do not leak sensitive data

## Secret Management

- **NEVER** hardcode secrets in source code
- **ALWAYS** use environment variables or a secrets manager
- Validate required secrets are present at startup
- Immediately rotate any potentially exposed secret
- `.env.local` in `.gitignore`

## OWASP Top 10 — Spec Verification

| # | Risk | Does the spec address this? |
|---|------|---------------------------|
| 1 | **Injection** | Are queries parameterized? Is the ORM safe? |
| 2 | **Broken Authentication** | Is hashing specified (bcrypt/argon2/scrypt)? JWT validated server-side? Sessions expired? |
| 3 | **Sensitive Data Exposure** | HTTPS required? Secrets in env vars? PII encrypted at rest? Logs sanitized? |
| 4 | **XXE** | Is XML parsing mentioned and secured (external entities disabled)? |
| 5 | **Broken Access Control** | Auth checked on every route? CORS configured restrictively? |
| 6 | **Security Misconfiguration** | Prod configs differentiated? Default credentials changed? Debug off in prod? |
| 7 | **XSS** | Output systematically escaped? CSP headers? Framework auto-escaping? |
| 8 | **Insecure Deserialization** | Deserialized inputs validated with schema (Zod, JSON Schema)? |
| 9 | **Known Vulnerabilities** | Dependency audit planned (`npm audit`, `cargo audit`, `pip-audit`)? |
| 10 | **Insufficient Logging** | Security events listed and logged? Alerts configured? |

## Dangerous Patterns — The spec MUST explicitly forbid these

| Pattern | Severity | Fix |
|---------|----------|-----|
| Hardcoded secrets (API keys, passwords, tokens) | CRITICAL | Use `process.env` / secrets manager |
| Shell command with user input (`exec`, `spawn`) | CRITICAL | Use safe APIs or `execFile` with allowlist |
| String-concatenated SQL | CRITICAL | Parameterized queries / ORM |
| Plaintext password comparison | CRITICAL | Use `bcrypt.compare()` / argon2 |
| No auth check on route | CRITICAL | Add authentication middleware |
| Balance/inventory check without lock | CRITICAL | Use `FOR UPDATE` in transaction |
| `innerHTML` / `dangerouslySetInnerHTML` with user input | HIGH | Use `textContent` or DOMPurify |
| `fetch(userProvidedUrl)` / SSRF | HIGH | Whitelist allowed domains |
| `JSON.parse()` on raw input without schema | HIGH | Schema validation first (Zod, JSON Schema) |
| No rate limiting on public endpoints | HIGH | Add rate limiter (express-rate-limit, etc.) |
| Logs with tokens/passwords/PII | MEDIUM | Redaction/masking |
| Catch-all `catch(e) {}` empty | MEDIUM | Log + handle specifically |
| Missing timeout on external calls | MEDIUM | Explicit timeout specified |

## Common False Positives

Verify context before flagging:

| Finding | When NOT to flag |
|---------|-----------------|
| Credentials in `.env.example` | Example placeholders, not actual secrets |
| Test credentials in test files | Clearly marked as test-only (`test-api-key`, `password123`) |
| Public API keys | Keys explicitly designed to be public (e.g., Stripe publishable key) |
| SHA256/MD5 usage | Used for checksums or content hashing, NOT for password storage |
| `eval()` in build tools | Build-time code generation, not runtime user input |
| Hardcoded URLs | Public API base URLs, not credentials |
| DoS / resource exhaustion patterns | Infrastructure-level concern, not a code vulnerability |
| Memory safety in Rust/Go | Impossible by design in memory-safe languages |
| Findings in test-only files | Unit tests and fixtures are not production code |
| Log spoofing (unsanitized user input in logs) | Not a security vulnerability |
| SSRF with path-only control | Only flag if attacker controls host or protocol |
| Regex injection | Injecting untrusted content into a regex is not a vulnerability |
| Input validation on non-security fields | Only flag if proven security impact exists |
| GitHub Actions workflow issues | Only flag if clearly triggerable via untrusted input |
| Lack of hardening measures | Not a vulnerability without a concrete exploit path |
| Race conditions (theoretical) | Only flag if concretely exploitable, not theoretical |
| Documentation files (markdown, etc.) | Not executable code — never a vulnerability |

### Judgment Precedents

| # | Precedent |
|---|-----------|
| 1 | Logging high-value secrets in plaintext IS a vulnerability. Logging URLs is safe. |
| 2 | UUIDs are unguessable — no need to validate for brute-force risk. |
| 3 | Environment variables and CLI flags are trusted values. Attacks requiring env var control are invalid. |
| 4 | Resource management issues (memory/FD leaks) are not security vulnerabilities. |
| 5 | Subtle web vulns (tabnabbing, XS-Leaks, prototype pollution, open redirects) — only report if extremely high confidence. |
| 6 | React/Angular are generally safe from XSS. Only flag `dangerouslySetInnerHTML`, `bypassSecurityTrustHtml`, or equivalent. |
| 7 | Client-side JS/TS code does not need permission checks — the server is responsible for auth. |

## Detection

For detection commands (secrets, Unicode, OWASP), run the `/security-review` workflow.

## Security Response Protocol

If a security issue is detected:

1. **STOP** current work immediately
2. **Document** the vulnerability with a detailed report (file, line, severity, impact)
3. Run `/security-review` for full audit — check for similar patterns across the codebase
4. Fix **CRITICAL** issues before continuing any other work
5. **Rotate** any potentially exposed secret immediately
6. **Verify** the remediation works (test the fix, not just the code)

### Severity escalation

| Severity | Action | Timeline |
|----------|--------|----------|
| CRITICAL | Stop all work, fix immediately, rotate secrets | Now |
| HIGH | Fix before next merge/deploy | Same session |
| MEDIUM | Document, schedule fix | Next sprint |

## Success Metrics

A security review is complete when:

- [ ] Zero CRITICAL issues remaining
- [ ] All HIGH issues addressed or explicitly accepted with documented risk
- [ ] No secrets in source code
- [ ] Dependencies audit clean (`npm audit` / `cargo audit` / `pip-audit`)
- [ ] Security checklist from pre-commit section fully passing

## Usage

- **At Spec Gate**: verify the implementation spec covers these points
- **At `/code-review`**: verify the code implements the specified protections
- **In `/plan`**: identify steps with security risk
- **Pre-deployment**: run the full checklist
