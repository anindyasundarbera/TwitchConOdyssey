"""Seeded reusable viewer-message fixtures; never live viewers or gameplay."""
from .content_cache import bytes_hash, canonical_hash, detached, require_hash, validate_json

_GENERATOR_ID = "viewer-fixture-v1"
_GENERATOR_VERSION = 1
_GENERATOR_SELECTION = "sha256(canonical-v1([seed,sequence])) modulo template count"
_GENERATOR_CLOCK = "start_tick + sequence * tick_stride"
_GENERATOR_ACTOR = "fixture-viewer-{sequence}"
_GENERATOR_SOURCE_PATH = "coordination/scenario_inputs.py"


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


def build_corpus_manifest(corpus, *, generator_source_path=_GENERATOR_SOURCE_PATH,
                          generator_source_sha256=None):
    """Validate corpus and return a content-addressed manifest with 64-hex SHA-256 digests."""
    if type(corpus) is not dict:
        raise ValueError("Corpus must be a dict")
    if "corpus_hash" in corpus:
        require_hash(corpus["corpus_hash"])
    if "generator_hash" in corpus:
        require_hash(corpus["generator_hash"])
    if "template_hash" in corpus:
        require_hash(corpus["template_hash"])
    validated = validate_corpus(corpus)
    if type(generator_source_path) is not str or not generator_source_path.strip():
        raise ValueError("Generator source path must be a non-empty string")
    if generator_source_sha256 is None:
        with open(__file__, "rb") as handle:
            generator_source_sha256 = bytes_hash(handle.read())
    else:
        require_hash(generator_source_sha256)
    seed = validated["seed"]
    count = validated["count"]
    start_tick = validated["start_tick"]
    tick_stride = validated["tick_stride"]
    if (validated["templates"] == list(DEFAULT_TEMPLATES)
            and start_tick == 0 and tick_stride == 1):
        recipe = (
            "from coordination.scenario_inputs import generate_viewer_corpus; "
            f"generate_viewer_corpus(seed={seed}, count={count})"
        )
    else:
        recipe = (
            "from coordination.scenario_inputs import generate_viewer_corpus; "
            f"generate_viewer_corpus(seed={seed}, count={count}, "
            f"templates={validated['templates']!r}, start_tick={start_tick}, "
            f"tick_stride={tick_stride})"
        )
    manifest = {
        "schema_version": 1,
        "provenance": "generated_fixture",
        "generator_id": _GENERATOR_ID,
        "generator_version": _GENERATOR_VERSION,
        "generator_source_path": generator_source_path,
        "generator_source_sha256": require_hash(generator_source_sha256),
        "generator_spec_sha256": require_hash(validated["generator_hash"]),
        "template_sha256": require_hash(validated["template_hash"]),
        "seed": seed,
        "count": count,
        "start_tick": start_tick,
        "tick_stride": tick_stride,
        "sha256": require_hash(validated["corpus_hash"]),
        "regeneration_recipe": recipe,
        "verified_regeneration_match": True,
    }
    return detached(manifest)

