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
        allowed = {"hashlib", "json", "math", "re", "content_cache"}
        for name in ("content_cache", "scenario_inputs", "canonical_commands", "state_transport"):
            tree = ast.parse((root / f"{name}.py").read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for item in node.names:
                        self.assertIn(item.name, allowed, name)
                elif isinstance(node, ast.ImportFrom):
                    self.assertIn(node.module, allowed, name)
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotEqual(node.func.id, "__import__", name)


if __name__ == "__main__":
    unittest.main()
