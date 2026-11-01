import ast
import builtins
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from coordination import context_contract as contract
from coordination.content_cache import bytes_hash, canonical_bytes, canonical_hash
from coordination.model_router import choose_model


class ContextContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.policy = json.loads((contract.ROOT / contract.DEFAULT_POLICY).read_bytes())
        # Fixtures copy only declared local source bytes, never import their code.
        for name in self.policy["required_paths"]:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((contract.ROOT / name).read_bytes())
        self.write_policy()

    def write_policy(self):
        (self.root / contract.DEFAULT_POLICY).write_text(json.dumps(self.policy))

    def refresh(self, name):
        self.policy["required_paths"][name] = bytes_hash((self.root / name).read_bytes())
        self.write_policy()

    def compile(self, task="development", phase="plan", owned_paths=()):
        return contract.compile_packet(task, phase, owned_paths, root=self.root)

    def test_deterministic_packet_and_hash(self):
        paths = ["AGENTS.md", "coordination/context_contract.py"]
        first = self.compile(owned_paths=paths)
        second = self.compile(owned_paths=list(reversed(paths)) + paths)
        self.assertEqual(canonical_bytes(first), canonical_bytes(second))
        expected = dict(first)
        self.assertEqual(expected.pop("packet_hash"), canonical_hash(expected))
        self.assertEqual(first["owned_paths"], sorted(paths))
        self.assertEqual(first["owned_path_bindings"], [
            {"path": name, "state": "existing", "sha256": first["required_paths"][name]}
            for name in sorted(paths)])
        self.assertNotIn("timestamp", first)

    def test_must_have_directives_gate_and_selected_decisions(self):
        packet = self.compile()
        self.assertTrue(contract.MUST_HAVE.issubset({d["id"] for d in packet["directives"]}))
        self.assertFalse(packet["gate"]["gameplay_enabled"])
        self.assertFalse(packet["gate"]["automatic_phase_advance"])
        self.assertEqual(packet["precedence"], contract.PRECEDENCE)
        self.assertEqual(packet["return_limit_words"], 250)
        decisions = packet["selected_decisions"]
        self.assertEqual({item["id"] for item in decisions}, contract.DECISION_IDS)
        for item in decisions:
            self.assertEqual(item["status"], contract.SELECTED_STATUS)
            self.assertEqual(item["gate"], "before_gameplay")
            self.assertEqual(item["contract"], contract.SELECTED_DECISIONS[item["id"]])
            self.assertIn(item["source_path"], packet["required_paths"])
            self.assertEqual(item["evidence_origin"], "project_design_inference")
        self.assertEqual([item["id"] for item in packet["unresolved_decisions"]],
                         ["failover_and_hotfix_trust"])
        for item in packet["directives"]:
            self.assertEqual(item["wording"], "normalized")
            self.assertIsNone(item["exact_user_wording"])
            self.assertEqual(item["wording_availability"], "unavailable")

    def test_selected_decisions_reject_missing_duplicate_cross_list_and_invalid_fields(self):
        baseline = copy.deepcopy(self.policy)
        mutations = [
            lambda p: p.pop("selected_decisions"),
            lambda p: p["selected_decisions"].pop(),
            lambda p: p["selected_decisions"].append(copy.deepcopy(p["selected_decisions"][0])),
            lambda p: p["selected_decisions"][1].update(id="D-01"),
            lambda p: p["selected_decisions"][0].update(id="D-09"),
            lambda p: p["selected_decisions"][0].update(id=[]),
            lambda p: p["selected_decisions"][0].update(contract="clock_contract"),
            lambda p: p["selected_decisions"][0].update(status="verified"),
            lambda p: p["selected_decisions"][0].update(gate="after_gameplay"),
            lambda p: p["selected_decisions"][0].update(source_path="unbound.md"),
            lambda p: p["selected_decisions"][0].update(source_locator=""),
            lambda p: p["selected_decisions"][0].update(evidence_origin="observed_gameplay"),
            lambda p: p["selected_decisions"][0].update(rule=""),
            lambda p: p["required_paths"].pop(contract.SELECTED_SOURCE),
            lambda p: p["unresolved_decisions"][0].update(id="D-01"),
            lambda p: p["unresolved_decisions"][0].update(id="player_agency"),
            lambda p: p["unresolved_decisions"].append(copy.deepcopy(p["unresolved_decisions"][0])),
        ]
        for index, mutate in enumerate(mutations):
            self.policy = copy.deepcopy(baseline)
            mutate(self.policy)
            self.write_policy()
            with self.subTest(mutation=index), self.assertRaises(ValueError):
                self.compile()

    def test_review_response_decisions_are_emitted_with_closed_gate_and_bound_history(self):
        packet = self.compile("complex_coding_debugging")
        decisions = {item["id"]: item for item in packet["selected_decisions"]}
        expected = {
            "D-01": ("planning, resolution and reward until terminal state",),
            "D-02": ("half-open [0,15.000s)", "entire [15,20) interval",
                     "no hazard, warning or increment", "committed hazard ID"),
            "D-03": ("half-open planning interval [0,20)", "committed hazard ID"),
            "D-04": ("no interim payout", "exactly one final settlement",
                     "immediately ends active simulation"),
            "D-05": ("exactly 5.0s reward", "never turn 4",
                     "deadline first, phase-close, pause request",
                     "clear_lane removal, collision adjudication, delivery detection, one final settlement",
                     "Pause cannot suspend a reached deadline", "planning t=15 for hazards, t=20"),
        }
        for ident, phrases in expected.items():
            for phrase in phrases:
                self.assertIn(phrase, decisions[ident]["rule"])
            self.assertEqual(decisions[ident]["status"], contract.SELECTED_STATUS)
        self.assertEqual(packet["ledger_revision"], 7)
        self.assertFalse(packet["gate"]["gameplay_enabled"])
        for name in ("docs/planning/S1-ASTRA-REVIEW.md",
                     "docs/planning/S1-ASTRA-REVIEW-RESPONSE.md"):
            self.assertEqual(packet["required_paths"][name],
                             bytes_hash((self.root / name).read_bytes()))
        history = [item for item in self.policy["superseded_decisions"]
                   if item.get("superseded_in_revision") == 7]
        self.assertEqual({item["superseded_by"] for item in history}, contract.DECISION_IDS)
        for item in history:
            self.assertEqual(item["status"], "superseded")
            self.assertEqual(item["prior_status"], contract.SELECTED_STATUS)
            self.assertEqual(item["prior_source_sha256"],
                             "d5216ff1c73f08153003f38077f67c59813b52b05e27d1a89a937c0636117266")
        self.assertNotIn("superseded_decisions", packet)

    def test_bounded_subagents_is_mandatory_active_and_emitted(self):
        packet = self.compile()
        directive = next(item for item in packet["directives"]
                         if item["id"] == "bounded_subagents")
        self.assertEqual(directive["topic"], "bounded_delegation")
        self.assertEqual(directive["wording"], "normalized")
        for text in ("background research or development", "subagents", "configured task model and effort",
                     "owned files", "acceptance criteria", "compact compiler packet",
                     "main session", "summary", "never automatic or open-ended"):
            self.assertIn(text, directive["rule"])
        self.policy["common_directive_ids"].remove("bounded_subagents")
        self.write_policy()
        with self.assertRaisesRegex(ValueError, "mandatory directive"):
            self.compile()
        self.policy["common_directive_ids"].append("bounded_subagents")
        record = next(item for item in self.policy["directives"]
                      if item["id"] == "bounded_subagents")
        record.update(status="superseded", superseded_by="model_allocation")
        successor = next(item for item in self.policy["directives"]
                         if item["id"] == "model_allocation")
        successor["supersedes"] = ["bounded_subagents"]
        self.write_policy()
        with self.assertRaisesRegex(ValueError, "inactive"):
            self.compile()

    def test_configured_routing_and_policy_hash_for_current_tasks(self):
        expected = {
            "development": ("gpt-6.1-sol", "high"),
            "research_synthesis_long_doc": ("gpt-6.1-sol", "medium"),
            "extraction_classification": ("gpt-6-luna", "low"),
            "everyday_writing_summarization": ("gpt-6.1-terra", "medium"),
            "plan_review": ("gpt-6-astra", "high"),
            "simulation_preparation": ("gpt-6.1-sol", "high"),
        }
        for task, allocation in expected.items():
            packet = self.compile(task)
            decision = packet["routing_decision"]
            self.assertEqual((decision["model"], decision["reasoning_effort"]), allocation)
            routing_task = "development" if task == "simulation_preparation" else task
            self.assertEqual(decision, choose_model(
                routing_task, scope="plan", policy_path=self.root / contract.MODEL_POLICY))
            self.assertEqual(decision["policy_hash"], packet["required_paths"][contract.MODEL_POLICY])
            self.assertEqual(packet["directive_policy"]["sha256"], bytes_hash(
                (self.root / contract.DEFAULT_POLICY).read_bytes()))

    def test_every_ledger_task_and_data_driven_selection(self):
        for task in self.policy["tasks"]:
            self.compile(task)
        for task, expected in (("development", True), ("extraction_classification", False)):
            ids = {d["id"] for d in self.compile(task)["directives"]}
            self.assertEqual("code_workflow" in ids, expected)

    def test_forbidden_or_unknown_task_phase_reads_only_ledger(self):
        original = Path.read_bytes
        reads = []

        def read(path):
            reads.append(path)
            self.assertEqual(path, self.root / contract.DEFAULT_POLICY)
            return original(path)

        with patch.object(Path, "read_bytes", read), patch(
                "coordination.model_router.choose_model", side_effect=AssertionError("router I/O")):
            for task, phase in (("gameplay_actor", "plan"), ("chat_action", "plan"),
                                ("development", "gameplay"), ("development", "simulation"),
                                ("development", "unknown"), ("unknown", "plan")):
                with self.assertRaisesRegex(ValueError, "task/phase"):
                    self.compile(task, phase, owned_paths=["server/app.py"])
        self.assertEqual(len(reads), 6)

    def test_configuration_cannot_enable_gameplay(self):
        self.policy["gate"]["gameplay_enabled"] = True
        self.write_policy()
        with self.assertRaisesRegex(ValueError, "gate"):
            self.compile()
        self.policy["gate"]["gameplay_enabled"] = False
        self.policy["allowed_phases"].append("gameplay")
        self.write_policy()
        with self.assertRaisesRegex(ValueError, "task/phase"):
            self.compile(phase="gameplay")
        with self.assertRaisesRegex(ValueError, "phase"):
            self.compile()

    def test_unsafe_owned_and_source_paths_fail_before_source_reads(self):
        original = Path.read_bytes

        def read(path):
            self.assertEqual(path, self.root / contract.DEFAULT_POLICY)
            return original(path)

        unsafe = ["../escape", "/tmp/escape", "./AGENTS.md", "a/../AGENTS.md",
                  "a//b", "AGENTS.md/", "a\\b", "C:/escape", "", "."]
        for path in unsafe:
            with self.subTest(path=path), patch.object(Path, "read_bytes", read):
                with self.assertRaisesRegex(ValueError, "relative"):
                    self.compile(owned_paths=[path])
        self.policy["required_paths"]["../escape"] = "0" * 64
        self.write_policy()
        with patch.object(Path, "read_bytes", read):
            with self.assertRaisesRegex(ValueError, "relative"):
                self.compile()

    def test_out_of_root_symlink_targets_and_invalid_ancestors(self):
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other) / "outside.txt"
            outside.write_text("outside")
            (self.root / "link.txt").symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "symlink"):
                self.compile(owned_paths=["link.txt"])
            (self.root / "parent-link").symlink_to(Path(other), target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "out-of-root"):
                self.compile(owned_paths=["parent-link/new/sub/file.py"])
            (self.root / "dangling.txt").symlink_to(self.root / "missing.txt")
            with self.assertRaisesRegex(ValueError, "symlink"):
                self.compile(owned_paths=["dangling.txt"])
            (self.root / "internal-link.txt").symlink_to(self.root / "AGENTS.md")
            with self.assertRaisesRegex(ValueError, "symlink"):
                self.compile(owned_paths=["internal-link.txt"])
        with self.assertRaisesRegex(ValueError, "Invalid"):
            self.compile(owned_paths=["AGENTS.md/new/sub/file.py"])
        with self.assertRaisesRegex(ValueError, "required path"):
            self.compile(owned_paths=["docs"])

    def test_planned_nested_owned_path_is_explicit_then_hashes_created_bytes(self):
        name = "new/sub/file.py"
        before = self.compile(owned_paths=[name])
        self.assertEqual(before["owned_paths"], [name])
        self.assertEqual(before["owned_path_bindings"], [
            {"path": name, "state": "planned", "sha256": None}])
        self.assertNotIn(name, before["required_paths"])
        self.assertFalse((self.root / "new").exists())
        path = self.root / name
        path.parent.mkdir(parents=True)
        path.write_bytes(b"new source bytes")
        after = self.compile(owned_paths=[name])
        self.assertEqual(after["owned_path_bindings"], [
            {"path": name, "state": "existing", "sha256": bytes_hash(path.read_bytes())}])
        self.assertNotEqual(before["packet_hash"], after["packet_hash"])

    def test_required_binding_changed_bytes_and_reconciled_hash(self):
        before = self.compile()
        source = "docs/planning/CONTEXT-v2.md"
        path = self.root / source
        path.write_bytes(path.read_bytes() + b"\nchanged fixture bytes\n")
        with self.assertRaisesRegex(ValueError, "Changed required source hash"):
            self.compile()
        self.refresh(source)
        after = self.compile()
        self.assertNotEqual(before["required_paths"][source], after["required_paths"][source])
        self.assertNotEqual(before["packet_hash"], after["packet_hash"])
        for name, digest in after["required_paths"].items():
            self.assertEqual(digest, bytes_hash((self.root / name).read_bytes()))

    def test_owned_bytes_change_packet_and_ledger_bytes_are_bound(self):
        path = self.root / "owned.txt"
        path.write_bytes(b"one")
        before = self.compile(owned_paths=["owned.txt"])
        path.write_bytes(b"two")
        after = self.compile(owned_paths=["owned.txt"])
        self.assertNotEqual(before["packet_hash"], after["packet_hash"])
        raw = (self.root / contract.DEFAULT_POLICY).read_bytes()
        (self.root / contract.DEFAULT_POLICY).write_bytes(raw + b"\n")
        newer = self.compile(owned_paths=["owned.txt"])
        self.assertNotEqual(newer["directive_policy"], after["directive_policy"])

    def test_missing_required_source_or_binding(self):
        (self.root / "AGENTS.md").unlink()
        with self.assertRaisesRegex(ValueError, "Missing"):
            self.compile()
        del self.policy["required_paths"]["docs/planning/GAMEPLAN-v2.md"]
        self.write_policy()
        with self.assertRaisesRegex(ValueError, "source bindings"):
            self.compile()

    def test_superseded_entry_retained_but_never_selected(self):
        old = next(item for item in self.policy["directives"]
                   if item["id"] == "setting_previous_city")
        self.assertEqual(old["status"], "superseded")
        self.assertEqual(old["superseded_by"], "setting_san_diego")
        ids = {d["id"] for d in self.compile()["directives"]}
        self.assertNotIn(old["id"], ids)
        self.policy["tasks"]["development"]["directive_ids"].append(old["id"])
        self.write_policy()
        with self.assertRaisesRegex(ValueError, "inactive"):
            self.compile()

    def test_conflicts_missing_directives_and_malformed_data_fail_closed(self):
        baseline = copy.deepcopy(self.policy)
        mutations = [
            lambda p: p["conflicts"].append("unresolved"),
            lambda p: p["common_directive_ids"].remove("manual_escalation"),
            lambda p: p["directives"].pop(2),
            lambda p: p["directives"].append(dict(p["directives"][2], id="conflict")),
            lambda p: p["directives"][0].update(superseded_by="absent"),
            lambda p: p["directives"][2].update(provenance=[]),
            lambda p: p["directives"][2].update(exact_user_wording="fabricated quotation"),
            lambda p: p["unresolved_decisions"].pop(0),
            lambda p: p["required_paths"].update({"AGENTS.md": "invalid hash"}),
            lambda p: p.update(schema_version=True),
            lambda p: p["forbidden_actions"].remove("server.app"),
            lambda p: p["unresolved_decisions"][0].update(id=[]),
            lambda p: p["directives"][0].update(superseded_by=[]),
        ]
        for index, mutate in enumerate(mutations):
            self.policy = copy.deepcopy(baseline)
            mutate(self.policy)
            self.write_policy()
            with self.subTest(mutation=index), self.assertRaises(ValueError):
                self.compile()

    def test_exact_wording_must_exist_verbatim_in_bound_record(self):
        item = self.policy["directives"][2]
        item.update(wording="exact", wording_availability="recorded_verbatim",
                    exact_user_wording="Invented exact user quote")
        self.write_policy()
        with self.assertRaisesRegex(ValueError, "absent from bound provenance"):
            self.compile()
        source = item["provenance"][0]["path"]
        with (self.root / source).open("a") as output:
            output.write("\nInvented exact user quote\n")
        self.refresh(source)
        self.compile()

    def test_duplicate_json_keys_are_rejected(self):
        path = self.root / contract.DEFAULT_POLICY
        path.write_text('{"schema_version":1,"schema_version":2}')
        with self.assertRaisesRegex(ValueError, "ledger JSON"):
            self.compile()

    def test_bound_model_policy_duplicate_json_keys_are_rejected(self):
        path = self.root / contract.MODEL_POLICY
        raw = path.read_text()
        path.write_text(raw.replace('"version": 3,', '"version": 2,"version": 3,', 1))
        self.refresh(contract.MODEL_POLICY)
        with patch("coordination.model_router.choose_model", side_effect=AssertionError("router")):
            with self.assertRaisesRegex(ValueError, "model policy JSON"):
                self.compile()

    def test_packet_budget_is_enforced_and_config_cannot_raise_cap(self):
        model_path = self.root / contract.MODEL_POLICY
        model_policy = json.loads(model_path.read_bytes())
        model_policy["profiles"]["engineering"]["max_input_chars"] = 100
        model_path.write_text(json.dumps(model_policy))
        self.refresh(contract.MODEL_POLICY)
        with self.assertRaisesRegex(ValueError, "character budget"):
            self.compile()
        model_policy["profiles"]["engineering"]["max_input_chars"] = 40001
        model_path.write_text(json.dumps(model_policy))
        self.refresh(contract.MODEL_POLICY)
        with self.assertRaisesRegex(ValueError, "directive limits"):
            self.compile()
        model_policy["profiles"]["engineering"]["max_input_chars"] = 32000
        model_policy["token_saving_strategy"]["automatic_retry"] = True
        model_path.write_text(json.dumps(model_policy))
        self.refresh(contract.MODEL_POLICY)
        with self.assertRaisesRegex(ValueError, "conflicts"):
            self.compile()

    def test_oversized_policy_is_rejected(self):
        path = self.root / contract.DEFAULT_POLICY
        path.write_bytes(b" " * (contract.MAX_POLICY_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "byte budget"):
            self.compile()

    def test_no_runtime_imports_network_models_or_subprocess(self):
        source = (contract.ROOT / "coordination/context_contract.py").read_text()
        imports = [node.module for node in ast.walk(ast.parse(source))
                   if isinstance(node, ast.ImportFrom)]
        imports += [alias.name for node in ast.walk(ast.parse(source))
                    if isinstance(node, ast.Import) for alias in node.names]
        self.assertTrue(set(imports).issubset({"argparse", "json", "pathlib",
                                            "content_cache", "model_router"}))
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name.split(".")[0] in {"server", "providers", "harness"}:
                raise AssertionError("Runtime import")
            return original_import(name, *args, **kwargs)

        with patch("socket.socket", side_effect=AssertionError("network")), patch(
                "subprocess.Popen", side_effect=AssertionError("subprocess")), patch(
                "coordination.model_router.infer", side_effect=AssertionError("inference")), patch(
                "builtins.__import__", guarded_import):
            packet = self.compile("simulation_preparation")
        self.assertEqual(packet["evidence_origin"], "local_directive_compilation")

    def test_cli_canonical_packet_and_validation_smoke(self):
        output = io.StringIO()
        with patch("sys.stdout", output):
            contract.main(["--task", "development", "--phase", "plan",
                           "--owned-path", "coordination/context_contract.py"])
        envelope = json.loads(output.getvalue())
        self.assertEqual(envelope["canonical_version"], 1)
        packet = envelope["value"]
        self.assertEqual(packet["task"], "development")
        self.assertEqual(output.getvalue(), canonical_bytes(packet).decode() + "\n")
        output = io.StringIO()
        with patch("sys.stdout", output):
            contract.main(["--task", "extraction_classification", "--validate-only"])
        self.assertTrue(json.loads(output.getvalue())["value"]["validated"])


if __name__ == "__main__":
    unittest.main()
