import { PaymentRepository } from '../../src/repository/payment.repository';
import { PaymentService, ProcessPaymentInput } from '../../src/services/payment.service';

describe('PaymentService Unit Tests', () => {
  let repository: PaymentRepository;
  let service: PaymentService;

  beforeEach(async () => {
    repository = new PaymentRepository();
    await repository.clear();
    service = new PaymentService(repository);
  });

  describe('Fee Calculation', () => {
    it('should correctly calculate credit card fee (2.9% + $0.30)', () => {
      const fee = service.calculateFee(100.0, 'CREDIT_CARD');
      expect(fee).toBe(3.20); // 100 * 0.029 + 0.30 = 3.20
    });

    it('should correctly calculate debit card fee (1.5% + $0.15)', () => {
      const fee = service.calculateFee(100.0, 'DEBIT_CARD');
      expect(fee).toBe(1.65); // 100 * 0.015 + 0.15 = 1.65
    });

    it('should correctly calculate bank transfer fee (0.5%)', () => {
      const fee = service.calculateFee(200.0, 'BANK_TRANSFER');
      expect(fee).toBe(1.00); // 200 * 0.005 = 1.00
    });
  });

  describe('Validation', () => {
    it('should reject payment with empty idempotency key', () => {
      const input: ProcessPaymentInput = {
        idempotencyKey: '',
        amount: 50,
        currency: 'USD',
        method: 'CREDIT_CARD'
      };
      expect(() => service.validatePaymentInput(input)).toThrow('Idempotency key is required');
    });

    it('should reject non-positive amount', () => {
      const input: ProcessPaymentInput = {
        idempotencyKey: 'idemp-123',
        amount: -10,
        currency: 'USD',
        method: 'CREDIT_CARD'
      };
      expect(() => service.validatePaymentInput(input)).toThrow('Amount must be a positive number');
    });

    it('should reject amount exceeding max limit', () => {
      const input: ProcessPaymentInput = {
        idempotencyKey: 'idemp-123',
        amount: 60000,
        currency: 'USD',
        method: 'CREDIT_CARD'
      };
      expect(() => service.validatePaymentInput(input)).toThrow('Amount exceeds maximum transaction limit');
    });

    it('should reject unsupported currency', () => {
      const input: ProcessPaymentInput = {
        idempotencyKey: 'idemp-123',
        amount: 100,
        currency: 'JPY',
        method: 'CREDIT_CARD'
      };
      expect(() => service.validatePaymentInput(input)).toThrow('Unsupported currency: JPY');
    });
  });

  describe('Payment Processing & Idempotency', () => {
    it('should successfully process a valid payment', async () => {
      const input: ProcessPaymentInput = {
        idempotencyKey: 'tx_success_001',
        amount: 100,
        currency: 'USD',
        method: 'CREDIT_CARD'
      };

      const result = await service.processPayment(input);
      expect(result.success).toBe(true);
      expect(result.status).toBe('CAPTURED');
      expect(result.fee).toBe(3.20);
      expect(result.netAmount).toBe(96.80);
      expect(result.paymentId).toBeDefined();
    });

    it('should return identical result on repeated idempotent call', async () => {
      const input: ProcessPaymentInput = {
        idempotencyKey: 'tx_idempotent_002',
        amount: 250,
        currency: 'EUR',
        method: 'DEBIT_CARD'
      };

      const firstCall = await service.processPayment(input);
      const secondCall = await service.processPayment(input);

      expect(secondCall.paymentId).toBe(firstCall.paymentId);
      expect(secondCall.netAmount).toBe(firstCall.netAmount);
    });
  });
});

