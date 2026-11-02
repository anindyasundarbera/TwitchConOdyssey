"""Live Twitch EventSub WebSocket boundary for ``channel.chat.message``.

The adapter is deliberately transport-injectable so local tests never touch
Twitch.  It validates a user OAuth token with the official validation endpoint,
opens one EventSub WebSocket, waits for the welcome session, subscribes to
``channel.chat.message`` version 1, then turns strict ``!`` commands into
canonical receipts for the existing :class:`server.intake.CommandIntake`.

Privacy rules:
- token bytes are used only for validation and subscription and are never
  stored on the adapter, logged, written or placed in evidence;
- raw chat text, handles, user IDs, session IDs and subscription IDs never
  enter evidence; stable SHA-256 hashes are recorded instead;
- the adapter never mutates engine state.  It only calls ``CommandIntake`` and
  reads detached snapshots to describe the visible consequence.

Accepted chat receipts are the exact, bounded tokens ``!left``, ``!right``,
``!cancel``, ``!hazard`` and ``!counter`` (trailing/leading whitespace ignored,
case-insensitive).  ``!counter`` binds to the currently committed hazard.

Evidence labelling:
- a real transport can produce ``origin="live"`` records only after token
  validation and an actual subscription notification;
- an injected fake transport must be constructed with
  ``transport_kind="fixture"`` and can never set ``live_verified``.
"""
from collections import OrderedDict
import base64
import copy
import hashlib
import json
import os
import socket
import ssl
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from coordination.canonical_commands import make_command
from schemas.validate import contract

WELCOME_URL = "wss://eventsub.wss.twitch.tv/ws"
VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"
SUBSCRIBE_URL = "https://api.twitch.tv/helix/eventsub/subscriptions"
SUBSCRIPTION_TYPE = "channel.chat.message"
SUBSCRIPTION_VERSION = "1"
REQUIRED_SCOPE = "user:read:chat"

LIVE_LABEL = "live Twitch EventSub channel.chat.message"
FIXTURE_LABEL = "fixture EventSub transport (not live Twitch evidence)"
DISCONNECTED_LABEL = "live adapter disconnected / offline (not live Twitch activity)"
REVOKED_LABEL = "live adapter revoked / offline (not live Twitch activity)"
FAILED_LABEL = "live adapter failed / offline (not live Twitch activity)"
CONNECTING_LABEL = (
    "live adapter active; awaiting first verified channel.chat.message "
    "(not live evidence yet)"
)

MAX_TOKEN_CHARS = 512
MAX_ID_CHARS = 64
MAX_CLIENT_ID_CHARS = 128
MAX_CHAT_CHARS = 160
MAX_WS_FRAME_BYTES = 262144
MAX_HTTP_BODY_BYTES = 1048576
MAX_DEDUPE = 1024
MAX_EVIDENCE_RECORDS = 64
MAX_SUBJECTS = 10000
MAX_RECONNECTS = 3
MAX_WELCOME_FRAMES = 8
DEFAULT_KEEPALIVE_TIMEOUT = 10
MIN_KEEPALIVE_TIMEOUT = 1
MAX_KEEPALIVE_TIMEOUT = 300
KEEPALIVE_GRACE_SECONDS = 2.0
RECEIVE_TIMEOUT_SECONDS = 1.0
MAX_RECONNECT_URL_CHARS = 512

_STEER_COMMANDS = {
    "!left": {"direction": "left"},
    "!right": {"direction": "right"},
    "!cancel": {"direction": "cancel"},
}


class TwitchLiveError(RuntimeError):
    """Bounded, token-free adapter failure code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class UrllibHttpTransport:
    """Small stdlib HTTP transport; no retries and no credential logging."""

    def request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[bytes],
        timeout: float = 10.0,
    ) -> Tuple[int, bytes]:
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.status, response.read(MAX_HTTP_BODY_BYTES)
        except HTTPError as exc:
            try:
                payload = exc.read(MAX_HTTP_BODY_BYTES)
            except Exception:
                payload = b""
            return exc.code, payload
        except (URLError, TimeoutError, OSError):
            raise TwitchLiveError("http_transport_failed") from None


class _StdlibWebSocketConnection:
    """Minimal RFC 6455 client sufficient for the EventSub receive stream."""

    _GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, sock: Any, timeout: float, buffered: bytes = b"") -> None:
        self._sock = sock
        self._timeout = timeout
        self._buffer = bytearray(buffered)
        self._closed = False
        self._fragments = bytearray()
        self._fragmenting = False

    @classmethod
    def connect(cls, url: str, timeout: float) -> "_StdlibWebSocketConnection":
        parsed = urlparse(url)
        if parsed.scheme != "wss" or not parsed.hostname:
            raise TwitchLiveError("invalid_websocket_url")
        raw = socket.create_connection((parsed.hostname, parsed.port or 443), timeout=timeout)
        try:
            context = ssl.create_default_context()
            sock = context.wrap_socket(raw, server_hostname=parsed.hostname)
        except Exception:
            raw.close()
            raise TwitchLiveError("websocket_handshake_failed") from None
        try:
            sock.settimeout(timeout)
            key = base64.b64encode(os.urandom(16)).decode("ascii")
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            host = parsed.hostname if parsed.port is None else f"{parsed.hostname}:{parsed.port}"
            request = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                "Sec-WebSocket-Version: 13\r\n\r\n"
            )
            sock.sendall(request.encode("ascii"))
            header = b""
            while b"\r\n\r\n" not in header:
                chunk = sock.recv(4096)
                if not chunk:
                    raise TwitchLiveError("websocket_handshake_failed")
                header += chunk
                if len(header) > 16384:
                    raise TwitchLiveError("websocket_handshake_failed")
            first, _, remainder = header.partition(b"\r\n\r\n")
            lines = first.split(b"\r\n")
            if len(lines) < 1 or b" 101" not in lines[0]:
                raise TwitchLiveError("websocket_handshake_failed")
            response_headers = {}
            for line in lines[1:]:
                if b":" not in line:
                    continue
                name, value = line.split(b":", 1)
                response_headers[name.strip().lower()] = value.strip()
            expected = base64.b64encode(
                hashlib.sha1((key + cls._GUID).encode("ascii")).digest()
            )
            if response_headers.get(b"sec-websocket-accept") != expected:
                raise TwitchLiveError("websocket_handshake_failed")
        except Exception:
            try:
                sock.close()
            except Exception:
                pass
            raise
        return cls(sock, timeout, remainder)

    def _read_exact(self, size: int) -> bytes:
        while len(self._buffer) < size:
            chunk = self._sock.recv(size - len(self._buffer))
            if not chunk:
                raise TwitchLiveError("websocket_closed")
            self._buffer.extend(chunk)
        value = bytes(self._buffer[:size])
        del self._buffer[:size]
        return value

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        if self._closed:
            return
        header = bytearray([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(length.to_bytes(2, "big"))
        else:
            header.append(0x80 | 127)
            header.extend(length.to_bytes(8, "big"))
        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self._sock.sendall(bytes(header) + masked)

    def recv(self, timeout: float) -> Optional[str]:
        self._sock.settimeout(timeout)
        while True:
            try:
                first = self._read_exact(2)
            except socket.timeout:
                return None
            fin = bool(first[0] & 0x80)
            opcode = first[0] & 0x0F
            masked = bool(first[1] & 0x80)
            length = first[1] & 0x7F
            if length == 126:
                length = int.from_bytes(self._read_exact(2), "big")
            elif length == 127:
                length = int.from_bytes(self._read_exact(8), "big")
            if length > MAX_WS_FRAME_BYTES:
                raise TwitchLiveError("websocket_frame_too_large")
            mask = self._read_exact(4) if masked else b""
            payload = self._read_exact(length)
            if masked:
                payload = bytes(
                    byte ^ mask[index % 4] for index, byte in enumerate(payload)
                )
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode == 0x8:
                raise TwitchLiveError("websocket_closed")
            if opcode == 0x1:
                if self._fragmenting:
                    raise TwitchLiveError("websocket_protocol_error")
                if not fin:
                    self._fragmenting = True
                    self._fragments = bytearray(payload)
                    continue
                return self._decode_text(payload)
            if opcode == 0x0:
                if not self._fragmenting:
                    raise TwitchLiveError("websocket_protocol_error")
                self._fragments.extend(payload)
                if len(self._fragments) > MAX_WS_FRAME_BYTES:
                    raise TwitchLiveError("websocket_frame_too_large")
                if not fin:
                    continue
                complete = bytes(self._fragments)
                self._fragments = bytearray()
                self._fragmenting = False
                return self._decode_text(complete)
            raise TwitchLiveError("websocket_protocol_error")

    @staticmethod
    def _decode_text(payload: bytes) -> str:
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            raise TwitchLiveError("websocket_frame_invalid_utf8") from None

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._send_frame(0x8, b"")
        except Exception:
            pass
        self._closed = True
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            self._sock.close()
        except Exception:
            pass


class _StdlibWebSocketTransport:
    def connect(self, url: str, timeout: float) -> _StdlibWebSocketConnection:
        return _StdlibWebSocketConnection.connect(url, timeout)


def _bounded_text(value: Any, label: str, limit: int) -> str:
    if (type(value) is not str or not value or len(value) > limit
            or any(ord(char) < 32 for char in value)):
        raise ValueError(f"{label} must be bounded nonempty text")
    return value


def _bounded_id(value: Any, label: str, limit: int = MAX_ID_CHARS) -> str:
    value = _bounded_text(value, label, limit)
    if not value.isascii() or not value.isdigit():
        raise ValueError(f"{label} must be a bounded numeric identifier")
    return value


def _identity_hash(kind: str, value: str) -> str:
    return hashlib.sha256(f"twitch:{kind}:{value}".encode("utf-8")).hexdigest()


def _receipt_hash(message_id: str) -> str:
    return hashlib.sha256(f"twitch:message:{message_id}".encode("utf-8")).hexdigest()


def _session_hash(session_id: str) -> str:
    return hashlib.sha256(f"twitch:session:{session_id}".encode("utf-8")).hexdigest()


def _subscription_hash(subscription_id: str) -> str:
    return hashlib.sha256(f"twitch:subscription:{subscription_id}".encode("utf-8")).hexdigest()


class TwitchEventSubAdapter:
    """One EventSub WebSocket connection feeding the authoritative intake."""

    def __init__(
        self,
        intake: Any,
        *,
        client_id: str,
        broadcaster_user_id: str,
        user_id: str,
        http: Optional[Any] = None,
        websocket: Optional[Any] = None,
        clock: Callable[[], float] = time.time,
        transport_kind: str = "live",
        timeout: float = 10.0,
    ) -> None:
        if transport_kind not in ("live", "fixture"):
            raise ValueError("transport_kind must be live or fixture")
        self.intake = intake
        self._transport_kind = transport_kind
        self._http = http if http is not None else UrllibHttpTransport()
        self._websocket = websocket if websocket is not None else _StdlibWebSocketTransport()
        self._clock = clock
        self._timeout = float(timeout)
        self._client_id = _bounded_text(client_id, "client_id", MAX_CLIENT_ID_CHARS)
        self._broadcaster_user_id = _bounded_id(broadcaster_user_id, "broadcaster_user_id")
        self._user_id = _bounded_id(user_id, "user_id")
        self._client_id_sha256 = _identity_hash("client", self._client_id)
        self._broadcaster_user_id_sha256 = _identity_hash("broadcaster", self._broadcaster_user_id)
        self._user_id_sha256 = _identity_hash("user", self._user_id)

        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._started = False
        self._validated = False
        self._connected = False
        self._subscribed = False
        self._active = False
        self._failed = False
        self._revoked = False
        self._validation: Optional[Dict[str, Any]] = None
        self._subscription: Optional[Dict[str, Any]] = None
        self._session: Optional[Dict[str, Any]] = None
        self._session_id: Optional[str] = None
        self._ws: Optional[Any] = None
        self._last_error: Optional[str] = None
        self._reconnect_count = 0
        self._keepalive_timeout = DEFAULT_KEEPALIVE_TIMEOUT
        self._last_activity = 0.0
        self._last_keepalive = 0.0
        self._seen_messages: OrderedDict[str, None] = OrderedDict()
        self._sequence_by_subject: Dict[str, int] = {}
        self._linked_subjects: set = set()
        self._records: List[Dict[str, Any]] = []
        self._notification_count = 0
        self._accepted_count = 0
        self._duplicate_count = 0
        self._ignored_frames = 0
        self._keepalive_count = 0
        self._live_verified = False
        self._rejections = {
            "non_command": 0,
            "oversized_chat": 0,
            "unsupported_chat": 0,
            "no_committed_hazard": 0,
            "invalid_notification": 0,
            "identity_rejected": 0,
        }

    # ----- lifecycle --------------------------------------------------------
    def start(self, token: str) -> None:
        """Validate the token, read the welcome, then subscribe exactly once."""
        with self._lock:
            if self._started:
                raise TwitchLiveError("already_started")
            self._started = True
        try:
            validation = self._validate_token(token)
            with self._lock:
                self._validation = validation
                self._validated = True
            connection = self._websocket.connect(WELCOME_URL, self._timeout)
            with self._lock:
                self._ws = connection
                self._connected = True
            welcome = self._read_welcome(connection)
            with self._lock:
                self._session = welcome
                self._session_id = welcome["session_id"]
                self._keepalive_timeout = welcome["keepalive_timeout_seconds"]
                self._last_activity = self._clock()
            self._subscribe(token)
            with self._lock:
                self._subscribed = True
                self._active = True
                self._last_activity = self._clock()
                self._clear_pending_identity()
        except TwitchLiveError as exc:
            self._fail(exc.code)
            raise
        except Exception:
            self._fail("adapter_start_failed")
            raise TwitchLiveError("adapter_start_failed") from None

    def run(self) -> None:
        """Read the bounded receive loop until stop or a fail-closed condition."""
        while not self._stop.is_set():
            try:
                processed = self.pump()
            except TwitchLiveError as exc:
                self._fail(exc.code)
                return
            except Exception:
                self._fail("adapter_loop_failed")
                return
            if processed == 0:
                self._stop.wait(0.05)

    def pump(self, max_frames: int = 64) -> int:
        """Process at most ``max_frames`` frames; return the number read."""
        processed = 0
        while processed < max_frames:
            with self._lock:
                if not self._is_active_locked() or self._ws is None:
                    break
                connection = self._ws
            try:
                frame = connection.recv(RECEIVE_TIMEOUT_SECONDS)
            except TwitchLiveError as exc:
                self._fail(exc.code)
                break
            except Exception:
                self._fail("websocket_receive_failed")
                break
            if frame is None:
                if self._keepalive_expired():
                    self._fail("keepalive_timeout")
                break
            processed += 1
            try:
                self._handle_frame(frame)
            except TwitchLiveError as exc:
                self._fail(exc.code)
                break
            except Exception:
                self._fail("frame_processing_failed")
                break
        return processed

    def stop(self) -> None:
        self._stop.set()
        with self._lock:
            self._active = False
            connection = self._ws
            self._ws = None
            self._clear_pending_identity()
        if connection is not None:
            connection.close()

    # ----- state ------------------------------------------------------------
    @property
    def transport_kind(self) -> str:
        return self._transport_kind

    @property
    def active(self) -> bool:
        with self._lock:
            return self._is_active_locked()

    @property
    def live_active(self) -> bool:
        return self._transport_kind == "live" and self.active

    @property
    def live_verified(self) -> bool:
        return self.live_active and self._live_verified

    @property
    def reconnect_count(self) -> int:
        with self._lock:
            return self._reconnect_count

    @property
    def session_id_sha256(self) -> Optional[str]:
        with self._lock:
            if self._session_id is None:
                return None
            return _session_hash(self._session_id)

    @property
    def last_error(self) -> Optional[str]:
        with self._lock:
            return self._last_error

    def evidence_records(self) -> List[Dict[str, Any]]:
        with self._lock:
            return copy.deepcopy(self._records)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "transport_kind": self._transport_kind,
                "validated": self._validated,
                "connected": self._connected,
                "subscribed": self._subscribed,
                "active": self._is_active_locked(),
                "live_verified": self._live_verified,
                "notifications": self._notification_count,
                "accepted_commands": self._accepted_count,
                "duplicates": self._duplicate_count,
                "ignored_frames": self._ignored_frames,
                "keepalives": self._keepalive_count,
                "dedupe_entries": len(self._seen_messages),
                "tracked_subjects": len(self._sequence_by_subject),
                "evidence_records": len(self._records),
                "rejections": dict(self._rejections),
            }

    def evidence_envelope(self) -> Dict[str, Any]:
        """Return the server-owned evidence context used by ``public_state``."""
        with self._lock:
            active = self._is_active_locked()
            adapter = {
                "transport": self._transport_kind,
                "validated": self._validated,
                "subscribed": self._subscribed,
                "state": self._state_locked(active),
                "session_id_sha256": (
                    _session_hash(self._session_id) if self._session_id else None
                ),
                "subscription_id_sha256": (
                    self._subscription["subscription_id_sha256"]
                    if self._subscription else None
                ),
                "notifications": self._notification_count,
                "accepted_commands": self._accepted_count,
                "reconnects": self._reconnect_count,
            }
            if self._last_error:
                adapter["last_error"] = self._last_error
            # A live origin is emitted only after token validation, an enabled
            # subscription and at least one accepted channel.chat.message
            # notification. A connected-but-unproven adapter is disconnected
            # evidence, never a live claim.
            if self._transport_kind == "live" and active and self._live_verified:
                return {
                    "origin": "live",
                    "origin_label": LIVE_LABEL,
                    "live_participation": True,
                    "live_verified": True,
                    "fixture": False,
                    "authority": "authoritative-runtime",
                    "adapter": adapter,
                }
            if self._transport_kind == "fixture":
                label = FIXTURE_LABEL
            elif self._revoked:
                label = REVOKED_LABEL
            elif self._failed:
                label = FAILED_LABEL
            elif self._transport_kind == "live" and active:
                label = CONNECTING_LABEL
            else:
                label = DISCONNECTED_LABEL
            return {
                "origin": "disconnected" if self._transport_kind == "live" else "fixture",
                "origin_label": label,
                "live_participation": False,
                "live_verified": False,
                "fixture": self._transport_kind != "live",
                "authority": "authoritative-runtime",
                "adapter": adapter,
            }

    # ----- token and subscription ------------------------------------------
    def _validate_token(self, token: str) -> Dict[str, Any]:
        if type(token) is not str or not 1 <= len(token) <= MAX_TOKEN_CHARS:
            raise TwitchLiveError("invalid_token")
        status, body = self._http.request(
            "GET", VALIDATE_URL,
            {"Authorization": f"OAuth {token}", "Accept": "application/json"},
            None, self._timeout,
        )
        if status != 200:
            raise TwitchLiveError("token_rejected")
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            raise TwitchLiveError("token_response_malformed") from None
        if type(payload) is not dict:
            raise TwitchLiveError("token_response_malformed")
        scopes = payload.get("scopes")
        if (type(scopes) is not list
                or any(type(scope) is not str or len(scope) > 64 for scope in scopes)):
            raise TwitchLiveError("token_response_malformed")
        if REQUIRED_SCOPE not in scopes:
            raise TwitchLiveError("missing_required_scope")
        expires_in = payload.get("expires_in")
        if type(expires_in) is not int or isinstance(expires_in, bool) or expires_in <= 0:
            raise TwitchLiveError("token_expired")
        if payload.get("client_id") != self._client_id:
            raise TwitchLiveError("client_id_mismatch")
        if payload.get("user_id") != self._user_id:
            raise TwitchLiveError("token_user_mismatch")
        validated_at = int(self._clock())
        return {
            "validated": True,
            "validated_at": validated_at,
            "expires_at": validated_at + expires_in,
            "client_id_sha256": self._client_id_sha256,
            "user_id_sha256": self._user_id_sha256,
            "scopes": sorted(set(scopes)),
        }

    def _subscribe(self, token: str) -> None:
        with self._lock:
            if self._session_id is None:
                raise TwitchLiveError("welcome_session_missing")
            payload = {
                "type": SUBSCRIPTION_TYPE,
                "version": SUBSCRIPTION_VERSION,
                "condition": {
                    "broadcaster_user_id": self._broadcaster_user_id,
                    "user_id": self._user_id,
                },
                "transport": {"method": "websocket", "session_id": self._session_id},
            }
            client_id = self._client_id
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        status, response = self._http.request(
            "POST", SUBSCRIBE_URL,
            {
                "Authorization": f"Bearer {token}",
                "Client-Id": client_id,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body, self._timeout,
        )
        if status not in (200, 202):
            raise TwitchLiveError("subscription_rejected")
        try:
            data = json.loads(response.decode("utf-8"))
        except Exception:
            raise TwitchLiveError("subscription_response_malformed") from None
        items = data.get("data") if type(data) is dict else None
        if type(items) is not list or not items or type(items[0]) is not dict:
            raise TwitchLiveError("subscription_response_malformed")
        item = items[0]
        if (item.get("type") != SUBSCRIPTION_TYPE
                or str(item.get("version")) != SUBSCRIPTION_VERSION
                or item.get("status") != "enabled"):
            raise TwitchLiveError("subscription_not_enabled")
        subscription_id = item.get("id")
        if (type(subscription_id) is not str or not subscription_id
                or len(subscription_id) > 128):
            raise TwitchLiveError("subscription_response_malformed")
        self._subscription = {
            "subscription_id_sha256": _subscription_hash(subscription_id),
            "type": SUBSCRIPTION_TYPE,
            "version": SUBSCRIPTION_VERSION,
            "status": "enabled",
            "subscribed_at": int(self._clock()),
        }

    # ----- receive path -----------------------------------------------------
    def _read_welcome(self, connection: Any) -> Dict[str, Any]:
        for _ in range(MAX_WELCOME_FRAMES):
            frame = connection.recv(self._timeout)
            if frame is None:
                continue
            message = self._decode_frame(frame)
            message_type = self._message_type(message)
            if message_type == "session_welcome":
                payload = message.get("payload")
                session = payload.get("session") if type(payload) is dict else None
                if type(session) is not dict:
                    raise TwitchLiveError("welcome_malformed")
                session_id = session.get("id")
                if (type(session_id) is not str or not session_id
                        or len(session_id) > 256):
                    raise TwitchLiveError("welcome_malformed")
                keepalive = session.get("keepalive_timeout_seconds", DEFAULT_KEEPALIVE_TIMEOUT)
                if (type(keepalive) is not int or isinstance(keepalive, bool)
                        or not MIN_KEEPALIVE_TIMEOUT <= keepalive <= MAX_KEEPALIVE_TIMEOUT):
                    raise TwitchLiveError("welcome_malformed")
                return {
                    "session_id": session_id,
                    "keepalive_timeout_seconds": keepalive,
                    "connected_at": int(self._clock()),
                }
            if message_type == "session_keepalive":
                continue
            if message_type in ("revocation", "session_revocation"):
                raise TwitchLiveError("revoked_before_welcome")
            raise TwitchLiveError("unexpected_welcome_message")
        raise TwitchLiveError("welcome_timeout")

    def _handle_frame(self, frame: str) -> None:
        message = self._decode_frame(frame)
        message_type = self._message_type(message)
        with self._lock:
            self._last_activity = self._clock()
        if message_type == "session_keepalive":
            with self._lock:
                self._last_keepalive = self._clock()
                self._keepalive_count += 1
            return
        if message_type == "notification":
            self._handle_notification(message)
            return
        if message_type == "session_reconnect":
            self._handle_reconnect(message)
            return
        if message_type in ("revocation", "session_revocation"):
            self._handle_revocation(message)
            return
        with self._lock:
            self._ignored_frames += 1

    def _handle_notification(self, message: Dict[str, Any]) -> None:
        metadata = _message_dict(message, "metadata")
        if metadata is None:
            self._bump("invalid_notification")
            return
        if (metadata.get("subscription_type") != SUBSCRIPTION_TYPE
                or str(metadata.get("subscription_version")) != SUBSCRIPTION_VERSION):
            self._bump("invalid_notification")
            return
        with self._lock:
            self._notification_count += 1
        message_id = metadata.get("message_id")
        if (type(message_id) is not str or not message_id or len(message_id) > 128
                or any(ord(char) < 32 for char in message_id)):
            self._bump("invalid_notification")
            return
        receipt = _receipt_hash(message_id)
        with self._lock:
            if receipt in self._seen_messages:
                self._duplicate_count += 1
                return
            self._remember(self._seen_messages, receipt)

        payload = message.get("payload")
        event = payload.get("event") if type(payload) is dict else None
        if type(event) is not dict:
            self._bump("invalid_notification")
            return
        chatter_id = event.get("chatter_user_id")
        broadcaster_id = event.get("broadcaster_user_id")
        if (type(chatter_id) is not str or not chatter_id.isdigit()
                or not 1 <= len(chatter_id) <= MAX_ID_CHARS
                or type(broadcaster_id) is not str
                or _identity_hash("broadcaster", broadcaster_id)
                != self._broadcaster_user_id_sha256):
            self._bump("invalid_notification")
            return
        chat = event.get("message")
        text = chat.get("text") if type(chat) is dict else None
        if type(text) is not str:
            self._bump("invalid_notification")
            return
        if len(text) > MAX_CHAT_CHARS:
            self._bump("oversized_chat")
            return
        if any(ord(char) < 32 for char in text):
            self._bump("unsupported_chat")
            return
        parsed = self._parse_command(text, receipt)
        if parsed[0] is None:
            self._bump(parsed[2] or "non_command")
            return
        kind, command_payload, hazard_id = parsed
        subject = _identity_hash("user", chatter_id)
        channel_identity = "twitch:" + subject
        try:
            with self._lock:
                linked = subject in self._linked_subjects
            if not linked:
                self.intake.registry.link(subject, channel_identity)
                # One-time roster registration, separate from the receipt's
                # single canonical command submission below.
                self.intake.join(subject)
                with self._lock:
                    self._linked_subjects.add(subject)
            with self._lock:
                if subject not in self._sequence_by_subject:
                    if len(self._sequence_by_subject) >= MAX_SUBJECTS:
                        raise ValueError("subject capacity reached")
                    sequence = 0
                else:
                    sequence = self._sequence_by_subject[subject] + 1
                self._sequence_by_subject[subject] = sequence
        except Exception:
            self._bump("identity_rejected")
            return

        before = self.intake.engine.snapshot()
        status = self.intake.submit(
            receipt, channel_identity, kind, command_payload, sequence, provenance="human"
        )
        after = self.intake.engine.snapshot()
        decision = self.intake.decisions[-1] if self.intake.decisions else {}
        if decision.get("receipt_id") != receipt:
            self._bump("invalid_notification")
            return
        command = make_command(
            kind, subject, "human", decision["tick"], sequence, command_payload
        )
        record = self._build_record(
            receipt=receipt,
            subject=subject,
            command=command,
            status=status,
            decision=decision,
            before=before,
            after=after,
            hazard_id=hazard_id,
        )
        contract("twitch-live", record)
        with self._lock:
            self._records = (self._records + [record])[-MAX_EVIDENCE_RECORDS:]
            if status in ("applied", "duplicate"):
                self._accepted_count += 1
                if self._transport_kind == "live":
                    self._live_verified = True

    def _handle_reconnect(self, message: Dict[str, Any]) -> None:
        payload = message.get("payload")
        session = payload.get("session") if type(payload) is dict else None
        url = session.get("reconnect_url") if type(session) is dict else None
        if not self._valid_reconnect_url(url):
            self._fail("invalid_reconnect_url")
            return
        with self._lock:
            if self._reconnect_count >= MAX_RECONNECTS:
                self._fail("reconnect_limit")
                return
            self._reconnect_count += 1
        try:
            connection = self._websocket.connect(url, self._timeout)
        except Exception:
            self._fail("reconnect_failed")
            return
        try:
            welcome = self._read_welcome(connection)
        except TwitchLiveError as exc:
            connection.close()
            self._fail(exc.code)
            return
        with self._lock:
            old = self._ws
            self._ws = connection
            self._session = welcome
            self._session_id = welcome["session_id"]
            self._keepalive_timeout = welcome["keepalive_timeout_seconds"]
            self._last_activity = self._clock()
        if old is not None:
            old.close()

    def _handle_revocation(self, message: Dict[str, Any]) -> None:
        with self._lock:
            self._revoked = True
            self._active = False
            if self._subscription is not None:
                self._subscription = dict(self._subscription, status="revoked")
            connection = self._ws
            self._ws = None
            self._clear_pending_identity()
        if connection is not None:
            connection.close()

    # ----- helpers ----------------------------------------------------------
    def _parse_command(
        self, text: str, receipt: str
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[str]]:
        normalized = text.strip().lower()
        if len(normalized) > MAX_CHAT_CHARS:
            return None, None, "oversized_chat"
        if not normalized.startswith("!"):
            return None, None, "non_command"
        steer = _STEER_COMMANDS.get(normalized)
        if steer is not None:
            return "streamer.steer", dict(steer), None
        if normalized == "!hazard":
            hazard_id = "twitch-" + receipt[:24]
            return "hazard.propose", {
                "hazard_id": hazard_id,
                "kind": "blocked_demo_lane",
                "lane": 1,
            }, hazard_id
        if normalized == "!counter":
            state = self.intake.engine.snapshot()
            hazard_id = state.get("hazard", {}).get("committed")
            if type(hazard_id) is not str or not hazard_id:
                return None, None, "no_committed_hazard"
            return "viewer.counter", {
                "hazard_id": hazard_id,
                "counter": "clear_lane",
            }, hazard_id
        return None, None, "non_command"

    def _build_record(
        self,
        *,
        receipt: str,
        subject: str,
        command: Dict[str, Any],
        status: str,
        decision: Dict[str, Any],
        before: Dict[str, Any],
        after: Dict[str, Any],
        hazard_id: Optional[str],
    ) -> Dict[str, Any]:
        with self._lock:
            validation = copy.deepcopy(self._validation)
            subscription = copy.deepcopy(self._subscription)
            session = {
                "session_id_sha256": (
                    _session_hash(self._session_id) if self._session_id else None
                ),
                "connected_at": self._session["connected_at"] if self._session else 0,
                "reconnect_count": self._reconnect_count,
                "keepalive_timeout_seconds": self._keepalive_timeout,
            }
        record = {
            "schema_version": 1,
            "origin": "live" if self._transport_kind == "live" else "fixture",
            "origin_label": LIVE_LABEL if self._transport_kind == "live" else FIXTURE_LABEL,
            "live_participation": self._transport_kind == "live",
            "live_verified": (
                self._transport_kind == "live" and status in ("applied", "duplicate")
            ),
            "fixture": self._transport_kind == "fixture",
            "recorded_at": int(self._clock()),
            "token_validation": validation,
            "subscription": subscription,
            "session": session,
            "receipt_sha256": receipt,
            "subject_sha256": subject,
            "command": {
                "command_id": command["command_id"],
                "kind": command["kind"],
                "actor_sha256": command["actor_id"],
                "provenance": command["provenance"],
                "logical_tick": command["logical_tick"],
                "sequence": command["sequence"],
                "payload": command["payload"],
            },
            "result": {
                "status": status,
                "reason": decision.get("reason") or ("engine_" + status),
            },
            "consequence": self._consequence(
                before, after, command["kind"], hazard_id, status, decision
            ),
        }
        return record

    def _consequence(
        self,
        before: Dict[str, Any],
        after: Dict[str, Any],
        kind: str,
        hazard_id: Optional[str],
        status: str,
        decision: Dict[str, Any],
    ) -> Dict[str, Any]:
        before_view = self._view(before)
        after_view = self._view(after)
        if status in ("applied", "duplicate"):
            if kind == "streamer.steer":
                summary = (
                    f"steer {after_view['lane']} lane after command; "
                    f"transition {after_view['transition_remaining_ticks']} ticks"
                )
            elif kind == "hazard.propose":
                summary = f"hazard {hazard_id} {status}; committed {after_view['hazard']}"
            elif kind == "viewer.counter":
                summary = (
                    f"counter {status}; hazard_countered "
                    f"{after_view['hazard_countered']}"
                )
            else:
                summary = f"{kind} {status}"
        else:
            reason = decision.get("reason") or ("engine_" + status)
            summary = f"{kind} {status}: {reason}"
        return {
            "summary": summary[:240],
            "before": before_view,
            "after": after_view,
        }

    @staticmethod
    def _view(state: Dict[str, Any]) -> Dict[str, Any]:
        avatar = state.get("avatar", {})
        movement = state.get("movement", {})
        hazard = state.get("hazard", {})
        bounty = state.get("bounty", {})
        audience = state.get("audience", {})
        return {
            "status": state.get("status"),
            "turn": state.get("turn"),
            "phase": state.get("phase"),
            "lane": avatar.get("lane"),
            "lateral_pos": avatar.get("lateral_pos"),
            "transition_remaining_ticks": avatar.get("transition_remaining_ticks"),
            "progress": movement.get("progress"),
            "hazard": hazard.get("committed"),
            "warning_active": hazard.get("warning_active"),
            "obstacle_active": hazard.get("obstacle_active"),
            "hazard_countered": hazard.get("hazard_countered"),
            "collisions_total": bounty.get("collisions_total"),
            "pool": bounty.get("pool"),
            "counter_votes_count": audience.get("counter_votes_count"),
            "eligible_voters_count": audience.get("eligible_voters_count"),
        }

    def _valid_reconnect_url(self, url: Any) -> bool:
        if (type(url) is not str or not url or len(url) > MAX_RECONNECT_URL_CHARS
                or any(ord(char) < 32 for char in url)):
            return False
        parsed = urlparse(url)
        host = parsed.hostname
        return (
            parsed.scheme == "wss"
            and host is not None
            and (host == "twitch.tv" or host.endswith(".twitch.tv"))
            and parsed.username is None
            and parsed.password is None
            and parsed.fragment == ""
            and parsed.port in (None, 443)
            and parsed.path.startswith("/")
        )

    def _keepalive_expired(self) -> bool:
        with self._lock:
            timeout = self._keepalive_timeout
            last = self._last_activity
        return self._clock() - last > timeout + KEEPALIVE_GRACE_SECONDS

    def _fail(self, code: str) -> None:
        with self._lock:
            self._failed = True
            self._active = False
            if self._last_error is None:
                self._last_error = _bounded_text(code, "error code", 64)
            connection = self._ws
            self._ws = None
            self._clear_pending_identity()
        if connection is not None:
            connection.close()

    def _clear_pending_identity(self) -> None:
        self._client_id = None
        self._broadcaster_user_id = None
        self._user_id = None

    def _is_active_locked(self) -> bool:
        return (
            self._active
            and self._validated
            and self._subscribed
            and not self._failed
            and not self._revoked
            and self._ws is not None
        )

    def _state_locked(self, active: bool) -> str:
        if active and self._transport_kind == "live":
            return "active_live"
        if active:
            return "active_fixture"
        if self._revoked:
            return "revoked"
        if self._failed:
            return "failed"
        if self._started:
            return "disconnected"
        return "not_started"

    def _bump(self, reason: str) -> None:
        with self._lock:
            if reason not in self._rejections:
                reason = "invalid_notification"
            self._rejections[reason] += 1

    @staticmethod
    def _remember(mapping: OrderedDict, key: str) -> None:
        mapping[key] = None
        mapping.move_to_end(key)
        while len(mapping) > MAX_DEDUPE:
            mapping.popitem(last=False)

    @staticmethod
    def _decode_frame(frame: str) -> Dict[str, Any]:
        if type(frame) is not str or len(frame.encode("utf-8")) > MAX_WS_FRAME_BYTES:
            raise TwitchLiveError("websocket_frame_too_large")
        try:
            message = json.loads(frame)
        except Exception:
            raise TwitchLiveError("websocket_frame_malformed") from None
        if type(message) is not dict:
            raise TwitchLiveError("websocket_frame_malformed")
        return message

    @staticmethod
    def _message_type(message: Dict[str, Any]) -> str:
        metadata = message.get("metadata")
        if type(metadata) is not dict:
            raise TwitchLiveError("websocket_frame_malformed")
        value = metadata.get("message_type")
        if type(value) is not str or not value or len(value) > 64:
            raise TwitchLiveError("websocket_frame_malformed")
        return value


def _message_dict(message: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    value = message.get(key)
    return value if type(value) is dict else None
