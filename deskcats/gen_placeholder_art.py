from pathlib import Path

from PIL import Image, ImageDraw

FRAME_SIZE = 64

PINK = (0xF2, 0xB8, 0xC6, 255)
DOT = (0x1A, 0x1A, 0x1A, 255)

SKINS = {
    "loki-black": {"fill": (0x11, 0x11, 0x11, 255), "outline": None, "eye": (0xE8, 0xA1, 0x3C, 255)},
    "mike-white": {"fill": (0xF2, 0xF2, 0xEF, 255), "outline": (0x4A, 0x4A, 0x4A, 255), "eye": (0x5A, 0xC8, 0xE8, 255)},
}

ANIMATIONS = {
    "idle": {"frames": 4, "fps": 10},
    "walk": {"frames": 6, "fps": 10},
    "sleep": {"frames": 4, "fps": 4},
    "sit": {"frames": 4, "fps": 10},
}

ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "skins"

CX = 32  # front-facing pose default center x


def _ear(draw, apex, base_l, base_r, fill, outline):
    draw.polygon([apex, base_l, base_r], fill=fill, outline=outline)
    inset = 0.45
    inner_apex = (apex[0], apex[1] + (base_l[1] - apex[1]) * inset)
    inner_l = (base_l[0] + (apex[0] - base_l[0]) * inset * 0.6, base_l[1] - 2)
    inner_r = (base_r[0] + (apex[0] - base_r[0]) * inset * 0.6, base_r[1] - 2)
    draw.polygon([inner_apex, inner_l, inner_r], fill=PINK)


def _whisker_nub(draw, cx, cy, side, fill, outline):
    x0 = cx + side * 20
    x1 = cx + side * 25
    draw.rectangle([min(x0, x1), cy - 3, max(x0, x1), cy + 3], fill=fill, outline=outline)


def _shadow(draw, cx, cy):
    draw.ellipse([cx - 18, cy - 4, cx + 18, cy + 4], fill=(0, 0, 0, 60))


def _tail_curl(draw, base, mid, tip, fill, width=8):
    draw.line([base, mid, tip], fill=fill, width=width, joint="curve")
    r = width / 2
    for pt in (base, mid):
        draw.ellipse([pt[0] - r, pt[1] - r, pt[0] + r, pt[1] + r], fill=fill)
    draw.ellipse([tip[0] - r, tip[1] - r, tip[0] + r, tip[1] + r], fill=fill)


def _front_pose(draw, skin, *, cx=CX, cy, bob, tail_lift, eyes_closed, mouth, blush):
    fill, outline, eye = skin["fill"], skin["outline"], skin["eye"]

    _shadow(draw, cx, 61)

    # tail, drawn first so it sits behind the body on the right side
    _tail_curl(
        draw,
        (cx + 17, cy + 16),
        (cx + 29, cy + 6 - tail_lift),
        (cx + 24, cy - 6 - tail_lift),
        fill,
    )

    # body
    draw.rectangle([cx - 19, cy - 2 + bob, cx + 19, cy + 22], fill=fill, outline=outline)
    # front paws peeking under the body
    draw.rectangle([cx - 13, cy + 20, cx - 5, cy + 26], fill=fill, outline=outline)
    draw.rectangle([cx + 5, cy + 20, cx + 13, cy + 26], fill=fill, outline=outline)

    # head
    head_top = cy - 24
    draw.rectangle([cx - 17, head_top, cx + 17, cy - 2], fill=fill, outline=outline)

    # ears, overlapping into the head top so there's no seam
    _ear(draw, (cx - 11, head_top - 10), (cx - 19, head_top + 4), (cx - 3, head_top + 4), fill, outline)
    _ear(draw, (cx + 11, head_top - 10), (cx + 3, head_top + 4), (cx + 19, head_top + 4), fill, outline)

    # whisker nubs
    _whisker_nub(draw, cx, head_top + 12, -1, fill, outline)
    _whisker_nub(draw, cx, head_top + 12, 1, fill, outline)

    # blush (mike only, warms up the flat white)
    if blush:
        draw.ellipse([cx - 16, head_top + 13, cx - 10, head_top + 17], fill=PINK)
        draw.ellipse([cx + 10, head_top + 13, cx + 16, head_top + 17], fill=PINK)

    # eyes
    ey = head_top + 10
    if eyes_closed:
        draw.line([(cx - 9, ey), (cx - 4, ey)], fill=DOT, width=2)
        draw.line([(cx + 4, ey), (cx + 9, ey)], fill=DOT, width=2)
    else:
        draw.rectangle([cx - 9, ey - 3, cx - 4, ey + 3], fill=eye)
        draw.rectangle([cx + 4, ey - 3, cx + 9, ey + 3], fill=eye)

    # mouth: three small dots
    my = head_top + 18
    if mouth == "sleep":
        pass
    else:
        for dx in (-4, 0, 4):
            draw.rectangle([cx + dx - 1, my - 1, cx + dx + 1, my + 1], fill=DOT)


def _draw_idle(draw, skin, frame):
    bob = [0, -1, 0, 1][frame]
    blink = frame == 2
    _front_pose(
        draw,
        skin,
        cy=38,
        bob=bob,
        tail_lift=[0, 2, 4, 2][frame],
        eyes_closed=blink,
        mouth="idle",
        blush=skin is SKINS["mike-white"],
    )


def _draw_sit(draw, skin, frame):
    sway = [0, 1, 0, -1][frame]
    _front_pose(
        draw,
        skin,
        cx=CX + sway,
        cy=40,
        bob=0,
        tail_lift=[1, 3, 1, -1][frame],
        eyes_closed=False,
        mouth="sit",
        blush=skin is SKINS["mike-white"],
    )


def _draw_sleep(draw, skin, frame):
    _front_pose(
        draw,
        skin,
        cy=46,
        bob=6,
        tail_lift=-4,
        eyes_closed=True,
        mouth="sleep",
        blush=skin is SKINS["mike-white"],
    )
    fill = skin["fill"]
    for i in range(frame + 1):
        zx, zy = CX + 24 + i * 5, 8 - i * 5
        draw.text((zx, zy), "z", fill=fill)


def _head_side(draw, hx, hy, fill, outline, eye):
    draw.rectangle([hx - 9, hy - 8, hx + 9, hy + 9], fill=fill, outline=outline)
    _ear(draw, (hx - 6, hy - 16), (hx - 11, hy - 8), (hx - 1, hy - 8), fill, outline)
    _ear(draw, (hx + 5, hy - 16), (hx, hy - 8), (hx + 10, hy - 8), fill, outline)
    draw.rectangle([hx + 2, hy - 2, hx + 6, hy + 2], fill=eye)
    draw.rectangle([hx + 5, hy + 4, hx + 8, hy + 5], fill=DOT)


def _legs_side(draw, cx, cy, offset, fill):
    for dx in (-8, -3, 3, 8):
        leg_off = offset if dx > 0 else -offset
        draw.line([(cx + dx, cy), (cx + dx + leg_off, cy + 10)], fill=fill, width=4)


def _draw_walk(draw, skin, frame):
    fill, outline, eye = skin["fill"], skin["outline"], skin["eye"]
    bob = [0, -1, 0, 1, 0, -1][frame]
    cx, cy = 26, 40 + bob
    _shadow(draw, cx, 58)
    draw.rectangle([cx - 16, cy - 10, cx + 16, cy + 10], fill=fill, outline=outline)
    _head_side(draw, cx + 18, cy - 8, fill, outline, eye)
    leg_offset = [3, 1, -1, -3, -1, 1][frame]
    _legs_side(draw, cx, cy + 8, leg_offset, fill)
    _tail_curl(draw, (cx - 14, cy + 2), (cx - 22, cy - 6 + bob), (cx - 26, cy - 14 + bob), fill, width=6)


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
