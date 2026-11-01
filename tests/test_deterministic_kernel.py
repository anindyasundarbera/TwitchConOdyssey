"""Synthetic, data-only checks; these do not run or validate gameplay."""
import ast
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from coordination.canonical_commands import (
    MAX_COMMAND_BYTES, MAX_COMMAND_NODES, make_command, validate_command,
)
from coordination.content_cache import (
    ContentCache, bytes_hash, canonical_bytes, canonical_hash, make_bindings,
    MAX_BINDING_STRING_BYTES, MAX_CACHE_VALUE_STRING_BYTES, MAX_JSON_CONTAINERS,
    MAX_JSON_DEPTH, MAX_JSON_INTEGER_BITS, MAX_JSON_NODES, MAX_JSON_STRING_BYTES,
    validate_json,
)
from coordination.scenario_inputs import GENERATOR_SPEC, generate_viewer_corpus, validate_corpus
from coordination.state_transport import (
    MAX_DELTA_OPERATIONS, MAX_DELTA_PATH_LENGTH, MAX_DELTA_STRING_BYTES,
    apply_diff, state_diff, summarize_diff,
)


def nested(value, depth):
    for _ in range(depth):
        value = [value]
    return value


def repeated_text_exceeding(byte_budget):
    return ["x" * 1024] * (byte_budget // 1024 + 1)


class CanonicalTests(unittest.TestCase):
    def test_admission_estimates_exact_bytes_and_accepts_boundaries(self):
        text = ''.join(chr(i) for i in range(32)) + '"\\é🤖'
        value = {text: [None, True, False, -0.0, 1.5, 1e20,
                        (1 << MAX_JSON_INTEGER_BITS) - 1]}
        size = len(canonical_bytes(value))
        self.assertEqual(validate_json(value), size)
        self.assertEqual(validate_json(value, max_bytes=size), size)
        with self.assertRaises(ValueError):
            validate_json(value, max_bytes=size - 1)
        self.assertEqual(canonical_hash(nested(None, MAX_JSON_DEPTH)),
                         canonical_hash(nested(None, MAX_JSON_DEPTH)))
        validate_json({"é": "é"}, max_depth=1, max_nodes=2,
                      max_containers=1, max_string_bytes=4)
        for limits in ({"max_depth": 0}, {"max_nodes": 1},
                       {"max_containers": 0}, {"max_string_bytes": 3}):
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                validate_json({"é": "é"}, **limits)
        with self.assertRaises(ValueError):
            validate_json("🤖" * 5, max_string_bytes=16)

    def test_invalid_or_amplifying_inputs_fail_before_serialization(self):
        cycle = {"loop": []}
        cycle["loop"].append(cycle)
        shared = []
        for _ in range(24):
            shared = [shared, shared]
        invalid = [nested(None, MAX_JSON_DEPTH + 1), cycle, shared,
                   [None] * MAX_JSON_NODES, [[]] * MAX_JSON_CONTAINERS,
                   repeated_text_exceeding(MAX_JSON_STRING_BYTES),
                   1 << MAX_JSON_INTEGER_BITS, "\ud800", {1: "bad"}, float("nan")]
        for index, value in enumerate(invalid):
            with self.subTest(index=index), patch(
                    "coordination.content_cache.json.dumps",
                    side_effect=AssertionError("Serialization reached")) as dumps:
                with self.assertRaises(ValueError):
                    canonical_bytes(value)
                dumps.assert_not_called()

    def test_shared_occurrences_are_counted_and_detached_independently(self):
        leaf = {"k": []}
        shared = [leaf, leaf]
        # Root + two occurrences of each dict/list, despite only three identities.
        validate_json(shared, max_nodes=5, max_containers=5, max_string_bytes=2)
        for limits in ({"max_nodes": 4}, {"max_containers": 4},
                       {"max_string_bytes": 1}):
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                validate_json(shared, **limits)
        detached = json.loads(canonical_bytes(shared))["value"]
        detached[0]["k"].append(1)
        self.assertEqual(detached[1]["k"], [])

    def test_stable_utf8_bytes_and_hash(self):
        first = {"z": [1, None, True], "a": "café"}
        second = {"a": "café", "z": [1, None, True]}
        self.assertEqual(canonical_bytes(first), canonical_bytes(second))
        self.assertEqual(canonical_bytes(first),
                         '{"canonical_version":1,"value":{"a":"café","z":[1,null,true]}}'.encode())
        self.assertEqual(canonical_hash(first), bytes_hash(canonical_bytes(second)))
        self.assertNotEqual(canonical_hash(first), canonical_hash({"a": "cafe"}))

    def test_invalid_json_values_rejected(self):
        cycle = []
        cycle.append(cycle)
        for invalid in (float("nan"), float("inf"), -float("inf"), {1: "x"},
                        (1, 2), {"bad": object()}, "\ud800", cycle):
            with self.subTest(invalid=repr(invalid)), self.assertRaises(ValueError):
                canonical_bytes(invalid)
        with self.assertRaises(ValueError):
            bytes_hash("text")


class CorpusTests(unittest.TestCase):
    def test_template_length_is_checked_before_strip(self):
        path = Path(__file__).resolve().parents[1] / "coordination" / "scenario_inputs.py"
        tree = ast.parse(path.read_text())
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef)
                        and node.name == "generate_viewer_corpus")
        predicate = next(node.elt for node in ast.walk(function)
                         if isinstance(node, ast.GeneratorExp))
        self.assertIsInstance(predicate, ast.BoolOp)
        self.assertIsInstance(predicate.op, ast.Or)
        # OR short-circuits in this order: reject type/size before scanning text.
        calls = [node.func.id if isinstance(node.func, ast.Name) else node.func.attr
                 for condition in predicate.values for node in ast.walk(condition)
                 if isinstance(node, ast.Call)]
        self.assertEqual(calls, ["type", "len", "strip"])
        for text in ("x" * 1001, " " * 1000 + "x" + " " * 1000):
            with self.subTest(length=len(text)), patch(
                    "coordination.scenario_inputs.canonical_hash") as fingerprint:
                with self.assertRaises(ValueError):
                    generate_viewer_corpus(1, 0, [text])
                fingerprint.assert_not_called()

    def test_public_generator_spec_mutation_cannot_change_corpus(self):
        original = copy.deepcopy(GENERATOR_SPEC)
        baseline = generate_viewer_corpus(42, 12, ["alpha", "beta"])
        try:
            GENERATOR_SPEC.clear()
            GENERATOR_SPEC.update({"id": "tampered", "version": 999})
            result = generate_viewer_corpus(42, 12, ["alpha", "beta"])
            self.assertEqual(canonical_bytes(result), canonical_bytes(baseline))
            for field in ("corpus_hash", "generator_id", "generator_hash"):
                self.assertEqual(result[field], baseline[field])
        finally:
            GENERATOR_SPEC.clear()
            GENERATOR_SPEC.update(original)

    def test_reproducible_and_recipe_bound(self):
        a = generate_viewer_corpus(42, 12, ["alpha", "beta"], start_tick=5, tick_stride=3)
        b = generate_viewer_corpus(42, 12, ["alpha", "beta"], start_tick=5, tick_stride=3)
        self.assertEqual(canonical_bytes(a), canonical_bytes(b))
        self.assertEqual(a["corpus_hash"], b["corpus_hash"])
        self.assertEqual(validate_corpus(a), a)
        for changed in (generate_viewer_corpus(43, 12, ["alpha", "beta"], start_tick=5, tick_stride=3),
                        generate_viewer_corpus(42, 12, ["alpha", "changed"], start_tick=5, tick_stride=3),
                        generate_viewer_corpus(42, 12, ["alpha", "beta"], start_tick=6, tick_stride=3),
                        generate_viewer_corpus(42, 12, ["alpha", "beta"], start_tick=5, tick_stride=4)):
            self.assertNotEqual(a["corpus_hash"], changed["corpus_hash"])
        for field in ("messages", "generator_hash", "template_hash", "corpus_hash"):
            altered = copy.deepcopy(a)
            if field == "messages":
                altered[field][0]["text"] = "tampered"
                altered["corpus_hash"] = canonical_hash({k: v for k, v in altered.items() if k != "corpus_hash"})
            else:
                altered[field] = "0" * 64
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_corpus(altered)

    def test_100k_fixture_capability(self):
        corpus = generate_viewer_corpus(123, 100000, ["synthetic"])
        self.assertEqual(len(corpus["messages"]), 100000)
        self.assertEqual(corpus["messages"][-1]["sequence"], 99999)
        self.assertEqual(corpus["provenance"], "fixture")
        self.assertEqual(corpus["evidence_origin"], "generated_fixture")
        self.assertEqual(validate_corpus(corpus), corpus)
        with self.assertRaises(ValueError):
            generate_viewer_corpus(123, 100001)

    def test_corpus_is_admitted_before_regeneration(self):
        corpus = generate_viewer_corpus(1, 1)
        corpus["messages"] = repeated_text_exceeding(MAX_JSON_STRING_BYTES)
        with patch("coordination.scenario_inputs.generate_viewer_corpus") as generate:
            with self.assertRaises(ValueError):
                validate_corpus(corpus)
            generate.assert_not_called()
        with patch("coordination.content_cache.json.dumps") as dumps:
            with self.assertRaises(ValueError):
                generate_viewer_corpus(1 << MAX_JSON_INTEGER_BITS, 100000)
            dumps.assert_not_called()


class CommandTests(unittest.TestCase):
    def test_command_admission_precedes_serialization(self):
        payloads = [{"text": "x" * MAX_COMMAND_BYTES},
                    {"text": "\x00" * (MAX_COMMAND_BYTES // 6)},
                    {"items": [None] * MAX_COMMAND_NODES}, {"deep": nested(None, 17)}]
        for payload in payloads:
            with self.subTest(kind=next(iter(payload))), patch(
                    "coordination.content_cache.json.dumps",
                    side_effect=AssertionError("Serialization reached")) as dumps:
                with self.assertRaises(ValueError):
                    make_command("proposal", "actor", "fixture", 0, 0, payload)
                dumps.assert_not_called()
        command = make_command("proposal", "actor", "fixture", 0, 0, {})
        command["payload"] = payloads[0]
        with patch("coordination.content_cache.json.dumps") as dumps:
            with self.assertRaises(ValueError):
                validate_command(command)
            dumps.assert_not_called()

    def test_command_byte_and_node_boundaries_remain_valid(self):
        base = make_command("proposal", "actor", "fixture", 0, 0, {"text": ""})
        body = {key: value for key, value in base.items() if key != "command_id"}
        available = MAX_COMMAND_BYTES - 100 - len(canonical_bytes(body))
        command = make_command("proposal", "actor", "fixture", 0, 0,
                               {"text": "x" * available})
        self.assertEqual(validate_command(command), command)
        with self.assertRaises(ValueError):
            make_command("proposal", "actor", "fixture", 0, 0,
                         {"text": "x" * (available + 1)})
        # Eight envelope nodes, the payload's list, and one reserved ID node.
        payload = {"items": [None] * (MAX_COMMAND_NODES - 10)}
        command = make_command("proposal", "actor", "fixture", 0, 0, payload)
        self.assertEqual(validate_command(command), command)
        payload["items"].append(None)
        with self.assertRaises(ValueError):
            make_command("proposal", "actor", "fixture", 0, 0, payload)

    def test_identity_provenance_and_detachment(self):
        payload = {"b": [1], "a": 2}
        command = make_command("proposal.move", "actor-1", "fixture", 2, 3, payload)
        self.assertEqual(command, make_command("proposal.move", "actor-1", "fixture", 2, 3,
                                               {"a": 2, "b": [1]}))
        self.assertNotEqual(command["command_id"], make_command(
            "proposal.move", "actor-1", "human", 2, 3, payload)["command_id"])
        payload["b"].append(3)
        validated = validate_command(command)
        validated["payload"]["b"].append(4)
        self.assertEqual(command["payload"]["b"], [1])
        # Validation only returns data: repeated validation neither executes nor
        # establishes eligibility or idempotent application of this command.
        self.assertEqual(validate_command(command), validate_command(command))
        self.assertIn("idempotent application or execution", validate_command.__doc__)

    def test_strict_fields_and_tampering(self):
        command = make_command("proposal", "actor", "bot", 0, 1, {"x": 1})
        changes = [lambda c: c.update(extra=1), lambda c: c.pop("actor_id"),
                   lambda c: c.update(provenance="human"),
                   lambda c: c["payload"].update(x=2), lambda c: c.update(command_id="0" * 64),
                   lambda c: c.update(logical_tick=True), lambda c: c.update(kind="INVALID")]
        for mutate in changes:
            altered = copy.deepcopy(command)
            mutate(altered)
            with self.subTest(command=altered), self.assertRaises(ValueError):
                validate_command(altered)
        for provenance in ("unknown", "", None):
            with self.assertRaises(ValueError):
                make_command("proposal", "actor", provenance, 0, 0, {})


class StateTransportTests(unittest.TestCase):
    def test_delta_admission_precedes_serialization_or_copy(self):
        base = state_diff({}, {})
        invalid = []
        for operation in (
                {"op": "set", "path": ["x"],
                 "value": repeated_text_exceeding(MAX_DELTA_STRING_BYTES)},
                {"op": "set", "path": ["x"] * (MAX_DELTA_PATH_LENGTH + 1), "value": 1},
                {"op": "set", "path": [], "value": nested(None, MAX_JSON_DEPTH)}):
            invalid.append({**base, "operations": [operation]})
        invalid.append({**base, "operations": [
            {"op": "delete", "path": ["x"]}] * (MAX_DELTA_OPERATIONS + 1)})
        for index, delta in enumerate(invalid):
            with self.subTest(index=index), patch(
                    "coordination.content_cache.json.dumps",
                    side_effect=AssertionError("Serialization reached")) as dumps:
                with self.assertRaises(ValueError):
                    apply_diff({}, delta)
                with self.assertRaises(ValueError):
                    summarize_diff(delta)
                dumps.assert_not_called()

    def test_delta_operation_boundary_and_generated_overflow(self):
        after = {f"key-{i}": i for i in range(MAX_DELTA_OPERATIONS)}
        delta = state_diff({}, after)
        self.assertEqual(len(delta["operations"]), MAX_DELTA_OPERATIONS)
        self.assertEqual(apply_diff({}, delta), after)
        after["extra"] = 0
        with self.assertRaises(ValueError):
            state_diff({}, after)

    def test_nested_round_trip_and_detachment(self):
        before = {"nested": {"remove": 1, "keep": [1]}, "slash/~": {"value": None}}
        after = {"nested": {"keep": [2], "add": {"x": 3}}, "slash/~": {"value": 4}}
        original = copy.deepcopy(before)
        delta = state_diff(before, after)
        self.assertIn({"op": "delete", "path": ["nested", "remove"]}, delta["operations"])
        result = apply_diff(before, delta)
        self.assertEqual(result, after)
        self.assertEqual(before, original)
        result["nested"]["add"]["x"] = 8
        after["nested"]["add"]["x"] = 9
        self.assertEqual(apply_diff(before, delta)["nested"]["add"]["x"], 3)
        self.assertEqual(apply_diff(before, state_diff(before, before)), before)

    def test_root_replacement_and_tampering(self):
        delta = state_diff({"old": 1}, ["new", {"v": 2}])
        self.assertEqual(delta["operations"][0]["path"], [])
        self.assertEqual(apply_diff({"old": 1}, delta), ["new", {"v": 2}])
        with self.assertRaises(ValueError):
            apply_diff({"old": 2}, delta)
        for field in ("base_hash", "result_hash"):
            bad = copy.deepcopy(delta)
            bad[field] = "0" * 64
            with self.subTest(field=field), self.assertRaises(ValueError):
                apply_diff({"old": 1}, bad)
        bad = copy.deepcopy(delta)
        bad["operations"][0]["value"][0] = "tampered"
        with self.assertRaises(ValueError):
            apply_diff({"old": 1}, bad)

    def test_summary_is_bounded_and_omits_values(self):
        secret = "VALUE_SHOULD_NOT_APPEAR"
        delta = state_diff({}, {f"key-{i}": secret for i in range(30)})
        text = summarize_diff(delta, max_operations=3, max_chars=300)
        summary = json.loads(text)
        self.assertLessEqual(len(text), 300)
        self.assertNotIn(secret, text)
        self.assertEqual(summary["operation_count"], 30)
        self.assertLessEqual(len(summary["changes"]), 3)
        self.assertEqual(summary["omitted_count"], 30 - len(summary["changes"]))
        self.assertTrue(all(set(change) == {"op", "path"} for change in summary["changes"]))


class CacheTests(unittest.TestCase):
    def test_cache_inputs_are_admitted_before_serialization(self):
        h = canonical_hash("x")
        binding = make_bindings(plan_hash=h, policy_hash=h, context_hashes={},
                                corpus_hash=h, code_hashes={})
        invalid_binding = {**binding, "context_hashes": {
            "x" * (MAX_BINDING_STRING_BYTES + 1): h}}
        cache = ContentCache()
        for supplied, value in (
                (binding, repeated_text_exceeding(MAX_CACHE_VALUE_STRING_BYTES)),
                (invalid_binding, {}), (binding, nested(None, MAX_JSON_DEPTH))):
            with patch("coordination.content_cache.json.dumps",
                       side_effect=AssertionError("Serialization reached")) as dumps:
                with self.assertRaises(ValueError):
                    cache.put(supplied, value)
                dumps.assert_not_called()
        self.assertEqual(cache._entries, {})

    def test_cache_string_boundary_is_admitted(self):
        h = canonical_hash("x")
        binding = make_bindings(plan_hash=h, policy_hash=h, context_hashes={},
                                corpus_hash=h, code_hashes={})
        cache = ContentCache()
        with patch("coordination.content_cache.MAX_CACHE_VALUE_STRING_BYTES", 8):
            cache.put(binding, {"k": "x" * 7})
            self.assertEqual(cache.get(binding)["value"], {"k": "x" * 7})
            with patch("coordination.content_cache.json.dumps") as dumps:
                with self.assertRaises(ValueError):
                    cache.put(binding, {"k": "x" * 8})
                dumps.assert_not_called()

    def test_bindings_hits_misses_invalidation_and_detachment(self):
        h = lambda value: canonical_hash(value)
        binding = make_bindings(plan_hash=h("plan"), policy_hash=h("policy"),
                                context_hashes={"context": h("context")}, corpus_hash=h("corpus"),
                                code_hashes={"code": h("code")}, result_hash=h({"items": [1]}))
        cache = ContentCache()
        value = {"items": [1]}
        cache.put(binding, value)
        value["items"].append(2)
        hit = cache.get(binding)
        self.assertEqual(hit["value"], {"items": [1]})
        self.assertEqual(hit["evidence_origin"], "cache_reuse")
        self.assertIs(hit["new_evidence"], False)
        hit["value"]["items"].append(3)
        self.assertEqual(cache.get(binding)["value"], {"items": [1]})
        for field in ("plan_hash", "policy_hash", "context_hashes", "corpus_hash", "code_hashes", "result_hash"):
            changed = copy.deepcopy(binding)
            if field in ("context_hashes", "code_hashes"):
                changed[field][next(iter(changed[field]))] = h("changed")
            else:
                changed[field] = h("changed")
            with self.subTest(field=field):
                self.assertIsNone(cache.get(changed))
        with self.assertRaises(ValueError):
            cache.put(binding, {"items": [9]})
        self.assertTrue(cache.invalidate(binding))
        self.assertIsNone(cache.get(binding))
        self.assertFalse(cache.invalidate(binding))

    def test_corrupt_bytes_and_rehashed_invalid_record_rejected(self):
        h = canonical_hash("x")
        binding = make_bindings(plan_hash=h, policy_hash=h, context_hashes={}, corpus_hash=h,
                                code_hashes={})
        cache = ContentCache()
        key = cache.put(binding, {"x": 1})
        digest, raw = cache._entries[key]
        cache._entries[key] = (digest, raw + b" ")
        with self.assertRaises(ValueError):
            cache.get(binding)
        record = json.loads(raw)["value"]
        record["new_evidence"] = True
        altered = canonical_bytes(record)
        cache._entries[key] = (bytes_hash(altered), altered)
        with self.assertRaises(ValueError):
            cache.get(binding)


class ImportBoundaryTests(unittest.TestCase):
    def test_kernel_static_imports_are_data_only(self):
        root = Path(__file__).resolve().parents[1] / "coordination"
        allowed = {
            "hashlib", "json", "math", "re", "content_cache", "copy", "fractions",
            "typing", "canonical_commands", "state_transport", "deterministic_kernel"
        }
        for name in ("content_cache", "scenario_inputs", "canonical_commands", "state_transport", "deterministic_kernel"):
            tree = ast.parse((root / f"{name}.py").read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for item in node.names:
                        self.assertIn(item.name, allowed, f"{name}: {item.name}")
                elif isinstance(node, ast.ImportFrom):
                    self.assertIn(node.module, allowed, f"{name}: {node.module}")
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotEqual(node.func.id, "__import__", name)


class DualConsumerSdcBindingTests(unittest.TestCase):
    def test_server_engine_imports_and_exposes_sdc_primitives(self):
        import coordination.full_game_simulator as fgs
        import server.engine as engine

        self.assertIs(engine.FullGameSimulator, fgs.FullGameSimulator)
        self.assertIs(engine.replay_command_stream, fgs.replay_command_stream)
        self.assertIs(engine.evaluate_independent_oracles, fgs.evaluate_independent_oracles)
        self.assertEqual(engine.HZ, fgs.HZ)
        self.assertEqual(engine.PLANNING_TICKS, fgs.PLANNING_TICKS)
        self.assertEqual(engine.RESOLUTION_TICKS, fgs.RESOLUTION_TICKS)
        self.assertEqual(engine.REWARD_TICKS, fgs.REWARD_TICKS)
        self.assertEqual(engine.TURN_TICKS, fgs.TURN_TICKS)
        self.assertEqual(engine.MATCH_DEADLINE_TICKS, fgs.MATCH_DEADLINE_TICKS)
        self.assertIs(engine.make_command, make_command)
        self.assertIs(engine.validate_command, validate_command)
        self.assertIs(engine.canonical_hash, canonical_hash)
        self.assertIs(engine.state_diff, state_diff)
        self.assertIs(engine.apply_diff, apply_diff)
        self.assertEqual(engine.DISTRICTS, tuple(d["name"] for d in fgs.DISTRICTS))

        # Verify legacy Engine construction and snapshot compatibility remain intact
        legacy = engine.Engine(k=4)
        snap = legacy.snapshot()
        self.assertEqual(snap["tick"], 0)
        self.assertEqual(snap["district"], engine.DISTRICTS[0])

        # Verify S1EngineAdapter wraps FullGameSimulator cleanly
        adapter = engine.S1EngineAdapter(seed=42, initial_lane=1, initial_roster=["viewer_a", "viewer_b"])
        self.assertIsInstance(adapter.simulator, fgs.FullGameSimulator)
        self.assertEqual(adapter.tick, 0)
        self.assertEqual(adapter.phase, "planning")
        self.assertEqual(adapter.status, "racing")
        self.assertEqual(adapter.state_hash(), canonical_hash(adapter.snapshot()))

    def test_negative_fixture_and_bot_hazard_isolation_and_tampered_replay_rejection(self):
        import server.engine as engine

        sim = engine.create_s1_simulator(seed=42, initial_lane=1, initial_roster=["acct_1", "acct_2"])
        bot_cmd = engine.make_command(
            "hazard.propose", "bot_actor", "bot", 0, 1,
            {"hazard_id": "haz_bot_1", "kind": "blocked_demo_lane", "lane": 1},
        )
        self.assertEqual(sim.submit_command(bot_cmd), "rejected")
        self.assertEqual(sim.pool, 0)
        self.assertEqual(sim.synthetic_fixture_pool, 0)

        fixture_cmd = engine.make_command(
            "hazard.propose", "fixture_actor", "fixture", 1, 2,
            {"hazard_id": "haz_fix_1", "kind": "blocked_demo_lane", "lane": 1},
        )
        self.assertEqual(sim.submit_command(fixture_cmd), "applied")
        self.assertEqual(sim.pool, 0)
        self.assertEqual(sim.synthetic_fixture_pool, 20)

        sim.step()
        sim.finalize_trace()
        expected_hash = engine.canonical_hash(sim.get_canonical_state())
        replayed = engine.verify_s1_replay(
            seed=42,
            initial_lane=1,
            initial_roster=["acct_1", "acct_2"],
            command_log=sim.command_history,
            steps_to_run=1,
            expected_final_state_hash=expected_hash,
        )
        self.assertEqual(replayed["final_state_hash"], expected_hash)
        self.assertEqual(replayed["pool"], 0)
        self.assertEqual(replayed["synthetic_fixture_pool"], 20)

        # Negative test: tampered expected_final_state_hash raises ValueError
        with self.assertRaises(ValueError):
            engine.verify_s1_replay(
                seed=42,
                initial_lane=1,
                initial_roster=["acct_1", "acct_2"],
                command_log=sim.command_history,
                steps_to_run=1,
                expected_final_state_hash="0" * 64,
            )

        # Negative test: tampered command log entry raises ValueError
        tampered_log = copy.deepcopy(sim.command_history)
        tampered_log[1]["state_hash"] = "f" * 64
        with self.assertRaises(ValueError):
            engine.verify_s1_replay(
                seed=42,
                initial_lane=1,
                initial_roster=["acct_1", "acct_2"],
                command_log=tampered_log,
                steps_to_run=1,
            )


class DeterministicKernelRemediationTests(unittest.TestCase):
    """Test matrix TST-01 through TST-20 covering deadline, warning, purity, parity, and invariants."""

    def test_tst01_delivery_at_1799(self):
        """TST-01: Delivery at tick 1799 is eligible; settlement occurs."""
        from coordination.deterministic_kernel import is_delivery_before_deadline
        import coordination.full_game_simulator as fgs

        self.assertTrue(is_delivery_before_deadline(1798, 1799))
        sim = fgs.FullGameSimulator(initial_tick=1798, initial_progress=99.9375, base_speed_override=1.25)
        sim.step()
        self.assertEqual(sim.status, "delivered")
        self.assertEqual(sim.tick, 1799)
        self.assertIsNotNone(sim.terminal_settlement)
        self.assertEqual(sim.terminal_settlement["status"], "delivered")
        self.assertEqual(sim.terminal_settlement["tick"], 1799)

    def test_tst02_delivery_at_1800(self):
        """TST-02: Delivery at tick 1800 is not eligible; deadline wipe wins; settlement is exactly zero."""
        from coordination.deterministic_kernel import is_delivery_before_deadline
        import coordination.full_game_simulator as fgs

        self.assertFalse(is_delivery_before_deadline(1799, 1800))
        sim = fgs.FullGameSimulator(initial_tick=1799, initial_progress=99.9375, base_speed_override=1.25)
        sim.step()
        self.assertEqual(sim.status, "wiped")
        self.assertEqual(sim.tick, 1800)
        self.assertIsNotNone(sim.terminal_settlement)
        self.assertEqual(sim.terminal_settlement["status"], "wiped")
        self.assertEqual(sim.terminal_settlement["reason"], "deadline_equality_wipe")
        self.assertEqual(sim.terminal_settlement["total_hype"], 0)
        self.assertEqual(sim.terminal_settlement["streamer_share"], 0)
        self.assertEqual(sim.terminal_settlement["audience_share_total"], 0)

    def test_tst03_delivery_at_1801(self):
        """TST-03: Delivery at tick 1801 is not eligible; no settlement."""
        from coordination.deterministic_kernel import is_delivery_before_deadline
        import coordination.full_game_simulator as fgs

        self.assertFalse(is_delivery_before_deadline(1800, 1801))
        sim = fgs.FullGameSimulator(initial_tick=1800, initial_progress=100.0)
        sim.step()
        self.assertEqual(sim.status, "wiped")
        self.assertEqual(sim.terminal_settlement["total_hype"], 0)

    def test_tst04_tst07_warning_boundaries(self):
        """TST-04..TST-07: Warning activity is half-open interval [300, 400)."""
        from coordination.deterministic_kernel import hazard_warning_active
        import coordination.full_game_simulator as fgs

        committed = {"hazard_id": "haz_t1", "committed_tick": 50}
        self.assertFalse(hazard_warning_active(committed, 299))   # TST-04
        self.assertTrue(hazard_warning_active(committed, 300))    # TST-05
        self.assertTrue(hazard_warning_active(committed, 399))    # TST-06
        self.assertFalse(hazard_warning_active(committed, 400))   # TST-07
        self.assertFalse(hazard_warning_active(committed, 450))   # In resolution
        self.assertFalse(hazard_warning_active(committed, 500))   # In reward

        # Verify on FullGameSimulator
        sim = fgs.FullGameSimulator()
        sim.submit_command(make_command("hazard.propose", "u0", "human", 10, 1, {"hazard_id": "h1", "lane": 1}))
        for _ in range(299):
            sim.step()
        self.assertFalse(sim.warning_active)
        sim.step()
        self.assertEqual(sim.tick, 300)
        self.assertTrue(sim.warning_active)

    def test_tst08_warning_hazard_id_mismatch(self):
        """TST-08: Committed hazard ID mismatch produces inactive warning state."""
        from coordination.deterministic_kernel import hazard_warning_active
        import coordination.full_game_simulator as fgs

        committed = {"hazard_id": "committed_haz_1", "committed_tick": 50}
        self.assertTrue(hazard_warning_active(committed, 350, target_hazard_id="committed_haz_1"))
        self.assertFalse(hazard_warning_active(committed, 350, target_hazard_id="wrong_hazard_id"))
        self.assertFalse(hazard_warning_active(None, 350))

        sim = fgs.FullGameSimulator()
        sim.submit_command(make_command("hazard.propose", "u0", "human", 10, 1, {"hazard_id": "h_real", "lane": 1}))
        for _ in range(350):
            sim.step()
        mismatch_cmd = make_command("viewer.counter", "u1", "human", 350, 2, {"hazard_id": "h_fake", "counter": "clear_lane"})
        res = sim.submit_command(mismatch_cmd)
        self.assertEqual(res, "rejected")

    def test_tst09_command_at_1799_applies_before_deadline(self):
        """TST-09: Command at 1799 applies before deadline boundary."""
        import coordination.full_game_simulator as fgs

        sim = fgs.FullGameSimulator(initial_tick=1798, initial_lane=1)
        cmd = make_command("streamer.steer", "s0", "human", 1799, 1, {"direction": "left"})
        res = sim.submit_command(cmd)
        self.assertEqual(res, "applied")
        self.assertEqual(sim.transition_target_lane, 0)
        sim.step()
        self.assertEqual(sim.tick, 1799)
        self.assertEqual(sim.status, "racing")

    def test_tst10_command_at_1800_wipe_wins(self):
        """TST-10: Command at 1800 with deadline at 1800 -> wipe wins; command does not apply."""
        import coordination.full_game_simulator as fgs

        sim = fgs.FullGameSimulator(initial_tick=1800, initial_lane=1)
        cmd = make_command("streamer.steer", "s0", "human", 1800, 1, {"direction": "left"})
        res = sim.submit_command(cmd)
        sim.step()
        self.assertEqual(sim.status, "wiped")
        self.assertEqual(sim.terminal_settlement["total_hype"], 0)

    def test_tst11_event_tick_preservation(self):
        """TST-11: State and trace record actual event tick, not settlement tick."""
        import coordination.full_game_simulator as fgs

        sim = fgs.FullGameSimulator(initial_tick=1798, initial_progress=99.9375, base_speed_override=1.25)
        sim.step()
        self.assertEqual(sim.tick, 1799)
        delivery_events = [e for e in sim.events if e.get("kind") == "delivery_settlement"]
        self.assertTrue(len(delivery_events) > 0)
        self.assertEqual(delivery_events[0]["tick"], 1799)

    def test_tst12_purity(self):
        """TST-12: Shared kernel performs no file, network, clock, or process I/O."""
        import coordination.deterministic_kernel as dk
        forbidden_attrs = ["time", "datetime", "socket", "urllib", "requests", "os", "sys"]
        for attr in forbidden_attrs:
            self.assertFalse(hasattr(dk, attr), f"Purity violation: {attr} exposed in deterministic_kernel")

    def test_tst13_authority_shared_functions(self):
        """TST-13: Engine and simulator call the shared functions; no duplicate transition logic."""
        import coordination.deterministic_kernel as dk
        import coordination.full_game_simulator as fgs
        import server.engine as engine

        self.assertIs(engine.advance_tick, dk.advance_tick)
        self.assertIs(engine.is_delivery_before_deadline, dk.is_delivery_before_deadline)
        self.assertIs(engine.hazard_warning_active, dk.hazard_warning_active)
        self.assertIs(engine.evaluate_scenario_properties, dk.evaluate_scenario_properties)
        self.assertIs(fgs.is_delivery_before_deadline, dk.is_delivery_before_deadline)
        self.assertIs(fgs.hazard_warning_active, dk.hazard_warning_active)
        self.assertIs(fgs.evaluate_scenario_properties, dk.evaluate_scenario_properties)

    def test_tst14_tst15_replay_parity(self):
        """TST-14 & TST-15: Engine and simulator produce identical states, events, and replays."""
        import coordination.full_game_simulator as fgs
        import server.engine as engine

        sim = engine.create_s1_simulator(seed=42, initial_lane=1, initial_roster=["u1", "u2"])
        cmd = engine.make_command("streamer.steer", "s0", "human", 0, 1, {"direction": "right"})
        sim.submit_command(cmd)
        sim.step()
        sim.finalize_trace()

        expected_hash = engine.canonical_hash(sim.get_canonical_state())
        replayed = engine.verify_s1_replay(
            seed=42, initial_lane=1, initial_roster=["u1", "u2"],
            command_log=sim.command_history, steps_to_run=1, expected_final_state_hash=expected_hash,
        )
        self.assertEqual(replayed["final_state_hash"], expected_hash)

    def test_tst16_tst18_pipeline_invariants(self):
        """TST-16..TST-18: Six pipeline invariants pass with complete evidence, fail on tamper/missing."""
        import coordination.deterministic_kernel as dk

        good_bundle = {
            "review_invocation": {
                "reviewer_author": "gpt-6-astra", "agent_id": "subagent-1",
                "route": "codex_subagent/gpt-6-astra", "configured_gate_satisfied": True,
            },
            "review_text": "Verdict: READY\nAll checks passed.",
            "new_run_id": "full-game-20261101T200000Z-12345678",
            "old_run_id": "full-game-20261101T174648Z-2647e033",
            "old_run_tree_sha256_before": "hash_a",
            "old_run_tree_sha256_after": "hash_a",
            "manifest": {"a.txt": "sha_a"},
            "recomputed_hashes": {"a.txt": "sha_a"},
            "source_bindings": {"s.py": {"sha256": "sha_s"}},
            "recomputed_source_hashes": {"s.py": "sha_s"},
            "matrix": [{"scenario_id": "S1", "invariants_tested": ["INV-A"]}],
            "per_invariant_results": [{"scenario_id": "S1", "invariant_id": "INV-A", "status": "PASS"}],
            "readiness": {"ready": True, "submission_ready": False},
            "review_verdict": "READY",
            "evidence_passed": True,
        }

        # TST-16: All 6 pass on good evidence
        r_auth = dk.validate_review_authorship(good_bundle)
        r_imm = dk.validate_run_immutability(good_bundle)
        r_cit = dk.validate_citation_hashes(good_bundle)
        r_src = dk.validate_source_bytes(good_bundle)
        r_cov = dk.validate_evidence_coverage(good_bundle)
        r_sep = dk.validate_readiness_separation(good_bundle)
        self.assertEqual(r_auth["status"], "PASS")
        self.assertEqual(r_imm["status"], "PASS")
        self.assertEqual(r_cit["status"], "PASS")
        self.assertEqual(r_src["status"], "PASS")
        self.assertEqual(r_cov["status"], "PASS")
        self.assertEqual(r_sep["status"], "PASS")

        # TST-17: Missing evidence produces FAIL
        bad_auth = dk.validate_review_authorship({})
        self.assertEqual(bad_auth["status"], "FAIL")

        # TST-18: Tampered trace or hash mismatch produces FAIL
        tampered_cit = dk.validate_citation_hashes({"manifest": {"a.txt": "sha_a"}, "recomputed_hashes": {"a.txt": "sha_tampered"}})
        self.assertEqual(tampered_cit["status"], "FAIL")

        # Readiness true while review is REVISE produces FAIL
        bad_readiness = dk.validate_readiness_separation({
            "readiness": {"ready": True, "submission_ready": False},
            "review_verdict": "REVISE",
            "evidence_passed": True,
        })
        self.assertEqual(bad_readiness["status"], "FAIL")

    def test_tst19_generic_oracle_pass_declared_property_fail(self):
        """TST-19: Generic oracle passes but declared property fails -> scenario fails, failing property reported."""
        import coordination.deterministic_kernel as dk

        contract = {
            "scenario_id": "TEST-SCEN",
            "invariants_tested": ["INV-BOT-ISOLATION"],
            "expected_oracle": {"expected_final_status": "racing"},
        }
        # Bot command applied (violating INV-BOT-ISOLATION)
        cmd_log = [{"cmd": {"provenance": "bot", "kind": "hazard.propose"}, "status": "applied"}]
        state = {"status": "racing", "bounty": {"pool": 20}}
        results = dk.evaluate_scenario_properties(contract, cmd_log, [], (state, state))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["invariant_id"], "INV-BOT-ISOLATION")
        self.assertEqual(results[0]["status"], "FAIL")

    def test_tst20_undeclared_invariant_excluded(self):
        """TST-20: Undeclared invariant is NOT evaluated and excluded from results."""
        import coordination.deterministic_kernel as dk

        contract = {
            "scenario_id": "TEST-SCEN",
            "invariants_tested": ["INV-SAFETY-CAPS"],
        }
        results = dk.evaluate_scenario_properties(contract, [], [], ({}, {}))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["invariant_id"], "INV-SAFETY-CAPS")
        self.assertNotIn("INV-BOT-ISOLATION", [r["invariant_id"] for r in results])


if __name__ == "__main__":
    unittest.main()
