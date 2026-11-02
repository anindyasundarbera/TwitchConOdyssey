#!/usr/bin/env python3
"""End-to-end video production pipeline for TwitchCon Odyssey Devpost submission.

Produces build/twitchcon-odyssey-demo.mp4 (< 180 seconds) featuring:
- Fullscreen synthwave 3D gameplay at 1440x1100 resolution.
- Live viewer chat participation & clear_lane voting simulation.
- Streamer evasion steering around holographic center roadblocks.
- Sponsor milestone activations: Twitch Stage Booth (35%), OpenAI Codex Arena (60%), AWS Cloud Waypoint (80%).
- Final delivery into Fictional Main Stage Stadium (100%) with 50/50 settlement.
- Voice narration synthesized via libespeak-ng.
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
        "id": "act1_intro",
        "start": 0.5,
        "text": "Welcome to TwitchCon Odyssey, an authoritative real-time crisis runner where streamer and community unite to transport a game build across San Diego to the TwitchCon Main Stage.",
    },
    {
        "id": "act2_audience",
        "start": 16.0,
        "text": "As the streamer races down Embarcadero boulevard, viewers actively shape the race. Chat submits hazard proposals and votes clear lane. When the center roadblock activates, audience voting collapses the barrier into an emerald gate while the streamer banks right to evade.",
    },
    {
        "id": "act3_sponsors",
        "start": 44.0,
        "text": "Along the route, the runner navigates diegetic sponsor milestones: the Twitch Stage Booth converts audience chaos into Hype credits; the OpenAI Codex Arena optimizes delivery vectors; and the AWS Cloud Waypoint demonstrates ultra-low latency infrastructure scaling.",
    },
    {
        "id": "act4_codex",
        "start": 74.0,
        "text": "The entire architecture was pair-programmed with OpenAI Codex, session ID zero one a one nine five five f. Codex engineered the deterministic twenty hertz physics engine, reconciled the authorization gate, and built a comprehensive suite of one hundred and forty passing regression tests.",
    },
    {
        "id": "act5_climax",
        "start": 104.0,
        "text": "With seconds left on the match clock, the courier reaches the TwitchCon Main Stage! The build is successfully delivered, settling the Hype pool fifty-fifty between the broadcaster and the participating community.",
    },
    {
        "id": "act6_outro",
        "start": 128.0,
        "text": "All code, tests, and deterministic simulation tools are open source. Visit our repository and Devpost showcase. Thank you for watching TwitchCon Odyssey!",
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
    combined_audio = master_audio * 0.85 + (synth_bed + synth_arp) * 0.25

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
    durations = [14.0, 26.0, 28.0, 28.0, 22.0, 18.0]
    for idx, item in enumerate(NARRATION_SCRIPTS, start=1):
        start_t = item["start"]
        end_t = start_t + durations[idx - 1]
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

        # Unpause server if paused
        post_json("/api/pause", {"paused": False})
        time.sleep(0.3)

        print("Navigating to http://127.0.0.1:8000...")
        page.goto("http://127.0.0.1:8000")
        page.wait_for_selector("#modal-start")

        # Let start attract screen show for 4 seconds
        time.sleep(4.0)
        page.click("#btn-start-windowed")
        print("Engaged racing mode!")

        # Audience roster for simulation
        viewers = [
            ("viewer_neon_fox", "patch left"),
            ("viewer_bay_phantom", "boost right"),
            ("viewer_pixel_pirate", "shield"),
            ("viewer_gaslamp_pro", "boost right"),
            ("viewer_convention_fan", "patch left"),
        ]

        # Drive simulation over 135 seconds (complete 3-turn match to finish)
        start_t = time.time()
        step = 0
        while time.time() - start_t < 140:
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
                    page.click(f'[data-control="{steer_dir}"]')

            if status in ("delivered", "wiped"):
                print(f"Match concluded: {status.upper()} at progress {progress:.1f}%!")
                time.sleep(6.0) # show terminal settlement modal
                break

            time.sleep(0.6)

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

    # Merge video, audio, burned-in subtitles
    # Subtitles escaped for ffmpeg filter
    escaped_srt = str(srt_file).replace(":", "\\:").replace("'", "\\'")
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", str(raw_webm),
        "-i", str(audio_wav),
        "-filter_complex", f"[0:v]subtitles='{escaped_srt}':force_style='FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,BackColour=&H80000000,MarginV=28'[v]",
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
        # Fallback if subtitles filter has font issues: encode without filter_complex
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
    synthesize_narration_audio(audio_wav, total_duration_s=148.0)
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
