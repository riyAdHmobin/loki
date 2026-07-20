from pathlib import Path

from PIL import Image

from deskcats.gen_placeholder_art import ANIMATIONS, FRAME_SIZE, SKINS, generate


def test_generate_produces_all_strips_and_meta(tmp_path: Path):
    generate(out_dir=tmp_path)

    for skin_name in SKINS:
        skin_dir = tmp_path / skin_name
        assert (skin_dir / "meta.toml").exists()
        for anim, cfg in ANIMATIONS.items():
            with Image.open(skin_dir / f"{anim}.png") as img:
                assert img.width == cfg["frames"] * FRAME_SIZE
                assert img.height == FRAME_SIZE
                assert img.mode == "RGBA"
