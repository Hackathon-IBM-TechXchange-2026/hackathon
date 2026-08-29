import { PaymentRepository } from '../../src/repository/payment.repository';
import { PaymentService } from '../../src/services/payment.service';
import { PaymentController, HttpRequest } from '../../src/controllers/payment.controller';

describe('Payment Flow Integration Tests', () => {
  let repository: PaymentRepository;
  let service: PaymentService;
  let controller: PaymentController;

  beforeEach(async () => {
    repository = new PaymentRepository();
    await repository.clear();
    service = new PaymentService(repository);
    controller = new PaymentController(service);
  });

  it('should successfully handle full payment lifecycle via controller', async () => {
    const createReq: HttpRequest = {
      body: {
        idempotencyKey: 'int_flow_001',
        amount: 350.00,
        currency: 'USD',
        method: 'CREDIT_CARD',
        metadata: { orderId: 'ord_9988' }
      }
    };

    const createRes = await controller.handleCreatePayment(createReq);
    expect(createRes.statusCode).toBe(201);
    expect(createRes.body.success).toBe(true);
    const paymentData = (createRes.body.data as any);
    expect(paymentData.paymentId).toBeDefined();

    // Query payment back
    const getReq: HttpRequest = {
      body: {},
      params: { id: paymentData.paymentId }
    };

    const getRes = await controller.handleGetPayment(getReq);
    expect(getRes.statusCode).toBe(200);
    expect(getRes.body.success).toBe(true);
    expect((getRes.body.data as any).id).toBe(paymentData.paymentId);
  });

  it('should return 400 when missing required payload fields', async () => {
    const badReq: HttpRequest = {
      body: {
        amount: 100
        // missing idempotencyKey, currency, method
      }
    };

    const res = await controller.handleCreatePayment(badReq);
    expect(res.statusCode).toBe(400);
    expect(res.body.error).toBe('Validation Error');
  });

  it('should return 404 when querying non-existent payment ID', async () => {
    const getReq: HttpRequest = {
      body: {},
      params: { id: 'non_existent_pay_id' }
    };

    const res = await controller.handleGetPayment(getReq);
    expect(res.statusCode).toBe(404);
    expect(res.body.error).toBe('Not Found');
  });

  it('should return 422 for domain validation errors like invalid currency', async () => {
    const invalidCurrencyReq: HttpRequest = {
      body: {
        idempotencyKey: 'int_invalid_curr_01',
        amount: 50.00,
        currency: 'CAD',
        method: 'CREDIT_CARD'
      }
    };

    const res = await controller.handleCreatePayment(invalidCurrencyReq);
    expect(res.statusCode).toBe(422);
    expect(res.body.error).toBe('Processing Error');
    expect(res.body.message).toContain('Unsupported currency');
  });
});

