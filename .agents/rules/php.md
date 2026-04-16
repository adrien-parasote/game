# PHP — Documentation Constraints

> The spec for a PHP project MUST cover these points.

## Standards

- **PSR-12** for formatting and naming conventions
- `declare(strict_types=1);` at the top of every application file
- Scalar type hints, return types, and typed properties everywhere

## Formatting (non-negotiable)

- **PHP-CS-Fixer** or **Laravel Pint** for formatting
- **PHPStan** or **Psalm** for static analysis
- Versioned Composer scripts — same commands locally and in CI

## Immutability

- Immutable DTOs and value objects for data crossing service boundaries
- `readonly` properties or immutable constructors for request/response payloads
- Arrays for simple maps — promote business structures to explicit classes

## Imports

- `use` statements for all referenced classes, interfaces, and traits
- Avoid global namespace unless explicit project convention

## Error Handling

- Exceptions for exceptional states — avoid `false`/`null` as hidden error channels
- Convert framework/request inputs into validated DTOs before domain logic

## Testing

- Coverage: 80%+

## Review Checklist (`/code-review`)

### CRITICAL — Security

- SQL injection: concatenation in queries → query builder or Eloquent/Doctrine
- XSS: `{!! $var !!}` (Blade unescaped) or `echo` without `htmlspecialchars`
- Command injection: input in `exec()`, `shell_exec()`, `system()`
- Path traversal: `file_get_contents($userInput)` without validation
- Unsafe deserialization: `unserialize()` on untrusted data → `json_decode()`
- `eval()` with external data
- Missing CSRF token on POST forms

### HIGH — Architecture

- Business logic in controllers → service/action classes
- Eloquent entities/models directly exposed in API → Resources/DTOs
- N+1 queries → `with()` (eager loading) or `load()`
- Missing transactions on multi-step operations → `DB::transaction()`

### HIGH — Error Handling

- Empty `catch (\Exception $e) {}`
- `false`/`null` as error channels → typed exceptions
- No input validation → Form Request or manual validation

### MEDIUM — Best Practices

- `var_dump()` / `dd()` left in production
- Missing strict typing: `declare(strict_types=1)`
- Properties without type hint
- `@` (error suppression operator) without justification

### Framework Checks

- **Laravel**: `with()` for eager loading, Form Requests for validation, Resources for API
- **Symfony**: autowiring, voters for authorization, Form types for validation

## Build & Lint Commands (`/build-fix`)

```bash
# Static analysis
./vendor/bin/phpstan analyse -l max src/ 2>&1
./vendor/bin/psalm 2>&1

# Format
./vendor/bin/php-cs-fixer fix --dry-run --diff
./vendor/bin/pint --test  # Laravel Pint

# Tests
./vendor/bin/phpunit --coverage-text
php artisan test  # Laravel

# Dependencies
composer audit
composer validate --strict
```
