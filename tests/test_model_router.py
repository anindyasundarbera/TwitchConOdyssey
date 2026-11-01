import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from coordination.model_router import DEFAULT_POLICY, choose_model, infer


class ModelRouterTests(unittest.TestCase):
    def test_planned_allocation_and_token_caps(self):
        policy = json.loads(DEFAULT_POLICY.read_text())
        expected = {
            "route_mapping": ("gpt-6-luna", "low"),
            "plan_streamer": ("gpt-6.1-terra", "medium"),
            "plan_attacker": ("gpt-6.1-sol", "medium"),
            "plan_security": ("gpt-6.1-sol", "high"),
            "plan_review": ("gpt-6-astra", "high"),
        }
        for task, allocation in expected.items():
            decision = choose_model(task)
            self.assertEqual((decision["model"], decision["reasoning_effort"]), allocation)
        profiles = policy["profiles"]
        self.assertEqual(profiles["economy"]["max_input_chars"], 24000)
        self.assertEqual(profiles["writing"]["max_input_chars"], 24000)
        self.assertEqual(profiles["research"]["max_input_chars"], 32000)
        self.assertEqual(profiles["engineering"]["max_input_chars"], 32000)
        self.assertEqual(profiles["principal_review"]["max_input_chars"], 40000)
        strategy = policy["token_saving_strategy"]
        self.assertEqual(strategy["mass_actor_execution"], "deterministic_scripts_not_llm_agents")
        self.assertEqual(strategy["state_transport"], "state_diffs_and_summaries_not_full_event_history")
        self.assertFalse(strategy["automatic_retry"])
        self.assertFalse(strategy["silent_model_fallback"])

    def test_shared_decision_provenance_and_single_executor_call(self):
        executor = Mock(return_value={"review": "done"})
        result = infer("plan_streamer", "Review", executor)
        self.assertEqual(result["decision"], choose_model("plan_streamer"))
        executor.assert_called_once_with(prompt="Review", decision=result["decision"])
        self.assertEqual(len(result["output_hash"]), 64)
        self.assertEqual(result["evidence_origin"], "injected_executor")

    def test_unknown_task_and_prompt_budget(self):
        with self.assertRaisesRegex(ValueError, "Unknown task"):
            choose_model("unknown")
        executor = Mock()
        with self.assertRaisesRegex(ValueError, "budget"):
            infer("plan_streamer", "x" * 24001, executor)
        executor.assert_not_called()

    def test_forbidden_scope_and_tasks_fail_before_io_or_executor(self):
        executor = Mock()
        with patch.object(Path, "read_bytes", side_effect=AssertionError("I/O")):
            for task, scope in (("plan_streamer", "gameplay"), ("gameplay_actor", "plan"),
                                ("chat_action", "plan"), ("development", "development")):
                with self.assertRaises(ValueError):
                    infer(task, "x", executor, scope=scope)
        executor.assert_not_called()

    def test_disabled_profile_and_invalid_budgets(self):
        policy = json.loads(DEFAULT_POLICY.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            policy["tasks"]["disabled_test"] = "legacy_4o"
            path.write_text(json.dumps(policy))
            with self.assertRaisesRegex(ValueError, "Disabled"):
                choose_model("disabled_test", policy_path=path)
            for budget in (0, -1, True, "100"):
                policy["profiles"]["economy"]["max_output_tokens"] = budget
                path.write_text(json.dumps(policy))
                with self.assertRaisesRegex(ValueError, "budget"):
                    choose_model("route_mapping", policy_path=path)

    def test_executor_errors_are_not_retried(self):
        executor = Mock(side_effect=RuntimeError("unavailable"))
        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            infer("plan_streamer", "review", executor)
        executor.assert_called_once()
