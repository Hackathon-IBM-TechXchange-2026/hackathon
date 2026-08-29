# Payment Service API Reference

## Base URL
`/api/v1`

---

## 1. Process Payment

Processes and captures a payment transaction synchronously.

- **Method**: `POST`
- **Path**: `/payments`
- **Headers**: `Content-Type: application/json`

### Request Body Schema

| Parameter | Type | Required | Description | Constraints |
|---|---|---|---|---|
| `idempotencyKey` | `string` | **Yes** | Unique request identifier for duplicate prevention | Non-empty string |
| `amount` | `number` | **Yes** | Transaction amount | Positive float, max $50,000 |
| `currency` | `string` | **Yes** | ISO-4217 Currency code | Supported: `USD`, `EUR`, `BRL` |
| `method` | `string` | **Yes** | Payment rails method | Supported: `CREDIT_CARD`, `DEBIT_CARD`, `BANK_TRANSFER` |
| `metadata` | `object` | No | Additional custom key-value pairs | Arbitrary JSON object |

### Example Request

```json
{
  "idempotencyKey": "tx_2026_9988_abc",
  "amount": 150.00,
  "currency": "USD",
  "method": "CREDIT_CARD",
  "metadata": {
    "orderId": "order_456"
  }
}
```

### Responses

#### `201 Created`
```json
{
  "success": true,
  "data": {
    "success": true,
    "paymentId": "pay_1772342400_x9a",
    "status": "CAPTURED",
    "fee": 4.65,
    "netAmount": 145.35
  }
}
```

#### `400 Bad Request`
```json
{
  "error": "Validation Error",
  "message": "Field idempotencyKey is required and must be a string"
}
```

#### `422 Unprocessable Entity`
```json
{
  "success": false,
  "error": "Processing Error",
  "message": "Unsupported currency: CAD"
}
```

---

## 2. Get Payment Details

Retrieves payment record by payment ID.

- **Method**: `GET`
- **Path**: `/payments/:id`

### Responses

#### `200 OK`
```json
{
  "success": true,
  "data": {
    "id": "pay_1772342400_x9a",
    "idempotencyKey": "tx_2026_9988_abc",
    "amount": 150.00,
    "currency": "USD",
    "method": "CREDIT_CARD",
    "status": "CAPTURED",
    "fee": 4.65,
    "netAmount": 145.35,
    "createdAt": "2026-08-29T18:00:00.000Z",
    "updatedAt": "2026-08-29T18:00:00.000Z"
  }
}
```

