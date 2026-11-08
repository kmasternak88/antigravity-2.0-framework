import unittest
from tools.jules_bridge import audit_deployment_plan, JulesPlanAuditResult

class TestJulesDeploymentBridge(unittest.TestCase):

    def test_audit_deployment_plan_success(self):
        plan = "I will perform a rolling zero-downtime deployment. If it fails, I will use a rollback script. I will also run smoke tests using curl to verify_health."
        protected = ["configs/prod.env", "contracts/db.json"]
        result = audit_deployment_plan(plan, protected)
        self.assertTrue(result.approved)
        self.assertEqual(result.status, "APPROVED")
        self.assertEqual(len(result.violations), 0)

    def test_audit_deployment_plan_missing_rollback(self):
        plan = "I will perform a rolling zero downtime deployment. I will run a smoke test."
        protected = ["configs/prod.env"]
        result = audit_deployment_plan(plan, protected)
        self.assertFalse(result.approved)
        self.assertIn("REJECTED_PLAN", result.status)
        self.assertTrue(any("MISSING_ROLLBACK_PROCEDURE" in v for v in result.violations))

    def test_audit_deployment_plan_missing_smoke_test(self):
        plan = "I will perform a zero-downtime deployment with a rollback strategy."
        protected = ["configs/prod.env"]
        result = audit_deployment_plan(plan, protected)
        self.assertFalse(result.approved)
        self.assertTrue(any("MISSING_SMOKE_TESTS" in v for v in result.violations))

    def test_audit_deployment_plan_missing_zero_downtime(self):
        plan = "I will deploy with a rollback strategy and verify health with smoke tests."
        protected = ["configs/prod.env"]
        result = audit_deployment_plan(plan, protected)
        self.assertFalse(result.approved)
        self.assertTrue(any("ZERO_DOWNTIME_VIOLATION" in v for v in result.violations))

    def test_audit_deployment_plan_tampering_protected(self):
        plan = "I will perform a zero-downtime deployment, with rollback and smoke tests. I will also edit configs/prod.env."
        protected = ["configs/prod.env"]
        result = audit_deployment_plan(plan, protected)
        self.assertFalse(result.approved)
        self.assertTrue(any("PROTECTED_CONFIG_TAMPERING" in v for v in result.violations))

    def test_deployment_self_healing_loop_simulation(self):
        # Symulacja 3-cyklowej pętli z pętlą naprawczą dla planu wdrożenia
        max_iterations = 3
        protected = ["configs/prod.env"]

        # Iteracja 1: brak rollbacku
        plan_iter_1 = "I will perform zero-downtime deployment and run smoke tests."
        res_1 = audit_deployment_plan(plan_iter_1, protected)
        self.assertFalse(res_1.approved)
        self.assertTrue(any("MISSING_ROLLBACK" in v for v in res_1.violations))

        # Iteracja 2: brak zero-downtime
        plan_iter_2 = "I will deploy with rollback and smoke tests."
        res_2 = audit_deployment_plan(plan_iter_2, protected)
        self.assertFalse(res_2.approved)
        self.assertTrue(any("ZERO_DOWNTIME_VIOLATION" in v for v in res_2.violations))

        # Iteracja 3: Poprawny plan
        plan_iter_3 = "I will deploy with a rolling zero-downtime approach, run smoke tests, and rollback on failure."
        res_3 = audit_deployment_plan(plan_iter_3, protected)
        self.assertTrue(res_3.approved)
        self.assertEqual(res_3.status, "APPROVED")

if __name__ == "__main__":
    unittest.main()
