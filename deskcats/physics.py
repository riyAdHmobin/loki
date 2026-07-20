def step_walk(x: float, vx: float, dt: float, bounds: tuple[float, float]) -> tuple[float, float]:
    lo, hi = bounds
    x += vx * dt
    if x <= lo:
        x, vx = lo, -vx
    elif x >= hi:
        x, vx = hi, -vx
    return x, vx


def step_fall(
    y: float,
    vy: float,
    dt: float,
    floor_y: float,
    gravity: float = 1500.0,
    terminal: float = 1200.0,
) -> tuple[float, float, bool]:
    vy = min(vy + gravity * dt, terminal)
    y += vy * dt
    landed = y >= floor_y
    if landed:
        y, vy = floor_y, 0.0
    return y, vy, landed
