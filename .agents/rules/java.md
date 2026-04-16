# Java — Documentation Constraints

> The spec for a Java project MUST cover these points.

## Formatting (non-negotiable)

- **google-java-format** or **Checkstyle** (Google/Sun style)
- Member ordering: constants, fields, constructors, public methods, protected, private

## Immutability

- `record` for value types (Java 16+)
- `final` on fields by default — mutable only if required
- Defensive copies in public APIs: `List.copyOf()`, `Map.copyOf()`
- Copy-on-write: return new instances, don't mutate

```java
// GOOD — the spec must specify record for DTOs
public record OrderSummary(Long id, String customerName, BigDecimal total) {}

// GOOD — final + defensive copy
public class Order {
    private final List<LineItem> items;
    public List<LineItem> getItems() { return List.copyOf(items); }
}
```

## Modern Java (the spec MUST specify the minimum version)

| Feature | Version | Usage |
|---------|---------|-------|
| **Records** | 16+ | DTOs, value types |
| **Sealed classes** | 17+ | Closed type hierarchies |
| **Pattern matching instanceof** | 16+ | No explicit cast |
| **Text blocks** | 15+ | SQL, multi-line JSON templates |
| **Switch expressions** | 14+ | Arrow syntax |
| **Pattern matching in switch** | 21+ | Exhaustive handling of sealed types |

## Mandatory Patterns in the Spec

| Pattern | When to document |
|---------|-----------------|
| **Constructor injection** | Any service with dependencies (never field injection) |
| **Repository interface** | All data access |
| **Service layer** | Business logic (thin controllers and repos) |
| **Builder** | Objects with many optional params |
| **Records as DTOs** | Mapping at service/controller boundary |
| **Sealed types** | Closed states/results (`PaymentResult`) |

```java
// Constructor injection (NEVER field injection @Autowired/@Inject)
public class NotificationService {
    private final EmailSender emailSender;
    public NotificationService(EmailSender emailSender) { this.emailSender = emailSender; }
}
```

## Optional

- Return `Optional<T>` for finders without guaranteed result
- `map()`, `flatMap()`, `orElseThrow()` — never `get()` without `isPresent()`
- **Never** `Optional` as parameter or field

## Error Handling

- Unchecked domain exceptions (`extends RuntimeException`)
- No broad `catch (Exception e)` except in top-level handlers
- Context in exception messages

## Streams

- Short pipelines: 3-4 operations max
- Method references when readable: `.map(Order::getTotal)`
- No side effects in stream operations
- Complex logic → loop, not contorted stream

## Testing

- Coverage: 80%+

## Review Checklist (`/code-review`)

### CRITICAL — Security

- SQL injection: concatenation in `@Query` or `JdbcTemplate` → bind parameters (`:param` or `?`)
- Command injection: input in `ProcessBuilder` / `Runtime.exec()`
- Code injection: input in `ScriptEngine.eval()`
- Path traversal: `new File(userInput)` without `getCanonicalPath()` validation
- `@RequestBody` without `@Valid` → never trust unvalidated inputs
- PII/tokens in logs
- CSRF disabled without documented justification

### CRITICAL — Error Handling

- Empty catches: `catch (Exception e) {}`
- `.get()` on Optional without `.isPresent()` → `.orElseThrow()`
- Scattered exception handling → centralize in `@RestControllerAdvice`
- Wrong HTTP status (200 with null body instead of 404)

### HIGH — Spring Boot Architecture

- **Field injection** (`@Autowired` on fields) → constructor injection mandatory
- Business logic in controllers → delegate to service layer
- `@Transactional` on controller or repository → must be on service
- Missing `@Transactional(readOnly = true)` on read-only methods
- JPA entity directly exposed in response → DTO or record

### HIGH — JPA / Database

- N+1 queries: `FetchType.EAGER` on collections → `JOIN FETCH` or `@EntityGraph`
- Endpoints without pagination: `List<T>` → `Page<T>` with `Pageable`
- Missing `@Modifying` on mutating `@Query`
- `CascadeType.ALL` + `orphanRemoval` → confirm intent

### MEDIUM — Concurrency

- Mutable fields in `@Service`/`@Component` singletons (race condition)
- `@Async` without custom `Executor` (unbounded threads)
- `@Scheduled` blocking the scheduler thread

### MEDIUM — Java Idioms

- String concatenation in a loop → `StringBuilder`
- Raw types without parameterization
- `instanceof` + explicit cast → pattern matching (Java 16+)
- Returning null in service → `Optional<T>`

### MEDIUM — Testing

- `@SpringBootTest` for unit tests → `@WebMvcTest`, `@DataJpaTest`
- `Thread.sleep()` in tests → `Awaitility`
- Non-descriptive test names → `should_return_404_when_user_not_found`

## Build & Lint Commands (`/build-fix`)

```bash
# Maven
./mvnw compile -q 2>&1 || mvn compile -q 2>&1
./mvnw test -q 2>&1
./mvnw checkstyle:check 2>&1 || echo "checkstyle not configured"
./mvnw spotbugs:check 2>&1 || echo "spotbugs not configured"
./mvnw dependency:tree -Dverbose

# Gradle
./gradlew build 2>&1
./gradlew check
./gradlew dependencies --configuration runtimeClasspath 2>&1 | head -100

# CVE scan
./mvnw dependency-check:check 2>&1 || echo "OWASP plugin not configured"
```

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `cannot find symbol` | Missing import, typo | Add import or dependency |
| `incompatible types` | Wrong type, missing cast | Explicit cast or fix the type |
| `package X does not exist` | Missing dependency | Add in `pom.xml`/`build.gradle` |
| `Annotation processor threw exception` | Lombok/MapStruct misconfiguration | Check annotation processor setup |
| `Source option X no longer supported` | Java version mismatch | Update `maven.compiler.source` |

### Spring Boot specific

```bash
# Check context loading
./mvnw test -Dtest=*ContextLoads* -q

# Find anti-patterns
grep -rn "@Autowired" src/main/java --include="*.java"
grep -rn "FetchType.EAGER" src/main/java --include="*.java"
```
