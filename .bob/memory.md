# ChangeFlow — IBM Bob 2.0 Dynamic Memory & Self-Correction Log
Last Updated: 2026-08-29T18:55:00Z
Project: ChangeFlow (Hackathon IBM TechXchange 2026)

## 1. Project Conventions & Architecture Patterns
- **Architecture Pattern**: Clean Architecture with strict 3-tier layering: `controllers` -> `services` -> `repository`.
- **Primary Domain**: Financial Transactions & Multi-Rail Payments (Card, Debit, Bank Transfer, Instant PIX).
- **Security Policy**: Sensitive card data masked as `****-****-****-XXXX`. CVV is strictly forbidden in logs and persistent storage. All database queries must use parameterized placeholders (`?`).
- **Documentation Policy**: Intent-Driven Documentation. All API contracts (`sample-app/docs/API.md`) and Architectural flows (`sample-app/docs/ARCHITECTURE.md`) must be synchronized synchronously on any method signature or payload change.
- **Testing Policy**: Consumer-Driven Contract Testing (Pact format) + Jest unit/integration tests with dynamic polling assertions (no static sleep).

## 2. Learned Heuristics & Route Corrections
- *Heuristic #1*: When parsing Git diffs, always check for cross-layer impact. A change in `payment.repository.ts` triggers cascades across `payment.service.ts`, `payment.controller.ts`, `API.md`, and integration test suites.
- *Heuristic #2*: PIX payment rails require strict currency binding (`BRL`) and fee ceiling enforcement (`Math.min(amount * 0.0099, 3.00)`).
- *Heuristic #3*: For contract testing, always generate valid Consumer-Provider interactions with explicit provider states (e.g. `"providerState": "account 12345 exists and has sufficient balance"`).

## 3. Human Feedback Ledger (Self-Improving Loop)
- `2026-08-29 14:20`: Developer emphasized that fee calculation logic must always be validated against boundary condition `0.00` and maximum transaction limits.
- `2026-08-29 15:10`: Developer enforced that documentation updates must detail the business rationale (*Why*) alongside the technical schema changes (*What*).

