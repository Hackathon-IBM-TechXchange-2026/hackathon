import { PaymentService, ProcessPaymentInput } from '../services/payment.service';

export interface HttpRequest {
  body: Record<string, unknown>;
  params?: Record<string, string>;
  headers?: Record<string, string>;
}

export interface HttpResponse {
  statusCode: number;
  body: Record<string, unknown>;
}

export class PaymentController {
  constructor(private readonly paymentService: PaymentService) {}

  public async handleCreatePayment(req: HttpRequest): Promise<HttpResponse> {
    try {
      const { idempotencyKey, amount, currency, method, metadata } = req.body;

      if (!idempotencyKey || typeof idempotencyKey !== 'string') {
        return {
          statusCode: 400,
          body: { error: 'Validation Error', message: 'Field idempotencyKey is required and must be a string' }
        };
      }

      if (typeof amount !== 'number') {
        return {
          statusCode: 400,
          body: { error: 'Validation Error', message: 'Field amount is required and must be a number' }
        };
      }

      if (typeof currency !== 'string') {
        return {
          statusCode: 400,
          body: { error: 'Validation Error', message: 'Field currency is required and must be a string' }
        };
      }

      if (typeof method !== 'string') {
        return {
          statusCode: 400,
          body: { error: 'Validation Error', message: 'Field method is required and must be a string' }
        };
      }

      const input: ProcessPaymentInput = {
        idempotencyKey,
        amount,
        currency,
        method: method as any,
        metadata: metadata as Record<string, unknown> | undefined
      };

      const result = await this.paymentService.processPayment(input);

      return {
        statusCode: 201,
        body: {
          success: true,
          data: result
        }
      };
    } catch (err: any) {
      return {
        statusCode: 422,
        body: {
          success: false,
          error: 'Processing Error',
          message: err.message || 'Internal Server Error'
        }
      };
    }
  }

  public async handleGetPayment(req: HttpRequest): Promise<HttpResponse> {
    try {
      const id = req.params?.id;
      if (!id) {
        return {
          statusCode: 400,
          body: { error: 'Validation Error', message: 'Payment ID parameter is required' }
        };
      }

      const payment = await this.paymentService.getPayment(id);
      if (!payment) {
        return {
          statusCode: 404,
          body: { error: 'Not Found', message: `Payment with id ${id} not found` }
        };
      }

      return {
        statusCode: 200,
        body: {
          success: true,
          data: payment
        }
      };
    } catch (err: any) {
      return {
        statusCode: 500,
        body: {
          success: false,
          error: 'Internal Error',
          message: err.message
        }
      };
    }
  }
}

