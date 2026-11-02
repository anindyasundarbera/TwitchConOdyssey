#!/usr/bin/env python3
"""End-to-end video production pipeline for TwitchCon Odyssey Devpost submission.

Produces build/twitchcon-odyssey-demo.mp4 (< 180 seconds) featuring:
- Fullscreen synthwave 3D gameplay at 1440x1100 resolution.
- Live viewer chat participation & clear_lane voting simulation.
- Streamer evasion steering around holographic center roadblocks.
- Sponsor milestone activations: Twitch Stage Booth (35%), OpenAI Codex Arena (60%), AWS Cloud Waypoint (80%).
- Final delivery into Fictional Main Stage Stadium (100%) with 50/50 settlement.
- Voice narration synthesized via libespeak-ng explicitly explaining Twitch integration and Codex session ID.
- Synthwave musical bed and burned-in accessible subtitles.
"""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request
import wave

import numpy as np
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "build"
RAW_VIDEO_DIR = BUILD_DIR / "raw_video"
OUTPUT_MP4 = BUILD_DIR / "twitchcon-odyssey-demo.mp4"
BASE_URL = "http://127.0.0.1:8000"

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
# 2. Voice Narration Synthesizer (libespeak-ng ctypes)
# -----------------------------------------------------------------------------
NARRATION_SCRIPTS = [
    {
        "id": "act1_1",
        "start": 1.0,
        "duration": 7.0,
        "text": "Welcome to TwitchCon Odyssey, an authoritative real-time co-op crisis runner built for streamers and their communities.",
    },
    {
        "id": "act1_2",
        "start": 8.5,
        "duration": 6.5,
        "text": "As the courier transports the game build across San Diego, Twitch chat actively shapes the race.",
    },
    {
        "id": "act2_1",
        "start": 16.0,
        "duration": 7.5,
        "text": "Viewers in rival squads propose hazards and coordinate clear-lane votes through live Twitch chat.",
    },
    {
        "id": "act2_2",
        "start": 24.5,
        "duration": 9.0,
        "text": "Watch the top-right Twitch chat overlay: community votes collapse roadblocks into emerald gates as the streamer banks right.",
    },
    {
        "id": "act3_1",
        "start": 35.0,
        "duration": 7.5,
        "text": "At thirty-five percent progress, the runner passes the Twitch Stage Booth with signature purple trusses and LED equalizers.",
    },
    {
        "id": "act3_2",
        "start": 43.5,
        "duration": 8.0,
        "text": "Next, the OpenAI Codex Arena emits matrix data streams, followed by the high-density AWS Cloud Waypoint.",
    },
    {
        "id": "act4_1",
        "start": 53.0,
        "duration": 9.5,
        "text": "This entire project was pair-programmed with OpenAI Codex, session ID zero one a one nine five five f.",
    },
    {
        "id": "act4_2",
        "start": 63.5,
        "duration": 9.0,
        "text": "Codex formulated our 3D pseudo-perspective engine, enforced invariant safety gates, and conducted multi-agent audits.",
    },
    {
        "id": "act5_1",
        "start": 74.0,
        "duration": 8.0,
        "text": "The courier enters the Fictional Main Stage stadium under golden fireworks, delivering the build before deadline!",
    },
    {
        "id": "act5_2",
        "start": 83.0,
        "duration": 7.5,
        "text": "The match concludes with a fifty-fifty Hype settlement split between the broadcaster and participating audience.",
    },
    {
        "id": "act6_1",
        "start": 91.5,
        "duration": 8.0,
        "text": "All source code and deterministic simulation tools are public on GitHub at anindyasundarbera slash TwitchConOdyssey.",
    },
    {
        "id": "act6_2",
        "start": 100.0,
        "duration": 4.0,
        "text": "Thank you for watching TwitchCon Odyssey!",
    },
]

def synthesize_narration_audio(output_wav: Path, total_duration_s: float):
    espeak = ctypes.cdll.LoadLibrary("libespeak-ng.so.1")
    AUDIO_OUTPUT_RETRIEVAL = 1
    sr = espeak.espeak_Initialize(AUDIO_OUTPUT_RETRIEVAL, 0, None, 0)
    espeak.espeak_SetVoiceByName(b"en-us")

    audio_chunks = []
    CALLBACK_TYPE = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)

    def callback(wav, numsamples, events):
        if numsamples > 0:
            chunk = np.ctypeslib.as_array(wav, shape=(numsamples,)).copy()
            audio_chunks.append(chunk)
        return 0

    cb = CALLBACK_TYPE(callback)
    espeak.espeak_SetSynthCallback(cb)

    # Master audio buffer (zeros)
    total_samples = int(total_duration_s * sr)
    master_audio = np.zeros(total_samples, dtype=np.float32)

    for item in NARRATION_SCRIPTS:
        audio_chunks.clear()
        text = item["text"]
        espeak.espeak_Synth(text.encode("utf-8"), len(text) + 1, 0, 0, 0, 0x1000, None, None)
        espeak.espeak_Synchronize()

        if audio_chunks:
            seg_samples = np.concatenate(audio_chunks).astype(np.float32) / 32768.0
            start_sample = int(item["start"] * sr)
            end_sample = min(start_sample + len(seg_samples), total_samples)
            fit_len = end_sample - start_sample
            if fit_len > 0:
                master_audio[start_sample:end_sample] += seg_samples[:fit_len]

    # Generate Synthwave Bassline Bed
    t = np.linspace(0, total_duration_s, total_samples, endpoint=False)
    bass_freq = 65.41 # C2
    synth_bed = np.sin(2 * np.pi * bass_freq * t) * 0.08
    # Add arp pulse
    synth_arp = np.sin(2 * np.pi * (bass_freq * 2) * t) * 0.04 * (0.5 + 0.5 * np.sin(2 * np.pi * 2 * t))
    combined_audio = master_audio * 0.85 + (synth_bed + synth_arp) * 0.22

    # Normalize to 16-bit PCM
    max_val = np.max(np.abs(combined_audio))
    if max_val > 0.01:
        combined_audio = combined_audio / max_val * 0.92

    pcm_data = (combined_audio * 32767.0).astype(np.int16)
    with wave.open(str(output_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm_data.tobytes())

    print(f"Synthesized master narration audio: {output_wav} ({total_duration_s:.1f}s)")

# -----------------------------------------------------------------------------
# 3. Subtitle (.srt) Generator
# -----------------------------------------------------------------------------
def format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def generate_subtitles_srt(output_srt: Path):
    lines = []
    for idx, item in enumerate(NARRATION_SCRIPTS, start=1):
        start_t = item["start"]
        end_t = start_t + item.get("duration", 6.0)
        lines.append(f"{idx}")
        lines.append(f"{format_srt_time(start_t)} --> {format_srt_time(end_t)}")
        lines.append(item["text"])
        lines.append("")
    output_srt.write_text("\n".join(lines))
    print(f"Generated subtitles SRT: {output_srt}")

# -----------------------------------------------------------------------------
# 4. Playwright Video Capture & Simulation Loop
# -----------------------------------------------------------------------------
def record_gameplay_match():
    RAW_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    # Clear out any stale webm files
    for old_file in RAW_VIDEO_DIR.glob("*.webm"):
        old_file.unlink(missing_ok=True)

    # 1. Reset match to t=0, progress=0.0%
    print("Resetting server match to progress 0.0%...")
    post_json("/api/restart", {})
    post_json("/api/pause", {"paused": False})
    time.sleep(0.5)

    print("Launching Playwright video capture session...")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 1100},
            record_video_dir=str(RAW_VIDEO_DIR),
            record_video_size={"width": 1440, "height": 1100}
        )
        page = context.new_page()

        print("Navigating to http://127.0.0.1:8000...")
        page.goto("http://127.0.0.1:8000")
        page.wait_for_selector("#modal-start")

        # Let start attract screen show for 3.5 seconds
        time.sleep(3.5)
        page.click("#btn-start-windowed")
        print("Engaged racing mode!")

        # Audience roster for simulation
        viewers = [
            ("viewer_neon_fox", "patch left"),
            ("viewer_bay_phantom", "boost right"),
            ("viewer_pixel_pirate", "shield"),
            ("viewer_gaslamp_pro", "boost right"),
            ("viewer_convention_fan", "patch left"),
            ("viewer_codex_coder", "patch center"),
        ]

        # Drive simulation until match conclusion + settlement showcase
        start_t = time.time()
        step = 0
        delivered_t = None
        while time.time() - start_t < 115:
            step += 1
            try:
                st = get_state()["state"]
            except Exception:
                time.sleep(0.5)
                continue

            turn = st["turn"]
            phase = st["phase"]
            status = st["status"]
            progress = st["movement"]["progress"]

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

            if status in ("delivered", "wiped"):
                if delivered_t is None:
                    delivered_t = time.time()
                    print(f"Match concluded: {status.upper()} at progress {progress:.1f}%! Showing settlement...")
                # Stay on settlement screen for 12 seconds to let final narration finish
                if time.time() - delivered_t >= 12.0:
                    print("Settlement showcase complete.")
                    break

            time.sleep(0.5)

        page.close()
        context.close()
        browser.close()

    # Find recorded webm file
    webm_files = list(RAW_VIDEO_DIR.glob("*.webm"))
    if not webm_files:
        raise RuntimeError("No recorded webm video produced by Playwright!")
    print(f"Recorded raw gameplay video: {webm_files[0]}")
    return webm_files[0]

# -----------------------------------------------------------------------------
# 5. FFmpeg Encoding & Assembly
# -----------------------------------------------------------------------------
def assemble_final_video(raw_webm: Path, audio_wav: Path, srt_file: Path, output_mp4: Path):
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = "/snap/bin/ffmpeg" if Path("/snap/bin/ffmpeg").exists() else "ffmpeg"

    # Merge video, audio, burned-in subtitles with compact, elegant typography
    escaped_srt = str(srt_file).replace(":", "\\:").replace("'", "\\'")
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(raw_webm),
        "-i", str(audio_wav),
        "-filter_complex", f"[0:v]subtitles='{escaped_srt}':force_style='FontSize=12,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,BackColour=&H90000000,MarginV=18,Alignment=2'[v]",
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_mp4)
    ]
    print(f"Encoding final MP4 video via FFmpeg...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Subtitles filter warning: {res.stderr[-200:]}, falling back to direct video+audio mux...")
        fallback_cmd = [
            ffmpeg_bin,
            "-y",
            "-i", str(raw_webm),
            "-i", str(audio_wav),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_mp4)
        ]
        res_fb = subprocess.run(fallback_cmd, capture_output=True, text=True)
        if res_fb.returncode != 0:
            raise RuntimeError(f"FFmpeg assembly failed: {res_fb.stderr[-300:]}")

    if not output_mp4.is_file():
        raise RuntimeError("Final MP4 was not created!")

    size_mb = output_mp4.stat().st_size / (1024 * 1024)
    print(f"SUCCESS: Final submission video produced at {output_mp4} ({size_mb:.2f} MB)")

def main():
    print("=" * 65)
    print("TwitchCon Odyssey: Automated Submission Video Production Pipeline")
    print("=" * 65)

    audio_wav = BUILD_DIR / "narration_master.wav"
    subtitles_srt = BUILD_DIR / "subtitles.srt"

    # 1. Synthesize Audio & Subtitles
    print("\n-> Phase 1: Synthesizing voice narration and subtitles...")
    synthesize_narration_audio(audio_wav, total_duration_s=106.0)
    generate_subtitles_srt(subtitles_srt)

    # 2. Record Gameplay & Simulation
    print("\n-> Phase 2: Recording gameplay and simulated audience match...")
    raw_webm = record_gameplay_match()

    # 3. Assemble and Encode MP4
    print("\n-> Phase 3: Merging video, audio, and subtitles with FFmpeg...")
    assemble_final_video(raw_webm, audio_wav, subtitles_srt, OUTPUT_MP4)

    print("\n" + "=" * 65)
    print(f"DEMO VIDEO READY FOR SUBMISSION: {OUTPUT_MP4}")
    print("=" * 65)

if __name__ == "__main__":
    main()
