from deskcats.physics import step_fall, step_walk


def test_step_walk_moves_within_bounds():
    x, vx = step_walk(10.0, 5.0, 1.0, (0.0, 100.0))
    assert x == 15.0
    assert vx == 5.0


def test_step_walk_bounces_at_upper_bound():
    x, vx = step_walk(98.0, 5.0, 1.0, (0.0, 100.0))
    assert x == 100.0
    assert vx == -5.0


def test_step_walk_bounces_at_lower_bound():
    x, vx = step_walk(2.0, -5.0, 1.0, (0.0, 100.0))
    assert x == 0.0
    assert vx == 5.0


def test_step_fall_accelerates_downward():
    y, vy, landed = step_fall(0.0, 0.0, 0.1, floor_y=1000.0, gravity=1000.0)
    assert vy == 100.0
    assert y == 10.0
    assert landed is False


def test_step_fall_lands_on_floor():
    y, vy, landed = step_fall(995.0, 200.0, 1.0, floor_y=1000.0, gravity=1500.0, terminal=1200.0)
    assert landed is True
    assert y == 1000.0
    assert vy == 0.0


def test_step_fall_respects_terminal_velocity():
    y, vy, landed = step_fall(0.0, 1190.0, 1.0, floor_y=100000.0, gravity=1500.0, terminal=1200.0)
    assert vy == 1200.0
