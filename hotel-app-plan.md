# ChangeFlow — Hotel App Integration Plan

## Top-Level Overview

Criar um segundo aplicativo de demonstração (`hotel-app/`) que espelha a arquitetura do `sample-app/` (Clean Architecture em TypeScript com 3 camadas: repository → service → controller), mas com domínio de negócio completamente diferente: **sistema de reservas de hotel**.

O objetivo é provar que o pipeline ChangeFlow é genérico — não é hardcoded para pagamentos — e consegue analisar, testar e validar qualquer sistema de software.

O diff de demonstração simulará um PR adicionando **desconto de fidelidade** (hóspedes com mais de 5 reservas ganham 10% de desconto automático), que o ChangeFlow analisará via `benchmarks/hotel-diff.patch`.

### Escopo
- `hotel-app/` — novo app TypeScript (repository, service, controller, tests, jest.config, tsconfig, package.json)
- `benchmarks/hotel-diff.patch` — diff simulando a adição do desconto de fidelidade
- O pipeline ChangeFlow existente (`core/orchestrator.py`) roda sem modificações — apenas recebe o novo patch como argumento

### Não está no escopo
- Modificar o orchestrator ou qualquer arquivo de `core/`
- Servidor HTTP real (apenas padrão in-memory, igual ao sample-app)
- Persistência em banco de dados

---

## Regras de Negócio do Hotel App

### Entidades
- **Room** (quarto): número, tipo (`SINGLE` | `DOUBLE` | `SUITE`), preço por noite, disponibilidade
- **Booking** (reserva): id, guestId, roomId, checkIn, checkOut, status, diárias, taxas, total
- **BookingStatus**: `PENDING` | `CONFIRMED` | `CANCELLED` | `COMPLETED`
- **RoomType**: `SINGLE` | `DOUBLE` | `SUITE`

### Cálculo de Diárias
- Número de noites = diferença em dias entre checkOut e checkIn (mínimo 1)
- Tarifa base = `nights × room.pricePerNight`

### Taxa de Limpeza
- `SINGLE`: R$ 30,00 fixo
- `DOUBLE`: R$ 50,00 fixo
- `SUITE`: R$ 80,00 fixo

### Política de Cancelamento
- Cancelamento com **> 48h** de antecedência ao checkIn: **reembolso 100%**
- Cancelamento com **24h–48h** de antecedência: **reembolso 50%**
- Cancelamento com **< 24h** de antecedência: **sem reembolso (0%)**
- Reservas com status `COMPLETED` ou já `CANCELLED` não podem ser canceladas

### Desconto de Fidelidade ← ADICIONADO PELO DIFF
- Hóspedes com **> 5 reservas confirmadas** no histórico ganham **10% de desconto** sobre a tarifa base
- A taxa de limpeza **não** é descontada
- O desconto é calculado antes de somar a taxa de limpeza

---

## Sub-Tarefa 1 — Repository Layer

**Status:** [x] done

### Intent
Criar a camada de dados do hotel-app com armazenamento em memória. Define os tipos TypeScript fundamentais e provê operações CRUD para quartos e reservas. Seguir exatamente o mesmo padrão do `PaymentRepository` (Maps internos, métodos async, `clear()` para teardown em testes).

### Expected Outcomes
- `hotel-app/src/repository/hotel.repository.ts` existe e compila
- Tipos exportados: `RoomType`, `BookingStatus`, `Room`, `BookingRecord`
- Classe `HotelRepository` com métodos: `createRoom()`, `findRoomById()`, `findAvailableRooms()`, `createBooking()`, `findBookingById()`, `findBookingsByGuestId()`, `updateBookingStatus()`, `clear()`
- Contagem de reservas confirmadas por hóspede disponível via `countConfirmedBookings(guestId)`

### Todo List
1. Criar `hotel-app/src/repository/hotel.repository.ts`
2. Definir type unions: `RoomType`, `BookingStatus`
3. Definir interfaces: `Room`, `BookingRecord`, `CreateBookingInput`
4. Implementar `HotelRepository` com dois Maps (rooms, bookings) e índice por guestId
5. Implementar `countConfirmedBookings(guestId)` — necessário para o desconto de fidelidade

### Relevant Context
- `sample-app/src/repository/payment.repository.ts` — padrão a seguir
- Manter `private readonly` em todos os Maps internos
- IDs gerados com o mesmo padrão: `` `booking_${Date.now()}_${Math.random()...}` ``

---

## Sub-Tarefa 2 — Service Layer

**Status:** [x] done

### Intent
Implementar as regras de negócio do hotel: cálculo de diárias, taxa de limpeza por tipo de quarto, política de cancelamento com reembolso escalonado, e validação de disponibilidade. **Não inclui o desconto de fidelidade** — esse será adicionado pelo diff (Sub-Tarefa 5).

### Expected Outcomes
- `hotel-app/src/services/hotel.service.ts` existe e compila
- Classe `HotelService` com métodos públicos:
  - `calculateNights(checkIn, checkOut): number`
  - `calculateCleaningFee(roomType): number`
  - `calculateRefund(booking, cancellationDate): number` (política 48h/24h)
  - `validateBookingInput(input): void`
  - `createBooking(input): Promise<BookingResult>`
  - `cancelBooking(bookingId, requestDate): Promise<CancelResult>`
  - `getBooking(id): Promise<BookingRecord | null>`
- Interface `BookingInput`: guestId, roomId, checkIn, checkOut
- Interface `BookingResult`: success, bookingId?, status, nights, baseRate, cleaningFee, total, errorMessage?
- Interface `CancelResult`: success, refundAmount, refundPercentage, errorMessage?

### Todo List
1. Criar `hotel-app/src/services/hotel.service.ts`
2. Definir interfaces `BookingInput`, `BookingResult`, `CancelResult`
3. Implementar `calculateNights()` com validação (checkOut > checkIn)
4. Implementar `calculateCleaningFee()` com valores fixos por `RoomType`
5. Implementar `calculateRefund()` com as 3 faixas de antecedência
6. Implementar `validateBookingInput()` — verifica datas, quarto existe, quarto disponível
7. Implementar `createBooking()` — chama validate, calcula taxas, persiste via repository
8. Implementar `cancelBooking()` — verifica status, calcula reembolso, atualiza status

### Relevant Context
- `sample-app/src/services/payment.service.ts` — padrão a seguir
- A política de cancelamento usa `Date` objects — cuidado com comparações de timezone
- `HotelRepository.countConfirmedBookings()` já existe mas **não é chamado aqui** — será adicionado pelo diff

---

## Sub-Tarefa 3 — Controller Layer

**Status:** [x] done

### Intent
Criar o controller HTTP que adapta requests/responses para o HotelService. Seguir o mesmo padrão do `PaymentController`: interfaces `HttpRequest`/`HttpResponse`, métodos `handleCreate`, `handleCancel`, `handleGet`, tratamento de erros mapeados para status codes corretos.

### Expected Outcomes
- `hotel-app/src/controllers/hotel.controller.ts` existe e compila
- Classe `HotelController` com métodos:
  - `handleCreateBooking(req): Promise<HttpResponse>` → 201 (criado), 400 (input inválido), 422 (quarto indisponível), 500 (erro inesperado)
  - `handleCancelBooking(req): Promise<HttpResponse>` → 200 (cancelado), 404 (não encontrado), 422 (não cancelável)
  - `handleGetBooking(req): Promise<HttpResponse>` → 200 (encontrado), 404 (não encontrado)

### Todo List
1. Criar `hotel-app/src/controllers/hotel.controller.ts`
2. Exportar interfaces `HttpRequest` e `HttpResponse` (mesmas do sample-app)
3. Implementar `handleCreateBooking()` com try-catch e mapeamento de erros
4. Implementar `handleCancelBooking()` com try-catch
5. Implementar `handleGetBooking()` com try-catch

### Relevant Context
- `sample-app/src/controllers/payment.controller.ts` — padrão a seguir
- Erros de validação do service → 400
- Quarto não disponível / booking não encontrado → 404 ou 422
- Erro inesperado → 500

---

## Sub-Tarefa 4 — Test Suites

**Status:** [x] done

### Intent
Criar testes unitários e de integração que cobrem as regras de negócio do hotel, garantindo ≥ 80% de cobertura (threshold do jest.config). Os testes devem validar todos os cenários: cálculo correto de diárias, taxas de limpeza, política de cancelamento nas 3 faixas, e fluxos de erro.

### Expected Outcomes
- `hotel-app/tests/unit/hotel.service.test.ts` — testa cada método do service isoladamente
- `hotel-app/tests/unit/hotel.repository.test.ts` — testa CRUD e índices do repository
- `hotel-app/tests/integration/hotel.booking.test.ts` — testa fluxos end-to-end via controller
- `npm test` dentro de `hotel-app/` passa com 100% de testes e ≥ 80% de cobertura
- Cenários obrigatórios cobertos:
  - Reserva válida criada com sucesso
  - Cancelamento > 48h → 100% reembolso
  - Cancelamento 24h–48h → 50% reembolso
  - Cancelamento < 24h → 0% reembolso
  - Quarto indisponível → erro
  - CheckOut antes de checkIn → erro

### Todo List
1. Criar `hotel-app/tests/unit/hotel.repository.test.ts`
2. Criar `hotel-app/tests/unit/hotel.service.test.ts` com helper `BUILD_BOOKING()`
3. Criar `hotel-app/tests/integration/hotel.booking.test.ts`
4. Garantir `beforeEach` com `repository.clear()` em todos os arquivos de teste

### Relevant Context
- `sample-app/tests/unit/payment.service.test.ts` — padrão de helper factory e describe blocks
- `sample-app/tests/integration/payment.flow.test.ts` — padrão de integração
- Usar `jest.useFakeTimers()` ou datas fixas para tornar os testes da política de cancelamento determinísticos

---

## Sub-Tarefa 5 — Configuração do Projeto (package.json, tsconfig, jest.config)

**Status:** [x] done

### Intent
Criar os arquivos de configuração do `hotel-app/` que espelham o `sample-app/`, permitindo que o Jest rode os testes TypeScript com cobertura e que o orchestrator consiga chamar `npm test` dentro da pasta correta.

### Expected Outcomes
- `hotel-app/package.json` com scripts `test`, `test:coverage`, `build`
- `hotel-app/tsconfig.json` com strict mode
- `hotel-app/jest.config.js` idêntico ao sample-app mas com `rootDir` apontando para `hotel-app/`
- `npm install` dentro de `hotel-app/` instala as dependências
- `npm test` dentro de `hotel-app/` executa e passa

### Todo List
1. Criar `hotel-app/package.json` espelhando `sample-app/package.json`
2. Criar `hotel-app/tsconfig.json`
3. Criar `hotel-app/jest.config.js`
4. Rodar `npm install` dentro de `hotel-app/`

### Relevant Context
- `sample-app/package.json` — copiar devDependencies (jest, ts-jest, @types/jest, typescript)
- `sample-app/jest.config.js` — copiar e ajustar paths

---

## Sub-Tarefa 6 — Diff de Demonstração (hotel-diff.patch)

**Status:** [x] done

### Intent
Criar o arquivo `benchmarks/hotel-diff.patch` que simula o PR adicionando o **desconto de fidelidade** ao hotel-app. Esse patch é o input que o ChangeFlow vai analisar — deve seguir o mesmo formato unified diff do `sample-diff.patch`.

A mudança modifica 2 arquivos:
1. `hotel-app/src/repository/hotel.repository.ts` — adiciona `countConfirmedBookings()`
2. `hotel-app/src/services/hotel.service.ts` — usa a contagem para aplicar 10% de desconto

### Expected Outcomes
- `benchmarks/hotel-diff.patch` existe no formato unified diff correto
- O diff modifica exatamente as 2 áreas relevantes (repository + service)
- O orchestrator consegue parsear o patch via `DiffParser` sem erros
- O ChangeFlow identifica as mudanças, revisa, testa e valida com sucesso

### Todo List
1. Definir exatamente quais linhas são adicionadas em cada arquivo (desconto de fidelidade)
2. Criar `benchmarks/hotel-diff.patch` no formato `diff --git a/... b/...`
3. Validar que o DiffParser consegue ler o arquivo (rodar `python3 -c "from core.analyzer.diff_parser import DiffParser; ..."`)

### Relevant Context
- `benchmarks/sample-diff.patch` — formato exato a replicar
- `core/analyzer/diff_parser.py` — parser que vai consumir o arquivo
- A mudança no service: `if (await this.countLoyaltyEligible(input.guestId)) { baseRate *= 0.9; }`
- A mudança no repository: método `countConfirmedBookings(guestId: string): Promise<number>`

---

## Sub-Tarefa 7 — Validação End-to-End

**Status:** [x] done

### Intent
Executar o pipeline ChangeFlow completo apontando para o `hotel-diff.patch` e confirmar que todos os 5 agentes rodam com sucesso no novo domínio, provando que o ChangeFlow é agnóstico ao domínio de negócio.

### Expected Outcomes
- `python3 core/orchestrator.py benchmarks/hotel-diff.patch` completa sem erros
- `pipeline_status: "READY_FOR_HUMAN_REVIEW"` no output
- `agents.reviewer.basis: "ai"` — Bob revisou o código do hotel
- `agents.tester.tests_passed > 0` — Jest rodou os testes do hotel-app
- `benchmarks/latest-hotel-pipeline-run.json` gerado como evidência

### Todo List
1. Confirmar que `hotel-app/node_modules` está instalado
2. Verificar que `core/runner/test_runner.py` aponta para `sample-app/` — ajustar para aceitar app configurável ou criar runner separado
3. Rodar `python3 core/orchestrator.py benchmarks/hotel-diff.patch`
4. Salvar output em `benchmarks/latest-hotel-pipeline-run.json`
5. Verificar os campos críticos no JSON de saída

### Relevant Context
- `core/runner/test_runner.py:16` — `self.sample_app_dir` está hardcoded para `sample-app/` — precisará de ajuste
- `core/orchestrator.py:50-54` — construtor do orchestrator (pode receber configuração adicional)
- Esta sub-tarefa pode revelar necessidade de pequenos ajustes no orchestrator para suportar múltiplos apps
