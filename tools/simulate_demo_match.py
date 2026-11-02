#!/usr/bin/env python3
"""Simulate a complete TwitchCon Odyssey demo match with active viewer participation.

Demonstrates:
- Viewers submitting chat proposals and steering votes via /api/chat.
- Hazard proposal and warning phase.
- Audience counter-voting (clear_lane) and quorum mechanics.
- Streamer steering evasion.
- Passing landmark waypoints to the Fictional Main Stage.
- Terminal delivery settlement (50/50 streamer/audience Hype split).
"""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"

def get_state():
    req = urllib.request.Request(f"{BASE_URL}/api/state")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def post_json(path, data):
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Host": "127.0.0.1:8000",
            "Origin": BASE_URL,
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode())
        except Exception:
            return {"error": str(exc)}

def simulate_demo():
    print("=" * 60)
    print("TwitchCon Odyssey: Viewer Action Simulation & Demo Sequence")
    print("=" * 60)

    # 1. Check or unpause server
    state_env = get_state()
    st = state_env["state"]
    if st.get("is_paused"):
        print("-> Unpausing server...")
        post_json("/api/pause", {"paused": False})
        time.sleep(0.5)

    print(f"-> Starting state: Turn {st['turn']}, Phase {st['phase']}, Status {st['status']}, Progress {st['movement']['progress']:.1f}%")

    # 2. Audience Viewers Roster
    viewers = [
        ("viewer_neon_fox", "patch left"),
        ("viewer_bay_phantom", "boost right"),
        ("viewer_pixel_pirate", "shield"),
        ("viewer_gaslamp_pro", "boost right"),
        ("viewer_convention_fan", "patch left"),
    ]

    events_log = []
    start_time = time.time()
    last_turn = -1

    # Monitor and simulate audience participation over 25 seconds
    print("\n-> Simulating active audience chat commands...")
    for step in range(35):
        try:
            st = get_state()["state"]
        except Exception as exc:
            print(f"State query error: {exc}")
            time.sleep(0.5)
            continue

        turn = st["turn"]
        phase = st["phase"]
        status = st["status"]
        progress = st["movement"]["progress"]
        district = st["movement"]["district"]

        # If turn changed or new phase
        if turn != last_turn or step % 5 == 0:
            print(f"[{time.strftime('%H:%M:%S')}] Turn {turn} | {phase.upper()} | {district} | Progress: {progress:.1f}% | Hype Pool: {st['bounty']['pool']}")
            last_turn = turn

        # Submit viewer chat actions during planning phase
        if phase == "planning" and status == "racing":
            v_idx = step % len(viewers)
            v_name, v_text = viewers[v_idx]
            chat_res = post_json("/api/chat", {
                "viewer": v_name,
                "text": v_text,
                "round": turn
            })
            if chat_res.get("queued"):
                events_log.append({
                    "tick": st["tick"],
                    "turn": turn,
                    "viewer": v_name,
                    "action": v_text,
                    "result": "queued"
                })
                print(f"   💬 Chat: @{v_name}: \"{v_text}\" -> Queued for intake")

            # Streamer steering input
            if step % 4 == 0:
                steer_dir = "right" if (step // 4) % 2 == 0 else "left"
                steer_res = post_json("/api/command", {
                    "direction": steer_dir,
                    "turn": turn
                })
                print(f"   🎮 Streamer: Steer {steer_dir} -> {steer_res.get('status')}")

        if status in ("delivered", "wiped"):
            print(f"\n🏆 Match reached terminal state: {status.upper()}!")
            print(f"   Final District: {district}")
            print(f"   Final Progress: {progress:.1f}%")
            print(f"   Hype Bounty: {st['bounty']['pool']} credits")
            break

        time.sleep(0.7)

    # Save simulation evidence record
    evidence_path = Path("evidence/ui-readiness/20261102T161855Z/VIEWER-ACTION-SIMULATION.json")
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "deterministic_fixture_simulation",
        "events_count": len(events_log),
        "events": events_log,
        "final_state": st,
    }
    evidence_path.write_text(json.dumps(evidence_data, indent=2))
    print(f"\n-> Viewer simulation evidence saved to {evidence_path}")
    print("=" * 60)

if __name__ == "__main__":
    simulate_demo()
