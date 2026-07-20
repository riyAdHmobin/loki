import random
from enum import Enum, auto


class State(Enum):
    IDLE = auto()
    WANDER = auto()
    SLEEP = auto()
    SIT = auto()
    DRAGGED = auto()
    FALLING = auto()
    STARTLED = auto()
    SOCIAL_APPROACH = auto()
    SOCIAL_NAP = auto()


IDLE_DURATION = (3.0, 15.0)
SLEEP_DURATION = (30.0, 180.0)
SIT_DURATION = (5.0, 12.0)

WEIGHTED_STATES = (State.WANDER, State.SLEEP, State.SIT, State.IDLE)
_EDGE_EPSILON = 1e-6
_ARRIVAL_EPSILON = 1.0


class Brain:
    """Personality-weighted state machine. No Qt; drives via tick(dt, context)."""

    def __init__(self, weights: dict[str, float], rng: random.Random, bounds: tuple[float, float]):
        self.weights = weights
        self.rng = rng
        self.bounds = bounds
        self.wander_target_x: float | None = None

        self.state = State.IDLE
        self.state_duration = self.rng.uniform(*IDLE_DURATION)
        self.state_elapsed = self.rng.uniform(0.0, self.state_duration)

    def _pick_next_state(self, exclude: State | None = None) -> State:
        candidates = [s for s in WEIGHTED_STATES if s is not exclude] or list(WEIGHTED_STATES)
        weights = [self.weights.get(state.name.lower(), 0) for state in candidates]
        return self.rng.choices(candidates, weights=weights, k=1)[0]

    def _pick_duration(self, state: State) -> float | None:
        if state is State.IDLE:
            return self.rng.uniform(*IDLE_DURATION)
        if state is State.SLEEP:
            return self.rng.uniform(*SLEEP_DURATION)
        if state is State.SIT:
            return self.rng.uniform(*SIT_DURATION)
        return None  # WANDER ends on arrival/edge, not on a timer

    def force(self, state: State) -> None:
        """Externally impose a state (interaction states Brain doesn't drive itself)."""
        self._enter(state)

    def _enter(self, state: State) -> None:
        self.state = state
        self.state_elapsed = 0.0
        self.state_duration = self._pick_duration(state)
        if state is State.WANDER:
            self.wander_target_x = self.rng.uniform(*self.bounds)

    def tick(self, dt: float, context: dict) -> State:
        self.state_elapsed += dt

        if self.state is State.WANDER:
            x = context.get("x")
            lo, hi = self.bounds
            at_target = (
                x is not None
                and self.wander_target_x is not None
                and abs(x - self.wander_target_x) < _ARRIVAL_EPSILON
            )
            at_edge = x is not None and (x <= lo + _EDGE_EPSILON or x >= hi - _EDGE_EPSILON)
            if at_target or at_edge:
                self._enter(self._pick_next_state(exclude=self.state))
        elif self.state_duration is not None and self.state_elapsed >= self.state_duration:
            self._enter(self._pick_next_state(exclude=self.state))

        return self.state
