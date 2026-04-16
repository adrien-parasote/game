# Python — Documentation Constraints

> The spec for a Python project MUST cover these points.

## Standards

- **PEP 8** for conventions
- **Type annotations** on all function signatures

## Formatting (non-negotiable)

- **black** for formatting
- **isort** for import sorting
- **ruff** for linting

## Immutability

The spec MUST specify immutable data structures:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class User:
    name: str
    email: str

from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float
```

## Mandatory Patterns in the Spec

| Pattern | When to document |
|---------|-----------------|
| **Protocol** (duck typing) | Interfaces/abstractions between modules |
| **Dataclasses** | All DTOs / value objects |
| **Context managers** | All resource management (files, connections) |
| **Generators** | Lazy evaluation, memory-efficient iteration |

```python
from typing import Protocol

class Repository(Protocol):
    def find_by_id(self, id: str) -> dict | None: ...
    def save(self, entity: dict) -> dict: ...
```

## Security

- **bandit** for static analysis: `bandit -r src/`
- Secrets via `os.environ` or `python-dotenv`
- Fail fast if variable missing: `os.environ["API_KEY"]` (raises `KeyError`)

## Testing

- Framework: **pytest**
- Categorization with `pytest.mark` (`@pytest.mark.unit`, `@pytest.mark.integration`)
- Coverage: `pytest --cov=src --cov-report=term-missing`
- Target: 80%+

## Review Checklist (`/code-review`)

### CRITICAL — Security

- SQL injection: f-strings in queries → parameterized queries
- Command injection: unvalidated input in `subprocess` → use `subprocess.run` with arg list
- Path traversal: user paths → `os.path.normpath`, reject `..`
- `eval()` / `exec()` with external data
- Unsafe deserialization (`pickle.load` on untrusted data)
- Weak crypto (MD5/SHA1 for security)
- `yaml.load()` without `Loader=SafeLoader`

### CRITICAL — Error Handling

- `except: pass` (bare except) → catch specific exceptions
- Silent exceptions
- Manual file/resource handling → `with` (context managers)

### HIGH — Type Hints

- Public functions without annotations
- `Any` when a specific type is possible
- Missing `Optional` for nullable parameters

### HIGH — Pythonic Patterns

- C-style loops → list/dict comprehensions
- `type() ==` → `isinstance()`
- Magic numbers → `Enum`
- String concatenation in a loop → `"".join()`
- **Mutable default arguments**: `def f(x=[])` → `def f(x=None)`

### HIGH — Concurrency

- Shared state without locks → `threading.Lock`
- Incorrect sync/async mixing
- N+1 queries in loops

### MEDIUM — Best Practices

- `print()` instead of `logging`
- `from module import *`
- `value == None` → `value is None`
- Shadowing builtins (`list`, `dict`, `str`)

### Framework Checks

- **Django**: `select_related`/`prefetch_related` for N+1, `atomic()`, migrations
- **FastAPI**: CORS config, Pydantic validation, response models, no blocking in async
- **Flask**: Error handlers, CSRF protection

## Build & Lint Commands (`/build-fix`)

```bash
# Type checking
mypy .

# Linting
ruff check .

# Format
black --check .

# Security
bandit -r src/

# Tests
pytest --cov=src --cov-report=term-missing
```
