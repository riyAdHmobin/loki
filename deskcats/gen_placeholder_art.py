from pathlib import Path

from PIL import Image, ImageDraw

FRAME_SIZE = 64

SKINS = {
    "loki-black": {"fill": (0x11, 0x11, 0x11, 255), "outline": None, "eye": (0x3F, 0xD1, 0x2C, 255)},
    "mike-white": {"fill": (0xF2, 0xF2, 0xEF, 255), "outline": (0x4A, 0x4A, 0x4A, 255), "eye": (0xE8, 0xA1, 0x3C, 255)},
}

ANIMATIONS = {
    "idle": {"frames": 4, "fps": 10},
    "walk": {"frames": 6, "fps": 10},
    "sleep": {"frames": 4, "fps": 4},
    "sit": {"frames": 4, "fps": 10},
}

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "skins"


def _ear(draw, cx, cy, w, h, fill, outline):
    draw.polygon([(cx - w, cy + h), (cx, cy - h), (cx + w, cy + h)], fill=fill, outline=outline)


def _eye(draw, cx, cy, color):
    draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=color)


def _head(draw, hx, hy, fill, outline, eye):
    draw.ellipse([hx - 9, hy - 9, hx + 9, hy + 9], fill=fill, outline=outline)
    _ear(draw, hx - 4, hy - 8, 4, 6, fill, outline)
    _ear(draw, hx + 4, hy - 8, 4, 6, fill, outline)
    _eye(draw, hx + 3, hy, eye)


def _tail(draw, base, tip, fill, width=4):
    draw.line([base, tip], fill=fill, width=width, joint="curve")
    r = width / 2
    draw.ellipse([tip[0] - r, tip[1] - r, tip[0] + r, tip[1] + r], fill=fill)


def _legs(draw, cx, cy, offset, fill):
    for dx in (-8, -3, 3, 8):
        leg_off = offset if dx > 0 else -offset
        draw.line([(cx + dx, cy), (cx + dx + leg_off, cy + 10)], fill=fill, width=4)


def _draw_idle(draw, skin, frame):
    fill, outline, eye = skin["fill"], skin["outline"], skin["eye"]
    cx, cy = 26, 40
    draw.ellipse([cx - 16, cy - 10, cx + 16, cy + 10], fill=fill, outline=outline)
    _head(draw, cx + 18, cy - 8, fill, outline, eye)
    tip_x = cx - 20 + [0, 2, 4, 2][frame]
    tip_y = cy - 2 + [0, -2, 0, 2][frame]
    _tail(draw, (cx - 14, cy + 2), (tip_x, tip_y), fill)


def _draw_walk(draw, skin, frame):
    fill, outline, eye = skin["fill"], skin["outline"], skin["eye"]
    bob = [0, -1, 0, 1, 0, -1][frame]
    cx, cy = 26, 40 + bob
    draw.ellipse([cx - 16, cy - 10, cx + 16, cy + 10], fill=fill, outline=outline)
    _head(draw, cx + 18, cy - 8, fill, outline, eye)
    leg_offset = [3, 1, -1, -3, -1, 1][frame]
    _legs(draw, cx, cy + 8, leg_offset, fill)
    _tail(draw, (cx - 14, cy + 2), (cx - 22, cy - 6 + bob), fill)


def _draw_sleep(draw, skin, frame):
    fill, outline, eye = skin["fill"], skin["outline"], skin["eye"]
    cx, cy = 30, 44
    draw.ellipse([cx - 18, cy - 12, cx + 18, cy + 12], fill=fill, outline=outline)
    hx, hy = cx + 12, cy - 4
    draw.ellipse([hx - 8, hy - 8, hx + 8, hy + 8], fill=fill, outline=outline)
    _ear(draw, hx - 4, hy - 7, 3, 4, fill, outline)
    _ear(draw, hx + 4, hy - 7, 3, 4, fill, outline)
    for i in range(frame + 1):
        zx, zy = hx + 8 + i * 6, hy - 10 - i * 6
        draw.text((zx, zy), "z", fill=fill)


def _draw_sit(draw, skin, frame):
    fill, outline, eye = skin["fill"], skin["outline"], skin["eye"]
    sway = [0, 1, 0, -1][frame]
    cx, cy = 32 + sway, 42
    draw.ellipse([cx - 12, cy - 16, cx + 12, cy + 16], fill=fill, outline=outline)
    _head(draw, cx, cy - 20, fill, outline, eye)
    _tail(draw, (cx - 10, cy + 14), (cx - 18, cy + 4), fill)


DRAWERS = {"idle": _draw_idle, "walk": _draw_walk, "sleep": _draw_sleep, "sit": _draw_sit}


def render_strip(anim: str, skin_name: str) -> Image.Image:
    skin = SKINS[skin_name]
    frames = ANIMATIONS[anim]["frames"]
    strip = Image.new("RGBA", (FRAME_SIZE * frames, FRAME_SIZE), (0, 0, 0, 0))
    drawer = DRAWERS[anim]
    for i in range(frames):
        frame = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        drawer(ImageDraw.Draw(frame), skin, i)
        strip.paste(frame, (i * FRAME_SIZE, 0), frame)
    return strip


def write_meta(skin_dir: Path) -> None:
    lines = [f"frame_size = {FRAME_SIZE}", ""]
    for anim, cfg in ANIMATIONS.items():
        lines.append(f"[{anim}]")
        lines.append(f"frames = {cfg['frames']}")
        lines.append(f"fps = {cfg['fps']}")
        lines.append("")
    (skin_dir / "meta.toml").write_text("\n".join(lines))


def generate(out_dir: Path = ASSETS_DIR) -> None:
    for skin_name in SKINS:
        skin_dir = out_dir / skin_name
        skin_dir.mkdir(parents=True, exist_ok=True)
        for anim in ANIMATIONS:
            render_strip(anim, skin_name).save(skin_dir / f"{anim}.png")
        write_meta(skin_dir)


def main() -> int:
    generate()
    print(f"Generated placeholder sprites in {ASSETS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
