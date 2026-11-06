"""Dual test suite for BillingService (Happy-Path + Negative Edge-Case)."""
import os, sys, unittest
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.billing.billing_service import BillingServiceError, BillingServiceRequest, BillingServiceResult, billing_service

class TestBillingService(unittest.TestCase):
    def test_billing_service_happy_path(self) -> None:
        req = BillingServiceRequest(item_id="item_101", amount=25.0)
        res = billing_service(req)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.item_id, "item_101")

    def test_billing_service_validation_failure_empty_id(self) -> None:
        with self.assertRaises(BillingServiceError):
            BillingServiceRequest(item_id="", amount=10.0)

    def test_billing_service_validation_failure_negative_amount(self) -> None:
        with self.assertRaises(BillingServiceError):
            BillingServiceRequest(item_id="item_102", amount=-1.0)

if __name__ == "__main__":
    unittest.main()
