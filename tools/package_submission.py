"""W7/TASK-010 offline submission evidence packager.

Hashes a bounded, explicit artifact set with SHA-256 and writes a reproducible
MANIFEST.json plus copies. Read-only on the repository; no network, no service
startup, no gameplay execution, no credential access. Live external capture and
public submission remain out of scope (unresolved `live_submission_external_capture`).

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
     "implemented-offline-fixture", ["client/hud.js", "client/index.html", "client/style.css"]),
    ("WP-03-twitch-extension-linking", "Twitch extension linking and command intake",
     "implemented-offline-fixture (no live integration)", ["server/intake.py"]),
    ("WP-04-codex-booth-telemetry", "Codex booth telemetry",
     "implemented-offline-fixture", ["server/telemetry.py"]),
    ("WP-05-submission-demo-pipeline", "Submission and demo pipeline",
     "implemented-offline-fixture (live capture open)", ["tools/package_submission.py",
                                                         "docs/submission/CLOSURE-DEMO-RUNBOOK.md"]),
]
ARTIFACTS = [
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
    "server/intake.py",
    "server/telemetry.py",
    "client/hud.js",
    "tests/test_gameplay_core.py",
    "tests/test_command_intake.py",
    "tests/test_telemetry.py",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(repo: Path = ROOT) -> dict:
    readiness = json.loads((repo / READINESS).read_text())
    artifacts = {}
    for rel in ARTIFACTS:
        path = repo / rel
        if not path.is_file():
            raise FileNotFoundError(f"missing evidence artifact: {rel}")
        artifacts[rel] = sha256_file(path)
    packages = []
    for ident, title, state, evidence in WORK_PACKAGES:
        packages.append({
            "id": ident,
            "title": title,
            "evidence_state": state,
            "evidence": [item for item in evidence if (repo / item).is_file()],
        })
    return {
        "schema_version": 1,
        "generator": "tools/package_submission.py",
        "readiness": {
            "submission_ready": bool(readiness["submission_ready"]),
            "simulation_and_plan_ready": bool(readiness["simulation_and_plan_ready"]),
            "source": READINESS,
            "open_before_live_submission": ["live_submission_external_capture"],
            "work_package_order": list(readiness["required_work_packages_order"]),
        },
        "labels": {
            "fixture_backed": True,
            "live_validated": False,
            "note": "Offline fixture/simulation evidence only; no live Twitch or external capture evidence.",
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
    failures = []
    for rel, expected in manifest["artifacts"].items():
        target = package_dir / "files" / rel
        if not target.is_file():
            failures.append(f"missing: {rel}")
        elif sha256_file(target) != expected:
            failures.append(f"hash mismatch: {rel}")
    if failures:
        raise ValueError("; ".join(failures))
    return {"verified": len(manifest["artifacts"]), "status": "ok"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Offline submission evidence packager")
    parser.add_argument("mode", choices=("build", "check"))
    parser.add_argument("target", nargs="?", default="build/submission-package")
    args = parser.parse_args(argv)
    target = ROOT / args.target
    if args.mode == "build":
        manifest = build(target)
        print(json.dumps({"status": "built", "manifest_sha256": sha256_file(target / "MANIFEST.json"),
                          "artifacts": len(manifest["artifacts"]),
                          "submission_ready": manifest["readiness"]["submission_ready"]}, sort_keys=True))
    else:
        print(json.dumps(check(target), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
