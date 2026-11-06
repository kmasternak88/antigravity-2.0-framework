"""Dual test suite for PaymentProcessor (Happy-Path + Negative Edge-Case)."""
import os, sys, unittest
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.billing.payment_processor import PaymentProcessorError, PaymentProcessorRequest, PaymentProcessorResult, payment_processor

class TestPaymentProcessor(unittest.TestCase):
    def test_payment_processor_happy_path(self) -> None:
        req = PaymentProcessorRequest(item_id="item_101", amount=25.0)
        res = payment_processor(req)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.item_id, "item_101")

    def test_payment_processor_validation_failure_empty_id(self) -> None:
        with self.assertRaises(PaymentProcessorError):
            PaymentProcessorRequest(item_id="", amount=10.0)

    def test_payment_processor_validation_failure_negative_amount(self) -> None:
        with self.assertRaises(PaymentProcessorError):
            PaymentProcessorRequest(item_id="item_102", amount=-1.0)

if __name__ == "__main__":
    unittest.main()
