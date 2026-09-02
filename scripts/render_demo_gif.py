#!/usr/bin/env python3
"""Render docs/demo.gif from scripts/demo.sh output (no VHS/ttyd required)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "demo.gif"
DEMO = ROOT / "scripts" / "demo.sh"

# Terminal theme (Catppuccin Mocha-ish)
BG = (30, 30, 46)
FG = (205, 214, 244)
CYAN = (137, 220, 235)
GREEN = (166, 227, 161)
DIM = (108, 112, 134)
MARGIN = 28
LINE_H = 22
WIDTH = 1280
HEIGHT = 720
FPS = 12
HOLD_END_FRAMES = FPS * 3  # pause on final frame


def strip_ansi(text: str) -> str:
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ):
        p = Path(path)
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def color_line(line: str) -> tuple[int, int, int]:
    s = line.strip()
    if s.startswith("==>"):
        return CYAN
    if "PASS" in s or "Demo complete" in s:
        return GREEN
    if s.startswith("prompt:") or s.startswith("curl "):
        return DIM
    return FG


def run_demo() -> list[str]:
    proc = subprocess.run(
        ["bash", str(DEMO)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=True,
    )
    lines: list[str] = []
    for raw in proc.stdout.splitlines():
        line = strip_ansi(raw)
        if line.strip():
            lines.append(line)
    return lines


def wrap_lines(lines: list[str], font: ImageFont.ImageFont, max_width: int) -> list[tuple[str, tuple[int, int, int]]]:
    wrapped: list[tuple[str, tuple[int, int, int]]] = []
    for line in lines:
        color = color_line(line)
        if not line:
            wrapped.append(("", color))
            continue
        chunk = ""
        for ch in line:
            test = chunk + ch
            bbox = font.getbbox(test)
            if bbox[2] - bbox[0] > max_width and chunk:
                wrapped.append((chunk, color))
                chunk = ch
            else:
                chunk = test
        if chunk:
            wrapped.append((chunk, color))
    return wrapped


def render_frame(
    visible: list[tuple[str, tuple[int, int, int]]],
    font: ImageFont.ImageFont,
) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    max_lines = (HEIGHT - 2 * MARGIN) // LINE_H
    start = max(0, len(visible) - max_lines)
    y = MARGIN
    for text, color in visible[start:]:
        draw.text((MARGIN, y), text, fill=color, font=font)
        y += LINE_H
    return img


def main() -> int:
    font = load_font(16)
    lines = run_demo()
    wrapped = wrap_lines(lines, font, WIDTH - 2 * MARGIN)

    frames: list[Image.Image] = []
    visible: list[tuple[str, tuple[int, int, int]]] = []
    for i, item in enumerate(wrapped):
        visible.append(item)
        # type ~2 lines per frame early, 1 per frame later
        step = 2 if i < 12 else 1
        if i % step == 0 or i == len(wrapped) - 1:
            frames.append(render_frame(visible, font))

    for _ in range(HOLD_END_FRAMES):
        frames.append(frames[-1].copy())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = int(1000 / FPS)
    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
    )
    print(f"Wrote {OUT} ({len(frames)} frames, {OUT.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
