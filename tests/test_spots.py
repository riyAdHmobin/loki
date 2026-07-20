from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter

from deskcats.spots import apply_spots, generate_spots, resolve_seed


def test_generate_spots_is_reproducible_with_fixed_seed():
    assert generate_spots(seed=42) == generate_spots(seed=42)


def test_generate_spots_differs_across_seeds():
    assert generate_spots(seed=1) != generate_spots(seed=2)


def test_generate_spots_respects_count_bounds():
    for seed in range(20):
        spots = generate_spots(seed=seed, n_min=2, n_max=4)
        assert 2 <= len(spots) <= 4


def test_resolve_seed_daily_is_stable_and_fixed_is_exact():
    assert resolve_seed("daily") == resolve_seed("daily")
    assert resolve_seed("fixed:123") == 123


def _silhouette_image(size: int = 64) -> QImage:
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    painter = QPainter(image)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 255))
    painter.drawEllipse(QRectF(8, 8, 48, 48))
    painter.end()
    return image


def test_apply_spots_never_adds_alpha_outside_base_silhouette():
    base = _silhouette_image()
    spots = generate_spots(seed=7, n_min=4, n_max=4)
    spotted = apply_spots(base, spots)

    assert spotted.size() == base.size()
    for y in range(base.height()):
        for x in range(base.width()):
            if base.pixelColor(x, y).alpha() == 0:
                assert spotted.pixelColor(x, y).alpha() == 0
