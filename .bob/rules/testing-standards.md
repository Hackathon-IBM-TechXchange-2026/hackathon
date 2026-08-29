# Testing Standards

## Guidelines
- **Unit Testing**: 100% path coverage for business logic in services. Test edge cases, boundaries, invalid input errors, and mock downstream dependencies.
- **Integration Testing**: Test full request-response lifecycle from controller down to repository/mock store. Validate serialization, status codes, and headers.
- **Deterministic & Isolated**: Tests must not rely on shared mutable state or external live network services. Use in-memory mocks or fixtures.
- **Automated Repair Loop**: When tests fail, identify whether the test assertion or implementation is incorrect, apply minimal fixes, and re-run until green.

