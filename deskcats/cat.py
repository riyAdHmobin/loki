import random

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QMouseEvent, QPainter
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QWidget

from .physics import step_fall
from .social import Registry
from .sprites import SpriteSet
from .state_machine import SOCIAL_STATES, Brain, State

MOVE_INTERVAL_MS = 33
SLEEP_ANIM_INTERVAL_MS = 500
STARTLED_DURATION_S = 1.0
STARTLED_FPS_MULTIPLIER = 2
SQUASH_DURATION_MS = 100
SQUASH_SCALE_Y = 0.8
CLICK_DRAG_THRESHOLD_PX = 4
GRAVITY_PX_S2 = 1500.0
TERMINAL_VELOCITY_PX_S = 1200.0
STARTLE_CHAIN_DISTANCE_PX = 100.0
STARTLE_CHAIN_DELAY_MS = 300
STEP_ASIDE_DISTANCE_PX = 20.0

STATE_ANIMATION = {
    State.WANDER: "walk",
    State.IDLE: "idle",
    State.SIT: "sit",
    State.SLEEP: "sleep",
    State.SOCIAL_APPROACH: "walk",
    State.SOCIAL_NAP: "walk",
}

BIOS = {
    "loki": "Solid black. Fast, restless, wanders a lot, sleeps little.",
    "mike": "White with ever-changing spots. Professional napper.",
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
        registry: Registry | None = None,
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
        self.vy = 0.0
        self.base_speed = abs(speed)
        self.facing_left = False

        self.dragging = False
        self.squashing = False
        self._press_global: QPoint | None = None
        self._press_offset: QPoint | None = None

        self.registry = registry
        self.sibling: "Cat | None" = None

        self.rng = rng or random.Random()
        self.brain = Brain(weights, self.rng, self._bounds())

        self.anim_name = STATE_ANIMATION[self.brain.state]
        self.anim_index = 0

        self.move(int(self.x), int(self.y))
        if self.registry is not None:
            self.registry.update(self.name, self.x, self.brain.state, self.base_speed)

        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self._tick_movement)
        self.move_timer.start(MOVE_INTERVAL_MS)

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick_animation)
        self._restart_anim_timer()
        self._update_mask()

    # -- animation / mask -------------------------------------------------

    def _restart_anim_timer(self) -> None:
        if self.brain.state is State.SLEEP:
            interval = SLEEP_ANIM_INTERVAL_MS
        else:
            fps = self.sprites.fps(self.anim_name)
            if self.brain.state is State.STARTLED:
                fps *= STARTLED_FPS_MULTIPLIER
            interval = max(1, int(1000 / fps))
        self.anim_timer.start(interval)

    def _update_mask(self) -> None:
        pix = self.sprites.frame(self.anim_name, self.anim_index, self.facing_left)
        self.setMask(pix.mask())

    def _reset_animation(self, anim_name: str) -> None:
        self.anim_name = anim_name
        self.anim_index = 0
        self._restart_anim_timer()
        self._update_mask()
        self.update()

    def _tick_animation(self) -> None:
        self.anim_index = (self.anim_index + 1) % self.sprites.frame_count(self.anim_name)
        self._update_mask()
        self.update()

    # -- geometry -----------------------------------------------------------

    def _bounds(self) -> tuple[float, float]:
        width = QApplication.primaryScreen().availableGeometry().width()
        return 0.0, float(width - self.frame_size)

    def floor_y(self) -> float:
        return float(QApplication.primaryScreen().availableGeometry().bottom() - self.frame_size)

    # -- brain-driven movement -----------------------------------------------

    def _other_status(self):
        return self.registry.other_of(self.name) if self.registry is not None else None

    def _sync_registry(self, state: State) -> None:
        if self.registry is not None:
            self.registry.update(self.name, self.x, state, self.base_speed)

    def _tick_movement(self) -> None:
        state = self.brain.state
        dt = self.move_timer.interval() / 1000.0

        if state is State.DRAGGED:
            self._sync_registry(state)
            return
        if state is State.FALLING:
            self._tick_falling(dt)
            self._sync_registry(self.brain.state)
            return
        if state is State.STARTLED:
            self.brain.tick(dt, {"x": self.x})
            if self.brain.state_elapsed >= STARTLED_DURATION_S:
                self.brain.force(State.IDLE)
                self._reset_animation(STATE_ANIMATION[State.IDLE])
            self._sync_registry(self.brain.state)
            return

        other = self._other_status()
        context = {"x": self.x}
        if other is not None:
            context["other_x"] = other.x
            context["other_state"] = other.state

        prev_state = state
        state = self.brain.tick(dt, context)

        target_x = None
        if state is State.WANDER:
            target_x = self.brain.wander_target_x
        elif state in SOCIAL_STATES:
            target_x = self.brain.social_target_x

        if target_x is not None:
            lo, hi = self._bounds()
            remaining = target_x - self.x
            direction = 1.0 if remaining >= 0 else -1.0
            step = min(abs(remaining), self.base_speed * dt)
            self.x = max(lo, min(hi, self.x + direction * step))
            self.facing_left = direction < 0

        if other is not None and state not in SOCIAL_STATES:
            self._maybe_step_aside(other, dt)

        if state is not prev_state:
            self._reset_animation(STATE_ANIMATION.get(state, self.anim_name))

        self.move(int(self.x), int(self.y))
        self._sync_registry(state)
        self.update()

    def _maybe_step_aside(self, other, dt: float) -> None:
        if other.state in SOCIAL_STATES:
            return
        distance = self.x - other.x
        if abs(distance) >= STEP_ASIDE_DISTANCE_PX:
            return
        if self.base_speed <= other.speed:
            return
        lo, hi = self._bounds()
        direction = 1.0 if distance >= 0 else -1.0
        step = self.base_speed * dt
        self.x = max(lo, min(hi, self.x + direction * step))
        self.facing_left = direction < 0

    def _tick_falling(self, dt: float) -> None:
        self.y, self.vy, landed = step_fall(
            self.y, self.vy, dt, self.floor_y(), gravity=GRAVITY_PX_S2, terminal=TERMINAL_VELOCITY_PX_S
        )
        self.move(int(self.x), int(self.y))
        if landed:
            self._land()

    def _land(self) -> None:
        self.vy = 0.0
        self.squashing = True
        QTimer.singleShot(SQUASH_DURATION_MS, self._end_squash)
        self.brain.force(State.IDLE)
        self._reset_animation(STATE_ANIMATION[State.IDLE])

    def _end_squash(self) -> None:
        self.squashing = False
        self.update()

    # -- mouse interaction ----------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._press_offset = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and self._press_offset is not None:
            current_global = event.globalPosition().toPoint()
            if not self.dragging:
                moved = (current_global - self._press_global).manhattanLength()
                if moved > CLICK_DRAG_THRESHOLD_PX:
                    self._start_drag()
            if self.dragging:
                self._drag_to(current_global)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self.dragging:
                self._end_drag()
            else:
                self._start_startled()
            self._press_global = None
            self._press_offset = None
        super().mouseReleaseEvent(event)

    def _start_drag(self) -> None:
        self.dragging = True
        self.brain.force(State.DRAGGED)
        self._reset_animation(STATE_ANIMATION[State.IDLE])

    def _drag_to(self, global_pos: QPoint) -> None:
        new_pos = global_pos - self._press_offset
        self.x, self.y = float(new_pos.x()), float(new_pos.y())
        self.move(new_pos)

    def _end_drag(self) -> None:
        self.dragging = False
        if self.y >= self.floor_y() - 0.5:
            self.brain.force(State.IDLE)
            self._reset_animation(STATE_ANIMATION[State.IDLE])
        else:
            self.vy = 0.0
            self.brain.force(State.FALLING)
            self._reset_animation(STATE_ANIMATION[State.IDLE])

    def _start_startled(self) -> None:
        self.brain.force(State.STARTLED)
        self._reset_animation(STATE_ANIMATION[State.IDLE])
        self._propagate_startle_chain()

    def _propagate_startle_chain(self) -> None:
        if self.sibling is None:
            return
        other = self._other_status()
        if other is None or abs(self.x - other.x) > STARTLE_CHAIN_DISTANCE_PX:
            return
        QTimer.singleShot(STARTLE_CHAIN_DELAY_MS, self.sibling._trigger_chained_startle)

    def _trigger_chained_startle(self) -> None:
        if self.brain.state in (State.DRAGGED, State.FALLING):
            return
        self.brain.force(State.STARTLED)
        self._reset_animation(STATE_ANIMATION[State.IDLE])

    # -- right-click menu -----------------------------------------------------

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.addAction("Sleep", self._menu_sleep)
        menu.addAction("Wake up", self._menu_wake_up)
        menu.addAction(f"About {self.name.capitalize()}", self._menu_about)
        menu.addSeparator()
        menu.addAction("Quit all", self._menu_quit_all)
        menu.exec(event.globalPos())

    def _menu_sleep(self) -> None:
        self.brain.force(State.SLEEP)
        self._reset_animation(STATE_ANIMATION[State.SLEEP])

    def _menu_wake_up(self) -> None:
        self.brain.force(State.IDLE)
        self._reset_animation(STATE_ANIMATION[State.IDLE])

    def _menu_about(self) -> None:
        bio = BIOS.get(self.name, "")
        QMessageBox.information(self, f"About {self.name.capitalize()}", f"{self.name.capitalize()} — {bio}")

    def _menu_quit_all(self) -> None:
        QApplication.instance().quit()

    # -- painting -----------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        pix = self.sprites.frame(self.anim_name, self.anim_index, self.facing_left)
        if self.squashing:
            painter.save()
            painter.translate(0, self.frame_size * (1 - SQUASH_SCALE_Y))
            painter.scale(1.0, SQUASH_SCALE_Y)
            painter.drawPixmap(0, 0, pix)
            painter.restore()
        else:
            painter.drawPixmap(0, 0, pix)
