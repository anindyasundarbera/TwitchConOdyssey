"""Seeded reusable viewer-message fixtures; never live viewers or gameplay."""
from .content_cache import canonical_hash, detached, validate_json

_GENERATOR_ID = "viewer-fixture-v1"
_GENERATOR_VERSION = 1
_GENERATOR_SELECTION = "sha256(canonical-v1([seed,sequence])) modulo template count"
_GENERATOR_CLOCK = "start_tick + sequence * tick_stride"
_GENERATOR_ACTOR = "fixture-viewer-{sequence}"


def _generator_spec():
    return {"id": _GENERATOR_ID, "version": _GENERATOR_VERSION,
            "selection": _GENERATOR_SELECTION, "clock": _GENERATOR_CLOCK,
            "actor": _GENERATOR_ACTOR}


# Compatibility snapshots only; generation never reads this mutable public dict.
GENERATOR_SPEC = _generator_spec()
GENERATOR_HASH = canonical_hash(_generator_spec())
DEFAULT_TEMPLATES = ("Fixture viewer message: observation.",
                     "Fixture viewer message: question.",
                     "Fixture viewer message: suggestion.")


def generate_viewer_corpus(seed, count, templates=DEFAULT_TEMPLATES, *,
                           start_tick=0, tick_stride=1):
    """Generate data only using a specified hash counter, never global RNG/time.

    Template and generator hashes bind the fixture recipe. The corpus hash binds
    its metadata and messages, excluding only the corpus_hash field itself.
    """
    if type(seed) is not int:
        raise ValueError("Seed must be an integer")
    if type(count) is not int or not 0 <= count <= 100000:
        raise ValueError("Fixture count must be between zero and 100000")
    if (type(start_tick) is not int or start_tick < 0
            or type(tick_stride) is not int or tick_stride <= 0):
        raise ValueError("Start tick must be nonnegative and stride positive")
    if (type(templates) not in (list, tuple) or not 1 <= len(templates) <= 128
            or any(type(item) is not str or len(item) > 1000 or not item.strip()
                   for item in templates)):
        raise ValueError("Require one to 128 nonempty templates of at most 1000 characters")
    templates = list(templates)
    validate_json([seed, start_tick, tick_stride, templates])
    validate_json(start_tick + max(0, count - 1) * tick_stride)
    generator_spec = _generator_spec()
    messages = []
    for sequence in range(count):
        index = int(canonical_hash([seed, sequence]), 16) % len(templates)
        messages.append({"actor_id": f"fixture-viewer-{sequence}",
                         "provenance": "fixture", "sequence": sequence,
                         "logical_tick": start_tick + sequence * tick_stride,
                         "text": templates[index]})
    corpus = {"schema_version": 1, "kind": "viewer_message_corpus",
              "provenance": "fixture", "evidence_origin": "generated_fixture",
              "generator_id": generator_spec["id"],
              "generator_hash": canonical_hash(generator_spec),
              "templates": templates, "template_hash": canonical_hash(templates),
              "seed": seed, "count": count, "start_tick": start_tick,
              "tick_stride": tick_stride, "messages": messages}
    return detached({**corpus, "corpus_hash": canonical_hash(corpus)})


def validate_corpus(corpus):
    """Regenerate the bound recipe and reject metadata/content tampering."""
    validate_json(corpus)
    if type(corpus) is not dict or not {"seed", "count", "templates",
                                          "start_tick", "tick_stride"} <= set(corpus):
        raise ValueError("Malformed viewer fixture corpus")
    expected = generate_viewer_corpus(corpus["seed"], corpus["count"], corpus["templates"],
                                      start_tick=corpus["start_tick"],
                                      tick_stride=corpus["tick_stride"])
    if canonical_hash(corpus) != canonical_hash(expected):
        raise ValueError("Viewer corpus does not match its bound fixture recipe")
    return expected
