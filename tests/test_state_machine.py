import random

from deskcats.state_machine import Brain, State

LOKI_WEIGHTS = {"wander": 45, "sleep": 10, "sit": 20, "idle": 25}
MIKE_WEIGHTS = {"wander": 25, "sleep": 30, "sit": 25, "idle": 20}

BOUNDS = (0.0, 800.0)
SPEED = 80.0
DT = 0.1
TICKS = 10_000


def _simulate(weights: dict[str, float], seed: int):
    rng = random.Random(seed)
    brain = Brain(weights, rng, BOUNDS)
    x = (BOUNDS[0] + BOUNDS[1]) / 2

    time_in_state = {state: 0.0 for state in (State.WANDER, State.SLEEP, State.SIT, State.IDLE)}
    max_dwell = {state: 0.0 for state in time_in_state}
    dwell = 0.0
    prev_state = brain.state

    for _ in range(TICKS):
        state = brain.tick(DT, {"x": x})

        if state is State.WANDER and brain.wander_target_x is not None:
            remaining = brain.wander_target_x - x
            direction = 1.0 if remaining >= 0 else -1.0
            step = min(abs(remaining), SPEED * DT)
            x = max(BOUNDS[0], min(BOUNDS[1], x + direction * step))

        if state is prev_state:
            dwell += DT
        else:
            max_dwell[prev_state] = max(max_dwell[prev_state], dwell)
            dwell = DT
            prev_state = state

        time_in_state[state] += DT

    max_dwell[prev_state] = max(max_dwell[prev_state], dwell)
    return time_in_state, max_dwell


def test_loki_wanders_more_than_mike():
    loki_time, _ = _simulate(LOKI_WEIGHTS, seed=1)
    mike_time, _ = _simulate(MIKE_WEIGHTS, seed=2)
    loki_total, mike_total = sum(loki_time.values()), sum(mike_time.values())

    assert (loki_time[State.WANDER] / loki_total) > (mike_time[State.WANDER] / mike_total)


def test_mike_sleeps_more_than_loki():
    loki_time, _ = _simulate(LOKI_WEIGHTS, seed=1)
    mike_time, _ = _simulate(MIKE_WEIGHTS, seed=2)
    loki_total, mike_total = sum(loki_time.values()), sum(mike_time.values())

    assert (mike_time[State.SLEEP] / mike_total) > (loki_time[State.SLEEP] / loki_total)


def test_all_weighted_states_are_reachable():
    for weights, seed in ((LOKI_WEIGHTS, 3), (MIKE_WEIGHTS, 4)):
        time_in_state, _ = _simulate(weights, seed)
        assert all(t > 0 for t in time_in_state.values())


def test_no_state_lasts_forever():
    for weights, seed in ((LOKI_WEIGHTS, 5), (MIKE_WEIGHTS, 6)):
        _, max_dwell = _simulate(weights, seed)
        assert max_dwell[State.SLEEP] <= 180.0 + DT
        assert max_dwell[State.SIT] <= 12.0 + DT
        assert max_dwell[State.IDLE] <= 15.0 + DT
        traversal_time = (BOUNDS[1] - BOUNDS[0]) / SPEED
        assert max_dwell[State.WANDER] <= traversal_time + DT
