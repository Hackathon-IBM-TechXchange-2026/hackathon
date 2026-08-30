export type PaymentStatus = 'PENDING' | 'AUTHORIZED' | 'CAPTURED' | 'FAILED' | 'REFUNDED';
export type PaymentMethod = 'CREDIT_CARD' | 'DEBIT_CARD' | 'BANK_TRANSFER';

export interface PaymentRecord {
  id: string;
  idempotencyKey: string;
  amount: number;
  currency: string;
  method: PaymentMethod;
  status: PaymentStatus;
  fee: number;
  netAmount: number;
  metadata?: Record<string, unknown>;
  createdAt: Date;
  updatedAt: Date;
}

export class PaymentRepository {
  private payments: Map<string, PaymentRecord> = new Map();
  private idempotencyIndex: Map<string, string> = new Map();

  async create(record: Omit<PaymentRecord, 'id' | 'createdAt' | 'updatedAt'>): Promise<PaymentRecord> {
    const existingId = this.idempotencyIndex.get(record.idempotencyKey);
    if (existingId) {
      const existing = this.payments.get(existingId);
      if (existing) return existing;
    }

    const id = `pay_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    const now = new Date();
    const newRecord: PaymentRecord = {
      ...record,
      id,
      createdAt: now,
      updatedAt: now
    };

    this.payments.set(id, newRecord);
    this.idempotencyIndex.set(record.idempotencyKey, id);
    return newRecord;
  }

  async findById(id: string): Promise<PaymentRecord | null> {
    return this.payments.get(id) || null;
  }

  async findByIdempotencyKey(key: string): Promise<PaymentRecord | null> {
    const id = this.idempotencyIndex.get(key);
    if (!id) return null;
    return this.findById(id);
  }

  async updateStatus(id: string, status: PaymentStatus): Promise<PaymentRecord> {
    const existing = this.payments.get(id);
    if (!existing) {
      throw new Error(`Payment with id ${id} not found`);
    }

    const updated: PaymentRecord = {
      ...existing,
      status,
      updatedAt: new Date()
    };

    this.payments.set(id, updated);
    return updated;
  }

  async clear(): Promise<void> {
    this.payments.clear();
    this.idempotencyIndex.clear();
  }
}

