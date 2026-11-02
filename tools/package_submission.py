"""Offline submission evidence packager.

Hashes a bounded, explicit artifact set with SHA-256 and writes a reproducible
MANIFEST.json plus copies. Read-only on the repository; no network, no service
startup, no gameplay execution, no credential access. Live external capture and
public submission remain out of scope.

The package has two tiers:

* ``CORE_ARTIFACTS`` must exist. A missing or tampered core artifact fails
  closed.
* ``EXTENSION_ARTIFACTS`` are the Wave A/B integration files. When absent they
  are recorded as ``artifact_set.pending`` and the package is explicitly
  incomplete. They are never silently omitted or fabricated. The readiness
  verifier treats an incomplete package as a failed predicate.

Usage:
    python3 -m tools.package_submission build [--out build/submission-package]
    python3 -m tools.package_submission check <package-dir>
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = "artifacts/simulations/full-game/full-game-20261101T185524Z-2647e033"
READINESS = RUN + "/DEVELOPMENT-READINESS.json"
WORK_PACKAGES = [
    ("WP-01-core-engine-implementation", "Core engine implementation",
     "implemented-offline-fixture", ["server/engine.py", "coordination/deterministic_kernel.py"]),
    ("WP-02-hud-and-mobile-presentation", "HUD and mobile presentation",
     "implemented-offline-fixture", ["client/app.js", "client/hud.js", "client/index.html",
                                     "client/style.css"]),
    ("WP-03-twitch-extension-linking", "Twitch command intake boundary",
     "implemented-offline-fixture; live EventSub adapter pending", ["server/intake.py"]),
    ("WP-04-codex-booth-telemetry", "Codex booth telemetry",
     "implemented-offline-fixture", ["server/telemetry.py"]),
    ("WP-05-submission-demo-pipeline", "Submission and demo pipeline",
     "implemented-offline-fixture; live capture open", [
         "tools/package_submission.py",
         "tools/verify_submission_readiness.py",
         "schemas/submission-readiness.json",
         "docs/submission/CLOSURE-DEMO-RUNBOOK.md",
         "docs/submission/SUBMISSION-METADATA.json",
     ]),
]
BASE_ARTIFACTS = [
    READINESS,
    RUN + "/RUN-MANIFEST.json",
    RUN + "/REVIEW-INVOCATION.json",
    RUN + "/SOURCE-BINDINGS.json",
    RUN + "/INVARIANT-RESULTS.json",
    RUN + "/results/SCENARIO-RESULTS.jsonl",
    "docs/planning/development-closure-20261102/verification/DEVELOPMENT-CLOSURE-VERIFICATION.md",
    "evidence/remediation-kernel-20261101/09_CORRECTIONS-20261102.md",
    "evidence/remediation-kernel-20261101/10_RUN-ROOT-DISPOSITION-20261102.md",
    "evidence/remediation-kernel-20261101/11_D-T1-DISPOSITION-20261102.md",
    "server/engine.py",
    "server/app.py",
    "server/intake.py",
    "server/telemetry.py",
    "client/hud.js",
    "tests/test_gameplay_core.py",
    "tests/test_runtime_integration.py",
    "tests/test_command_intake.py",
    "tests/test_telemetry.py",
]
WORK_PACKAGE_ARTIFACTS = [
    path for _, _, _, evidence in WORK_PACKAGES for path in evidence
]
CORE_ARTIFACTS = list(dict.fromkeys(BASE_ARTIFACTS + WORK_PACKAGE_ARTIFACTS + [
    "coordination/review_route.py",
    "tests/test_review_route.py",
    "tests/test_submission_package.py",
    "tests/test_submission_readiness.py",
    "schemas/submission-readiness.json",
    "docs/submission/SETUP.md",
    "docs/submission/PROJECT-DESCRIPTION.md",
    "docs/submission/CODEX-SESSION.md",
    "docs/submission/LICENSING-CHECKLIST.md",
    "docs/submission/SUBMISSION-METADATA.json",
    "README.md",
    "docs/DEMO.md",
]))
ARTIFACTS = CORE_ARTIFACTS  # Backward-compatible name for required core bytes.
EXTENSION_ARTIFACTS = [
    "server/twitch_live.py",
    "schemas/twitch-live.json",
    "tests/test_twitch_live.py",
    "tools/capture_submission.py",
    "tests/test_presentation_capture.py",
    "docs/submission/STORYBOARD.md",
    "evidence/submission-capture/README.md",
    # Worker B rendered these offline fixture/disconnected states. They are
    # packaged as fixture evidence only; the manifest keeps live_validated false.
    "evidence/submission-capture/disconnected/accessibility.json",
    "evidence/submission-capture/disconnected/CAPTURE-MANIFEST.json",
    "evidence/submission-capture/disconnected/disconnected-desktop.png",
    "evidence/submission-capture/disconnected/disconnected-mobile.png",
    "evidence/submission-capture/disconnected/timeline.json",
    "evidence/submission-capture/fixture/accessibility.json",
    "evidence/submission-capture/fixture/CAPTURE-MANIFEST.json",
    "evidence/submission-capture/fixture/fixture-desktop.png",
    "evidence/submission-capture/fixture/fixture-mobile.png",
    "evidence/submission-capture/fixture/timeline.json",
]
ARTIFACT_CATALOG = list(dict.fromkeys(CORE_ARTIFACTS + EXTENSION_ARTIFACTS))
SENSITIVE_PREFIXES = (".env", ".runtime/", "build/", "__pycache__/", ".git/")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_relpath(rel: str) -> None:
    path = Path(rel)
    if not rel or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe artifact path: {rel!r}")
    if rel == ".env" or rel.startswith(SENSITIVE_PREFIXES):
        raise ValueError(f"sensitive artifact path is forbidden: {rel}")


def build_manifest(repo: Path = ROOT) -> dict:
    readiness = json.loads((repo / READINESS).read_text())
    missing_core = [rel for rel in CORE_ARTIFACTS if not (repo / rel).is_file()]
    if missing_core:
        raise FileNotFoundError(f"missing core evidence artifact: {', '.join(missing_core)}")
    present_extension = [rel for rel in EXTENSION_ARTIFACTS if (repo / rel).is_file()]
    pending = [rel for rel in EXTENSION_ARTIFACTS if rel not in present_extension]
    artifacts = {}
    for rel in list(CORE_ARTIFACTS) + present_extension:
        _validate_relpath(rel)
        path = repo / rel
        if not path.is_file():
            raise FileNotFoundError(f"missing evidence artifact: {rel}")
        artifacts[rel] = sha256_file(path)
    packages = []
    for ident, title, state, evidence in WORK_PACKAGES:
        missing = [item for item in evidence if item not in artifacts]
        if missing:
            raise ValueError(f"work-package evidence is not hashed: {ident}: {missing}")
        packages.append({
            "id": ident,
            "title": title,
            "evidence_state": state,
            "evidence": list(evidence),
        })
    complete = not pending
    return {
        "schema_version": 2,
        "generator": "tools/package_submission.py",
        "artifact_set": {
            "complete": complete,
            "catalog": list(ARTIFACT_CATALOG),
            "core": list(CORE_ARTIFACTS),
            "pending": pending,
            "pending_reason": None if complete else (
                "Wave A/B integration artifacts are not present in this tree. "
                "The package is deliberately incomplete and cannot support "
                "submission readiness."
            ),
        },
        "readiness": {
            "submission_ready": bool(readiness["submission_ready"]),
            "simulation_and_plan_ready": bool(readiness["simulation_and_plan_ready"]),
            "source": READINESS,
            "readiness_record": "docs/submission/SUBMISSION-METADATA.json",
            "open_before_live_submission": ["live_submission_external_capture"],
            "work_package_order": list(readiness["required_work_packages_order"]),
        },
        "labels": {
            "evidence_scope": "fixture_offline",
            "fixture_backed": True,
            "live_validated": False,
            "note": ("Offline fixture/simulation and disconnected-state evidence only. "
                     "No live Twitch receipt or final submission video is packaged; "
                     "bundled captures are labelled fixture/disconnected."),
        },
        "work_packages": packages,
        "artifacts": artifacts,
    }


def build(out_dir: Path, repo: Path = ROOT) -> dict:
    manifest = build_manifest(repo)
    out_dir.mkdir(parents=True, exist_ok=True)
    files_dir = out_dir / "files"
    if files_dir.exists():
        shutil.rmtree(files_dir)
    for rel in manifest["artifacts"]:
        target = files_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / rel, target)
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    (out_dir / "MANIFEST.json").write_text(payload)
    return manifest


def check(package_dir: Path) -> dict:
    manifest = json.loads((package_dir / "MANIFEST.json").read_text())
    if manifest.get("schema_version") != 2:
        raise ValueError("manifest schema_version must be 2")
    artifact_set = manifest.get("artifact_set")
    if type(artifact_set) is not dict:
        raise ValueError("manifest artifact_set must be an object")
    if artifact_set.get("catalog") != list(ARTIFACT_CATALOG):
        raise ValueError("manifest artifact catalog does not match required catalog")
    if artifact_set.get("core") != list(CORE_ARTIFACTS):
        raise ValueError("manifest core artifact set does not match required evidence set")
    pending = artifact_set.get("pending")
    if type(pending) is not list or any(type(item) is not str for item in pending):
        raise ValueError("manifest pending artifact list must be a string array")
    if len(set(pending)) != len(pending) or not set(pending).issubset(set(EXTENSION_ARTIFACTS)):
        raise ValueError("manifest pending artifact list is invalid")
    complete = not pending
    if artifact_set.get("complete") is not complete:
        raise ValueError("manifest complete flag contradicts the pending artifact list")
    declared_artifacts = manifest.get("artifacts")
    expected_artifacts = set(CORE_ARTIFACTS) | (set(EXTENSION_ARTIFACTS) - set(pending))
    if not isinstance(declared_artifacts, dict) or set(declared_artifacts) != expected_artifacts:
        raise ValueError("manifest artifact set does not match required evidence set and pending list")
    labels = manifest.get("labels")
    if type(labels) is not dict:
        raise ValueError("manifest labels must be an object")
    if labels.get("live_validated") is not False:
        raise ValueError("offline package may not claim live_validated: true")
    readiness = manifest.get("readiness")
    if type(readiness) is not dict:
        raise ValueError("manifest readiness must be an object")
    if readiness.get("submission_ready") is not False:
        raise ValueError("package may not claim submission_ready: this wave is offline evidence only")
    required_packages = [
        {"id": ident, "title": title, "evidence_state": state, "evidence": list(evidence)}
        for ident, title, state, evidence in WORK_PACKAGES
    ]
    if manifest.get("work_packages") != required_packages:
        raise ValueError("manifest work packages do not match required evidence coverage")
    failures = []
    for rel, digest in declared_artifacts.items():
        _validate_relpath(rel)
        if not isinstance(digest, str) or len(digest) != 64 or any(
                c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"invalid SHA-256 digest: {rel}")
        target = package_dir / "files" / rel
        if not target.is_file():
            failures.append(f"missing: {rel}")
        elif sha256_file(target) != digest:
            failures.append(f"hash mismatch: {rel}")
    if failures:
        raise ValueError("; ".join(failures))
    return {
        "verified": len(declared_artifacts),
        "complete": complete,
        "pending": len(pending),
        "status": "ok",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Offline submission evidence packager")
    parser.add_argument("mode", choices=("build", "check"))
    parser.add_argument("target", nargs="?", default="build/submission-package")
    args = parser.parse_args(argv)
    target = ROOT / args.target
    if args.mode == "build":
        manifest = build(target)
        print(json.dumps({
            "status": "built",
            "manifest_sha256": sha256_file(target / "MANIFEST.json"),
            "artifacts": len(manifest["artifacts"]),
            "complete": manifest["artifact_set"]["complete"],
            "pending": len(manifest["artifact_set"]["pending"]),
            "submission_ready": manifest["readiness"]["submission_ready"],
        }, sort_keys=True))
    else:
        print(json.dumps(check(target), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
