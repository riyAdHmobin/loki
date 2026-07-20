import argparse
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from .cat import Cat
from .config import BASE_SPEED_PX_PER_S, load_config
from .social import Registry
from .spots import generate_spots, resolve_seed
from .sprites import SpriteSet

ASSETS_SKINS_DIR = Path(__file__).resolve().parent.parent / "assets" / "skins"


def _spawn_cats(config: dict, app: QApplication) -> list[Cat]:
    geo = app.primaryScreen().availableGeometry()
    registry = Registry()
    cats = []
    for name, profile in config["cats"].items():
        spots = None
        if profile.get("spots"):
            seed = resolve_seed(profile.get("spot_seed", "daily"))
            spots = generate_spots(seed)
        sprite_set = SpriteSet(ASSETS_SKINS_DIR / profile["skin"], spots=spots)
        frame_size = sprite_set.frame_size
        x = geo.width() * profile["start_frac"] - frame_size / 2
        y = geo.bottom() - frame_size
        speed = profile["speed"] * BASE_SPEED_PX_PER_S
        cats.append(Cat(name, sprite_set, x, y, speed, profile["weights"], registry=registry))

    for cat in cats:
        cat.sibling = next((other for other in cats if other is not cat), None)
    return cats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="deskcats")
    parser.add_argument("--demo-slide", action="store_true", help="constant-velocity motion demo")
    parser.add_argument("--smoke-test", action="store_true", help="headless construction check")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    app = QApplication(sys.argv[:1])
    config = load_config()
    cats = _spawn_cats(config, app)

    if args.smoke_test:
        for cat in cats:
            for _ in range(100):
                cat._tick_movement()
        return 0

    for cat in cats:
        cat.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
