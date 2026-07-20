import random
from dataclasses import dataclass
from datetime import date

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter


@dataclass(frozen=True)
class Spot:
    cx: float  # fraction of frame width
    cy: float  # fraction of frame height
    rx: float  # fraction of frame size
    ry: float  # fraction of frame size
    rotation: float  # degrees


def generate_spots(seed: int, n_min: int = 2, n_max: int = 4) -> list[Spot]:
    rng = random.Random(seed)
    count = rng.randint(n_min, n_max)
    return [
        Spot(
            cx=rng.uniform(0.25, 0.75),
            cy=rng.uniform(0.25, 0.75),
            rx=rng.uniform(0.08, 0.18),
            ry=rng.uniform(0.08, 0.18),
            rotation=rng.uniform(0.0, 360.0),
        )
        for _ in range(count)
    ]


def resolve_seed(spot_seed: str) -> int:
    if spot_seed == "daily":
        today = date.today()
        return today.year * 10000 + today.month * 100 + today.day
    if spot_seed == "random":
        return random.SystemRandom().randint(0, 2**31 - 1)
    if spot_seed.startswith("fixed:"):
        return int(spot_seed.split(":", 1)[1])
    raise ValueError(f"invalid spot_seed: {spot_seed!r}")


def apply_spots(frame_qimage: QImage, spots: list[Spot]) -> QImage:
    size = frame_qimage.size()
    overlay = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
    overlay.fill(0)

    paint_spots = QPainter(overlay)
    paint_spots.setRenderHint(QPainter.RenderHint.Antialiasing)
    paint_spots.setPen(Qt.PenStyle.NoPen)
    paint_spots.setBrush(QColor(0, 0, 0, 255))
    for spot in spots:
        cx, cy = spot.cx * size.width(), spot.cy * size.height()
        rx, ry = spot.rx * size.width(), spot.ry * size.height()
        paint_spots.save()
        paint_spots.translate(cx, cy)
        paint_spots.rotate(spot.rotation)
        paint_spots.drawEllipse(QRectF(-rx, -ry, rx * 2, ry * 2))
        paint_spots.restore()
    paint_spots.end()

    base = frame_qimage.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    clip = QPainter(overlay)
    clip.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    clip.drawImage(0, 0, base)
    clip.end()

    result = QImage(base)
    composite = QPainter(result)
    composite.drawImage(0, 0, overlay)
    composite.end()
    return result
