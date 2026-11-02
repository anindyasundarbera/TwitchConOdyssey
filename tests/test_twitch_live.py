"""Focused local tests for the Twitch EventSub live adapter boundary.

Every transport in this module is fake.  Records produced here are labelled
``fixture`` and are not live Twitch evidence.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from server.app import Runtime
from server.engine import AuthoritativeGame
from server.intake import CommandIntake
from server.twitch_live import (
    CONNECTING_LABEL,
    FIXTURE_LABEL,
    MAX_DEDUPE,
    MAX_EVIDENCE_RECORDS,
    MAX_RECONNECTS,
    SUBSCRIBE_URL,
    VALIDATE_URL,
    WELCOME_URL,
    TwitchEventSubAdapter,
    TwitchLiveError,
)

CLIENT_ID = "client-900000000000000000"
BROADCASTER_ID = "900000000000000001"
CHAT_USER_ID = "900000000000000002"
TOKEN = "sentinel-not-a-credential"


def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def welcome(session_id="session-1", keepalive=10):
    return json.dumps({
        "metadata": {"message_type": "session_welcome"},
        "payload": {"session": {
            "id": session_id,
            "keepalive_timeout_seconds": keepalive,
        }},
    })


def notification(message_id="message-1", text="!left", user_id=CHAT_USER_ID,
                 broadcaster_id=BROADCASTER_ID):
    return json.dumps({
        "metadata": {
            "message_type": "notification",
            "subscription_type": "channel.chat.message",
            "subscription_version": "1",
            "message_id": message_id,
        },
        "payload": {
            "subscription": {
                "type": "channel.chat.message",
                "version": "1",
                "status": "enabled",
            },
            "event": {
                "broadcaster_user_id": broadcaster_id,
                "chatter_user_id": user_id,
                "chatter_user_login": "raw-login-must-not-persist",
                "message": {"text": text, "message_id": "inner-message-id"},
            },
        },
    })


def keepalive():
    return json.dumps({"metadata": {"message_type": "session_keepalive"}})


def reconnect(session_id="session-1", url="wss://eventsub.wss.twitch.tv/ws?session_id=next"):
    return json.dumps({
        "metadata": {"message_type": "session_reconnect"},
        "payload": {"session": {
            "id": session_id,
            "reconnect_url": url,
            "keepalive_timeout_seconds": 10,
        }},
    })


def revocation():
    return json.dumps({
        "metadata": {
            "message_type": "revocation",
            "subscription_type": "channel.chat.message",
            "subscription_version": "1",
        },
        "payload": {"subscription": {
            "id": "subscription-1",
            "status": "authorization_revoked",
            "type": "channel.chat.message",
            "version": "1",
        }},
    })


class FakeClock:
    def __init__(self, value=1700000000.0):
        self.value = value

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class FakeHttp:
    def __init__(self, events, validation=None, subscription=None):
        self.events = events
        self.validation = validation or {
            "client_id": CLIENT_ID,
            "user_id": CHAT_USER_ID,
            "scopes": ["user:read:chat"],
            "expires_in": 3600,
        }
        self.subscription = subscription or {
            "data": [{
                "id": "subscription-1",
                "status": "enabled",
                "type": "channel.chat.message",
                "version": "1",
            }]
        }
        self.validation_status = 200
        self.subscription_status = 202
        self.calls = []
        self.subscription_body = None

    def request(self, method, url, headers, body, timeout=10.0):
        self.events.append("validate" if url == VALIDATE_URL else "subscribe")
        self.calls.append((method, url, dict(headers), body))
        if url == VALIDATE_URL:
            return self.validation_status, json.dumps(self.validation).encode()
        if url == SUBSCRIBE_URL:
            self.subscription_body = json.loads(body)
            return self.subscription_status, json.dumps(self.subscription).encode()
        return 404, b"{}"


class FakeConnection:
    def __init__(self, frames=None, events=None):
        self.frames = list(frames or [])
        self.events = events
        self.closed = False

    def recv(self, timeout):
        if not self.frames:
            return None
        if self.events is not None:
            self.events.append("welcome")
        frame = self.frames.pop(0)
        if isinstance(frame, Exception):
            raise frame
        return frame

    def close(self):
        self.closed = True

    def push(self, frame):
        self.frames.append(frame)


class FakeWebSocketTransport:
    def __init__(self, connections):
        self.connections = list(connections)
        self.urls = []

    def connect(self, url, timeout):
        self.urls.append(url)
        if not self.connections:
            raise TwitchLiveError("connection_refused")
        return self.connections.pop(0)


class TwitchLiveAdapterTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.events = []
        self.http = FakeHttp(self.events)
        self.connection = FakeConnection([welcome()], self.events)
        self.websocket = FakeWebSocketTransport([self.connection])
        self.game = AuthoritativeGame(seed=42, initial_lane=1, initial_roster=[])
        self.intake = CommandIntake(self.game)
        self.adapter = self._adapter(self.intake)

    def _adapter(self, intake, websocket=None, http=None):
        return TwitchEventSubAdapter(
            intake,
            client_id=CLIENT_ID,
            broadcaster_user_id=BROADCASTER_ID,
            user_id=CHAT_USER_ID,
            http=http or self.http,
            websocket=websocket or self.websocket,
            clock=self.clock,
            transport_kind="fixture",
        )

    def _start(self):
        self.adapter.start(TOKEN)

    def _commands(self, kind=None):
        entries = self.game._simulator.command_history
        if kind is None:
            return entries
        return [entry for entry in entries if entry["cmd"]["kind"] == kind]

    def _pump_all(self):
        while self.adapter.pump() > 0:
            pass

    def test_welcome_is_read_before_subscribe_and_subscribe_uses_session(self):
        self._start()
        self.assertEqual(self.events, ["validate", "welcome", "subscribe"])
        self.assertEqual(self.websocket.urls, [WELCOME_URL])
        self.assertEqual(self.http.subscription_body["type"], "channel.chat.message")
        self.assertEqual(self.http.subscription_body["version"], "1")
        self.assertEqual(self.http.subscription_body["condition"], {
            "broadcaster_user_id": BROADCASTER_ID,
            "user_id": CHAT_USER_ID,
        })
        self.assertEqual(self.http.subscription_body["transport"], {
            "method": "websocket",
            "session_id": "session-1",
        })
        self.assertTrue(self.adapter.active)
        self.assertFalse(self.adapter.live_active)

    def test_rejects_missing_scope_and_expired_token_without_connecting(self):
        self.http.validation["scopes"] = ["chat:read"]
        with self.assertRaises(TwitchLiveError) as missing:
            self._start()
        self.assertEqual(missing.exception.code, "missing_required_scope")
        self.assertEqual(self.websocket.urls, [])

        expired_http = FakeHttp(self.events, validation={
            "client_id": CLIENT_ID,
            "user_id": CHAT_USER_ID,
            "scopes": ["user:read:chat"],
            "expires_in": 0,
        })
        expired = self._adapter(
            CommandIntake(AuthoritativeGame(seed=42, initial_lane=1)),
            http=expired_http,
        )
        with self.assertRaises(TwitchLiveError) as expired_error:
            expired.start(TOKEN)
        self.assertEqual(expired_error.exception.code, "token_expired")
        self.assertFalse(expired.active)
        self.assertEqual(expired.evidence_envelope()["origin"], "fixture")

    def test_rejects_validation_and_subscription_failures(self):
        self.http.validation_status = 401
        with self.assertRaises(TwitchLiveError) as rejected:
            self._start()
        self.assertEqual(rejected.exception.code, "token_rejected")
        self.assertEqual(self.websocket.urls, [])

        http = FakeHttp(self.events)
        http.subscription_status = 403
        connection = FakeConnection([welcome()])
        websocket = FakeWebSocketTransport([connection])
        adapter = self._adapter(
            CommandIntake(AuthoritativeGame(seed=42, initial_lane=1)),
            websocket=websocket,
            http=http,
        )
        with self.assertRaises(TwitchLiveError) as subscription:
            adapter.start(TOKEN)
        self.assertEqual(subscription.exception.code, "subscription_rejected")
        self.assertTrue(connection.closed)
        self.assertFalse(adapter.active)
        self.assertEqual(adapter.evidence_records(), [])

    def test_live_envelope_waits_for_a_verified_notification(self):
        connection = FakeConnection([welcome()])
        adapter = TwitchEventSubAdapter(
            self.intake,
            client_id=CLIENT_ID,
            broadcaster_user_id=BROADCASTER_ID,
            user_id=CHAT_USER_ID,
            http=self.http,
            websocket=FakeWebSocketTransport([connection]),
            clock=self.clock,
            transport_kind="live",
        )
        adapter.start(TOKEN)
        before = adapter.evidence_envelope()
        self.assertEqual(before["origin"], "disconnected")
        self.assertFalse(before["live_participation"])
        self.assertFalse(before["live_verified"])
        self.assertEqual(before["origin_label"], CONNECTING_LABEL)
        connection.push(notification("live-message-1", "!left"))
        adapter.pump()
        after = adapter.evidence_envelope()
        self.assertEqual(after["origin"], "live")
        self.assertTrue(after["live_participation"])
        self.assertTrue(after["live_verified"])
        self.assertFalse(after["fixture"])

    def test_notification_reaches_canonical_intake_with_hashed_identity(self):
        self.connection.push(notification("message-1", "!left"))
        self._start()
        self.adapter.pump()

        steer = self._commands("streamer.steer")
        self.assertEqual(len(steer), 1)
        command = steer[0]["cmd"]
        subject = _sha("twitch:user:" + CHAT_USER_ID)
        self.assertEqual(command["actor_id"], subject)
        self.assertEqual(command["provenance"], "human")
        self.assertEqual(command["payload"], {"direction": "left"})

        records = self.adapter.evidence_records()
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["origin"], "fixture")
        self.assertEqual(record["origin_label"], FIXTURE_LABEL)
        self.assertFalse(record["live_participation"])
        self.assertFalse(record["live_verified"])
        self.assertTrue(record["fixture"])
        self.assertEqual(record["receipt_sha256"], _sha("twitch:message:message-1"))
        self.assertEqual(record["subject_sha256"], subject)
        self.assertEqual(record["result"]["status"], "applied")
        self.assertEqual(record["command"]["command_id"], command["command_id"])
        self.assertEqual(record["command"]["actor_sha256"], subject)

        envelope = self.adapter.evidence_envelope()
        self.assertEqual(envelope["origin"], "fixture")
        self.assertFalse(envelope["live_participation"])
        self.assertEqual(envelope["adapter"]["state"], "active_fixture")

    def test_deduplicates_message_id_in_a_bounded_store(self):
        self.connection.push(notification("same-message", "!left"))
        self.connection.push(notification("same-message", "!right"))
        self._start()
        self._pump_all()

        self.assertEqual(len(self._commands("streamer.steer")), 1)
        self.assertEqual(len(self.adapter.evidence_records()), 1)
        self.assertEqual(self.adapter.stats()["duplicates"], 1)

    def test_rejects_non_command_unsupported_and_oversized_chat(self):
        self.connection.push(notification("m1", "hello"))
        self.connection.push(notification("m2", "!" + "a" * 500))
        self.connection.push(notification("m3", "!unsupported"))
        self._start()
        self._pump_all()

        self.assertEqual(self._commands(), [])
        self.assertEqual(self.adapter.evidence_records(), [])
        rejections = self.adapter.stats()["rejections"]
        self.assertEqual(rejections["non_command"], 2)
        self.assertEqual(rejections["oversized_chat"], 1)

    def test_hazard_and_counter_use_canonical_intake_and_record_consequence(self):
        self.connection.push(notification("hazard-1", "!hazard"))
        self._start()
        self.adapter.pump()
        for _ in range(600):
            self.game.step()
        self.connection.push(notification("hazard-2", "!hazard"))
        self.adapter.pump()
        for _ in range(10):
            self.game.step()
        self.connection.push(notification("counter-1", "!counter"))
        self.adapter.pump()

        hazard_entries = self._commands("hazard.propose")
        counter_entries = self._commands("viewer.counter")
        self.assertEqual(len(hazard_entries), 2)
        self.assertEqual(len(counter_entries), 1)
        self.assertEqual(counter_entries[0]["status"], "applied")
        state = self.game.snapshot()
        self.assertEqual(state["audience"]["roster_size"], 1)
        self.assertEqual(state["audience"]["eligible_voters_count"], 1)
        record = self.adapter.evidence_records()[-1]
        self.assertEqual(record["command"]["kind"], "viewer.counter")
        self.assertEqual(record["result"]["status"], "applied")
        self.assertEqual(record["consequence"]["after"]["counter_votes_count"], 1)
        self.assertEqual(record["consequence"]["after"]["eligible_voters_count"], 1)
        for _ in range(390):
            self.game.step()
        self.assertTrue(self.game.snapshot()["hazard"]["hazard_countered"])

    def test_keepalive_updates_liveness_and_timeout_fails_closed(self):
        self.connection.push(keepalive())
        self._start()
        self.adapter.pump()
        self.assertTrue(self.adapter.active)
        self.assertEqual(self.adapter.stats()["keepalives"], 1)

        self.clock.advance(100)
        self.adapter.pump()
        self.assertFalse(self.adapter.active)
        self.assertEqual(self.adapter.last_error, "keepalive_timeout")
        self.assertEqual(self.adapter.evidence_envelope()["origin"], "fixture")

    def test_reconnect_uses_only_announced_url_and_is_bounded(self):
        first = FakeConnection([welcome("session-1")])
        second = FakeConnection([welcome("session-2")])
        websocket = FakeWebSocketTransport([first, second])
        adapter = self._adapter(self.intake, websocket=websocket)
        adapter.start(TOKEN)
        first.push(reconnect("session-1"))
        adapter.pump()
        self.assertEqual(websocket.urls, [
            WELCOME_URL,
            "wss://eventsub.wss.twitch.tv/ws?session_id=next",
        ])
        self.assertEqual(adapter.reconnect_count, 1)
        self.assertEqual(adapter.session_id_sha256, _sha("twitch:session:session-2"))
        self.assertTrue(first.closed)
        self.assertTrue(adapter.active)

        bounded_connections = [FakeConnection([welcome(f"bounded-{index}")])
                               for index in range(MAX_RECONNECTS + 1)]
        bounded = self._adapter(
            self.intake, websocket=FakeWebSocketTransport(bounded_connections)
        )
        bounded.start(TOKEN)
        for index in range(MAX_RECONNECTS + 1):
            bounded_connections[index].push(reconnect(f"bounded-{index}"))
            bounded.pump()
        self.assertFalse(bounded.active)
        self.assertEqual(bounded.last_error, "reconnect_limit")

    def test_reconnect_rejects_non_twitch_url(self):
        first = FakeConnection([welcome("session-1")])
        websocket = FakeWebSocketTransport([first])
        adapter = self._adapter(self.intake, websocket=websocket)
        adapter.start(TOKEN)
        first.push(reconnect(url="wss://attacker.example/ws"))
        adapter.pump()
        self.assertFalse(adapter.active)
        self.assertEqual(adapter.last_error, "invalid_reconnect_url")
        self.assertEqual(websocket.urls, [WELCOME_URL])

    def test_revocation_fails_closed_and_clears_live_label(self):
        self.connection.push(revocation())
        self._start()
        self.adapter.pump()
        self.assertFalse(self.adapter.active)
        self.assertFalse(self.adapter.live_verified)
        envelope = self.adapter.evidence_envelope()
        self.assertEqual(envelope["origin"], "fixture")
        self.assertFalse(envelope["live_participation"])
        self.assertEqual(envelope["origin_label"], FIXTURE_LABEL)
        self.assertEqual(envelope["adapter"]["state"], "revoked")

    def test_evidence_and_dedupe_state_are_bounded(self):
        self.connection.frames.extend(
            notification(f"non-command-{index}", "hello")
            for index in range(MAX_DEDUPE + 5)
        )
        self._start()
        self._pump_all()
        self.assertEqual(len(self.adapter._seen_messages), MAX_DEDUPE)
        self.assertEqual(self.adapter.stats()["dedupe_entries"], MAX_DEDUPE)

        connection = FakeConnection([welcome()])
        connection.frames.extend(
            notification(f"evidence-{index}", "!left")
            for index in range(MAX_EVIDENCE_RECORDS + 3)
        )
        adapter = self._adapter(
            CommandIntake(AuthoritativeGame(seed=42, initial_lane=1)),
            websocket=FakeWebSocketTransport([connection]),
        )
        adapter.start(TOKEN)
        while adapter.pump() > 0:
            pass
        self.assertEqual(len(adapter.evidence_records()), MAX_EVIDENCE_RECORDS)
        self.assertEqual(adapter.stats()["tracked_subjects"], 1)

    def test_token_raw_chat_and_raw_ids_are_not_persisted_in_evidence(self):
        self.connection.push(notification("secret-message", "!left"))
        self._start()
        self.adapter.pump()
        payload = json.dumps({
            "records": self.adapter.evidence_records(),
            "envelope": self.adapter.evidence_envelope(),
            "stats": self.adapter.stats(),
        })
        for secret in (TOKEN, CHAT_USER_ID, BROADCASTER_ID,
                       "raw-login-must-not-persist", "!left", "secret-message"):
            self.assertNotIn(secret, payload)
        self.assertNotIn(TOKEN, repr(self.adapter))
        self.assertFalse(hasattr(self.adapter, "_token"))
        self.assertIsNone(self.adapter._client_id)
        self.assertIsNone(self.adapter._broadcaster_user_id)
        self.assertIsNone(self.adapter._user_id)

    def test_runtime_exposes_fixture_evidence_for_fake_transports(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(db=str(Path(tmp) / "runtime.sqlite"))
            connection = FakeConnection([welcome()])
            adapter = self._adapter(
                runtime.intake,
                websocket=FakeWebSocketTransport([connection]),
            )
            try:
                runtime.attach_live(adapter)
                runtime.start_live(TOKEN)
                envelope = runtime.public_state()["evidence"]
                self.assertEqual(envelope["origin"], "fixture")
                self.assertFalse(envelope["live_participation"])
                self.assertFalse(envelope["live_verified"])
                self.assertEqual(envelope["adapter"]["state"], "active_fixture")
            finally:
                runtime.close()


if __name__ == "__main__":
    unittest.main()
