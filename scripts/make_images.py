#!/usr/bin/env python3
"""Render the quote cards in content/cards.json into images/.

    pip install -r requirements-images.txt
    python scripts/make_images.py

Run locally and commit the PNGs. The posting workflow never runs this, it only
reads whatever is already in images/.

Output is 1600x900 (16:9), which is what X shows uncropped for a single image.
Colours are lifted from mupler.com so the cards sit next to the site.
"""

import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CARDS_PATH = ROOT / "content" / "cards.json"
OUT_DIR = ROOT / "images"

W, H = 1600, 900
MARGIN = 120

# Sampled from the live site.
INK = (26, 26, 26)
SAGE = (106, 129, 92)
SAGE_LIGHT = (153, 165, 130)
OLIVE = (100, 108, 86)
SAND = (205, 148, 91)
CREAM = (253, 242, 231)
PALE = (228, 234, 209)
WHITE = (255, 255, 255)

# Alternating so a run of posts does not look like one long block.
THEMES = [
    {"bg": CREAM, "rule": SAGE, "kicker": SAND},
    {"bg": PALE, "rule": SAGE, "kicker": OLIVE},
    {"bg": WHITE, "rule": SAGE_LIGHT, "kicker": SAND},
]

# Inter first, since that is what the site uses. Everything after is a fallback
# so this still renders on a machine that does not have it.
FONT_CANDIDATES = {
    "bold": [
        "Inter-Bold.ttf", "Inter_18pt-Bold.ttf", "InterDisplay-Bold.ttf",
        "C:/Windows/Fonts/Inter-Bold.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "medium": [
        "Inter-Medium.ttf", "Inter_18pt-Medium.ttf",
        "C:/Windows/Fonts/Inter-Medium.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
}


def find_font(weight):
    for path in FONT_CANDIDATES[weight]:
        try:
            ImageFont.truetype(path, 40)
            return path
        except OSError:
            continue
    sys.exit(
        f"no usable {weight} font found. Install Inter from rsms.me/inter, "
        "or add a .ttf path to FONT_CANDIDATES."
    )


def wrap(text, font, draw, max_width):
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_headline(text, draw, font_path, max_width, max_height, max_lines=4):
    """Largest size at which the line still fits the text block."""
    for size in range(104, 46, -2):
        font = ImageFont.truetype(font_path, size)
        lines = wrap(text, font, draw, max_width)
        leading = int(size * 1.22)
        if len(lines) <= max_lines and len(lines) * leading <= max_height:
            return font, lines, leading
    font = ImageFont.truetype(font_path, 46)
    return font, wrap(text, font, draw, max_width), int(46 * 1.22)


def draw_tracked(draw, xy, text, font, fill, tracking):
    """Pillow has no letter-spacing, so place the glyphs by hand."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + tracking


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def render(card, index, bold_path, medium_path):
    theme = THEMES[index % len(THEMES)]
    img = Image.new("RGB", (W, H), theme["bg"])
    draw = ImageDraw.Draw(img)

    kicker_font = ImageFont.truetype(medium_path, 30)
    footer_font = ImageFont.truetype(medium_path, 32)

    body_width = W - MARGIN * 2
    top = MARGIN

    # accent rule
    draw.rectangle([MARGIN, top, MARGIN + 92, top + 8], fill=theme["rule"])
    top += 62

    # kicker
    draw_tracked(
        draw, (MARGIN, top), card["kicker"].upper(), kicker_font, theme["kicker"], 3.2
    )
    top += 74

    footer_baseline = H - MARGIN - 40
    available = footer_baseline - top - 60
    font, lines, leading = fit_headline(
        card["line"], draw, bold_path, body_width, available
    )

    # Centre the block in what is left, or a two-line card leaves a dead band
    # where a three-line card has text.
    top += max(0, (available - len(lines) * leading) // 2)
    for line in lines:
        draw.text((MARGIN, top), line, font=font, fill=INK)
        top += leading

    draw.text((MARGIN, footer_baseline), "mupler.com", font=footer_font, fill=OLIVE)

    # a quiet corner block so the card is not a pure text slab
    draw.rectangle([W - MARGIN - 160, H - MARGIN - 26, W - MARGIN, H - MARGIN - 18],
                   fill=theme["rule"])

    name = f"{index + 1:02d}-{slugify(card['kicker'])}.png"
    path = OUT_DIR / name
    img.save(path, "PNG", optimize=True)
    return path, len(lines), font.size


def main():
    cards = json.loads(CARDS_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(exist_ok=True)

    bold_path = find_font("bold")
    medium_path = find_font("medium")
    print(f"bold:   {bold_path}\nmedium: {medium_path}\n")

    for i, card in enumerate(cards):
        path, lines, size = render(card, i, bold_path, medium_path)
        kb = path.stat().st_size / 1024
        print(f"{path.name:38} {lines} lines @ {size}px  {kb:5.0f} KB")

    # Relative, not absolute: a non-ASCII path blows up on a cp1252 console.
    print(f"\n{len(cards)} cards written to images/")


if __name__ == "__main__":
    main()
