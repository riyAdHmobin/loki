import random

from deskcats.social import Registry
from deskcats.state_machine import SOCIAL_STATES, Brain, State

LOKI_WEIGHTS = {"wander": 45, "sleep": 10, "sit": 20, "idle": 25}
MIKE_WEIGHTS = {"wander": 25, "sleep": 30, "sit": 25, "idle": 20}

BOUNDS = (0.0, 800.0)
SPEED = 80.0
DT = 0.1
TICKS = 50_000
MIN_COOLDOWN_S = 60.0


def _target_x(brain: Brain) -> float | None:
    if brain.state is State.WANDER:
        return brain.wander_target_x
    if brain.state in SOCIAL_STATES:
        return brain.social_target_x
    return None


def _step_toward(x: float, target: float | None, dt: float) -> float:
    if target is None:
        return x
    remaining = target - x
    direction = 1.0 if remaining >= 0 else -1.0
    step = min(abs(remaining), SPEED * dt)
    return max(BOUNDS[0], min(BOUNDS[1], x + direction * step))


def _simulate(seed: int, ticks: int = TICKS):
    brain_a = Brain(LOKI_WEIGHTS, random.Random(seed), BOUNDS)
    brain_b = Brain(MIKE_WEIGHTS, random.Random(seed + 1), BOUNDS)
    x_a, x_b = 200.0, 600.0

    registry = Registry()
    registry.update("a", x_a, brain_a.state)
    registry.update("b", x_b, brain_b.state)

    social_ticks = 0
    nap_seen = False
    episodes = {"a": [], "b": []}
    in_social = {"a": False, "b": False}
    episode_start = {"a": None, "b": None}

    for i in range(ticks):
        other_a = registry.other_of("a")
        other_b = registry.other_of("b")

        state_a = brain_a.tick(DT, {"x": x_a, "other_x": other_a.x, "other_state": other_a.state})
        state_b = brain_b.tick(DT, {"x": x_b, "other_x": other_b.x, "other_state": other_b.state})

        x_a = _step_toward(x_a, _target_x(brain_a), DT)
        x_b = _step_toward(x_b, _target_x(brain_b), DT)

        registry.update("a", x_a, state_a)
        registry.update("b", x_b, state_b)

        for key, state in (("a", state_a), ("b", state_b)):
            now_social = state in SOCIAL_STATES
            if now_social and not in_social[key]:
                episode_start[key] = i
                in_social[key] = True
            elif not now_social and in_social[key]:
                episodes[key].append((episode_start[key], i))
                in_social[key] = False

        if state_a in SOCIAL_STATES:
            social_ticks += 1
        if state_b in SOCIAL_STATES:
            social_ticks += 1
        if state_a is State.SOCIAL_NAP or state_b is State.SOCIAL_NAP:
            nap_seen = True

    return nap_seen, social_ticks, ticks * 2, episodes


def test_social_nap_occurs_over_a_long_simulation():
    nap_seen, *_ = _simulate(seed=1)
    assert nap_seen


def test_social_states_are_a_minority_of_total_time():
    _, social_ticks, total_ticks, _ = _simulate(seed=2)
    assert social_ticks / total_ticks <= 0.25


def test_cooldowns_are_respected_between_social_episodes():
    *_, episodes = _simulate(seed=4)
    min_cooldown_ticks = MIN_COOLDOWN_S / DT
    for eps in episodes.values():
        for (_, end_tick), (start_tick, _) in zip(eps, eps[1:]):
            assert (start_tick - end_tick) >= min_cooldown_ticks - 1
