"""Generate the AutoMacro application icon (icon.png and icon.ico).

Run with:  python assets/generate_icon.py

Produces a crisp, self-contained icon so the packaged app has a proper
taskbar / dock / window icon.  Committed outputs mean the build scripts do
not need Pillow at build time.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent

# Brand colours.
BG_TOP = (56, 132, 216)  # lighter blue
BG_BOTTOM = (24, 60, 120)  # deep blue
BOLT = (255, 255, 255)
KEY = (255, 255, 255)
KEY_SHADOW = (13, 38, 76)


def _rounded_mask(size: int, radius_ratio: float = 0.22) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    r = int(size * radius_ratio)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=255)
    return mask


def _vertical_gradient(size: int, top, bottom) -> Image.Image:
    grad = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / max(1, size - 1)
        grad.putpixel(
            (0, y),
            tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)),
        )
    return grad.resize((size, size))


def render(size: int) -> Image.Image:
    # Supersample for smooth edges, then downscale.
    ss = size * 4
    base = _vertical_gradient(ss, BG_TOP, BG_BOTTOM).convert("RGBA")

    draw = ImageDraw.Draw(base)

    # Two stylised keycaps (bottom-left, top-right) suggesting a keyboard.
    key_w = int(ss * 0.30)
    key_h = int(ss * 0.24)
    kr = int(ss * 0.05)
    for cx, cy in [(ss * 0.30, ss * 0.68), (ss * 0.70, ss * 0.34)]:
        x0, y0 = cx - key_w / 2, cy - key_h / 2
        x1, y1 = cx + key_w / 2, cy + key_h / 2
        draw.rounded_rectangle(
            [x0, y0 + ss * 0.012, x1, y1 + ss * 0.012], radius=kr, fill=KEY_SHADOW
        )
        draw.rounded_rectangle([x0, y0, x1, y1], radius=kr, fill=(230, 238, 248))

    # A bold lightning bolt across the middle: fast automation.
    w, h = ss, ss
    bolt = [
        (w * 0.58, h * 0.16),
        (w * 0.34, h * 0.55),
        (w * 0.49, h * 0.55),
        (w * 0.42, h * 0.86),
        (w * 0.68, h * 0.44),
        (w * 0.52, h * 0.44),
        (w * 0.62, h * 0.16),
    ]
    # Subtle shadow then the white bolt.
    draw.polygon([(x, y + ss * 0.012) for (x, y) in bolt], fill=KEY_SHADOW)
    draw.polygon(bolt, fill=BOLT)

    base = base.resize((size, size), Image.LANCZOS)
    base.putalpha(_rounded_mask(size))
    return base


def main() -> None:
    png = render(256)
    png.save(HERE / "icon.png")

    sizes = [16, 32, 48, 64, 128, 256]
    png.save(HERE / "icon.ico", sizes=[(s, s) for s in sizes])
    written = [HERE / "icon.png", HERE / "icon.ico"]

    # macOS .icns (best effort; needs a large square source).
    try:
        render(1024).save(HERE / "icon.icns", format="ICNS")
        written.append(HERE / "icon.icns")
    except Exception as exc:  # pragma: no cover - platform/Pillow dependent
        print(f"(skipped icon.icns: {exc})")

    print("Wrote " + ", ".join(str(p) for p in written))


if __name__ == "__main__":
    main()
