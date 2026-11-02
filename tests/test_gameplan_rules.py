"""Static selected-plan/gate checks; no runtime, model or gameplay imports."""

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = {"D-01": "player_agency", "D-02": "survival_contract",
             "D-03": "audience_fairness", "D-04": "reward_contract",
             "D-05": "clock_contract"}
STATUS = "selected_for_s1_simulation_unverified"


class GameplanRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads((ROOT / "docs/planning/gameplan-v2.json").read_text())
        cls.policy = json.loads((ROOT / "config/directive-policy.json").read_text())
        cls.decisions = {item["id"]: item for item in cls.plan["selected_decisions"]}

    def test_selected_decisions_are_bound_and_separate_from_remaining_gates(self):
        selected = {item["id"]: item for item in self.policy["selected_decisions"]}
        self.assertEqual(set(self.decisions), set(CONTRACTS))
        self.assertEqual(set(selected), set(CONTRACTS))
        for ident, contract in CONTRACTS.items():
            record, ledger = self.decisions[ident], selected[ident]
            for item in (record, ledger):
                self.assertEqual(item["contract"], contract)
                self.assertEqual(item["status"], STATUS)
                self.assertEqual(item["gate"], "before_gameplay")
                self.assertEqual(item["evidence_origin"], "project_design_inference")
                self.assertEqual(item["source_path"], "docs/planning/S1-SIMULATION-PROFILE.md")
                self.assertIn(item["source_path"], self.policy["required_paths"])
                self.assertEqual(item["source_locator"], ident)
            self.assertTrue(record["selected_constraints"])
            self.assertEqual(ledger["rule"], " ".join(record["selected_constraints"]))
            self.assertNotIn("open_selections", record)
            self.assertIn("not external validation", record["evidence_caveat"])
        self.assertEqual([item["id"] for item in self.plan["open_decisions"]],
                         ["live_submission_external_capture"])
        delegated = {item["id"]: item for item in self.plan["delegated_remediation_decisions"]}
        self.assertEqual(set(delegated), {"D-06", "D-07", "D-08", "D-09"})
        for ident, item in delegated.items():
            self.assertEqual(item["status"], "delegated_for_s1_remediation_provisional")
            self.assertEqual(item["source_path"], "docs/planning/DECISIONS.md")
            self.assertIn(item["source_path"], self.policy["required_paths"])
        self.assertEqual(delegated["D-09"]["issue_ids"],
                         ["ISSUE-SIM-01", "ISSUE-SIM-02", "ISSUE-SIM-03"])
        self.assertEqual([item["id"] for item in self.policy["unresolved_decisions"]],
                         ["live_submission_external_capture"])
        self.assertEqual(self.policy["unresolved_decisions"][0]["gate"],
                         "before_live_submission")
        self.assertTrue(set(CONTRACTS).issubset(
            {item["superseded_by"] for item in self.policy["superseded_decisions"]}))

    def test_selection_does_not_authorize_gameplay(self):
        for field in ("gameplay_simulation_enabled", "gameplay_execution_authorized",
                      "ticks_moves_or_state_transitions_simulated"):
            self.assertIs(self.plan["authorization"][field], False)
        self.assertIs(self.plan["acceptance_gates"]["current_gameplay_authorization"], False)
        self.assertTrue(self.policy["gate"]["gameplay_enabled"])
        self.assertIs(self.policy["gate"]["automatic_phase_advance"], False)
        self.assertEqual(self.policy["allowed_phases"], ["plan"])

    def test_control_and_hazard_values_preserve_steering_and_bounded_pressure(self):
        controls = self.decisions["D-01"]["parameters"]
        self.assertEqual((controls["lanes"], controls["transition_seconds"]), (3, 0.5))
        self.assertEqual(controls["discrete_lanes"], [0, 1, 2])
        self.assertEqual(controls["transition_ticks"], 10)
        self.assertEqual(controls["lateral_interpolation"], "linear")
        self.assertEqual(controls["collision_overlap_half_width"], 0.4)
        self.assertEqual(controls["transition_lockout"], "rejected")
        self.assertEqual(controls["edge_clamping"], "rejected")
        self.assertEqual(controls["steering_active_phases"], ["plan", "resolution", "reward"])
        self.assertEqual(controls["resolution_lock"], "crowd_counter_only")
        for key in ("held_repeat", "manual_counter_confirmation", "manual_counter_override"):
            self.assertFalse(controls[key])
        self.assertEqual(controls["same_tick_opposites"], "cancel")
        hazard = self.decisions["D-02"]["parameters"]
        self.assertEqual((hazard["max_obstacles_per_turn"], hazard["max_obstacles_per_match"],
                          hazard["warning_final_planning_seconds"],
                          hazard["active_first_resolution_seconds"]), (1, 3, 5, 3))
        self.assertEqual(hazard["obstacle_lane"], "center")
        self.assertEqual((hazard["collision_applications_per_obstacle"],
                          hazard["slowdown_fraction"], hazard["slowdown_seconds"]), (1, [1, 5], 2))
        self.assertEqual((hazard["route_distance_units"], hazard["nominal_route_seconds"],
                          hazard["nominal_free_speed_units_per_sec"],
                          hazard["max_collision_completion_seconds"]),
                         (100.0, 88, "100/88", 89.2))
        for key in ("hp_damage", "stun_seconds", "steering_loss_seconds", "displacement",
                    "automatic_retries"):
            self.assertEqual(hazard[key], 0)
        for key in ("overlap", "stack", "refresh", "residual", "hp_death_respawn_checkpoints",
                    "state_or_pool_carry"):
            self.assertIs(hazard[key], False)
        self.assertTrue(hazard["clear_lane_before_collision"])
        self.assertTrue(hazard["later_reachability_fixtures_required"])
        resolution = next(p for p in self.plan["phases"] if p["id"] == "resolution")
        self.assertTrue(resolution["crowd_counter_input_locked"])
        self.assertTrue(resolution["streamer_steering_active"])
        self.assertNotIn("input_locked", resolution)

    def test_account_quorum_reward_and_retired_formula_are_explicit(self):
        audience = self.decisions["D-03"]["parameters"]
        self.assertFalse(audience["one_human_proof"])
        self.assertFalse(audience["squads_are_electoral_blocks"])
        self.assertEqual((audience["squads"], audience["subject_weight"],
                          audience["max_influence_per_subject_per_turn"],
                          audience["replacements"]), (2, 1, 1, 0))
        self.assertEqual(audience["quorum_fraction"], [3, 5])
        self.assertEqual(audience["quorum_rounding"], "ceil")
        self.assertEqual(audience["minimum_eligible_votes"], 1)
        self.assertEqual(audience["tie_winner"], "abstain")
        for key in ("bot_weight", "bot_quorum", "bot_votes", "bot_bounty"):
            self.assertEqual(audience[key], 0)
        reward = self.decisions["D-04"]["parameters"]
        self.assertEqual((reward["starting_pool"], reward["accepted_distinct_human_origin_hazard_increment"],
                          reward["max_increments_per_turn"], reward["pool_cap"],
                          reward["multiplier"]), (0, 20, 1, 60, 1))
        for key in ("streamer_share", "audience_share", "collision_total_multiplier"):
            self.assertEqual(reward[key], [1, 2])
        self.assertEqual(reward["max_collision_penalty_applications"], 1)
        self.assertTrue(reward["collision_penalty_before_split"])
        self.assertEqual(reward["audience_allocation"], "equal_exact_rational_shares")
        self.assertFalse(reward["rounding_redistribution"])
        self.assertEqual(reward["absent_audience_share"], "withheld")
        self.assertEqual(reward["residual_risk"], "safe_danger_farming")
        self.assertIn("100+25/voter", self.decisions["D-04"]["retired_formulas"])

    def test_clock_oracles_and_evidence_separation(self):
        clock = self.decisions["D-05"]["parameters"]
        self.assertEqual((clock["match_active_seconds"], clock["planning_seconds"],
                          clock["resolution_seconds"], clock["reward_seconds"],
                          clock["max_turns"], clock["authoritative_hz_target"]), (90, 20, 5, 5, 3, 20))
        self.assertEqual((clock["route_distance_units"], clock["nominal_route_seconds"],
                          clock["nominal_free_speed_units_per_sec"],
                          clock["max_collision_completion_seconds"]),
                         (100.0, 88, "100/88", 89.2))
        self.assertEqual([(w["id"], w["progress"]) for w in clock["booth_waypoints"]],
                         [("twitch_booth", 35.0), ("codex_booth", 60.0),
                          ("aws_booth", 80.0), ("fictional_main_stage", 100.0)])
        self.assertEqual([d["range"] for d in clock["district_progress_ranges"]],
                         [[0, 25], [25, 50], [50, 75], [75, 95], [95, 100]])
        self.assertEqual(clock["planning_interval"], "half_open")
        self.assertEqual(clock["receipt_at_planning_close"], "expired")
        self.assertEqual(clock["same_time_order"], ["deadline", "phase_close", "pause_request",
                                                   "authoritative_sequence_ordered_commands",
                                                   "effects_settlement"])
        self.assertEqual((clock["model_timeout_seconds"], clock["automatic_model_retries"],
                          clock["post_cutoff_grace_nanoseconds"]), (2, 0, 0))
        self.assertFalse(clock["client_backdating"])
        self.assertEqual(clock["delivery_at_deadline"], "wipe")
        self.assertFalse(clock["real_world_deadline_claim"])
        profile = (ROOT / "docs/planning/S1-SIMULATION-PROFILE.md").read_text()
        self.assertIn("External evidence, separate from project choices", profile)
        self.assertIn("project design inferences, not externally validated facts", profile)
        self.assertIn("safe-danger farming", profile)
        for name in ("S1-PLATFORM-EVIDENCE.md", "S1-SYSTEMS-EVIDENCE.md"):
            self.assertIn("docs/planning/research/" + name, self.policy["required_paths"])

    def test_exact_reward_timeline_and_single_terminal_settlement(self):
        clock = self.decisions["D-05"]["parameters"]
        reward = self.decisions["D-04"]["parameters"]
        controls = self.decisions["D-01"]["parameters"]
        phase = next(p for p in self.plan["phases"] if p["id"] == "reward")
        self.assertFalse(self.plan["cadence"]["reward_seconds_approximate"])
        self.assertFalse(clock["reward_approximate"])
        self.assertFalse(phase["duration_approximate"])
        self.assertTrue(clock["reward_presentation_approximate"])
        self.assertEqual(clock["turn_end_active_seconds"], [30, 60, 90])
        self.assertEqual(clock["third_turn_reward_active_interval_seconds"], [85, 90])
        self.assertEqual(clock["after_third_reward"], "process_deadline_no_turn_four")
        self.assertEqual(controls["auto_forward_active_phases"], ["plan", "resolution", "reward"])
        self.assertEqual(controls["movement_ends"], "terminal_state")
        self.assertTrue(phase["auto_forward_active"])
        self.assertTrue(phase["streamer_steering_active"])
        self.assertFalse(phase["settlement"])
        self.assertFalse(reward["reward_phase_settlement"])
        self.assertEqual(reward["reward_phase_display"], "outcome_and_pending_pool_only")
        self.assertEqual(reward["final_settlements_per_match"], 1)
        self.assertTrue(reward["delivery_ends_active_simulation_immediately"])
        self.assertEqual(reward["deadline_settlement"], 0)

    def test_deadline_and_collision_delivery_priority_are_total(self):
        clock = self.decisions["D-05"]["parameters"]
        self.assertEqual(clock["same_time_order"], ["deadline", "phase_close", "pause_request",
                                                   "authoritative_sequence_ordered_commands",
                                                   "effects_settlement"])
        self.assertEqual(clock["pause_at_reached_deadline"], "cannot_suspend_deadline")
        self.assertEqual(clock["admitted_effect_order"], ["clear_lane_removal",
                                                        "collision_adjudication",
                                                        "delivery_detection",
                                                        "one_final_settlement"])
        self.assertEqual(clock["same_time_pre_deadline_collision_delivery"],
                         "record_collision_then_delivery_halve_settlement_once")
        self.assertEqual(clock["delivery_at_deadline"], "wipe")

    def test_hazard_commitment_warning_counter_and_review_bindings(self):
        hazard = self.decisions["D-02"]["parameters"]
        audience = self.decisions["D-03"]["parameters"]
        reward = self.decisions["D-04"]["parameters"]
        clock = self.decisions["D-05"]["parameters"]
        self.assertEqual(hazard["hazard_admission_close_planning_seconds"], 15)
        self.assertEqual(hazard["hazard_admission_interval"], "half_open")
        self.assertEqual(hazard["hazard_at_or_after_admission_close"],
                         "expired_for_turn_no_backdating_no_rollover")
        self.assertEqual(hazard["warning_planning_interval_seconds"], [15, 20])
        self.assertTrue(hazard["warning_requires_committed_human_origin_hazard"])
        self.assertEqual(hazard["no_committed_hazard"], "no_hazard_warning_or_bounty_increment")
        for value in (hazard["warning_counter_bounty_binding"], audience["counter_binding"],
                      reward["hazard_increment_binding"]):
            self.assertEqual(value, "committed_hazard_id")
        self.assertEqual(audience["counter_vote_planning_interval_seconds"], [0, 20])
        self.assertEqual(audience["counter_vote_interval"], "half_open")
        self.assertEqual(reward["hazard_increment_requires_commit_before_planning_seconds"], 15)
        self.assertEqual(clock["general_input_close_planning_seconds"], 20)
        self.assertEqual(clock["hazard_model_admission_close_planning_seconds"], 15)
        self.assertEqual(clock["model_cutoff"],
                         "min_dispatch_plus_timeout_or_applicable_admission_close")
        self.assertEqual(self.plan["revision"]["number"], 5)
        self.assertEqual(self.plan["revision"]["baseline_sha256"],
                         "1b43be51add9d6c5e1cc2b6378e66a7f48fb76985435693b3dcf303ad6234937")
        self.assertEqual(self.plan["revision"]["baseline_markdown_sha256"],
                         "a6967a24601f259be027ed7fbebed5ad6e0784d4a7f7b7f6c0a2c3967e47e6ed")
        self.assertEqual(self.policy["revision"], 16)
        review = self.plan["s1_review"]
        self.assertEqual(review["verdict"], "REVISE")
        self.assertEqual(review["reviewed_plan_revision"], 3)
        self.assertEqual(review["revised_plan_review_status"], "fresh_version_bound_review_required")
        self.assertEqual(hashlib.sha256((ROOT / review["path"]).read_bytes()).hexdigest(),
                         "29280f55a0d69fd4f8cb06d70f22e7daa23cf0d511c1e0b8eb8a82614c71e530")
        self.assertEqual(review["sha256"], self.policy["required_paths"][review["path"]])
        self.assertIn(review["response_path"], self.policy["required_paths"])
        response = (ROOT / review["response_path"]).read_text()
        self.assertIn(review["sha256"], response)
        self.assertIn("not a new Astra verdict", response)
        self.assertIn("Gameplay stays disabled", response)


if __name__ == "__main__":
    unittest.main()
