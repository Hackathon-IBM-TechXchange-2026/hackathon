# ChangeFlow Testing Standards (Consumer-Driven Contract & Dynamic Assertions)

<instrucoes_exatas>
## 1. Consumer-Driven Contract Testing (Pact Standard)
- **Pact Specification Compliance**: All API service boundaries must support Consumer-Driven Contract verification using Pact JSON format (Specification v3+).
- **Realistic Provider State Modeling**: Provider states must never be blank. They must explicitly model realistic domain states, for example:
  ```json
  "providerStates": [
    {
      "name": "payment account 12345 exists with active BRL ledger and sufficient balance"
    }
  ]
  ```
- **Contract Boundary Testing**: Verify payload schemas, required keys, matching rules (e.g. `pact:match:type`, `pact:match:regex`), headers, and expected HTTP status codes.
</instrucoes_exatas>

<regras_estritas>
## 2. Dynamic Assertions & Execution Determinism
- **Prohibition of Fixed Sleep (`time.sleep`)**: Tests must NEVER use fixed arbitrary sleep delays (`time.sleep()`, `setTimeout()`) to wait for asynchronous events or state transitions. Fixed delays cause flaky test pipelines and slow execution.
- **Mandatory Polling Assertions**: Use dynamic polling assertions with timeout and backoff intervals (e.g., `await waitFor(() => expect(...), { timeout: 3000, interval: 50 })`).
- **Message Isolation**: For event-driven or async messaging components, isolate message queues using in-memory semantic adapters that guarantee deterministic message delivery without test cross-contamination.
- **Coverage & Self-Correction**: Enforce $\ge 90\%$ branch and line coverage on modified files. When assertions fail, execute the automated repair loop up to 3 iterations.
</regras_estritas>
