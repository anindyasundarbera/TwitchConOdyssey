"""W5/TASK-008 offline intake matrix: identity, dedupe, sequence, timing, roster, isolation."""
import unittest

from server.engine import AuthoritativeGame
from server.intake import CommandIntake, IdentityRegistry


class CommandIntakeTests(unittest.TestCase):
    def setUp(self):
        self.registry = IdentityRegistry()
        self.subject = self.registry.link("acct_subject_1", "chat:subject_1")
        self.game = AuthoritativeGame(seed=42, initial_lane=1,
                                      initial_roster=[self.subject])
        self.intake = CommandIntake(self.game, self.registry)

    def test_unlinked_identity_is_rejected_before_the_engine(self):
        before_hash = self.game.state_hash()
        before_history = len(self.game._simulator.command_history)
        self.assertEqual(self.intake.submit("r1", "chat:ghost", "streamer.steer",
                                            {"direction": "right"}, 0), "rejected")
        self.assertEqual(self.intake.decisions[-1]["reason"], "unlinked_identity")
        self.assertEqual(self.game.state_hash(), before_hash)
        self.assertEqual(len(self.game._simulator.command_history), before_history)

    def test_linked_command_applies_only_through_canonical_envelope(self):
        self.assertEqual(self.intake.submit("r1", "chat:subject_1", "streamer.steer",
                                            {"direction": "right"}, 0), "applied")
        history = self.game._simulator.command_history[-1]
        self.assertEqual(history["cmd"]["kind"], "streamer.steer")
        self.assertEqual(history["cmd"]["actor_id"], self.subject)
        self.assertEqual(history["cmd"]["provenance"], "human")

    def test_transport_dedupe_is_separate_from_influence_dedupe(self):
        self.assertEqual(self.intake.submit("r1", "chat:subject_1", "streamer.steer",
                                            {"direction": "right"}, 0), "applied")
        self.assertEqual(self.intake.submit("r1", "chat:subject_1", "streamer.steer",
                                            {"direction": "left"}, 1), "duplicate")
        self.assertEqual(self.intake.decisions[-1]["reason"], "transport_duplicate")
        self.assertEqual(len(self.game._simulator.command_history), 1)

        # Cross-channel reconnect keeps the same account subject: one influence per turn.
        self.registry.reconnect(self.subject, "button:subject_1")
        for _ in range(11):
            self.game.step()
        self.assertEqual(self.intake.submit("r2", "button:subject_1", "hazard.propose",
                                            {"hazard_id": "hz_1"}, 2), "applied")
        for _ in range(11):
            self.game.step()
        self.assertEqual(self.intake.submit("r3", "button:subject_1", "viewer.counter",
                                            {"hazard_id": "hz_1", "counter": "clear_lane"}, 3), "applied")
        for _ in range(11):
            self.game.step()
        self.assertEqual(self.intake.submit("r4", "chat:subject_1", "viewer.counter",
                                            {"hazard_id": "hz_1", "counter": "clear_lane"}, 4), "duplicate")

    def test_stale_sequence_and_rate_limit_use_canonical_statuses(self):
        self.assertEqual(self.intake.submit("r1", "chat:subject_1", "streamer.steer",
                                            {"direction": "right"}, 5), "applied")
        self.assertEqual(self.intake.submit("r2", "chat:subject_1", "streamer.steer",
                                            {"direction": "left"}, 5), "rejected")
        self.assertEqual(self.intake.decisions[-1]["reason"], "stale_sequence")
        self.assertEqual(self.intake.submit("r3", "chat:subject_1", "streamer.steer",
                                            {"direction": "cancel"}, 6), "rejected")
        self.assertEqual(self.intake.decisions[-1]["reason"], "rate_limited")

    def test_pause_and_terminal_states_reject_before_engine(self):
        self.assertEqual(self.game.pause(), "applied")
        self.assertEqual(self.intake.submit("r1", "chat:subject_1", "streamer.steer",
                                            {"direction": "right"}, 0), "rejected")
        self.assertEqual(self.intake.decisions[-1]["reason"], "paused")

        terminal = AuthoritativeGame(seed=42, initial_lane=1,
                                     initial_roster=[self.subject],
                                     initial_tick=1799, initial_progress=99.9375,
                                     base_speed_override=1.25)
        terminal.step()
        self.assertEqual(terminal.status, "wiped")
        intake = CommandIntake(terminal, self.registry)
        self.assertEqual(intake.submit("r2", "chat:subject_1", "streamer.steer",
                                       {"direction": "right"}, 0), "rejected")
        self.assertEqual(intake.decisions[-1]["reason"], "terminal_state")

    def test_late_counter_vote_returns_expired_from_the_engine(self):
        late = AuthoritativeGame(seed=42, initial_lane=1,
                                 initial_roster=[self.subject], initial_tick=400)
        intake = CommandIntake(late, self.registry)
        self.assertEqual(intake.submit("r1", "chat:subject_1", "hazard.propose",
                                       {"hazard_id": "hz_1"}, 0), "expired")
        self.assertEqual(intake.decisions[-1]["status"], "expired")

    def test_bots_and_fixtures_carry_zero_weight_and_never_earn_human_influence(self):
        for provenance in ("bot", "fixture"):
            receipt = "r_" + provenance
            status = self.intake.submit(receipt, "chat:subject_1", "viewer.counter",
                                        {"hazard_id": "hz_1", "counter": "clear_lane"},
                                        0, provenance=provenance)
            self.assertEqual(status, "rejected")
            self.assertEqual(self.intake.influence_weight(provenance), 0)
            self.assertEqual(self.intake.decisions[-1]["provenance"], provenance)

    def test_joins_freeze_at_the_next_turn_and_reconnect_keeps_influence(self):
        game = AuthoritativeGame(seed=42, initial_lane=1, initial_roster=[])
        other = self.registry.link("acct_subject_2", "chat:subject_2")
        intake = CommandIntake(game, self.registry)
        self.assertEqual(intake.join(other), "applied")
        self.assertEqual(intake.submit("r1", "chat:subject_2", "streamer.steer",
                                       {"direction": "right"}, 0), "applied")
        for _ in range(600):
            game.step()
        self.assertIn(other, game._simulator.frozen_roster)
        self.assertEqual(intake.leave(other), "applied")
        self.assertEqual(intake.submit("r2", "chat:subject_2", "streamer.steer",
                                       {"direction": "left"}, 1), "rejected")
        self.assertEqual(intake.decisions[-1]["reason"], "subject_left")


if __name__ == "__main__":
    unittest.main()
