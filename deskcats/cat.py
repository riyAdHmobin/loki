import random

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QApplication, QWidget

from .sprites import SpriteSet
from .state_machine import Brain, State

MOVE_INTERVAL_MS = 33
SLEEP_ANIM_INTERVAL_MS = 500

STATE_ANIMATION = {
    State.WANDER: "walk",
    State.IDLE: "idle",
    State.SIT: "sit",
    State.SLEEP: "sleep",
}


class Cat(QWidget):
    def __init__(
        self,
        name: str,
        sprite_set: SpriteSet,
        x: float,
        y: float,
        speed: float,
        weights: dict[str, float],
        rng: random.Random | None = None,
    ):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.name = name
        self.sprites = sprite_set
        self.frame_size = sprite_set.frame_size
        self.setFixedSize(self.frame_size, self.frame_size)

        self.x = x
        self.y = y
        self.base_speed = abs(speed)
        self.facing_left = False

        self.rng = rng or random.Random()
        self.brain = Brain(weights, self.rng, self._bounds())

        self.anim_name = STATE_ANIMATION[self.brain.state]
        self.anim_index = 0

        self.move(int(self.x), int(self.y))

        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self._tick_movement)
        self.move_timer.start(MOVE_INTERVAL_MS)

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick_animation)
        self._restart_anim_timer()

    def _restart_anim_timer(self) -> None:
        if self.brain.state is State.SLEEP:
            interval = SLEEP_ANIM_INTERVAL_MS
        else:
            fps = self.sprites.fps(self.anim_name)
            interval = max(1, int(1000 / fps))
        self.anim_timer.start(interval)

    def _bounds(self) -> tuple[float, float]:
        width = QApplication.primaryScreen().availableGeometry().width()
        return 0.0, float(width - self.frame_size)

    def floor_y(self) -> float:
        return float(QApplication.primaryScreen().availableGeometry().bottom() - self.frame_size)

    def _tick_movement(self) -> None:
        dt = self.move_timer.interval() / 1000.0
        prev_state = self.brain.state
        state = self.brain.tick(dt, {"x": self.x})

        if state is State.WANDER and self.brain.wander_target_x is not None:
            lo, hi = self._bounds()
            remaining = self.brain.wander_target_x - self.x
            direction = 1.0 if remaining >= 0 else -1.0
            step = min(abs(remaining), self.base_speed * dt)
            self.x = max(lo, min(hi, self.x + direction * step))
            self.facing_left = direction < 0

        if state is not prev_state:
            self._on_state_changed(state)

        self.move(int(self.x), int(self.y))
        self.update()

    def _on_state_changed(self, state: State) -> None:
        self.anim_name = STATE_ANIMATION.get(state, self.anim_name)
        self.anim_index = 0
        self._restart_anim_timer()

    def _tick_animation(self) -> None:
        self.anim_index = (self.anim_index + 1) % self.sprites.frame_count(self.anim_name)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        pix = self.sprites.frame(self.anim_name, self.anim_index, self.facing_left)
        painter.drawPixmap(0, 0, pix)
