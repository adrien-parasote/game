---
name: security-review
description: Activate when implementing authentication, handling user input, working with secrets, creating API endpoints, or implementing payment features. Enforces security rules and guides security audits.
---

# Security Review Skill

Auto-activated when security-sensitive context is detected. Ensures security constraints are enforced and guides the developer through security audits.

## When to Activate

### ALWAYS (proactive — activate automatically)

- New API endpoints or route changes
- Authentication or authorization code
- User input handling or file uploads
- Database query changes
- Payment or financial code
- External API integrations
- Dependency updates (`package.json`, `go.mod`, `Cargo.toml`, etc.)

### IMMEDIATELY (reactive — drop everything)

- Production security incidents
- Dependency CVE notifications
- User security reports
- Before major releases or deployments

## What This Skill Does

1. **Enforce** the security constraints from `.agents/rules/security.md`
2. **Flag** any code that matches the dangerous patterns listed in the rule
3. **Suggest** running `/security-review` workflow for a full audit when significant security-related changes are detected
4. **Verify** the spec includes security requirements (Error Handling Matrix, Anti-Patterns) before coding begins

## Automated Script

> **This skill includes an executable scanner** following the [agentskills.io](https://agentskills.io) standard.

```bash
# Full security scan (all 4 scanners, JSON output)
python .agents/skills/security-review/scripts/security_scan.py .

# Human-readable summary
python .agents/skills/security-review/scripts/security_scan.py . --output summary

# Scan specific category only
python .agents/skills/security-review/scripts/security_scan.py . --scan-type secrets
python .agents/skills/security-review/scripts/security_scan.py . --scan-type patterns
python .agents/skills/security-review/scripts/security_scan.py . --scan-type config
python .agents/skills/security-review/scripts/security_scan.py . --scan-type deps
```

### Scanner Coverage

| Scanner | OWASP | What It Catches |
|---------|-------|-----------------|
| `secrets` | A04/A07 | AWS keys, GCP SA keys, GitHub PATs, JWTs, DB URIs, hardcoded passwords |
| `patterns` | A03/A05/A08 | eval(), SQL injection, command injection, XSS, unsafe deserialization |
| `config` | A02/A05 | Debug mode, CORS wildcards, SSL disabled |
| `deps` | A06 | Missing lock files, npm audit, govulncheck |

> Exit code 0 = no critical/high findings. Exit code 1 = action required. Use `--help` for full options.

## Stream Coding Principle

> Security is SPECIFIED in the spec (Error Handling Matrix, Anti-Patterns). This skill verifies spec-to-code conformance on security.
> If a vulnerability comes from a spec gap → fix the spec, not just the code.

## Quick Reference

| Need | Where |
|------|-------|
| Security constraints & checklists | `.agents/rules/security.md` |
| Full security audit procedure | `/security-review` workflow |
| Pre-commit checklist | `.agents/rules/security.md` → "Mandatory Pre-Commit Checklist" |
| OWASP Top 10 verification | `.agents/rules/security.md` → "OWASP Top 10 — Spec Verification" |
| Dangerous patterns | `.agents/rules/security.md` → "Dangerous Patterns" |
| False positive filtering | `/security-review` workflow → Step 5 "False Positive Filtering" |
| Judgment precedents | `.agents/rules/security.md` → "Judgment Precedents" |
| Detection commands | `/security-review` workflow → Steps 1-4 |

## Finding Triage — Risk Prioritization

> **CVSS severity alone causes alert fatigue.** A "CRITICAL" CVSS finding in dead code is less urgent than a "HIGH" in your login handler. Use this matrix to prioritize based on **real-world exploitability**.

### Prioritization Matrix

| Priority | Criteria | Action | SLA |
|----------|----------|--------|-----|
| **P0 — Fix NOW** | Exploitable + Internet-facing + Contains sensitive data | Stop current work, fix immediately | Same session |
| **P1 — Fix before merge** | Exploitable + Used in production code paths | Fix before PR/commit | Same day |
| **P2 — Fix this sprint** | Exploitable but requires preconditions (auth, specific input) | Schedule fix, document risk | This week |
| **P3 — Track** | Theoretical risk, no known exploit path in this codebase | Create issue, accept risk explicitly | Backlog |
| **P4 — Won't fix** | False positive or acceptable risk (document WHY) | Document decision in ADR | N/A |

### Exploitability Questions

Before triaging a finding, answer these 3 questions:

| # | Question | If YES → | If NO → |
|---|----------|----------|---------|
| 1 | **Is the vulnerable code reachable from external input?** | +2 priority levels | -1 priority level |
| 2 | **Does it handle sensitive data?** (auth, PII, payments, secrets) | +1 priority level | No change |
| 3 | **Is there a known exploit in the wild?** (CVE with public PoC) | Automatic P0 | Use matrix above |

### Dependency Vulnerability Triage

For `npm audit` / `govulncheck` / dependency scanner findings:

```
1. Is the vulnerable dependency in your DIRECT dependencies? → Higher priority
2. Is the vulnerable code path actually CALLED by your code? → Check import chain
3. Is there a patched version available? → Update. If not → document + mitigate
4. Is it dev-only? (devDependencies, test scope) → Lower priority (P3-P4)
```

> **Anti-pattern:** Never blindly `npm audit fix --force`. This often introduces breaking changes. Triage first, update deliberately.

---

**Remember**: Security is not optional. One vulnerability compromises the entire platform. When in doubt, err on the side of caution.
