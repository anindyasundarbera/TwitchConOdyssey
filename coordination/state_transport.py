"""Recursive JSON state transport, independent of state meaning or authority.

Mappings recurse; arrays and scalar values replace atomically. Explicit delete
operations distinguish deletion from setting null. Paths contain mapping keys,
so slash/tilde characters need no special encoding. All values are detached.
"""
import json

from .content_cache import canonical_bytes, canonical_hash, detached, require_hash, validate_json

MAX_DELTA_OPERATIONS = 4096
MAX_DELTA_PATH_LENGTH = 64
MAX_DELTA_NODES = 100_000
MAX_DELTA_CONTAINERS = 20_000
MAX_DELTA_STRING_BYTES = 4 * 1024 * 1024
MAX_DELTA_BYTES = 8 * 1024 * 1024


def state_diff(before, after):
    validate_json(before)
    validate_json(after)
    before, after = detached(before), detached(after)
    operations = []

    def append(operation):
        if len(operations) >= MAX_DELTA_OPERATIONS:
            raise ValueError("State delta exceeds operation budget")
        operations.append(operation)

    def walk(old, new, path):
        if canonical_bytes(old) == canonical_bytes(new):
            return
        if type(old) is dict and type(new) is dict:
            for key in sorted(set(old) | set(new)):
                child = path + [key]
                if key not in new:
                    append({"op": "delete", "path": child})
                elif key not in old:
                    append({"op": "set", "path": child, "value": new[key]})
                else:
                    walk(old[key], new[key], child)
        else:
            append({"op": "set", "path": path, "value": new})

    walk(before, after, [])
    return _validate_delta({"schema_version": 1, "base_hash": canonical_hash(before),
                            "result_hash": canonical_hash(after), "operations": operations})


def _validate_delta(delta):
    validate_json(delta, max_nodes=MAX_DELTA_NODES,
                  max_containers=MAX_DELTA_CONTAINERS,
                  max_string_bytes=MAX_DELTA_STRING_BYTES, max_bytes=MAX_DELTA_BYTES)
    if (type(delta) is not dict or set(delta) != {
            "schema_version", "base_hash", "result_hash", "operations"}
            or type(delta["schema_version"]) is not int or delta["schema_version"] != 1
            or type(delta["operations"]) is not list
            or len(delta["operations"]) > MAX_DELTA_OPERATIONS):
        raise ValueError("Malformed state delta")
    require_hash(delta["base_hash"])
    require_hash(delta["result_hash"])
    paths = []
    for operation in delta["operations"]:
        if type(operation) is not dict or type(operation.get("op")) is not str:
            raise ValueError("Malformed state operation")
        op = operation["op"]
        expected = {"op", "path", "value"} if op == "set" else {"op", "path"}
        path = operation.get("path")
        if (op not in {"set", "delete"} or set(operation) != expected
                or type(path) is not list or len(path) > MAX_DELTA_PATH_LENGTH
                or any(type(key) is not str for key in path)
                or (op == "delete" and not path)):
            raise ValueError("Malformed state operation or path")
        paths.append(tuple(path))
    paths.sort()
    if any(right[:len(left)] == left for left, right in zip(paths, paths[1:])):
        raise ValueError("Duplicate or overlapping state paths")
    return detached(delta)


def apply_diff(before, delta):
    validate_json(before)
    delta = _validate_delta(delta)
    result = detached(before)
    if canonical_hash(result) != delta["base_hash"]:
        raise ValueError("State delta base mismatch")
    for operation in delta["operations"]:
        path = operation["path"]
        if not path:
            result = operation["value"]
            continue
        parent = result
        for key in path[:-1]:
            if type(parent) is not dict or key not in parent:
                raise ValueError("State path parent does not exist")
            parent = parent[key]
        if type(parent) is not dict:
            raise ValueError("State path parent must be an object")
        if operation["op"] == "delete":
            if path[-1] not in parent:
                raise ValueError("Deleted state path does not exist")
            del parent[path[-1]]
        else:
            parent[path[-1]] = operation["value"]
    if canonical_hash(result) != delta["result_hash"]:
        raise ValueError("State delta result mismatch")
    return result


def summarize_diff(delta, *, max_operations=20, max_chars=2000):
    """Return bounded deterministic JSON text listing paths, never full values."""
    delta = _validate_delta(delta)
    if (type(max_operations) is not int or max_operations < 0
            or type(max_chars) is not int or max_chars < 256):
        raise ValueError("Summary requires nonnegative operation count and at least 256 characters")
    operations = delta["operations"]
    selected = [{"op": item["op"], "path": item["path"]}
                for item in operations[:max_operations]]
    summary = {"schema_version": 1, "base_hash": delta["base_hash"],
               "result_hash": delta["result_hash"], "operation_count": len(operations),
               "changes": selected, "omitted_count": len(operations) - len(selected)}
    while True:
        text = json.dumps(summary, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if len(text) <= max_chars:
            return text
        if not selected:
            raise ValueError("Summary metadata exceeds character budget")
        selected.pop()
        summary["omitted_count"] += 1
