# Payment Service Architecture

## Architectural Layers

The application follows Clean Architecture principles with strict layering and unidirectional dependencies:

```mermaid
graph TD
    Client[HTTP Client / API Gateway] --> Controller[PaymentController]
    Controller --> Service[PaymentService]
    Service --> Repository[PaymentRepository]
    Repository --> Database[(In-Memory / Database)]
```

## Component Overview

1. **`PaymentController` (`src/controllers/payment.controller.ts`)**:
   - Validates incoming HTTP request formats, data types, and status code transformations.
   - Decouples HTTP concerns from business logic.

2. **`PaymentService` (`src/services/payment.service.ts`)**:
   - Executes domain rules, limits, fee calculations, and currency checks.
   - Enforces idempotent transaction execution.

3. **`PaymentRepository` (`src/repository/payment.repository.ts`)**:
   - Manages persistence layer and fast idempotency key indexing.

## Sequence Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant Controller as PaymentController
    participant Service as PaymentService
    participant Repo as PaymentRepository

    Client->>Controller: POST /payments
    Controller->>Service: processPayment(input)
    Service->>Repo: findByIdempotencyKey(key)
    alt Transaction Exists
        Repo-->>Service: Existing Record
        Service-->>Controller: Cached Result
    else New Transaction
        Service->>Service: validate & calculateFee()
        Service->>Repo: create(record)
        Repo-->>Service: Saved Record
        Service-->>Controller: PaymentResult (201 Created)
    end
    Controller-->>Client: HTTP JSON Response
```

## ChangeFlow Automated Documentation Sync

<!-- This section is automatically maintained by ChangeFlow -->
- `PIX` (_new identifier from sample-app/src/repository/payment.repository.ts, sample-app/src/services/payment.service.ts_)

