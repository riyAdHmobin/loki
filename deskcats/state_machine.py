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
SOCIAL_STATES = (State.SOCIAL_APPROACH, State.SOCIAL_NAP)

SOCIAL_APPROACH_CHANCE = 0.10
SOCIAL_APPROACH_STOP_DISTANCE = 40.0
SOCIAL_NAP_CHANCE = 0.30
SOCIAL_NAP_TRIGGER_DISTANCE = 150.0
SOCIAL_NAP_STOP_DISTANCE = 30.0
SOCIAL_COOLDOWN_RANGE = (60.0, 180.0)

_EDGE_EPSILON = 1e-6
_ARRIVAL_EPSILON = 1.0


class Brain:
    """Personality-weighted state machine. No Qt; drives via tick(dt, context)."""

    def __init__(self, weights: dict[str, float], rng: random.Random, bounds: tuple[float, float]):
        self.weights = weights
        self.rng = rng
        self.bounds = bounds
        self.wander_target_x: float | None = None
        self.social_target_x: float | None = None
        self.cooldown_remaining = 0.0
        self._social_arrival_state: State | None = None

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
        return None  # WANDER/social states end on arrival/edge, not on a timer

    def force(self, state: State) -> None:
        """Externally impose a state (interaction states Brain doesn't drive itself)."""
        self._enter(state)

    def _enter(self, state: State) -> None:
        self.state = state
        self.state_elapsed = 0.0
        self.state_duration = self._pick_duration(state)
        if state is State.WANDER:
            self.wander_target_x = self.rng.uniform(*self.bounds)

    def _enter_social(self, state: State, other_x: float, stop_distance: float, arrival_state: State) -> None:
        self.state = state
        self.state_elapsed = 0.0
        self.state_duration = None
        self._social_arrival_state = arrival_state
        offset = stop_distance if self.rng.random() < 0.5 else -stop_distance
        lo, hi = self.bounds
        self.social_target_x = max(lo, min(hi, other_x + offset))

    def _end_social_interaction(self, next_state: State) -> None:
        self.social_target_x = None
        self._social_arrival_state = None
        self.cooldown_remaining = self.rng.uniform(*SOCIAL_COOLDOWN_RANGE)
        self._enter(next_state)

    def _try_start_social_approach(self, other_x: float | None) -> bool:
        if other_x is None or self.cooldown_remaining > 0.0:
            return False
        if self.rng.random() >= SOCIAL_APPROACH_CHANCE:
            return False
        self._enter_social(State.SOCIAL_APPROACH, other_x, SOCIAL_APPROACH_STOP_DISTANCE, State.SIT)
        return True

    def _try_start_social_nap(self, self_x: float | None, other_x: float | None, other_state: State | None) -> bool:
        if other_x is None or other_state is not State.SLEEP or self.cooldown_remaining > 0.0:
            return False
        if self_x is None or abs(self_x - other_x) > SOCIAL_NAP_TRIGGER_DISTANCE:
            return False
        if self.rng.random() >= SOCIAL_NAP_CHANCE:
            return False
        self._enter_social(State.SOCIAL_NAP, other_x, SOCIAL_NAP_STOP_DISTANCE, State.SLEEP)
        return True

    def tick(self, dt: float, context: dict) -> State:
        if self.cooldown_remaining > 0.0:
            self.cooldown_remaining = max(0.0, self.cooldown_remaining - dt)

        self.state_elapsed += dt
        other_x = context.get("other_x")
        other_state = context.get("other_state")

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
                if not self._try_start_social_nap(x, other_x, other_state):
                    self._enter(self._pick_next_state(exclude=self.state))
        elif self.state in SOCIAL_STATES:
            x = context.get("x")
            if (
                x is not None
                and self.social_target_x is not None
                and abs(x - self.social_target_x) < _ARRIVAL_EPSILON
                and self._social_arrival_state is not None
            ):
                self._end_social_interaction(self._social_arrival_state)
        elif self.state_duration is not None and self.state_elapsed >= self.state_duration:
            if self.state is State.IDLE and self._try_start_social_approach(other_x):
                return self.state
            self._enter(self._pick_next_state(exclude=self.state))

        return self.state
