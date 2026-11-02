#!/usr/bin/env python3
"""End-to-end Full HD 1080p Video Production Pipeline for TwitchCon Odyssey Devpost submission.

Produces build/twitchcon-odyssey-demo.mp4 (1920x1080, ~2m 20s, < 180s):
- Full HD 1080p (1920x1080) high-bitrate canvas rendering.
- Big, prominent Twitch Chat overlay with dynamic live vote focus zoom.
- Streamer evasion steering around holographic center roadblocks.
- Sponsor milestone activations: Twitch Stage Booth (35%), OpenAI Codex Arena (60%), AWS Waypoint (80%).
- Final delivery into Fictional Main Stage Stadium (100%) with 50/50 settlement modal.
- Studio broadcast-quality natural human narration via edge-tts (en-US-ChristopherNeural).
- High-energy cyberpunk synthwave musical bed.
- Pristine unblocked view: zero subtitles covering the road or canvas!
"""
import asyncio
import base64
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request
import wave

import edge_tts
import numpy as np
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "build"
RAW_VIDEO_DIR = BUILD_DIR / "raw_video_1080p"
OUTPUT_MP4 = BUILD_DIR / "twitchcon-odyssey-demo.mp4"
BASE_URL = "http://127.0.0.1:8000"
VOICE = "en-US-ChristopherNeural"
TOTAL_TARGET_DURATION = 140.0

# -----------------------------------------------------------------------------
# 1. Authoritative Engine & REST Helper
# -----------------------------------------------------------------------------
def get_state():
    req = urllib.request.Request(f"{BASE_URL}/api/state")
    with urllib.request.urlopen(req, timeout=3) as resp:
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
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode())
        except Exception:
            return {"error": str(exc)}

# -----------------------------------------------------------------------------
# 2. Narration Scripts (~140 seconds total)
# -----------------------------------------------------------------------------
SCRIPTS = [
    # Act 1: The Concept & Mission Briefing (0s - 22s)
    (1.0, "Welcome to TwitchCon Odyssey, an authoritative real-time Twitch co-op crisis runner built for streamers and their live communities."),
    (10.5, "The broadcaster pilots a high-speed cyberpunk courier delivering the master game build across stylized San Diego to the TwitchCon Main Stage."),

    # Act 2: Twitch Chat Live Co-Op & Squads (22s - 52s)
    (21.5, "Notice the prominent Twitch stream chat overlay in the upper right. Viewers in four rival squads join directly from chat, actively shaping the race."),
    (32.0, "Chat commands like clear-lane, patch, boost, and shield are evaluated authoritatively with strict audience fairness."),
    (42.0, "When the center roadblock activates, community votes collapse the barrier into an emerald gate while the streamer banks hard right to evade."),

    # Act 3: Diegetic Sponsor Milestones (53s - 80s)
    (53.0, "Along the route, the runner navigates diegetic sponsor milestones celebrating TwitchCon and its premier partners."),
    (62.5, "At thirty-five percent, we pass the Twitch Stage Booth with signature purple trusses and LED equalizers, converting audience chaos into Hype."),
    (72.5, "Next, the OpenAI Codex Arena emits matrix code streams, followed by the high-density AWS Cloud Waypoint at eighty percent."),

    # Act 4: How OpenAI Codex Built The Project (81s - 110s)
    (82.0, "This entire project was pair-programmed with OpenAI Codex, session ID zero one a one nine five five f."),
    (91.5, "Codex formulated our pseudo-3D perspective projection math and enforced strict determinism invariants in the Python authoritative kernel."),
    (101.0, "Codex also orchestrated multi-agent review swarms to verify responsive viewports and audit our 140 regression tests."),

    # Act 5: Climax Delivery & 50/50 Settlement (111s - 128s)
    (111.0, "With seconds left on the match clock, the courier reaches the Fictional Main Stage stadium under golden fireworks!"),
    (120.0, "The build is successfully delivered, settling the accumulated Hype pool fifty-fifty between broadcaster and participating viewers."),

    # Act 6: Open Source GitHub & Outro (129s - 140s)
    (129.0, "All source code, deterministic kernel tests, and replay tools are public on GitHub at anindyasundarbera slash TwitchConOdyssey."),
    (136.0, "Thank you for watching TwitchCon Odyssey, and see you on the main stage!"),
]

async def generate_voice_clips(parts_dir: Path):
    parts_dir.mkdir(parents=True, exist_ok=True)
    for idx, (start_t, text) in enumerate(SCRIPTS):
        out_mp3 = parts_dir / f"clip_{idx:02d}.mp3"
        comm = edge_tts.Communicate(text, VOICE, rate="+4%")
        await comm.save(str(out_mp3))
        print(f"Generated natural voice clip {idx:02d} ({start_t:.1f}s): {text[:45]}...")

def build_master_soundtrack(parts_dir: Path, output_wav: Path, total_dur: float):
    SR = 44100
    total_samples = int(total_dur * SR)
    voice_buffer = np.zeros(total_samples, dtype=np.float32)

    for idx, (start_t, _) in enumerate(SCRIPTS):
        clip_path = parts_dir / f"clip_{idx:02d}.mp3"
        # decode to raw pcm via ffmpeg
        cmd = ["ffmpeg", "-y", "-i", str(clip_path), "-f", "s16le", "-ar", str(SR), "-ac", "1", "-"]
        res = subprocess.run(cmd, capture_output=True, check=True)
        samples = np.frombuffer(res.stdout, dtype=np.int16).astype(np.float32) / 32768.0

        start_idx = int(start_t * SR)
        end_idx = min(start_idx + len(samples), total_samples)
        fit = end_idx - start_idx
        if fit > 0:
            voice_buffer[start_idx:end_idx] += samples[:fit]

    # Cyberpunk Synthwave Music Bed
    t = np.linspace(0, total_dur, total_samples, endpoint=False)
    bass = np.sin(2 * np.pi * 65.41 * t) * 0.08  # C2 bass
    arp = np.sin(2 * np.pi * 130.81 * t) * 0.04 * (0.5 + 0.5 * np.sin(2 * np.pi * 2.5 * t))
    hi_lead = np.sin(2 * np.pi * 261.63 * t) * 0.02 * (0.5 + 0.5 * np.sin(2 * np.pi * 1.25 * t))
    music = bass + arp + hi_lead

    # Mix Voice + Music Bed
    mixed = voice_buffer * 0.88 + music * 0.22
    max_val = np.max(np.abs(mixed))
    if max_val > 0.01:
        mixed = mixed / max_val * 0.94

    pcm = (mixed * 32767.0).astype(np.int16)
    with wave.open(str(output_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())

    print(f"Synthesized Full HD Master Audio: {output_wav} ({total_dur:.1f}s)")

# -----------------------------------------------------------------------------
# 3. Playwright 1080p Capture & Simulation Loop
# -----------------------------------------------------------------------------
def record_1080p_gameplay():
    RAW_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    for old in RAW_VIDEO_DIR.glob("*.webm"):
        old.unlink(missing_ok=True)

    # Reset match state
    print("Resetting server match to progress 0.0%...")
    post_json("/api/restart", {})
    post_json("/api/pause", {"paused": False})
    time.sleep(0.5)

    print("Launching Chromium 1080p Full HD video recording session...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--high-dpi-support=1",
                "--force-device-scale-factor=1",
                "--enable-font-antialiasing",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(RAW_VIDEO_DIR),
            record_video_size={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        print("Navigating to http://127.0.0.1:8000 at 1920x1080 Full HD...")
        page.goto("http://127.0.0.1:8000")
        page.wait_for_selector("#modal-start")

        # Let start attract screen show for 5.5 seconds
        time.sleep(5.5)
        page.click("#btn-start-windowed")
        print("Engaged Full HD racing mode!")

        viewers = [
            ("viewer_neon_fox", "patch left"),
            ("viewer_bay_phantom", "boost right"),
            ("viewer_pixel_pirate", "shield"),
            ("viewer_gaslamp_pro", "boost right"),
            ("viewer_convention_fan", "patch left"),
            ("viewer_codex_coder", "patch center"),
        ]

        start_t = time.time()
        step = 0
        delivered_t = None
        has_paused_booth = False

        while time.time() - start_t < (TOTAL_TARGET_DURATION + 5):
            step += 1
            now_elapsed = time.time() - start_t

            try:
                st = get_state()["state"]
            except Exception:
                time.sleep(0.5)
                continue

            turn = st["turn"]
            phase = st["phase"]
            status = st["status"]
            progress = st["movement"]["progress"]

            # Trigger live chat zoom during Turn 1 audience showcase
            if 20.0 <= now_elapsed <= 46.0:
                try:
                    page.evaluate("window.__zoomChat = true")
                except Exception:
                    pass
            else:
                try:
                    page.evaluate("window.__zoomChat = false")
                except Exception:
                    pass

            # Submit chat actions during planning
            if phase == "planning" and status == "racing":
                v_name, v_text = viewers[step % len(viewers)]
                post_json("/api/chat", {
                    "viewer": v_name,
                    "text": v_text,
                    "round": turn
                })

                # Streamer steering evasion
                if step % 5 == 0:
                    steer_dir = "right" if (step // 5) % 2 == 0 else "left"
                    try:
                        page.click(f'[data-control="{steer_dir}"]')
                    except Exception:
                        pass

            # Pause briefly near OpenAI Codex Arena (around 60%) to let judges appreciate the architecture
            if not has_paused_booth and 58.0 <= progress <= 65.0 and now_elapsed >= 75.0:
                print(f"Pausing at {progress:.1f}% to highlight OpenAI Codex Arena billboard & architecture...")
                has_paused_booth = True
                post_json("/api/pause", {"paused": True})
                time.sleep(14.0)  # 14s showcase of Codex Arena
                post_json("/api/pause", {"paused": False})
                print("Resumed racing towards Main Stage!")

            if status in ("delivered", "wiped"):
                if delivered_t is None:
                    delivered_t = time.time()
                    print(f"Match concluded: {status.upper()} at progress {progress:.1f}%! Showing celebration...")
                # Stay on settlement screen until reaching target duration
                if now_elapsed >= TOTAL_TARGET_DURATION:
                    print("Match recording complete.")
                    break

            time.sleep(0.5)

        page.close()
        context.close()
        browser.close()

    webm_files = list(RAW_VIDEO_DIR.glob("*.webm"))
    if not webm_files:
        raise RuntimeError("No recorded webm video produced by Playwright!")
    print(f"Recorded Full HD raw video: {webm_files[0]}")
    return webm_files[0]

# -----------------------------------------------------------------------------
# 4. High-Bitrate 1080p FFmpeg Encoding
# -----------------------------------------------------------------------------
def encode_1080p_mp4(raw_webm: Path, audio_wav: Path, output_mp4: Path):
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = "/snap/bin/ffmpeg" if Path("/snap/bin/ffmpeg").exists() else "ffmpeg"

    # High-bitrate broadcast encode at 1920x1080 with CRF 16 (clean, sharp, no blur)
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(raw_webm),
        "-i", str(audio_wav),
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "16",
        "-b:v", "12M",
        "-maxrate", "16M",
        "-bufsize", "24M",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "256k",
        "-shortest",
        str(output_mp4)
    ]
    print("Encoding final Full HD (1920x1080) MP4 via FFmpeg (broadcast quality, no subtitles)...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg encode failed: {res.stderr[-300:]}")

    if not output_mp4.is_file():
        raise RuntimeError("Final MP4 was not created!")

    size_mb = output_mp4.stat().st_size / (1024 * 1024)
    print(f"SUCCESS: Final Full HD submission video produced at {output_mp4} ({size_mb:.2f} MB)")

def main():
    print("=" * 70)
    print("TwitchCon Odyssey: 1080p Full HD Video Production Pipeline")
    print("=" * 70)

    clips_dir = BUILD_DIR / "voice_clips_140s"
    audio_wav = BUILD_DIR / "master_audio_140s.wav"

    # 1. Synthesize Natural Voice Clips & Master Audio
    print("\n-> Phase 1: Synthesizing natural human narration clips with edge-tts...")
    asyncio.run(generate_voice_clips(clips_dir))
    build_master_soundtrack(clips_dir, audio_wav, total_dur=TOTAL_TARGET_DURATION)

    # 2. Record 1080p Full HD Gameplay
    print("\n-> Phase 2: Recording 1920x1080 Full HD gameplay with dynamic Twitch chat zoom...")
    raw_webm = record_1080p_gameplay()

    # 3. High-Bitrate Encoding
    print("\n-> Phase 3: Encoding 1080p broadcast MP4 with pristine visual clarity...")
    encode_1080p_mp4(raw_webm, audio_wav, OUTPUT_MP4)

    print("\n" + "=" * 70)
    print(f"FULL HD DEMO VIDEO READY: {OUTPUT_MP4}")
    print("=" * 70)

if __name__ == "__main__":
    main()
