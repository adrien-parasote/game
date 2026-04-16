---
description: TDD cycle from the spec Test Case Specifications. RED → GREEN → REFACTOR. Tests come from the spec, not improvisation.
---

# /tdd — Test-Driven Development

> **Stream Coding reminder:** Tests are not invented — they are the **direct translation** of the Test Case Specifications from the implementation spec. If a test reveals unspecified behavior, the spec is incomplete, not the code buggy.

## Prerequisites

- [ ] The implementation spec contains Test Case Specifications
- [ ] The implementation plan (`/plan`) is confirmed

If no Test Case Specifications → the spec does not pass the Spec Gate. Return to 📋 SPEC.

## Process

### 0. Read testing constraints

1. Read the Testing section of `.agents/rules/<language>.md`
2. Identify the test framework, commands, and conventions
3. If `docs/CODEMAPS/` exists, read all `.md` files in it to understand module boundaries and dependencies — this scopes which test files to create and what cross-module interactions to mock

### 1. RED — Write the test (from spec)

For each Test Case in the spec:
1. Create the test file following language conventions
2. Translate the Test Case into a concrete assertion
3. Run the test → **it MUST fail**

If the test passes without implementation → the test is poorly written or trivial.

### 2. GREEN — Implement the minimum

Write only the code needed to pass the test. Nothing more.
- No "while we are at it"
- No optimization
- No refactoring

### 3. REFACTOR — Improve

Tests are green → improve the code:
- Remove duplication
- Improve names
- Extract helpers

**Tests MUST stay green.** If a test breaks during refactoring → revert the refactoring, not the test.

### 4. Verify coverage

Target: **80%+** on branches, functions, lines.

### 5. Divergence check

After each TDD cycle, verify:
- Does the implemented code exactly match the spec?
- Did unspecified behavior emerge?
- If yes → **return to spec** to document it, then continue

## Mandatory edge cases

The spec MUST cover these cases. If absent, the Spec Gate does not pass:

| Category | Examples |
|----------|----------|
| **Null/undefined** | Null input, missing property |
| **Empty** | Empty array, empty string, empty object |
| **Invalid types** | Wrong type passed, NaN, Infinity |
| **Boundaries** | Min/max, zero, negative, overflow |
| **I/O errors** | Network timeout, DB down, file not found |
| **Race conditions** | Concurrent calls, shared state |
| **Large volumes** | 10k+ items, large payloads |
| **Special characters** | Unicode, emoji, SQL chars, HTML entities |

## E2E Testing (Playwright / Selenium)

E2E tests cover **critical user flows**. They are specified in the spec (Test Cases section → Integration/E2E).

### When to write E2E

- New complete user flows (registration, purchase, onboarding)
- Changes to existing critical flows
- After a production bug on a browser flow

### Patterns

**Semantic locators (no fragile CSS):**
```
❌ page.click('.css-class-xyz')
✅ page.click('button:has-text("Submit")')
✅ page.click('[data-testid="submit-button"]')
```

**Page Object Model:**
```
class LoginPage {
  url = '/login'
  emailInput = '[data-testid="email-input"]'
  passwordInput = '[data-testid="password-input"]'
  submitButton = 'button:has-text("Sign in")'

  async login(page, email, password) {
    await page.goto(this.url)
    await page.fill(this.emailInput, email)
    await page.fill(this.passwordInput, password)
    await page.click(this.submitButton)
  }
}
```

**Explicit waits:**
```
❌ page.waitForTimeout(3000)
✅ page.waitForSelector('[data-testid="result"]')
✅ expect(page.locator('h1')).toContainText('Dashboard')
```

### Flaky Tests

- Retry 2x before declaring a failure
- If a test is flaky > 3 times → investigate root cause
- Capture screenshot + video on failure

### CI/CD

```yaml
- name: E2E Tests
  run: npx playwright test
  env:
    CI: true
- name: Upload Artifacts on Failure
  if: failure()
  uses: actions/upload-artifact@v4
  with:
    name: playwright-report
    path: playwright-report/
```

## Test Anti-Patterns

| ❌ Do Not | ✅ Do |
|-----------|------|
| Test implementation details | Test observable behavior |
| Tests that depend on each other | Independent tests (no shared state) |
| Weak assertions (`toBeTruthy`) | Specific assertions (`toBe(42)`) |
| No mocks on external dependencies | Mock everything outside the tested module |
| Test only the happy path | Test error paths as priority |
