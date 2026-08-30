# ChangeFlow Coding Standards & Architectural Security Rules

<strict_rules>
## 1. Clean Code & Architectural Separation
- **Strict Layering**: Business logic must reside strictly in the service layer (`services/`). Controllers (`controllers/`) must remain thin adapters for HTTP validation and status code translation. Repositories (`repository/`) are strictly reserved for data persistence and transactional storage.
- **Explicit Typing**: Strictly typed TypeScript / Python. The use of `any` or untyped dictionary representations for domain entities is prohibited. All public methods must specify explicit return types.
- **Single Responsibility Principle (SRP)**: Each class and module must have exactly one reason to change. Deconstruct large functions into discrete, testable units with cyclomatic complexity $\le 10$.
</strict_rules>

<owasp_security_rules>
## 2. Security Standards & OWASP Compliance
- **Sensitive Data Masking (PCI-DSS)**: Credit card numbers, account tokens, and PII must strictly be masked using the format `****-****-****-XXXX` (showing only the last 4 digits) across all logging, debugging, exception payloads, and external serialization.
- **Zero CVV Logging**: CVV / CVC codes must NEVER be persisted in storage, recorded in audit logs, printed in stdout, or returned in API responses under any circumstance.
- **SQL Injection Prevention**: All database queries and store operations must use parameterized queries with binding placeholders (`?` or named parameters `$1, $2`). Dynamic string interpolation/concatenation in database access code is strictly forbidden.
- **Input Validation & DTO Boundaries**: All external payloads must pass boundary schema validation (e.g. DTO verification, regex checks, type coercions) before reaching domain services.
</owasp_security_rules>

<exception_handling>
## 3. Exception Handling & Error Architecture
- **Typed Domain Exceptions**: All errors must be modeled as typed exception classes inheriting from base domain error classes (e.g., `PaymentValidationError`, `IdempotencyConflictError`, `InsufficientFundsError`).
- **Prohibition of Silent Catching**: Generic bare exception handlers (e.g., `except: pass` or `catch (e) {}`) are strictly forbidden. All caught exceptions must either be handled with contextual log enrichment or rethrown as structured domain errors.
- **Error Codes & Traceability**: Each error response must supply a machine-readable `errorCode`, a user-friendly `message`, and a correlation `traceId`.
</exception_handling>
