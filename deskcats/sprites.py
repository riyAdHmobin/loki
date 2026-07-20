import tomllib
from pathlib import Path

from PyQt6.QtGui import QImage, QPixmap, QTransform

from .spots import Spot, apply_spots


class SpriteSet:
    def __init__(self, skin_dir: Path, spots: list[Spot] | None = None):
        self.skin_dir = Path(skin_dir)
        self.spots = spots
        meta = tomllib.loads((self.skin_dir / "meta.toml").read_text())
        self.frame_size: int = meta["frame_size"]
        self.animations: dict[str, dict] = {}
        for name, cfg in meta.items():
            if name == "frame_size":
                continue
            self.animations[name] = self._load_animation(name, cfg)

    def _load_animation(self, name: str, cfg: dict) -> dict:
        sheet = QPixmap(str(self.skin_dir / f"{name}.png"))
        frames = [
            sheet.copy(i * self.frame_size, 0, self.frame_size, self.frame_size)
            for i in range(cfg["frames"])
        ]
        if self.spots:
            frames = [self._apply_spots(f) for f in frames]
        flip = QTransform().scale(-1, 1)
        flipped = [f.transformed(flip) for f in frames]
        return {"frames": frames, "flipped": flipped, "fps": cfg["fps"]}

    def _apply_spots(self, frame: QPixmap) -> QPixmap:
        image = frame.toImage().convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        return QPixmap.fromImage(apply_spots(image, self.spots))

    def frame(self, anim: str, index: int, facing_left: bool = False) -> QPixmap:
        data = self.animations[anim]
        frames = data["flipped"] if facing_left else data["frames"]
        return frames[index % len(frames)]

    def frame_count(self, anim: str) -> int:
        return len(self.animations[anim]["frames"])

    def fps(self, anim: str) -> int:
        return self.animations[anim]["fps"]
