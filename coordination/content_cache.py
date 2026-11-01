"""Versioned JSON fingerprints and an in-memory content-addressed reuse cache.

Format v1 is UTF-8 JSON, sorted string keys, no whitespace, finite JSON numbers,
and a canonical-version wrapper. Hashes identify bytes/content, not truth,
authentication, or newly observed evidence. No files or services are read here.
"""
import hashlib
import json
import math
import re

CANONICAL_VERSION = 1
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ESCAPED = re.compile(r'[\x00-\x1f"\\]')
_WRAPPER_BYTES = len(b'{"canonical_version":1,"value":}')

# Admission counts JSON value occurrences, not distinct Python identities. Keys
# contribute to string/byte budgets; containers also count as value nodes. These
# limits admit 100,000 default viewer fixtures without permitting unbounded JSON.
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 1_000_000
MAX_JSON_CONTAINERS = 150_000
MAX_JSON_STRING_BYTES = 32 * 1024 * 1024
MAX_JSON_BYTES = 64 * 1024 * 1024
MAX_JSON_INTEGER_BITS = 256
MAX_BINDING_NODES = 4096
MAX_BINDING_STRING_BYTES = 64 * 1024
MAX_CACHE_VALUE_NODES = 750_000
MAX_CACHE_VALUE_CONTAINERS = 125_000
MAX_CACHE_VALUE_STRING_BYTES = 16 * 1024 * 1024
MAX_CACHE_VALUE_BYTES = 32 * 1024 * 1024


def validate_json(value, *, max_depth=MAX_JSON_DEPTH, max_nodes=MAX_JSON_NODES,
                  max_containers=MAX_JSON_CONTAINERS,
                  max_string_bytes=MAX_JSON_STRING_BYTES, max_bytes=MAX_JSON_BYTES):
    """Bound traversal and exact canonical byte cost before serialization/copy.

    Root depth is zero. Shared values are charged on every occurrence, while
    ancestor identities detect cycles. Only exact built-in JSON types enter;
    integer conversion is bounded to 256 bits. UTF-8 strings/keys and JSON escape
    expansion both count. Limits include the canonical wrapper's byte overhead.
    """
    limits = (max_depth, max_nodes, max_containers, max_string_bytes, max_bytes)
    ceilings = (MAX_JSON_DEPTH, MAX_JSON_NODES, MAX_JSON_CONTAINERS,
                MAX_JSON_STRING_BYTES, MAX_JSON_BYTES)
    if any(type(limit) is not int or not 0 <= limit <= ceiling
           for limit, ceiling in zip(limits, ceilings)):
        raise ValueError("JSON admission limits must be within the safe bounds")
    nodes = containers = string_bytes = 0
    encoded_bytes = _WRAPPER_BYTES
    ancestors = set()

    def charge_bytes(count):
        nonlocal encoded_bytes
        encoded_bytes += count
        if encoded_bytes > max_bytes:
            raise ValueError("JSON exceeds canonical byte budget")

    def charge_string(text):
        nonlocal string_bytes
        # UTF-8 uses at least one byte per character. Check before encoding so
        # one oversized input cannot allocate an oversized temporary byte string.
        if len(text) > max_string_bytes - string_bytes:
            raise ValueError("JSON exceeds aggregate UTF-8 string budget")
        size = 0
        try:
            # Bound temporary encodings too, including a rejected multibyte
            # string whose character count fits but UTF-8 byte count does not.
            for offset in range(0, len(text), 4096):
                size += len(text[offset:offset + 4096].encode("utf-8"))
                if size > max_string_bytes - string_bytes:
                    raise ValueError("JSON exceeds aggregate UTF-8 string budget")
        except UnicodeError as exc:
            raise ValueError("JSON strings must be valid UTF-8") from exc
        string_bytes += size
        charge_bytes(size + 2)
        for match in _ESCAPED.finditer(text):
            charge_bytes(1 if match[0] in '"\\\b\f\n\r\t' else 5)

    def walk(item, depth):
        nonlocal nodes, containers
        nodes += 1
        if depth > max_depth or nodes > max_nodes:
            raise ValueError("JSON exceeds depth or value-node budget")
        kind = type(item)
        if item is None:
            charge_bytes(4)
        elif kind is bool:
            charge_bytes(4 if item else 5)
        elif kind is str:
            charge_string(item)
        elif kind is int:
            if item.bit_length() > MAX_JSON_INTEGER_BITS:
                raise ValueError("JSON integer exceeds bit budget")
            charge_bytes(len(str(item)))
        elif kind is float and math.isfinite(item):
            charge_bytes(len(repr(item)))
        elif kind in (list, dict):
            containers += 1
            if containers > max_containers or len(item) > max_nodes - nodes:
                raise ValueError("JSON exceeds container or value-node budget")
            identity = id(item)
            if identity in ancestors:
                raise ValueError("JSON must be acyclic")
            charge_bytes(2 + max(0, len(item) - 1))
            ancestors.add(identity)
            try:
                if kind is dict:
                    for key, child in item.items():
                        if type(key) is not str:
                            raise ValueError("JSON object keys must be strings")
                        charge_string(key)
                        charge_bytes(1)
                        walk(child, depth + 1)
                else:
                    for child in item:
                        walk(child, depth + 1)
            finally:
                ancestors.remove(identity)
        else:
            raise ValueError("Expected JSON values with string keys and finite numbers")

    walk(value, 0)
    return encoded_bytes


def canonical_bytes(value):
    """Serialize JSON data in the explicitly versioned canonical format."""
    try:
        validate_json(value)
        return json.dumps({"canonical_version": CANONICAL_VERSION, "value": value},
                          sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8")
    except (RecursionError, UnicodeError) as exc:
        raise ValueError("JSON must be acyclic and valid UTF-8") from exc


def bytes_hash(raw):
    """Hash exact bytes, for callers binding existing plan/policy/code files."""
    if type(raw) is not bytes:
        raise ValueError("Expected bytes")
    return hashlib.sha256(raw).hexdigest()


def canonical_hash(value):
    return bytes_hash(canonical_bytes(value))


def detached(value):
    """Validate and return a JSON copy sharing no mutable values with the input."""
    return json.loads(canonical_bytes(value))["value"]


def require_hash(value):
    if type(value) is not str or not _HASH.fullmatch(value):
        raise ValueError("Expected a lowercase SHA-256 hex digest")
    return value


def make_bindings(*, plan_hash, policy_hash, context_hashes, corpus_hash,
                  code_hashes, result_hash=None):
    """Bind named explicit inputs; no ambient files or configuration are loaded."""
    for mapping in (context_hashes, code_hashes):
        _admit_binding(mapping)
        if (type(mapping) is not dict
                or any(type(key) is not str or not key.strip() for key in mapping)):
            raise ValueError("Context/code bindings must be named hash mappings")
        for value in mapping.values():
            require_hash(value)
    binding = {"schema_version": 1, "plan_hash": require_hash(plan_hash),
               "policy_hash": require_hash(policy_hash),
               "context_hashes": context_hashes, "corpus_hash": require_hash(corpus_hash),
               "code_hashes": code_hashes, "result_hash": result_hash}
    if result_hash is not None:
        require_hash(result_hash)
    _admit_binding(binding)
    return detached(binding)


def _binding_copy(binding):
    _admit_binding(binding)
    if type(binding) is not dict or set(binding) != {
            "schema_version", "plan_hash", "policy_hash", "context_hashes",
            "corpus_hash", "code_hashes", "result_hash"}:
        raise ValueError("Malformed content bindings")
    if type(binding["schema_version"]) is not int or binding["schema_version"] != 1:
        raise ValueError("Unsupported binding version")
    return make_bindings(**{key: value for key, value in binding.items()
                            if key != "schema_version"})


def _admit_binding(binding):
    validate_json(binding, max_depth=8, max_nodes=MAX_BINDING_NODES,
                  max_containers=256, max_string_bytes=MAX_BINDING_STRING_BYTES,
                  max_bytes=128 * 1024)


def _admit_cache_value(value):
    validate_json(value, max_depth=MAX_JSON_DEPTH - 1,
                  max_nodes=MAX_CACHE_VALUE_NODES,
                  max_containers=MAX_CACHE_VALUE_CONTAINERS,
                  max_string_bytes=MAX_CACHE_VALUE_STRING_BYTES,
                  max_bytes=MAX_CACHE_VALUE_BYTES)


class ContentCache:
    """Explicit in-memory cache. Changed bindings miss; corrupt hits fail closed."""

    def __init__(self):
        self._entries = {}

    def put(self, binding, value):
        # Admit both untrusted arguments before even serializing the bindings.
        _admit_binding(binding)
        _admit_cache_value(value)
        binding = _binding_copy(binding)
        result_hash = canonical_hash(value)
        if binding["result_hash"] not in (None, result_hash):
            raise ValueError("Result does not match its binding")
        key = canonical_hash(binding)
        record = {"schema_version": 1, "cache_key": key, "bindings": binding,
                  "result_hash": result_hash, "value": value,
                  "evidence_origin": "cache_reuse", "new_evidence": False}
        raw = canonical_bytes(record)
        self._entries[key] = (bytes_hash(raw), raw)
        return key

    def get(self, binding):
        binding = _binding_copy(binding)
        key = canonical_hash(binding)
        entry = self._entries.get(key)
        if entry is None:
            return None
        entry_hash, raw = entry
        if type(raw) is not bytes or len(raw) > MAX_JSON_BYTES:
            raise ValueError("Cache record exceeds byte budget")
        if bytes_hash(raw) != entry_hash:
            raise ValueError("Corrupt cache bytes")
        try:
            envelope = json.loads(raw)
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise ValueError("Invalid cache JSON") from exc
        if (type(envelope) is not dict or len(envelope) != 2
                or set(envelope) != {"canonical_version", "value"}
                or type(envelope["canonical_version"]) is not int
                or envelope["canonical_version"] != CANONICAL_VERSION):
            raise ValueError("Invalid cache envelope")
        record = envelope["value"]
        validate_json(record)
        if type(record) is dict and "value" in record:
            _admit_cache_value(record["value"])
        expected = {"schema_version", "cache_key", "bindings", "result_hash",
                    "value", "evidence_origin", "new_evidence"}
        if (type(record) is not dict or set(record) != expected or record["schema_version"] != 1
                or record["cache_key"] != key or record["bindings"] != binding
                or canonical_bytes(record) != raw
                or record["result_hash"] != canonical_hash(record["value"])
                or binding["result_hash"] not in (None, record["result_hash"])
                or record["evidence_origin"] != "cache_reuse"
                or record["new_evidence"] is not False):
            raise ValueError("Invalid cache record")
        return record

    def invalidate(self, binding):
        key = canonical_hash(_binding_copy(binding))
        return self._entries.pop(key, None) is not None
