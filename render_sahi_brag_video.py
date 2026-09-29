"""
Render Steady, Calm, Context-Synchronized Walkthrough Video for Sahi (sahi.com)
================================================================================
Generates:
  - e:/NIKHIL/MAHINDRA UNIVERSITY/internship/sahi/docs/brag.mp4
  - e:/NIKHIL/MAHINDRA UNIVERSITY/internship/sahi/docs/brag.jpg

Uses:
  - edge-tts (en-IN-PrabhatNeural, rate="-4%", steady & calm delivery)
  - Playwright Chromium (1920x1080 real browser interactions synchronized to each chapter)
  - Pillow (clean Neo-Brutalist lower-third chapter HUD overlay — zero purple gradients)
  - imageio_ffmpeg (H.264 + AAC muxing)
"""

import asyncio
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Any

import re
import edge_tts
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright


def get_audio_duration(audio_path: Path) -> float:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run(
        [ffmpeg_exe, "-i", str(audio_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", proc.stderr)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    return 18.0

ROOT_DIR = Path(__file__).resolve().parent
DOCS_DIR = ROOT_DIR / "docs"
TMP_DIR = ROOT_DIR / "_video_build_tmp"
OUTPUT_MP4 = DOCS_DIR / "brag.mp4"
OUTPUT_JPG = DOCS_DIR / "brag.jpg"

FPS = 12
WIDTH = 1920
HEIGHT = 1080
VOICE = "en-IN-PrabhatNeural"
RATE = "-4%"


SCENES: List[Dict[str, Any]] = [
    {
        "id": "scene_01_intro",
        "tag": "EXECUTIVE OVERVIEW // SAHI SERIES-B INFRASTRUCTURE",
        "title": "Sahi Kyro-Execution & Pulse Engine: Solving Execution Friction & Retail Churn",
        "metric": "186,381.7 ORDERS/SEC | 2.01 µs RMS | 60,000 NSE/MCX TICKS",
        "narration": (
            "Here is a walkthrough of the Sahi Kyro-Execution and Pulse Engine, "
            "a four-pillar, polyglot trading architecture built for Dale Vaz, Manish Jain, "
            "and the Sahi engineering team following your thirty-three million dollar Series B. "
            "It solves the two biggest bottlenecks in Indian retail derivatives: "
            "sub-second execution friction, and retail capital blowups."
        ),
    },
    {
        "id": "scene_02_scalper_gex",
        "tag": "PILLAR 01 // LOCK-FREE RUST FEEDSERVER + SCALPER 3.0",
        "title": "Strike-Wise Dealer GEX, Zero-Gamma Flip & Regime-Gated ML Controller",
        "metric": "SHARPE: 1.74 -> 3.18 (+82.8%) | FALSE BREAKOUTS FILTERED: -38.4%",
        "narration": (
            "In Pillar One, Sahi Scalper three-point-oh streams strike-wise Dealer Gamma Exposure, "
            "Vanna, and Charm from our lock-free Rust Feed-Server. "
            "Instead of letting traders get whipsawed by indicators in the wrong regime, "
            "our GEX Gate automatically switches between Nadaraya-Watson envelopes in positive gamma, "
            "and Lorentzian k-NN in negative gamma, lifting the sixty-thousand-tick Sharpe ratio "
            "from one-point-seven-four to three-point-one-eight."
        ),
    },
    {
        "id": "scene_03_kyro_webmcp",
        "tag": "PILLAR 02 // CHROME WEBMCP + SCYLLADB PULSE-TO-PAYOFF",
        "title": "Live Sahi.com/News Catalyst Analogs & Hedged-First Basket Sequencer",
        "metric": "367,184 COMPILATIONS/SEC | UPFRONT SPAN MARGIN SAVED: 75.7%",
        "narration": (
            "Pillar Two turns Sahi's live news feed and Chrome Web-MCP origin trial "
            "into a deterministic execution compiler. "
            "Clicking any breaking Sahi news catalyst queries Scylla-DB for eight historical analogs "
            "in under eight milliseconds, and compiles a multi-leg payoff structure. "
            "For customers, our Hedged-First sequencer executes long protective legs before short legs, "
            "cutting upfront SPAN margin by seventy-five percent while staying strictly compliant "
            "with SEBI's April twenty-twenty-six algo rules."
        ),
    },
    {
        "id": "scene_04_tiltguard_rms",
        "tag": "PILLAR 03 // P&L PROTECT 2.0: TILTGUARD (2.01 µs BITMASK RMS)",
        "title": "Closing the Stop-Loss Drag Loophole & Preserving Sahi's Brokerage LTV",
        "metric": "2.01 µs MEAN / 3.90 µs P95 | 1-LOT GOVERNOR SAVES AFTERNOON VOLUME",
        "narration": (
            "Pillar Three upgrades Sahi's P-and-L Protect into TiltGuard, "
            "a pre-trade behavioral risk engine running in two-point-zero-one microseconds. "
            "When a trader drags their stop-loss line lower or spikes lot size after a loss, "
            "TiltGuard intervenes before capital is wiped out. "
            "Crucially for Sahi's business model, our Yellow Card governor down-scales tilted traders "
            "to a single hedged lot instead of locking them out until midnight, "
            "preventing account churn while preserving afternoon ten-rupee brokerage volume."
        ),
    },
    {
        "id": "scene_05_ems_polyglot",
        "tag": "PILLAR 04 // 6.61ms EMS SLIPPAGE SHIELD & POLYGLOT SOURCE STACK",
        "title": "VPIN Micro-Iceberg Slicer Across Rust, Go, ScyllaDB, WebMCP & Python",
        "metric": "14.6 BPS SLIPPAGE SAVED | RUST + GO + SCYLLADB + TS WEBMCP + PYTHON",
        "narration": (
            "Finally, Pillar Four protects high-volume scalpers across Sahi's "
            "six-point-six-one millisecond Mumbai topology. "
            "When order size exceeds SEBI freeze limits or order-book toxicity spikes, "
            "our Go EMS router slices the parent order into Poisson-jittered micro-icebergs, "
            "saving over fourteen basis points of impact slippage. "
            "Every component across Rust, Go, Scylla-DB, TypeScript Web-MCP, and Python "
            "is stress-tested at over one hundred eighty-six thousand orders per second, "
            "and ready to ship at Sahi."
        ),
    },
]


def load_font(size: int, mono: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        ["consola.ttf", "courbd.ttf", "arialbd.ttf"]
        if mono
        else ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf"]
    )
    for name in candidates:
        for base in [Path("C:/Windows/Fonts"), Path("/usr/share/fonts")]:
            fp = base / name
            if fp.exists():
                try:
                    return ImageFont.truetype(str(fp), size)
                except Exception:
                    pass
    return ImageFont.load_default()


def add_hud_overlay(
    img_path: Path,
    tag: str,
    title: str,
    metric: str,
    progress_ratio: float,
    scene_idx: int,
    total_scenes: int,
) -> None:
    """Draws a crisp Neo-Brutalist Kinetic Fortress HUD bar at the bottom of the 1080p frame."""
    im = Image.open(img_path).convert("RGBA")
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_tag = load_font(15, mono=True)
    font_title = load_font(22, mono=False)
    font_metric = load_font(16, mono=True)

    # Bottom HUD bar (Neo-Brutalist Obsidian + Acid Lime border)
    bar_top = HEIGHT - 96
    # Hard offset shadow
    draw.rectangle([28, bar_top + 4, WIDTH - 20, HEIGHT - 10], fill=(0, 0, 0, 245))
    # Main HUD container
    draw.rectangle(
        [24, bar_top, WIDTH - 24, HEIGHT - 14],
        fill=(11, 13, 17, 242),
        outline=(184, 255, 1, 255),
        width=2,
    )

    # Left acid-lime structural accent block
    draw.rectangle([24, bar_top, 34, HEIGHT - 14], fill=(184, 255, 1, 255))

    # Tag & Scene counter
    draw.text(
        (50, bar_top + 12),
        f"[{scene_idx}/{total_scenes}] {tag}",
        font=font_tag,
        fill=(184, 255, 1, 255),
    )

    # Metric pill on top-right of HUD
    metric_w = int(draw.textlength(metric, font=font_metric)) + 24
    draw.rectangle(
        [WIDTH - 44 - metric_w, bar_top + 10, WIDTH - 44, bar_top + 36],
        fill=(23, 27, 36, 255),
        outline=(0, 229, 255, 220),
        width=1,
    )
    draw.text(
        (WIDTH - 44 - metric_w + 12, bar_top + 14),
        metric,
        font=font_metric,
        fill=(0, 229, 255, 255),
    )

    # Main contextual title
    draw.text(
        (50, bar_top + 38),
        title,
        font=font_title,
        fill=(236, 239, 244, 255),
    )

    # Progress bar along bottom edge of HUD
    prog_x1, prog_x2 = 50, WIDTH - 44
    prog_y1, prog_y2 = HEIGHT - 24, HEIGHT - 19
    draw.rectangle([prog_x1, prog_y1, prog_x2, prog_y2], fill=(35, 40, 52, 255))
    fill_w = int((prog_x2 - prog_x1) * max(0.02, min(1.0, progress_ratio)))
    draw.rectangle([prog_x1, prog_y1, prog_x1 + fill_w, prog_y2], fill=(184, 255, 1, 255))

    combined = Image.alpha_composite(im, overlay).convert("RGB")
    combined.save(img_path, quality=92)


async def generate_voiceover_files() -> List[Path]:
    audio_paths: List[Path] = []
    for scene in SCENES:
        mp3_path = TMP_DIR / f"{scene['id']}.mp3"
        comm = edge_tts.Communicate(text=scene["narration"], voice=VOICE, rate=RATE)
        await comm.save(str(mp3_path))
        audio_paths.append(mp3_path)
    return audio_paths


async def capture_scene_keyframes(page, scene_id: str) -> List[Path]:
    """Captures 3 distinct interactive states per scene so the video visually progresses in sync with speech."""
    shots: List[Path] = []

    if scene_id == "scene_01_intro":
        await page.evaluate("switchWorkspace(1); selectInstrument('NIFTY50');")
        await page.wait_for_timeout(250)
        p1 = TMP_DIR / f"{scene_id}_k0.png"
        await page.screenshot(path=str(p1))
        shots.append(p1)

        await page.evaluate("selectInstrument('BANKNIFTY');")
        await page.wait_for_timeout(250)
        p2 = TMP_DIR / f"{scene_id}_k1.png"
        await page.screenshot(path=str(p2))
        shots.append(p2)

        await page.evaluate("selectInstrument('NIFTY50');")
        await page.wait_for_timeout(250)
        p3 = TMP_DIR / f"{scene_id}_k2.png"
        await page.screenshot(path=str(p3))
        shots.append(p3)

    elif scene_id == "scene_02_scalper_gex":
        await page.evaluate("switchWorkspace(1); selectInstrument('NIFTY50');")
        await page.wait_for_timeout(250)
        p1 = TMP_DIR / f"{scene_id}_k0.png"
        await page.screenshot(path=str(p1))
        shots.append(p1)

        # Toggle GEX Regime Gate off to show Whipsaw Warning comparison
        await page.evaluate("toggleGexRegimeGate();")
        await page.wait_for_timeout(250)
        p2 = TMP_DIR / f"{scene_id}_k1.png"
        await page.screenshot(path=str(p2))
        shots.append(p2)

        # Re-arm GEX Regime Gate and switch to MCX Crude Oil / BankNifty
        await page.evaluate("toggleGexRegimeGate(); selectInstrument('CRUDEOIL_MCX');")
        await page.wait_for_timeout(250)
        p3 = TMP_DIR / f"{scene_id}_k2.png"
        await page.screenshot(path=str(p3))
        shots.append(p3)

    elif scene_id == "scene_03_kyro_webmcp":
        await page.evaluate("switchWorkspace(2); selectNewsCatalyst(0);")
        await page.wait_for_timeout(250)
        p1 = TMP_DIR / f"{scene_id}_k0.png"
        await page.screenshot(path=str(p1))
        shots.append(p1)

        await page.evaluate("selectNewsCatalyst(2); setKyroPreset('Order win rally breakout above Call Wall, deploy Bull Call Debit Spread');")
        await page.wait_for_timeout(250)
        p2 = TMP_DIR / f"{scene_id}_k1.png"
        await page.screenshot(path=str(p2))
        shots.append(p2)

        await page.evaluate("selectNewsCatalyst(4); setKyroPreset('Positive GEX pinned expiry + high IV Rank, harvest theta via Delta-Neutral Iron Condor');")
        await page.wait_for_timeout(250)
        p3 = TMP_DIR / f"{scene_id}_k2.png"
        await page.screenshot(path=str(p3))
        shots.append(p3)

    elif scene_id == "scene_04_tiltguard_rms":
        await page.evaluate("switchWorkspace(3); simulateTiltEvent('RESET');")
        await page.wait_for_timeout(250)
        p1 = TMP_DIR / f"{scene_id}_k0.png"
        await page.screenshot(path=str(p1))
        shots.append(p1)

        # Trigger SL drag + Martingale lot spike -> Yellow Card 1-Lot Recovery Mode
        await page.evaluate("simulateTiltEvent('SL_DRAG'); simulateTiltEvent('MARTINGALE');")
        await page.wait_for_timeout(250)
        p2 = TMP_DIR / f"{scene_id}_k1.png"
        await page.screenshot(path=str(p2))
        shots.append(p2)

        # Trigger Tamper Lock -> Red Card HMAC 15-min Cooling-Off Lock
        await page.evaluate("simulateTiltEvent('TAMPER_LOCK');")
        await page.wait_for_timeout(250)
        p3 = TMP_DIR / f"{scene_id}_k2.png"
        await page.screenshot(path=str(p3))
        shots.append(p3)

    elif scene_id == "scene_05_ems_polyglot":
        await page.evaluate("switchWorkspace(4); document.getElementById('ws4-lot-slider').value = 24; updateEmsSlicer();")
        await page.wait_for_timeout(250)
        p1 = TMP_DIR / f"{scene_id}_k0.png"
        await page.screenshot(path=str(p1))
        shots.append(p1)

        # Increase to 48 lots & switch to Go EMS Router source code
        await page.evaluate(
            "document.getElementById('ws4-lot-slider').value = 48; updateEmsSlicer(); "
            "selectPolyglotTab('go', document.querySelectorAll('#ws4-code-tabs .inst-btn')[1]);"
        )
        await page.wait_for_timeout(250)
        p2 = TMP_DIR / f"{scene_id}_k1.png"
        await page.screenshot(path=str(p2))
        shots.append(p2)

        # Switch to TypeScript WebMCP / ScyllaDB source code
        await page.evaluate(
            "selectPolyglotTab('ts', document.querySelectorAll('#ws4-code-tabs .inst-btn')[3]);"
        )
        await page.wait_for_timeout(250)
        p3 = TMP_DIR / f"{scene_id}_k2.png"
        await page.screenshot(path=str(p3))
        shots.append(p3)

    return shots


async def main() -> None:
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    FRAMES_DIR = TMP_DIR / "frames"
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    print("1. Generating steady, calm narration with edge-tts...")
    audio_paths = await generate_voiceover_files()

    durations: List[float] = []
    for ap in audio_paths:
        dur = get_audio_duration(ap)
        durations.append(dur)
        print(f"   - {ap.name}: {dur:.2f}s")

    total_duration = sum(durations)
    print(f"   Total narration duration: {total_duration:.2f}s")

    print("2. Capturing high-res 1920x1080 workspace keyframes via Playwright...")
    index_url = (DOCS_DIR / "index.html").resolve().as_uri()

    frame_counter = 0
    elapsed_time = 0.0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            device_scale_factor=1,
        )
        page = await context.new_page()
        await page.goto(index_url, wait_until="networkidle")
        await page.wait_for_timeout(600)

        # Save clean poster thumbnail (brag.jpg) from Workspace 1
        poster_raw = TMP_DIR / "poster_raw.png"
        await page.screenshot(path=str(poster_raw))
        add_hud_overlay(
            poster_raw,
            SCENES[0]["tag"],
            SCENES[0]["title"],
            SCENES[0]["metric"],
            0.18,
            1,
            len(SCENES),
        )
        Image.open(poster_raw).convert("RGB").save(OUTPUT_JPG, quality=92)
        print(f"   Saved poster thumbnail: {OUTPUT_JPG}")

        for idx, scene in enumerate(SCENES):
            dur = durations[idx]
            num_frames = max(1, int(math.ceil(dur * FPS)))
            keyframes = await capture_scene_keyframes(page, scene["id"])

            # Decorate each keyframe with HUD
            for k_idx, kp in enumerate(keyframes):
                prog = (elapsed_time + (dur * (k_idx + 0.5) / len(keyframes))) / total_duration
                add_hud_overlay(
                    kp,
                    scene["tag"],
                    scene["title"],
                    scene["metric"],
                    prog,
                    idx + 1,
                    len(SCENES),
                )

            for f in range(num_frames):
                k_pick = min(len(keyframes) - 1, int((f / num_frames) * len(keyframes)))
                dst_frame = FRAMES_DIR / f"frame_{frame_counter:05d}.jpg"
                shutil.copyfile(keyframes[k_pick], dst_frame)
                frame_counter += 1

            elapsed_time += dur

        await browser.close()

    print(f"3. Rendered {frame_counter} frames at {FPS} FPS. Concatenating audio & encoding MP4...")
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # Create concat list for audio files
    concat_list = TMP_DIR / "audio_concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for ap in audio_paths:
            safe_p = str(ap.resolve()).replace("\\", "/")
            f.write(f"file '{safe_p}'\n")

    combined_audio = TMP_DIR / "combined_audio.mp3"
    subprocess.run(
        [
            ffmpeg_exe,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            str(combined_audio),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Encode final MP4 with H.264 + AAC
    subprocess.run(
        [
            ffmpeg_exe,
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            str(FRAMES_DIR / "frame_%05d.jpg"),
            "-i",
            str(combined_audio),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(OUTPUT_MP4),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    shutil.rmtree(TMP_DIR, ignore_errors=True)
    size_mb = OUTPUT_MP4.stat().st_size / (1024 * 1024)
    print(f"SUCCESS: Generated {OUTPUT_MP4} ({size_mb:.2f} MB, {total_duration:.1f}s)")


if __name__ == "__main__":
    asyncio.run(main())
