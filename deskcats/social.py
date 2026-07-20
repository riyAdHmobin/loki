from dataclasses import dataclass

from .state_machine import State


@dataclass(frozen=True)
class CatStatus:
    x: float
    state: State
    speed: float


class Registry:
    """Shared, Qt-free view of both cats' positions/states for social behaviors."""

    def __init__(self):
        self._status: dict[str, CatStatus] = {}

    def update(self, name: str, x: float, state: State, speed: float = 0.0) -> None:
        self._status[name] = CatStatus(x=x, state=state, speed=speed)

    def other_of(self, name: str) -> CatStatus | None:
        for other_name, status in self._status.items():
            if other_name != name:
                return status
        return None
