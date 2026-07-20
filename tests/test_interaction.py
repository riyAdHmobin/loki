from pathlib import Path

from deskcats.cat import GRAVITY_PX_S2, TERMINAL_VELOCITY_PX_S
from deskcats.physics import step_fall
from deskcats.sprites import SpriteSet

ASSETS_SKINS_DIR = Path(__file__).resolve().parent.parent / "deskcats" / "assets" / "skins"


def test_fall_accelerates_with_configured_gravity_and_terminal_velocity():
    y, vy, landed = step_fall(
        0.0, 0.0, 1.0, floor_y=100_000.0, gravity=GRAVITY_PX_S2, terminal=TERMINAL_VELOCITY_PX_S
    )
    assert vy == TERMINAL_VELOCITY_PX_S
    assert landed is False


def test_fall_lands_and_clamps_to_floor():
    y, vy, landed = step_fall(
        990.0, 0.0, 1.0, floor_y=1000.0, gravity=GRAVITY_PX_S2, terminal=TERMINAL_VELOCITY_PX_S
    )
    assert landed is True
    assert y == 1000.0
    assert vy == 0.0


def test_sprite_frame_has_a_usable_alpha_mask():
    sprite_set = SpriteSet(ASSETS_SKINS_DIR / "loki-black")
    frame = sprite_set.frame("idle", 0)
    mask = frame.mask()
    assert not mask.isNull()
    assert mask.size() == frame.size()
