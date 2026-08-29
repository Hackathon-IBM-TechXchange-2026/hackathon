# Coding Standards & Best Practices

## General Principles
- **Clean Architecture & Separation of Concerns**: Keep business logic isolated in service layers; keep controllers thin and repositories focused strictly on data persistence.
- **Type Safety**: Strictly typed TypeScript / Python. Avoid `any` types; declare explicit return types and interface contracts for all public methods.
- **Error Handling**: Custom error classes with HTTP status codes and domain codes. Always capture, log with context, and never fail silently.
- **Security by Design**: Validate all input payloads with schemas/DTOs. Sanitize parameters, prevent injection, and enforce strict boundary validation.
- **Idempotency & Transactions**: Financial operations (payments, refunds, ledger entries) must use idempotency keys and transactional guarantees.

