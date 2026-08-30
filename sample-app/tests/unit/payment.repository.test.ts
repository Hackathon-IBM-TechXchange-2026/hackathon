import { PaymentRepository, PaymentMethod, PaymentStatus } from '../../src/repository/payment.repository';

const BUILD_PAYLOAD = (overrides: Partial<Record<string, unknown>> = {}) => ({
  idempotencyKey: 'tx_repo_001',
  amount: 100,
  currency: 'USD',
  method: 'CREDIT_CARD' as PaymentMethod,
  status: 'CAPTURED' as PaymentStatus,
  fee: 3.2,
  netAmount: 96.8,
  metadata: { orderId: 'order_9876' },
  ...overrides
});

describe('PaymentRepository Unit Tests', () => {
  let repository: PaymentRepository;

  beforeEach(async () => {
    repository = new PaymentRepository();
    await repository.clear();
  });

  describe('create', () => {
    it('should create a record with auto-generated id and timestamps', async () => {
      const record = await repository.create(BUILD_PAYLOAD());

      expect(record.id).toBeDefined();
      expect(record.id).toMatch(/^pay_/);
      expect(record.createdAt).toBeInstanceOf(Date);
      expect(record.updatedAt).toBeInstanceOf(Date);
      expect(record.amount).toBe(100);
      expect(record.method).toBe('CREDIT_CARD');
      expect(record.metadata).toEqual({ orderId: 'order_9876' });
    });

    it('should return the existing record when idempotency key already exists', async () => {
      const first = await repository.create(BUILD_PAYLOAD());
      const second = await repository.create(BUILD_PAYLOAD());

      expect(second.id).toBe(first.id);
      expect(second.idempotencyKey).toBe('tx_repo_001');
    });

    it('should return the existing record even if idempotency map points to a stored payment', async () => {
      const first = await repository.create(BUILD_PAYLOAD({ status: 'AUTHORIZED' as PaymentStatus }));
      const existing = await repository.findById(first.id);
      expect(existing?.status).toBe('AUTHORIZED');
    });
  });

  describe('findById', () => {
    it('should find a record by id', async () => {
      const created = await repository.create(BUILD_PAYLOAD());
      const found = await repository.findById(created.id);

      expect(found).not.toBeNull();
      expect(found?.netAmount).toBe(96.8);
    });

    it('should return null for an unknown id', async () => {
      expect(await repository.findById('pay_missing_123')).toBeNull();
    });
  });

  describe('findByIdempotencyKey', () => {
    it('should find a record by idempotency key', async () => {
      await repository.create(BUILD_PAYLOAD());
      const found = await repository.findByIdempotencyKey('tx_repo_001');

      expect(found?.idempotencyKey).toBe('tx_repo_001');
      expect(found?.currency).toBe('USD');
    });

    it('should return null when the idempotency key does not exist', async () => {
      expect(await repository.findByIdempotencyKey('tx_unknown')).toBeNull();
    });
  });

  describe('updateStatus', () => {
    it('should update the status of an existing record', async () => {
      const created = await repository.create(BUILD_PAYLOAD());
      const updated = await repository.updateStatus(created.id, 'REFUNDED');

      expect(updated.status).toBe('REFUNDED');
      expect(updated.id).toBe(created.id);
    });

    it('should throw when the record does not exist', async () => {
      await expect(repository.updateStatus('pay_nonexistent', 'FAILED')).rejects.toThrow(
        'Payment with id pay_nonexistent not found'
      );
    });
  });

  describe('clear', () => {
    it('should wipe payments and idempotency index', async () => {
      await repository.create(BUILD_PAYLOAD());
      await repository.create(BUILD_PAYLOAD({ idempotencyKey: 'tx_repo_002' }));

      await repository.clear();

      expect(await repository.findByIdempotencyKey('tx_repo_001')).toBeNull();
      expect(await repository.findByIdempotencyKey('tx_repo_002')).toBeNull();
    });
  });
});