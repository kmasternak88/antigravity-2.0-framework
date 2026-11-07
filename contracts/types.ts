/**
 * Frozen Domain Interface Contracts (DREE v8.2 / TypeScript Strict)
 */
export interface EntityBase {
  id: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface PaymentProcessorPayload extends EntityBase {
  name?: string;
  status?: string;
  metadata?: Record<string, any>;
}

export interface PaymentProcessorResult extends EntityBase {
  name?: string;
  status?: string;
  metadata?: Record<string, any>;
}

export interface IPaymentProcessorService extends EntityBase {
  name?: string;
  status?: string;
  metadata?: Record<string, any>;
}
