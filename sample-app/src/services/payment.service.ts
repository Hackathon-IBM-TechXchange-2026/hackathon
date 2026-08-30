import { PaymentRepository, PaymentRecord, PaymentMethod, PaymentStatus } from '../repository/payment.repository';

export interface ProcessPaymentInput {
  idempotencyKey: string;
  amount: number;
  currency: string;
  method: PaymentMethod;
  metadata?: Record<string, unknown>;
}

export interface PaymentResult {
  success: boolean;
  paymentId?: string;
  status: PaymentStatus;
  fee: number;
  netAmount: number;
  errorMessage?: string;
}

export class PaymentService {
  private readonly SUPPORTED_CURRENCIES = new Set(['USD', 'EUR', 'BRL']);
  private readonly MAX_TRANSACTION_LIMIT = 50000;

  constructor(private readonly repository: PaymentRepository) {}

  public calculateFee(amount: number, method: PaymentMethod): number {
    switch (method) {
      case 'CREDIT_CARD':
        return Number((amount * 0.029 + 0.30).toFixed(2));
      case 'DEBIT_CARD':
        return Number((amount * 0.015 + 0.15).toFixed(2));
      case 'BANK_TRANSFER':
        return Number((amount * 0.005).toFixed(2));
      default:
        throw new Error(`Unsupported payment method: ${method}`);
    }
  }

  public validatePaymentInput(input: ProcessPaymentInput): void {
    if (!input.idempotencyKey || input.idempotencyKey.trim().length === 0) {
      throw new Error('Idempotency key is required');
    }
    if (typeof input.amount !== 'number' || isNaN(input.amount) || input.amount <= 0) {
      throw new Error('Amount must be a positive number');
    }
    if (input.amount > this.MAX_TRANSACTION_LIMIT) {
      throw new Error(`Amount exceeds maximum transaction limit of ${this.MAX_TRANSACTION_LIMIT}`);
    }
    if (!this.SUPPORTED_CURRENCIES.has(input.currency.toUpperCase())) {
      throw new Error(`Unsupported currency: ${input.currency}`);
    }
  }

  public async processPayment(input: ProcessPaymentInput): Promise<PaymentResult> {
    this.validatePaymentInput(input);

    const existing = await this.repository.findByIdempotencyKey(input.idempotencyKey);
    if (existing) {
      return {
        success: existing.status !== 'FAILED',
        paymentId: existing.id,
        status: existing.status,
        fee: existing.fee,
        netAmount: existing.netAmount
      };
    }

    const fee = this.calculateFee(input.amount, input.method);
    const netAmount = Number((input.amount - fee).toFixed(2));

    const record = await this.repository.create({
      idempotencyKey: input.idempotencyKey,
      amount: input.amount,
      currency: input.currency.toUpperCase(),
      method: input.method,
      status: 'CAPTURED',
      fee,
      netAmount,
      metadata: input.metadata
    });

    return {
      success: true,
      paymentId: record.id,
      status: record.status,
      fee: record.fee,
      netAmount: record.netAmount
    };
  }

  public async getPayment(id: string): Promise<PaymentRecord | null> {
    return this.repository.findById(id);
  }
}

