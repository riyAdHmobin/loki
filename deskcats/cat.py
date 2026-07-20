from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QApplication, QWidget

from .physics import step_walk
from .sprites import SpriteSet

MOVE_INTERVAL_MS = 33


class Cat(QWidget):
    def __init__(self, name: str, sprite_set: SpriteSet, x: float, y: float, speed: float):
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
        self.vx = speed
        self.anim_name = "walk"
        self.anim_index = 0
        self.facing_left = speed < 0

        self.move(int(self.x), int(self.y))

        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self._tick_movement)
        self.move_timer.start(MOVE_INTERVAL_MS)

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick_animation)
        self._restart_anim_timer()

    def _restart_anim_timer(self) -> None:
        fps = self.sprites.fps(self.anim_name)
        self.anim_timer.start(max(1, int(1000 / fps)))

    def _bounds(self) -> tuple[float, float]:
        width = QApplication.primaryScreen().availableGeometry().width()
        return 0.0, float(width - self.frame_size)

    def floor_y(self) -> float:
        return float(QApplication.primaryScreen().availableGeometry().bottom() - self.frame_size)

    def _tick_movement(self) -> None:
        dt = self.move_timer.interval() / 1000.0
        new_x, new_vx = step_walk(self.x, self.vx, dt, self._bounds())
        if new_vx != self.vx:
            self.facing_left = new_vx < 0
        self.x, self.vx = new_x, new_vx
        self.move(int(self.x), int(self.y))
        self.update()

    def _tick_animation(self) -> None:
        self.anim_index = (self.anim_index + 1) % self.sprites.frame_count(self.anim_name)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        pix = self.sprites.frame(self.anim_name, self.anim_index, self.facing_left)
        painter.drawPixmap(0, 0, pix)
