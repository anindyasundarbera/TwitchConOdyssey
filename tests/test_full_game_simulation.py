"""Comprehensive positive and negative anti-forgery test suite for the full-game simulation pipeline."""

import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from coordination.review_boundary import record_external_review
from coordination.canonical_commands import make_command
from coordination.content_cache import canonical_hash, require_hash
from coordination.evidence_pipeline import (
    AUTHORIZATION_TOKEN,
    PRESERVED_REJECTED_RUN_ID,
    PRESERVED_REJECTED_TREE_SHA256,
    compute_development_readiness,
    compute_tree_sha256,
    create_immutable_run_root,
    derive_feature_statuses,
    derive_run_id,
    file_sha256,
    prepare_pending_review_packet,
    verify_independent_review_artifact,
    verify_scenario_trace_integrity,
    write_exclusive_json,
    write_exclusive_text,
)
from coordination.full_game_simulator import (
    FullGameSimulator,
    MATCH_DEADLINE_TICKS,
    TURN_TICKS,
    evaluate_independent_oracles,
    execute_frozen_scenario,
    validate_scenario_contract,
)
from coordination.run_full_game_simulation import (
    build_feature_specs,
    build_frozen_scenario_contracts,
    run_finalize_stage,
    run_simulation_stage,
)

ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS_ROOT = ROOT / "artifacts/simulations/full-game"
REJECTED_DIR = SIMULATIONS_ROOT / PRESERVED_REJECTED_RUN_ID
REJECTED_MANIFEST_SHA256 = "bf34da0ef4764dfd86857aafa3ea9f864cfb98a34f7dadf0af7cad07f1904cf6"


class FullGameSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp_dir = tempfile.TemporaryDirectory()
        cls.temp_root = Path(cls._temp_dir.name)
        cls.sim_run_id = "full-game-20261101T140000Z-a1b2c3d4"

        # Stage 1: Execute simulation stage in isolated tempdir
        cls.run_dir = run_simulation_stage(
            output_root=cls.temp_root,
            run_id=cls.sim_run_id,
            authorize_token=AUTHORIZATION_TOKEN,
        )

        # Capture pre-review state assertions immediately after Stage 1
        cls.stage1_review_packet_exists = (cls.run_dir / "REVIEW-PACKET.md").is_file()
        cls.stage1_independent_review_exists = (cls.run_dir / "INDEPENDENT-REVIEW.md").exists()
        cls.stage1_readiness_exists = (cls.run_dir / "DEVELOPMENT-READINESS.json").exists()
        cls.stage1_manifest_exists = (cls.run_dir / "RUN-MANIFEST.json").exists()

        # Simulate external independent review artifact creation between Stage 1 and Stage 2
        packet_sha = file_sha256(cls.run_dir / "REVIEW-PACKET.md")
        review_md_text = (
            f"# Independent Systems Review — `{cls.sim_run_id}`\n\n"
            "- **Reviewer:** `gpt-6-astra` (`high` reasoning effort)\n"
            f"- **Bound Review Packet SHA-256:** `{packet_sha}`\n"
            "- **Verdict:** `READY`\n\n"
            "All 46 frozen scenario contracts, state-diff traces, and Revision 5 bindings verified.\n"
        )
        invocation_data = {
            "verdict": "READY", "configured_model": "gpt-6-astra",
            "configured_effort": "high", "configured_provider": "codex_subagent",
            "reviewer_model": "gpt-6-astra", "reviewer_effort": "high",
            "reviewer_provider": "codex_subagent",
            "configured_model_available": True, "configured_gate_satisfied": True,
            "gate_binding": "configured_gate",
            "evidence_origin": "independent_subagent_review",
            "subagent_conversation_id": "fixture-conversation-not-a-real-review",
            "packet_hash": packet_sha, "review_packet_sha256": packet_sha,
            "prompt_sha256": hashlib.sha256(b"test-only-review-prompt").hexdigest(),
        }
        # This is explicitly a mocked transport fixture, never real review evidence.
        record_external_review(
            cls.run_dir, review_markdown=review_md_text,
            review_json={"verdict": "READY"}, invocation=invocation_data,
        )

        # Stage 2: Execute finalize stage in isolated tempdir
        run_finalize_stage(output_root=cls.temp_root, run_id=cls.sim_run_id)

    @classmethod
    def tearDownClass(cls):
        cls._temp_dir.cleanup()

    def test_preserved_rejected_run_remains_byte_for_byte_unchanged(self):
        self.assertTrue(REJECTED_DIR.is_dir(), f"Missing preserved rejected run: {REJECTED_DIR}")
        files = [p for p in REJECTED_DIR.rglob("*") if p.is_file()]
        self.assertEqual(len(files), 116)
        self.assertEqual(compute_tree_sha256(REJECTED_DIR), PRESERVED_REJECTED_TREE_SHA256)

        manifest_path = REJECTED_DIR / "RUN-MANIFEST.json"
        self.assertEqual(file_sha256(manifest_path), REJECTED_MANIFEST_SHA256)

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for rel_path, expected_hash in manifest["artifact_hashes"].items():
            full_path = REJECTED_DIR / rel_path
            self.assertTrue(full_path.is_file(), f"Missing rejected artifact: {rel_path}")
            self.assertEqual(file_sha256(full_path), expected_hash)

    def test_negative_validators_reject_defective_baseline_artifacts(self):
        # AUDIT-05: Placeholder command stream and summary-only trace in rejected run
        with self.assertRaises(ValueError):
            verify_scenario_trace_integrity("SCEN-CTRL-01", REJECTED_DIR)
        with self.assertRaises(ValueError):
            verify_scenario_trace_integrity("SCEN-E2E-01", REJECTED_DIR)

        # AUDIT-08: Placeholder non-SHA-256 corpus hash in rejected run
        rejected_corpus_manifest = json.loads(
            (REJECTED_DIR / "CORPUS-MANIFEST.json").read_text(encoding="utf-8")
        )
        self.assertEqual(rejected_corpus_manifest["sha256"], "42-reused-corpus-100k")
        with self.assertRaises(ValueError):
            require_hash(rejected_corpus_manifest["sha256"])

        # AUDIT-06: Placeholder non-SHA-256 candidate plan hash in rejected run
        rejected_readiness = json.loads(
            (REJECTED_DIR / "DEVELOPMENT-READINESS.json").read_text(encoding="utf-8")
        )
        self.assertEqual(rejected_readiness["candidate_plan_hash"], "rev5-candidate-bound")
        with self.assertRaises(ValueError):
            require_hash(rejected_readiness["candidate_plan_hash"])

        # AUDIT-02: Generic string oracle in rejected SCENARIO-MATRIX.json fails contract validation
        rejected_matrix = json.loads(
            (REJECTED_DIR / "SCENARIO-MATRIX.json").read_text(encoding="utf-8")
        )
        with self.assertRaises(ValueError):
            validate_scenario_contract(rejected_matrix[0])

        # AUDIT-01 & AUDIT-09: Missing REVIEW-INVOCATION.json and pre-hashed DEVELOPMENT-READINESS.json
        with self.assertRaises(ValueError):
            verify_independent_review_artifact(REJECTED_DIR)

        with tempfile.TemporaryDirectory() as tmp:
            copy_dir = Path(tmp) / "defective-review-copy"
            shutil.copytree(REJECTED_DIR, copy_dir)
            fake_hash = "a" * 64
            (copy_dir / "REVIEW-INVOCATION.json").write_text(json.dumps({
                "evidence_origin": "subagent_invocation",
                "subagent_conversation_id": "conv-test", "packet_hash": fake_hash,
                "prompt_sha256": fake_hash,
                "independent_review_sha256": file_sha256(copy_dir / "INDEPENDENT-REVIEW.md"),
                "verdict": "READY",
            }))
            with self.assertRaisesRegex(ValueError, "AUDIT-09"):
                verify_independent_review_artifact(copy_dir)

    def test_negative_fixture_and_bot_provenance_cannot_mint_live_hype_or_quorum(self):
        sim = FullGameSimulator(seed=77, initial_lane=1, initial_roster=["human_1", "human_2"])

        # Bot hazard proposal is rejected and mints zero pool
        bot_haz = make_command(
            "hazard.propose", "bot_actor", "bot", 10, 1, {"hazard_id": "haz_bot", "lane": 1}
        )
        self.assertEqual(sim.submit_command(bot_haz), "rejected")
        self.assertEqual(sim.pool, 0)
        self.assertEqual(sim.synthetic_fixture_pool, 0)
        self.assertIsNone(sim.committed_hazard)

        # Fixture hazard proposal applies to synthetic_fixture_pool only, never live pool
        fix_haz = make_command(
            "hazard.propose", "fixture_actor", "fixture", 20, 2, {"hazard_id": "haz_fix", "lane": 1}
        )
        self.assertEqual(sim.submit_command(fix_haz), "applied")
        self.assertEqual(sim.pool, 0)
        self.assertEqual(sim.synthetic_fixture_pool, 20)

        # Bot and fixture counter votes are rejected and cannot affect human clear_lane quorum
        bot_vote = make_command(
            "viewer.counter", "human_1", "bot", 30, 3, {"hazard_id": "haz_fix", "counter": "clear_lane"}
        )
        fix_vote = make_command(
            "viewer.counter", "human_2", "fixture", 31, 4, {"hazard_id": "haz_fix", "counter": "clear_lane"}
        )
        self.assertEqual(sim.submit_command(bot_vote), "rejected")
        self.assertEqual(sim.submit_command(fix_vote), "rejected")
        self.assertEqual(len(sim.counter_votes), 0)
        self.assertEqual(len(sim.eligible_audience), 0)

        # Advance across resolution start (tick 400): clear_lane must fail with 0 valid human votes
        while sim.tick <= 400:
            sim.step()
        self.assertFalse(sim.hazard_countered)

        # Steer away and run to delivery: live total_hype must be 0
        sim.submit_command(make_command("streamer.steer", "streamer", "human", sim.tick, 5, {"direction": "left"}))
        while sim.status == "racing" and sim.tick < MATCH_DEADLINE_TICKS:
            sim.step()
        self.assertEqual(sim.status, "delivered")
        self.assertEqual(sim.terminal_settlement["total_hype"], 0)
        self.assertEqual(sim.terminal_settlement["streamer_share"], 0)
        self.assertEqual(sim.terminal_settlement["audience_share_total"], 0)
        self.assertEqual(sim.terminal_settlement["synthetic_fixture_hype_illustrated"], 20)
        self.assertFalse(sim.terminal_settlement["live_participant_minted_from_fixture"])

        # AUDIT-02 & AUDIT-03: Independent oracle rejects synthetic state with inflated live pool
        contracts = build_frozen_scenario_contracts()
        aud03_contract = next(c for c in contracts if c["scenario_id"] == "SCEN-AUD-03")
        bundle = execute_frozen_scenario(aud03_contract)
        self.assertTrue(bundle["passed"])

        forged_bundle = copy.deepcopy(bundle)
        forged_bundle["final_state"]["bounty"]["pool"] = 20
        forged_bundle["final_state_hash"] = canonical_hash(forged_bundle["final_state"])
        oracle_res = evaluate_independent_oracles(aud03_contract, forged_bundle)
        self.assertFalse(oracle_res["passed"])
        self.assertTrue(
            any("AUDIT-03" in msg or "INV-BOT-ISOLATION" in msg for msg in oracle_res["failures"]),
            f"Expected AUDIT-03 failure in {oracle_res['failures']}",
        )

    def test_negative_feature_coverage_cannot_fabricate_passed_for_unobserved_render(self):
        feature_specs = build_feature_specs()
        contracts = build_frozen_scenario_contracts()
        synthetic_scenario_results = [
            {
                "scenario_id": c["scenario_id"],
                "verdict": "passed",
                "features": list(c["features_exercised"]),
                "invariants_passed": list(c["invariants_tested"]),
            }
            for c in contracts
        ]

        inventory, summary = derive_feature_statuses(
            feature_specs,
            synthetic_scenario_results,
            render_observed=False,
            audio_observed=False,
            live_service_observed=False,
        )
        by_id = {entry["feature_id"]: entry for entry in inventory}

        feat14 = by_id["FEAT-14-READABILITY-AND-HUD"]
        self.assertEqual(feat14["status"], "not_observed")
        self.assertEqual(feat14["coverage_state"], "not_observed")

        for partial_id in (
            "FEAT-12-BULLET-TIME-PRESENTATION",
            "FEAT-13-ADAPTIVE-AUDIO",
            "FEAT-15-PUBLIC-DEMO-TIMELINE",
        ):
            feat = by_id[partial_id]
            self.assertEqual(feat["coverage_state"], "partially_observed_state_only")
            self.assertEqual(feat["state_contract_status"], "passed")
            self.assertTrue(len(feat["unobserved_sub_claims"]) >= 1)

        self.assertEqual(summary["total_active_features"], 16)
        self.assertEqual(summary["covered_features"], 12)
        self.assertEqual(summary["partially_observed_state_only_features"], 3)
        self.assertEqual(summary["not_observed_features"], 1)

        # Fabricating FEAT-14 as covered when render_observed=False must fail readiness gate
        with tempfile.TemporaryDirectory() as tmp:
            copy_dir = Path(tmp) / "forged-coverage"
            copy_dir.mkdir(parents=True, exist_ok=True)
            forged_inv = json.loads((self.run_dir / "FEATURE-INVENTORY.json").read_text(encoding="utf-8"))
            for item in forged_inv:
                item["status"] = "passed"
                item["coverage_state"] = "covered"
            (copy_dir / "FEATURE-INVENTORY.json").write_text(json.dumps(forged_inv, indent=2), encoding="utf-8")
            shutil.copy2(self.run_dir / "COVERAGE.json", copy_dir / "COVERAGE.json")
            readiness = compute_development_readiness(
                copy_dir,
                candidate_plan_hash=file_sha256(ROOT / "docs/planning/GAMEPLAN-v2.md"),
                blocking_issues_count=0,
                unresolved_human_decisions=[],
                all_invariants_passed=True,
                all_scenarios_passed=True,
                golden_replay_verified=True,
                corpus_hash_valid=True,
                all_traces_substantive=True,
                review_verdict="READY",
                independent_review_verified=True,
            )
            self.assertFalse(readiness["gates"]["feature_coverage_honestly_derived"])
            self.assertFalse(readiness["ready"])

    def test_negative_simulator_cannot_author_independent_review_or_overwrite_run_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            valid_id = "full-game-20261101T150000Z-12345678"

            # Missing authorization token fails closed
            with self.assertRaises(PermissionError):
                create_immutable_run_root(base, valid_id, "AUTHORIZE_COMPLETE_GAME_SIMULATION=false")

            # Preserved rejected run ID is always rejected
            with self.assertRaises(ValueError):
                create_immutable_run_root(base, PRESERVED_REJECTED_RUN_ID, AUTHORIZATION_TOKEN)
            with self.assertRaises(ValueError):
                derive_run_id("a8e33043" + "0" * 56, utc_timestamp="20261101T102226Z")

            # Creating a valid run root once succeeds; creating it a second time raises FileExistsError
            run_root = create_immutable_run_root(base, valid_id, AUTHORIZATION_TOKEN)
            with self.assertRaises(FileExistsError):
                create_immutable_run_root(base, valid_id, AUTHORIZATION_TOKEN)

            # Simulator mode (allow_external_review=False) cannot write INDEPENDENT-REVIEW.md or .json
            with self.assertRaises(PermissionError):
                write_exclusive_text(run_root / "INDEPENDENT-REVIEW.md", "# Forged Review\n")
            with self.assertRaises(PermissionError):
                write_exclusive_json(run_root / "INDEPENDENT-REVIEW.json", {"verdict": "READY"})
            for name in ("INDEPENDENT-REVIEW.md", "INDEPENDENT-REVIEW.json",
                         "REVIEW-INVOCATION.json", "MODEL-USAGE.json"):
                for flags in ({}, {"allow_external_review": True}, {"forbid_synthetic_review": False}):
                    with self.subTest(name=name, flags=flags), self.assertRaises(PermissionError):
                        write_exclusive_text(run_root / name, "forged", **flags)

            # Overwriting an existing file via write_exclusive_text fails closed
            sample_file = run_root / "SAMPLE.txt"
            write_exclusive_text(sample_file, "first write")
            with self.assertRaises(FileExistsError):
                write_exclusive_text(sample_file, "second write")

            # Writing inside any path bearing PRESERVED_REJECTED_RUN_ID fails closed
            fake_preserved = base / PRESERVED_REJECTED_RUN_ID
            fake_preserved.mkdir(parents=True, exist_ok=True)
            with self.assertRaises(PermissionError):
                write_exclusive_text(fake_preserved / "TAMPER.txt", "forbidden")

            # REVIEW-PACKET.md helper refuses to pre-hash post-review artifacts
            with self.assertRaises(ValueError):
                prepare_pending_review_packet(
                    run_root,
                    valid_id,
                    artifact_rel_paths=["DEVELOPMENT-READINESS.json"],
                )

    def test_negative_readiness_is_false_when_any_gate_fails(self):
        # Verify baseline tempdir run is ready
        baseline_readiness = compute_development_readiness(self.run_dir)
        self.assertTrue(baseline_readiness["ready"])
        self.assertFalse(baseline_readiness["submission_ready"])

        with tempfile.TemporaryDirectory() as tmp:
            copy_dir = Path(tmp) / self.run_dir.name
            shutil.copytree(self.run_dir, copy_dir)

            orig_issues = (copy_dir / "ISSUES.json").read_text(encoding="utf-8")
            orig_invs = (copy_dir / "INVARIANT-RESULTS.json").read_text(encoding="utf-8")
            orig_reg = (copy_dir / "REGRESSION-RESULTS.json").read_text(encoding="utf-8")
            orig_trace = (copy_dir / "traces/SCEN-CTRL-01.jsonl").read_text(encoding="utf-8")
            orig_invoc = (copy_dir / "REVIEW-INVOCATION.json").read_text(encoding="utf-8")

            # 1. Open issue in ISSUES.json
            issues = json.loads(orig_issues)
            issues[0]["status"] = "open"
            (copy_dir / "ISSUES.json").write_text(json.dumps(issues, indent=2), encoding="utf-8")
            res = compute_development_readiness(
                copy_dir,
                all_traces_substantive=True,
                review_verdict="READY",
                independent_review_verified=True,
            )
            self.assertFalse(res["gates"]["all_s0_s1_blocking_s2_issues_closed"])
            self.assertFalse(res["ready"])

            # 2. Closed issue with non-SHA-256 placeholder resolution_hash
            issues = json.loads(orig_issues)
            issues[0]["resolution_hash"] = "rev5-placeholder"
            (copy_dir / "ISSUES.json").write_text(json.dumps(issues, indent=2), encoding="utf-8")
            res = compute_development_readiness(
                copy_dir,
                all_traces_substantive=True,
                review_verdict="READY",
                independent_review_verified=True,
            )
            self.assertFalse(res["gates"]["all_s0_s1_blocking_s2_issues_closed"])
            self.assertFalse(res["ready"])
            (copy_dir / "ISSUES.json").write_text(orig_issues, encoding="utf-8")

            # 3. Unresolved human decision
            res_decision = compute_development_readiness(
                copy_dir,
                unresolved_human_decisions=["D-06"],
                all_traces_substantive=True,
                review_verdict="READY",
                independent_review_verified=True,
            )
            self.assertFalse(res_decision["gates"]["no_unresolved_blocking_decisions"])
            self.assertFalse(res_decision["ready"])

            # 4. Placeholder candidate_plan_hash
            res_plan_hash = compute_development_readiness(
                copy_dir,
                candidate_plan_hash="rev5-candidate-bound",
                all_traces_substantive=True,
                review_verdict="READY",
                independent_review_verified=True,
            )
            self.assertFalse(res_plan_hash["gates"]["candidate_plan_hash_bound_and_matches"])
            self.assertFalse(res_plan_hash["ready"])

            # 5. Failed invariant in INVARIANT-RESULTS.json
            invs = json.loads(orig_invs)
            invs[0]["passed"] = False
            (copy_dir / "INVARIANT-RESULTS.json").write_text(json.dumps(invs, indent=2), encoding="utf-8")
            res = compute_development_readiness(
                copy_dir,
                all_traces_substantive=True,
                review_verdict="READY",
                independent_review_verified=True,
            )
            self.assertFalse(res["gates"]["all_scenario_invariants_passed"])
            self.assertFalse(res["ready"])
            (copy_dir / "INVARIANT-RESULTS.json").write_text(orig_invs, encoding="utf-8")

            # 6. Failed scenario in REGRESSION-RESULTS.json
            reg = json.loads(orig_reg)
            reg["scenarios_passed"] = 45
            reg["scenarios_failed"] = 1
            (copy_dir / "REGRESSION-RESULTS.json").write_text(json.dumps(reg, indent=2), encoding="utf-8")
            res = compute_development_readiness(
                copy_dir,
                all_traces_substantive=True,
                review_verdict="READY",
                independent_review_verified=True,
            )
            self.assertFalse(res["gates"]["all_scenarios_passed"])
            self.assertFalse(res["ready"])
            (copy_dir / "REGRESSION-RESULTS.json").write_text(orig_reg, encoding="utf-8")

            # 7. Placeholder trace in traces/SCEN-CTRL-01.jsonl
            (copy_dir / "traces/SCEN-CTRL-01.jsonl").write_text(
                json.dumps(
                    {
                        "scenario_id": "SCEN-CTRL-01",
                        "final_status": "racing",
                        "final_tick": 25,
                        "state_hash": "0" * 64,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            res = compute_development_readiness(
                copy_dir, review_verdict="READY", independent_review_verified=True
            )
            self.assertFalse(res["gates"]["all_traces_substantive"])
            self.assertFalse(res["ready"])
            (copy_dir / "traces/SCEN-CTRL-01.jsonl").write_text(orig_trace, encoding="utf-8")

            # 8. Missing or REVISE or synthetic independent review
            (copy_dir / "REVIEW-INVOCATION.json").unlink()
            res_missing = compute_development_readiness(copy_dir, all_traces_substantive=True)
            self.assertFalse(res_missing["gates"]["independent_review_verified"])
            self.assertFalse(res_missing["ready"])
            (copy_dir / "REVIEW-INVOCATION.json").write_text(orig_invoc, encoding="utf-8")

            res_revise = compute_development_readiness(
                copy_dir,
                all_traces_substantive=True,
                review_verdict="REVISE",
                independent_review_verified=True,
            )
            self.assertFalse(res_revise["gates"]["review_verdict_is_ready"])
            self.assertFalse(res_revise["ready"])

            # 9. Verified review served by a substituted (non-configured) reviewer model.
            substituted = json.loads(orig_invoc)
            substituted["configured_model"] = "gpt-6-astra"
            substituted["configured_model_available"] = False
            substituted["reviewer_model"] = "ollama-cloud/kimi-k3"
            substituted["reviewer_effort"] = "high"
            substituted["reviewer_provider"] = "ollama-cloud"
            substituted["gate_binding"] = "substitute_reviewer_authorized_by_requester"
            substituted["configured_gate_satisfied"] = False
            substitute_dir = Path(tmp) / "substitute" / self.run_dir.name
            shutil.copytree(self.run_dir, substitute_dir)
            for name in ("INDEPENDENT-REVIEW.md", "INDEPENDENT-REVIEW.json", "REVIEW-INVOCATION.json",
                         "MODEL-USAGE.json", "DEVELOPMENT-READINESS.json", "README.md", "RUN-MANIFEST.json"):
                (substitute_dir / name).unlink()
            record_external_review(substitute_dir, review_markdown="Verdict: READY\nTest substitute fixture.\n",
                                   review_json={"verdict": "READY"}, invocation=substituted)
            res_substitute = compute_development_readiness(substitute_dir, all_traces_substantive=True)
            self.assertTrue(res_substitute["independent_review_verified"])
            self.assertFalse(res_substitute["gates"]["independent_review_uses_configured_gate"])
            self.assertFalse(res_substitute["ready"])
            (copy_dir / "REVIEW-INVOCATION.json").write_text(orig_invoc, encoding="utf-8")

            # Restored baseline still passes every gate after the mutation round-trip.
            self.assertTrue(compute_development_readiness(copy_dir)["ready"])

    def test_missing_and_malformed_prerequisites_fail_closed_despite_true_arguments(self):
        prerequisites = {
            "SOURCE-BINDINGS.json": "source_bytes_match",
            "READINESS-CONTRACT.json": "frozen_requirements_valid",
            "SCENARIO-MATRIX.json": "frozen_requirements_valid",
            "MATRIX-FREEZE.json": "frozen_requirements_valid",
            "INVARIANT-CATALOG.json": "frozen_requirements_valid",
            "INVARIANT-RESULTS.json": "all_scenario_invariants_passed",
            "REGRESSION-RESULTS.json": "all_scenarios_passed",
            "CORPUS-MANIFEST.json": "corpus_hash_valid",
            "seeds.json": "corpus_hash_valid",
            "FEATURE-INVENTORY.json": "feature_coverage_honestly_derived",
            "COVERAGE.json": "feature_coverage_honestly_derived",
            "ISSUES.json": "all_s0_s1_blocking_s2_issues_closed",
            "AUDIT-FINDINGS.json": "audit_findings_resolved",
            "STAGE-METADATA.json": "generated_stage_metadata_valid",
            "results/SCENARIO-RESULTS.jsonl": "all_scenarios_passed",
            "state-hashes/SCEN-CTRL-01.json": "all_scenarios_passed",
            "commands/SCEN-CTRL-01.json": "all_scenarios_passed",
            "traces/SCEN-CTRL-01.jsonl": "all_traces_substantive",
            "REVIEW-EVIDENCE.json": "pre_review_evidence_complete",
            "REVIEW-INVOCATION.json": "independent_review_verified",
            "INDEPENDENT-REVIEW.md": "independent_review_verified",
            "INDEPENDENT-REVIEW.json": "independent_review_verified",
            "MODEL-USAGE.json": "independent_review_verified",
        }
        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp) / self.run_dir.name
            shutil.copytree(self.run_dir, copied)
            for rel, gate in prerequisites.items():
                path = copied / rel
                original = path.read_bytes()
                for corrupt in (False, True):
                    with self.subTest(path=rel, malformed=corrupt):
                        if corrupt:
                            path.write_bytes(b"not valid JSON or evidence")
                        else:
                            path.unlink()
                        result = compute_development_readiness(
                            copied, blocking_issues_count=0, unresolved_human_decisions=[],
                            all_invariants_passed=True, all_scenarios_passed=True,
                            golden_replay_verified=True, corpus_hash_valid=True,
                            all_traces_substantive=True, feature_coverage_honestly_derived=True,
                            review_verdict="READY", independent_review_verified=True,
                            independent_review_is_configured_gate=True,
                        )
                        self.assertFalse(result["gates"][gate])
                        self.assertFalse(result["ready"])
                        path.write_bytes(original)

    def test_raw_inventory_and_review_authorship_tampering_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp) / self.run_dir.name
            shutil.copytree(self.run_dir, copied)
            for rel in ("commands/SCEN-CTRL-01.json", "traces/SCEN-CTRL-01.jsonl",
                        "state-hashes/SCEN-CTRL-01.json", "seeds.json", "REMEDIATION-RESULTS.json"):
                path = copied / rel
                raw = path.read_bytes()
                path.write_bytes(raw + b" ")
                with self.subTest(path=rel), self.assertRaises(ValueError):
                    verify_independent_review_artifact(copied)
                path.write_bytes(raw)
            unexpected = copied / "results/unexpected.json"
            unexpected.write_text("{}")
            with self.assertRaises(ValueError):
                verify_independent_review_artifact(copied)
            unexpected.unlink()
            invocation_path = copied / "REVIEW-INVOCATION.json"
            invocation = json.loads(invocation_path.read_text())
            invocation["authored_by"] = "coordination.run_full_game_simulation"
            invocation_path.write_text(json.dumps(invocation))
            with self.assertRaisesRegex(ValueError, "external review boundary"):
                verify_independent_review_artifact(copied)

    def test_finalize_rejects_reseal_before_any_writes(self):
        before = compute_tree_sha256(self.run_dir)
        with self.assertRaises(FileExistsError):
            run_finalize_stage(output_root=self.temp_root, run_id=self.sim_run_id)
        self.assertEqual(compute_tree_sha256(self.run_dir), before)

    def test_source_drift_aborts_finalize_before_any_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp) / self.run_dir.name
            shutil.copytree(self.run_dir, copied)
            (copied / "RUN-MANIFEST.json").unlink()
            bindings_path = copied / "SOURCE-BINDINGS.json"
            bindings = json.loads(bindings_path.read_text())
            bindings["coordination/evidence_pipeline.py"]["sha256"] = "0" * 64
            bindings_path.write_text(json.dumps(bindings))
            before = compute_tree_sha256(copied)
            with self.assertRaisesRegex(ValueError, "Source-byte drift"):
                run_finalize_stage(output_root=Path(tmp), run_id=self.sim_run_id)
            self.assertEqual(compute_tree_sha256(copied), before)

    def test_valid_revise_remains_sealable_and_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            copied = Path(tmp) / self.run_dir.name
            shutil.copytree(self.run_dir, copied)
            invocation = json.loads((copied / "REVIEW-INVOCATION.json").read_text())
            for name in ("INDEPENDENT-REVIEW.md", "INDEPENDENT-REVIEW.json", "REVIEW-INVOCATION.json",
                         "MODEL-USAGE.json", "DEVELOPMENT-READINESS.json", "README.md", "RUN-MANIFEST.json"):
                (copied / name).unlink()
            invocation["verdict"] = "REVISE"
            record_external_review(copied, review_markdown="Verdict: REVISE\n",
                                   review_json={"verdict": "REVISE"}, invocation=invocation)
            run_finalize_stage(output_root=Path(tmp), run_id=self.sim_run_id)
            self.assertEqual(verify_independent_review_artifact(copied)["verdict"], "REVISE")
            readiness = json.loads((copied / "DEVELOPMENT-READINESS.json").read_text())
            manifest = json.loads((copied / "RUN-MANIFEST.json").read_text())
            self.assertFalse(readiness["ready"])
            self.assertEqual(manifest["status"], "completed_not_ready")

    def test_positive_two_stage_simulation_and_finalization_in_isolated_tempdir(self):
        # Verify Stage 1 pre-review invariants captured before Stage 2
        self.assertTrue(self.stage1_review_packet_exists)
        self.assertFalse(self.stage1_independent_review_exists)
        self.assertFalse(self.stage1_readiness_exists)
        self.assertFalse(self.stage1_manifest_exists)

        # Verify finalized tempdir bundle and any finalized non-rejected bundle in artifacts/simulations/full-game/
        candidate_dirs = [self.run_dir]
        if SIMULATIONS_ROOT.is_dir():
            for child in sorted(SIMULATIONS_ROOT.iterdir()):
                if (
                    child.is_dir()
                    and child.name != PRESERVED_REJECTED_RUN_ID
                    and (child / "RUN-MANIFEST.json").is_file()
                ):
                    candidate_dirs.append(child)

        for bundle_dir in candidate_dirs:
            with self.subTest(bundle=bundle_dir.name):
                matrix = json.loads((bundle_dir / "SCENARIO-MATRIX.json").read_text(encoding="utf-8"))
                self.assertEqual(len(matrix), 46)
                for contract in matrix:
                    validated = validate_scenario_contract(contract)
                    trace_info = verify_scenario_trace_integrity(
                        contract["scenario_id"],
                        bundle_dir,
                        expected_contract_hash=validated["contract_hash"],
                    )
                    self.assertTrue(trace_info["substantive"])
                    self.assertGreaterEqual(trace_info["trace_records_count"], 2)

                corpus_manifest = json.loads(
                    (bundle_dir / "CORPUS-MANIFEST.json").read_text(encoding="utf-8")
                )
                require_hash(corpus_manifest["sha256"])
                self.assertTrue(corpus_manifest["verified_regeneration_match"])

                invariants = json.loads(
                    (bundle_dir / "INVARIANT-RESULTS.json").read_text(encoding="utf-8")
                )
                self.assertEqual(len(invariants), 18)
                self.assertTrue(all(inv["passed"] and inv["evaluations_count"] > 0 for inv in invariants))

                issues = json.loads((bundle_dir / "ISSUES.json").read_text(encoding="utf-8"))
                self.assertEqual(len(issues), 3)
                for issue in issues:
                    self.assertEqual(issue["status"], "closed")
                    require_hash(issue["resolution_hash"])

                coverage = json.loads((bundle_dir / "COVERAGE.json").read_text(encoding="utf-8"))
                self.assertEqual(coverage["total_active_features"], 16)
                self.assertEqual(coverage["covered_features"], 12)
                self.assertEqual(coverage["partially_observed_state_only_features"], 3)
                self.assertEqual(coverage["not_observed_features"], 1)

                rev_verify = verify_independent_review_artifact(bundle_dir)
                self.assertTrue(rev_verify["verified"])
                self.assertIn(rev_verify["verdict"], ("READY", "REVISE"))

                readiness = json.loads(
                    (bundle_dir / "DEVELOPMENT-READINESS.json").read_text(encoding="utf-8")
                )
                manifest = json.loads((bundle_dir / "RUN-MANIFEST.json").read_text())
                self.assertEqual(readiness["simulation_and_plan_ready"], readiness["ready"])
                if bundle_dir == self.run_dir:
                    self.assertEqual(rev_verify["verdict"], "READY")
                    self.assertTrue(readiness["ready"])
                    contract = json.loads((bundle_dir / "READINESS-CONTRACT.json").read_text())
                    self.assertEqual(readiness["expected_scenarios"], len(contract["scenario_ids"]))
                    self.assertEqual(readiness["expected_invariants"], len(contract["invariant_ids"]))
                    self.assertEqual(len(readiness["invariant_results"]), len(contract["invariant_ids"]))
                    self.assertEqual(len(readiness["audit_findings"]), 19)
                    self.assertEqual([a["id"] for a in readiness["audit_findings"] if a["status"] == "open"],
                                     ["AUDIT-16"])
                elif manifest["status"] == "completed_not_ready":
                    self.assertFalse(readiness["ready"])
                if rev_verify["verdict"] == "REVISE":
                    self.assertFalse(readiness["ready"])
                self.assertFalse(readiness["submission_ready"])
                self.assertEqual(readiness["candidate_plan_revision"], 5)
                require_hash(readiness["candidate_plan_hash"])
                self.assertEqual(readiness["blocking_issues_count"], 0)
                self.assertEqual(readiness["unresolved_human_decisions"], [])

                manifest = json.loads((bundle_dir / "RUN-MANIFEST.json").read_text(encoding="utf-8"))
                for rel_path, expected_hash in manifest["artifact_hashes"].items():
                    full_path = bundle_dir / rel_path
                    self.assertTrue(full_path.is_file(), f"Missing artifact in {bundle_dir.name}: {rel_path}")
                    self.assertEqual(file_sha256(full_path), expected_hash)

    def test_deterministic_golden_replay_identical_digests(self):
        def _run_e2e_01() -> str:
            sim = FullGameSimulator(seed=101, initial_lane=1)
            sim.set_roster([f"user_{i}" for i in range(10)])
            sim.submit_command(
                make_command("hazard.propose", "user_0", "human", 100, 1, {"hazard_id": "haz_t1", "lane": 1})
            )
            sim.submit_command(
                make_command("streamer.steer", "streamer", "human", 200, 2, {"direction": "left"})
            )
            for _ in range(TURN_TICKS):
                sim.step()
            sim.submit_command(
                make_command("hazard.propose", "user_1", "human", 700, 3, {"hazard_id": "haz_t2", "lane": 1})
            )
            for i in range(7):
                sim.submit_command(
                    make_command(
                        "viewer.counter",
                        f"user_{i}",
                        "human",
                        750 + i,
                        4 + i,
                        {"hazard_id": "haz_t2", "counter": "clear_lane"},
                    )
                )
            for _ in range(TURN_TICKS):
                sim.step()
            sim.submit_command(
                make_command("hazard.propose", "user_2", "human", 1300, 20, {"hazard_id": "haz_t3", "lane": 1})
            )
            while sim.status == "racing" and sim.tick < MATCH_DEADLINE_TICKS:
                sim.step()
            return canonical_hash(sim.get_canonical_state())

        d1 = _run_e2e_01()
        d2 = _run_e2e_01()
        self.assertEqual(d1, d2)
        scenario_hashes = json.loads(
            (self.run_dir / "state-hashes/scenario_hashes.json").read_text(encoding="utf-8")
        )
        self.assertEqual(d1, scenario_hashes["SCEN-E2E-01"])


if __name__ == "__main__":
    unittest.main()
