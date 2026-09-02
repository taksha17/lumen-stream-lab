#!/usr/bin/env python3
"""Render docs/walkthrough.mp4 — ~60s Lumen intro with pros, cons, and live routing demo."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT_MP4 = ROOT / "docs" / "walkthrough.mp4"
OUT_GIF = ROOT / "docs" / "walkthrough.gif"

WIDTH, HEIGHT = 1280, 720
FPS = 12
TARGET_SEC = 60

BG = (30, 30, 46)
FG = (205, 214, 244)
CYAN = (137, 220, 235)
GREEN = (166, 227, 161)
YELLOW = (249, 226, 175)
RED = (243, 139, 168)
DIM = (108, 112, 134)
MARGIN = 36
LINE_H = 26


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        ["DejaVuSans-Bold.ttf", "DejaVuSansMono-Bold.ttf"] if bold
        else ["DejaVuSansMono.ttf", "DejaVuSans.ttf"]
    )
    bases = (
        "/usr/share/fonts/truetype/dejavu",
        "/usr/share/fonts/TTF",
        "/usr/share/fonts/truetype/liberation",
    )
    for base in bases:
        for name in names:
            p = Path(base) / name
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def wrap(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if font.getbbox(test)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def draw_slide(
    title: str,
    body_lines: list[tuple[str, tuple[int, int, int]]],
    *,
    subtitle: str = "",
) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    title_font = load_font(34, bold=True)
    sub_font = load_font(18)
    body_font = load_font(20)

    y = MARGIN + 10
    draw.text((MARGIN, y), title, fill=CYAN, font=title_font)
    y += 48
    if subtitle:
        draw.text((MARGIN, y), subtitle, fill=DIM, font=sub_font)
        y += 34

    for text, color in body_lines:
        for line in wrap(text, body_font, WIDTH - 2 * MARGIN):
            draw.text((MARGIN, y), line, fill=color, font=body_font)
            y += LINE_H
            if y > HEIGHT - MARGIN:
                break
    return img


def route_line(prompt: str) -> list[str]:
    proc = subprocess.run(
        ["python3", str(ROOT / "lumen.py"), "route", "--prompt", prompt],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    p = json.loads(proc.stdout)
    return [
        f"$ lumen route --prompt \"{prompt[:42]}{'...' if len(prompt) > 42 else ''}\"",
        f"  tier:  {p['tier']}",
        f"  model: {p['model']}",
        f"  why:   {p['reason']}",
        "",
    ]


def terminal_scene(lines: list[str], header: str) -> list[Image.Image]:
    font = load_font(18)
    wrapped: list[tuple[str, tuple[int, int, int]]] = []
    wrapped.append((f"==> {header}", CYAN))
    wrapped.append(("", FG))
    for line in lines:
        color = GREEN if "PASS" in line else DIM if line.startswith("$") else FG
        if line.startswith("  tier") or line.startswith("  model"):
            color = YELLOW
        for part in wrap(line, font, WIDTH - 2 * MARGIN):
            wrapped.append((part, color))

    frames: list[Image.Image] = []
    visible: list[tuple[str, tuple[int, int, int]]] = []
    for i, item in enumerate(wrapped):
        visible.append(item)
        if i % 2 == 0 or i == len(wrapped) - 1:
            body = visible[-min(len(visible), 18):]
            frames.append(draw_slide("LUMEN STREAM LAB", body, subtitle="live routing demo"))
    return frames


def hold(img: Image.Image, seconds: float) -> list[Image.Image]:
    return [img.copy() for _ in range(max(1, int(seconds * FPS)))]


def build_frames() -> list[Image.Image]:
    frames: list[Image.Image] = []

    # 0–5s: hook
    intro = draw_slide(
        "LUMEN STREAM LAB",
        [
            ("Hybrid LLM orchestration for modest hardware", FG),
            ("Route each prompt to the right local model", FG),
            ("Proven +40% vs always using one 3B model", GREEN),
            ("", FG),
            ("Reference lab: GTX 1650 4GB · offline Ollama", DIM),
        ],
        subtitle="~60 second walkthrough",
    )
    frames.extend(hold(intro, 5))

    # 5–10s: problem
    problem = draw_slide(
        "THE PROBLEM",
        [
            ("Most people run one model for everything.", FG),
            ("On 4GB GPUs that means ~49 tok/s for every query.", YELLOW),
            ("Math, greetings, and long essays all hit the same 3B.", FG),
            ("", FG),
            ("Lumen picks fast / balanced / domain / quality per prompt.", GREEN),
        ],
    )
    frames.extend(hold(problem, 5))

    # 10–28s: live routing
    demo_lines: list[str] = []
    for prompt in (
        "What is 2+2?",
        "Explain TCP vs UDP briefly.",
        "What is Lumen Stream Lab?",
    ):
        demo_lines.extend(route_line(prompt))
    demo_lines.append("$ lumen compare --baseline 48.38 --optimized 68.1")
    demo_lines.extend([
        "  Baseline:  48.38 tok/s",
        "  Optimized: 68.10 tok/s",
        "  Gain:      40.8%",
        "  Result:    PASS",
    ])
    term_frames = terminal_scene(demo_lines, "route three prompts + +40% gate")
    # stretch to ~18s
    per = max(1, int(18 * FPS / max(len(term_frames), 1)))
    for f in term_frames:
        frames.extend([f] * per)

    # 28–40s: pros
    pros = draw_slide(
        "PROS",
        [
            ("+ Measured +40% mean decode on reference 4GB lab", GREEN),
            ("+ Works offline — Ollama, localhost gateway, no API keys", GREEN),
            ("+ Right-sized models: 1B fast · LFM · domain 3B · opt-in 7B", GREEN),
            ("+ Auditable JSON plan per request (tier, model, reason)", GREEN),
            ("+ Open source — probe, bench, route, regression gates", GREEN),
            ("+ Scales to teams: local by default, cloud by exception", GREEN),
        ],
    )
    frames.extend(hold(pros, 12))

    # 40–52s: cons
    cons = draw_slide(
        "CONS (HONEST LIMITS)",
        [
            ("− Not frontier cloud quality on hardest reasoning tasks", RED),
            ("− 7B quality tier ~10 tok/s on 4GB — use sparingly", YELLOW),
            ("− Live chat needs Ollama + pulled models installed", YELLOW),
            ("− Keyword router today; learned v2 still experimental", YELLOW),
            ("− Absolute tok/s depends on YOUR GPU — re-bench locally", DIM),
            ("− Hybrid enterprise savings need ops + routing policy", DIM),
        ],
    )
    frames.extend(hold(cons, 12))

    # 52–60s: CTA
    cta = draw_slide(
        "GET STARTED",
        [
            ("git clone github.com/taksha17/lumen-stream-lab", FG),
            ("./scripts/demo.sh          # routing demo, no GPU required", FG),
            ("python3 lumen.py           # interactive menu + chat", FG),
            ("", FG),
            ("Docs: LOW-SPEC-BUILDERS.md · MODELS.md · ENTERPRISE.md", DIM),
            ("Domain models on Hugging Face: qwen2.5-3b-lumen", DIM),
        ],
        subtitle="github.com/taksha17/lumen-stream-lab",
    )
    frames.extend(hold(cta, 8))

    # trim or pad to ~60s
    target = TARGET_SEC * FPS
    if len(frames) > target:
        frames = frames[:target]
    elif len(frames) < target:
        frames.extend([frames[-1].copy()] * (target - len(frames)))
    return frames


def write_mp4(frames: list[Image.Image], path: Path) -> None:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg required to write walkthrough.mp4")

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i, frame in enumerate(frames):
            frame.save(tmp_path / f"frame_{i:05d}.png")
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-framerate", str(FPS),
                "-i", str(tmp_path / "frame_%05d.png"),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(path),
            ],
            check=True,
            capture_output=True,
        )


def write_gif(frames: list[Image.Image], path: Path) -> None:
    # lighter preview — 8 fps, every 2nd frame
    preview = frames[::2]
    path.parent.mkdir(parents=True, exist_ok=True)
    preview[0].save(
        path,
        save_all=True,
        append_images=preview[1:],
        duration=int(1000 / 8),
        loop=0,
        optimize=True,
    )


def main() -> int:
    frames = build_frames()
    write_mp4(frames, OUT_MP4)
    write_gif(frames, OUT_GIF)
    print(f"Wrote {OUT_MP4} ({len(frames)/FPS:.1f}s, {OUT_MP4.stat().st_size // 1024} KB)")
    print(f"Wrote {OUT_GIF} ({len(frames)//2/8:.1f}s preview, {OUT_GIF.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
