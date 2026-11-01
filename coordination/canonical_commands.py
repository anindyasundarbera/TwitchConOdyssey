"""Generic data-only command envelopes; no game rules or execution authority."""
import re

from .content_cache import canonical_bytes, canonical_hash, detached, validate_json

_KIND = re.compile(r"[a-z][a-z0-9_.-]{0,63}\Z")
_FIELDS = {"schema_version", "command_id", "kind", "actor_id", "provenance",
           "logical_tick", "sequence", "payload"}
MAX_COMMAND_BYTES = 65536
MAX_COMMAND_DEPTH = 16
MAX_COMMAND_NODES = 4096
MAX_COMMAND_CONTAINERS = 1024


def _admit_command(command, *, max_bytes=MAX_COMMAND_BYTES, max_nodes=MAX_COMMAND_NODES):
    validate_json(command, max_depth=MAX_COMMAND_DEPTH, max_nodes=max_nodes,
                  max_containers=MAX_COMMAND_CONTAINERS,
                  max_string_bytes=MAX_COMMAND_BYTES, max_bytes=max_bytes)


def _validate_body(body):
    _admit_command(body, max_bytes=MAX_COMMAND_BYTES - 100,
                   max_nodes=MAX_COMMAND_NODES - 1)
    if type(body["schema_version"]) is not int or body["schema_version"] != 1:
        raise ValueError("Unsupported command version")
    if type(body["kind"]) is not str or not _KIND.fullmatch(body["kind"]):
        raise ValueError("Command kind must be a bounded lowercase identifier")
    actor = body["actor_id"]
    if (type(actor) is not str or not actor.strip() or len(actor) > 128
            or any(ord(char) < 32 for char in actor)):
        raise ValueError("Actor ID must be bounded nonempty text")
    if type(body["provenance"]) is not str or body["provenance"] not in {
            "human", "bot", "fixture"}:
        raise ValueError("Provenance must be human, bot or fixture")
    for field in ("logical_tick", "sequence"):
        if type(body[field]) is not int or body[field] < 0:
            raise ValueError("Logical tick/sequence must be nonnegative integers")
    if type(body["payload"]) is not dict:
        raise ValueError("Payload must be a JSON object")
    if len(canonical_bytes(body)) > MAX_COMMAND_BYTES - 100:
        raise ValueError("Command exceeds byte budget")


def make_command(kind, actor_id, provenance, logical_tick, sequence, payload):
    """Build a detached envelope whose ID binds every field except the ID."""
    body = {"schema_version": 1, "kind": kind, "actor_id": actor_id,
            "provenance": provenance, "logical_tick": logical_tick,
            "sequence": sequence, "payload": payload}
    _validate_body(body)
    return detached({**body, "command_id": canonical_hash(body)})


def validate_command(command):
    """Reject unknown fields, invalid data and stale IDs; return a detached copy.

    Provenance is a caller label, not independently authenticated identity.
    Validation does not imply eligibility, idempotent application or execution.
    """
    _admit_command(command)
    if type(command) is not dict or set(command) != _FIELDS:
        raise ValueError("Malformed command envelope")
    body = {key: value for key, value in command.items() if key != "command_id"}
    _validate_body(body)
    if type(command["command_id"]) is not str or command["command_id"] != canonical_hash(body):
        raise ValueError("Command ID mismatch")
    if len(canonical_bytes(command)) > MAX_COMMAND_BYTES:
        raise ValueError("Command exceeds byte budget")
    return detached(command)
