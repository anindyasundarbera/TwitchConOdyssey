"""W3/TASK-006 acceptance tests: authoritative gameplay engine boundary.

Static, deterministic and offline: no network, provider, server, browser or
wall-clock I/O. Values asserted here come from the selected ledger rules
(D-01..D-05) as encoded by the Shared Determinism Core.
"""
import ast
import unittest
from pathlib import Path

from coordination.canonical_commands import make_command
from server.engine import AuthoritativeGame

ROOT = Path(__file__).resolve().parents[1]


def command(kind, actor="s0", provenance="human", tick=0, sequence=0, **payload):
    return make_command(kind, actor, provenance, tick, sequence, payload)


class AuthoritativeGameBoundaryTests(unittest.TestCase):
    def game(self, **kwargs):
        kwargs.setdefault("initial_roster", ["acct_1", "acct_2", "acct_3"])
        return AuthoritativeGame(seed=42, initial_lane=1, **kwargs)

    # Criterion 1/9: the engine alone owns physics and state; consumers get detached views.
    def test_engine_owns_state_and_snapshots_are_detached(self):
        game = self.game()
        self.assertEqual(game.submit(command("streamer.steer", direction="right")), "applied")
        before = game.state_hash()
        snapshot = game.snapshot()
        snapshot["avatar"]["lane"] = 0
        snapshot["movement"]["progress"] = 50.0
        snapshot["bounty"]["pool"] = 999
        self.assertEqual(game.state_hash(), before)
        self.assertEqual(game.snapshot()["avatar"]["lane"], 1)
        self.assertNotEqual(game.snapshot()["bounty"]["pool"], 999)
        # No mutable engine handle and no alternative mutation surface is exposed.
        self.assertFalse(hasattr(game, "simulator"))
        self.assertFalse(hasattr(game, "submit_command"))
        self.assertFalse(hasattr(game, "command_history"))

    # Criterion 2: canonical intake validates, locks in-flight transitions, clamps edges.
    def test_canonical_command_intake_and_lane_rules(self):
        game = self.game()
        self.assertEqual(game.submit(command("streamer.steer", direction="right")), "applied")
        # In-flight transition lockout: second request rejected, no held repeat.
        self.assertEqual(game.submit(command("streamer.steer", direction="right")), "rejected")
        self.assertEqual(game.submit(command("streamer.steer", direction="cancel")), "applied")
        self.assertEqual(game.submit(command("streamer.steer", direction="sideways")), "rejected")
        self.assertEqual(game.submit({"kind": "streamer.steer"}), "rejected")
        edge = AuthoritativeGame(seed=42, initial_lane=0)
        self.assertEqual(edge.submit(command("streamer.steer", direction="left")), "rejected")

    # Criterion 4/6: hazard admission [0,15s), one per turn, dedup, bot isolation, pool cap.
    def test_hazard_window_dedup_and_origin_isolation(self):
        closed = AuthoritativeGame(seed=42, initial_tick=300)
        self.assertEqual(closed.submit(command("hazard.propose", hazard_id="hz_late")), "expired")
        self.assertEqual(closed.pool, 0)

        game = self.game()
        self.assertEqual(game.submit(command("hazard.propose", hazard_id="hz_1")), "applied")
        self.assertEqual(game.pool, 20)
        self.assertEqual(game.submit(command("hazard.propose", hazard_id="hz_1")), "duplicate")
        self.assertEqual(game.submit(command("hazard.propose", hazard_id="hz_2")), "rejected")
        self.assertEqual(game.submit(command("hazard.propose", actor="bot_1",
                                              provenance="bot", hazard_id="hz_3")), "rejected")
        self.assertEqual(game.pool, 20)

    # Criterion 2/3: counter votes bind to the committed hazard and one subject = one influence.
    def test_counter_vote_binding_roster_and_atomicity(self):
        game = self.game()
        self.assertEqual(game.submit(command("hazard.propose", hazard_id="hz_1")), "applied")
        self.assertEqual(game.submit(command("viewer.counter", actor="acct_1",
                                             hazard_id="hz_1", counter="clear_lane")), "applied")
        self.assertEqual(game.submit(command("viewer.counter", actor="acct_1",
                                             hazard_id="hz_1", counter="clear_lane")), "duplicate")
        self.assertEqual(game.submit(command("viewer.counter", actor="ghost",
                                             hazard_id="hz_1")), "rejected")
        self.assertEqual(game.submit(command("viewer.counter", actor="bot_1",
                                             provenance="bot", hazard_id="hz_1")), "rejected")
        self.assertEqual(game.snapshot()["audience"]["counter_votes_count"], 1)

    # Criterion 7: pause freezes the logical clock, rejects commands, resumes cleanly.
    def test_pause_freezes_clocks_without_catch_up(self):
        game = self.game()
        self.assertEqual(game.pause(), "applied")
        self.assertTrue(game.is_paused)
        game.step()
        self.assertEqual(game.tick, 0)
        self.assertEqual(game.submit(command("streamer.steer", direction="right")), "rejected")
        self.assertEqual(game.pause(False), "applied")
        self.assertFalse(game.is_paused)
        game.step()
        self.assertEqual(game.tick, 1)
        with self.assertRaises(ValueError):
            game.pause("yes")

    # Criterion 4/5: delivery equality at the 90s deadline is a wipe with zero settlement.
    def test_deadline_equality_wipes_with_zero_settlement(self):
        game = self.game(initial_tick=1799, initial_progress=99.9375, base_speed_override=1.25)
        game.step()
        self.assertEqual(game.status, "wiped")
        self.assertEqual(game.tick, 1800)
        settlement = game.settlement
        self.assertEqual(settlement["reason"], "deadline_equality_wipe")
        self.assertEqual(settlement["total_hype"], 0)
        self.assertEqual(settlement["streamer_share"], 0)
        self.assertEqual(settlement["audience_share_total"], 0)
        self.assertTrue(settlement["settled_once"])

    # Criterion 5: delivery strictly before the deadline settles exactly once.
    def test_delivery_before_deadline_settles_once(self):
        game = self.game(initial_tick=1798, initial_progress=99.9375, base_speed_override=1.25)
        game.step()
        self.assertEqual(game.status, "delivered")
        self.assertEqual(game.tick, 1799)
        first = game.settlement
        self.assertEqual(first["tick"], 1799)
        self.assertTrue(first["settled_once"])
        game.step()
        self.assertEqual(game.settlement, first)

    # Criterion 8: hotfix data is signed, bounded, versioned and activates at a turn boundary.
    def test_hotfix_signature_bounds_and_turn_boundary_activation(self):
        game = self.game(initial_tick=599)
        self.assertEqual(game.hotfix_rules["slowdown_fraction"], 0.2)
        self.assertEqual(game.submit(command(
            "booth.hotfix", actor="booth",
            patch_data={"slowdown_fraction": 0.1}, signature="TRUSTED_CODEX_KEY",
            patch_version=1, expiry_tick=1800,
        )), "applied")
        self.assertEqual(game.submit(command(
            "booth.hotfix", actor="booth",
            patch_data={"slowdown_fraction": 0.1}, signature="UNTRUSTED",
            patch_version=2, expiry_tick=1800,
        )), "rejected")
        self.assertEqual(game.submit(command(
            "booth.hotfix", actor="booth",
            patch_data={"slowdown_fraction": 0.5}, signature="TRUSTED_CODEX_KEY",
            patch_version=3, expiry_tick=1800,
        )), "rejected")
        self.assertEqual(game.hotfix_rules["slowdown_fraction"], 0.2)
        game.step()
        self.assertEqual(game.turn, 2)
        self.assertEqual(game.hotfix_rules["slowdown_fraction"], 0.1)
        self.assertEqual(game.applied_hotfix_version, 1)

    # Criterion 9: the boundary and its kernel remain pure and deterministic.
    def test_engine_boundary_is_pure_and_replayable(self):
        tree = ast.parse((ROOT / "server/engine.py").read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        forbidden = {"time", "datetime", "socket", "urllib", "requests",
                     "asyncio", "os", "sys", "subprocess"}
        self.assertEqual(imported & forbidden, set())

        game = AuthoritativeGame(seed=42, initial_lane=1, initial_roster=[])
        replayed = AuthoritativeGame.verify_replay(
            seed=42, initial_lane=1, initial_roster=[],
            command_log=[], steps_to_run=0,
        )
        self.assertEqual(replayed["final_state_hash"], game.state_hash())


if __name__ == "__main__":
    unittest.main()
