import copy
import unittest

from coordination.review_route import REQUESTED_ROUTE, evaluate_review_route


def record():
    return {
        "requested_route": dict(REQUESTED_ROUTE),
        "configured_route": dict(REQUESTED_ROUTE),
        "spawn": {"accepted": True, "substitution_reported": False},
        "serving_attestation_available": False,
        "candidate_match": True,
        "substantive_verdict": "READY",
    }


class ReviewRouteTests(unittest.TestCase):
    def test_missing_serving_attestation_is_a_caveat_not_a_veto(self):
        result = evaluate_review_route(record())
        self.assertTrue(result["review_ready"])
        self.assertTrue(result["substantive_review_gate_satisfied"])
        self.assertTrue(result["serving_attestation_caveat"])
        self.assertFalse(result["serving_attestation_blocking"])
        self.assertEqual(result["failure_reasons"], [])

    def test_available_attestation_is_not_required_or_invented(self):
        data = record()
        data["serving_attestation_available"] = True
        result = evaluate_review_route(data)
        self.assertTrue(result["review_ready"])
        self.assertFalse(result["serving_attestation_caveat"])

    def test_rejected_spawn_fails_closed(self):
        data = record()
        data["spawn"]["accepted"] = False
        result = evaluate_review_route(data)
        self.assertFalse(result["review_ready"])
        self.assertIn("spawn_accepted", result["failure_reasons"])

    def test_reported_substitution_fails_closed(self):
        data = record()
        data["spawn"]["substitution_reported"] = True
        result = evaluate_review_route(data)
        self.assertFalse(result["review_ready"])
        self.assertTrue(result["substitution_observed"])

    def test_reported_route_mismatch_is_a_substitution(self):
        data = record()
        data["spawn"]["reported_route"] = dict(REQUESTED_ROUTE, model="gpt-6.1-sol")
        result = evaluate_review_route(data)
        self.assertFalse(result["review_ready"])
        self.assertTrue(result["substitution_observed"])

    def test_candidate_mismatch_and_not_ready_fail_closed(self):
        for field, value, reason in (
            ("candidate_match", False, "candidate_match"),
            ("substantive_verdict", "NOT-READY", "substantive_verdict_ready"),
        ):
            data = record()
            data[field] = value
            result = evaluate_review_route(data)
            self.assertFalse(result["review_ready"])
            self.assertIn(reason, result["failure_reasons"])

    def test_non_astra_request_fails_closed(self):
        data = record()
        data["requested_route"] = dict(REQUESTED_ROUTE, model="gpt-6.1-sol")
        data["configured_route"] = dict(REQUESTED_ROUTE, model="gpt-6.1-sol")
        result = evaluate_review_route(data)
        self.assertFalse(result["review_ready"])
        self.assertIn("route_request_is_exact_astra_high", result["failure_reasons"])

    def test_malformed_route_raises(self):
        data = record()
        data["requested_route"].pop("fork_turns")
        with self.assertRaises(ValueError):
            evaluate_review_route(data)
        data = record()
        data["serving_attestation_available"] = "no"
        with self.assertRaises(ValueError):
            evaluate_review_route(data)
        data = copy.deepcopy(record())
        data["spawn"]["accepted"] = 1
        with self.assertRaises(ValueError):
            evaluate_review_route(data)


if __name__ == "__main__":
    unittest.main()
