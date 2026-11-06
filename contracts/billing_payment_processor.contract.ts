// SYNAPSE Interface-First Frozen Contract
// Domain: billing | Module: PaymentProcessor
export interface PaymentProcessorPayload {
  id: string;
  data: Record<string, unknown>;
}

export interface PaymentProcessorResult {
  success: boolean;
  timestamp: number;
}

export interface IPaymentProcessorService {
  execute(payload: PaymentProcessorPayload): Promise<PaymentProcessorResult>;
}
