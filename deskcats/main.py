import argparse
import fcntl
import os
import shutil
import signal
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox

from .cat import Cat
from .config import BASE_SPEED_PX_PER_S, CONFIG_DIR, load_config
from .social import Registry
from .spots import generate_spots, resolve_seed
from .sprites import SpriteSet

ASSETS_SKINS_DIR = Path(__file__).resolve().parent / "assets" / "skins"
LOCK_PATH = CONFIG_DIR / "deskcats.lock"
AUTOSTART_PATH = Path.home() / ".config" / "autostart" / "deskcats.desktop"
SIGNAL_PUMP_INTERVAL_MS = 200

AUTOSTART_DESKTOP_ENTRY = """[Desktop Entry]
Type=Application
Name=deskcats
Comment=Loki & Mike desktop pet cats
Exec={exec_path}
X-GNOME-Autostart-enabled=true
"""

WAYLAND_MESSAGE = (
    "deskcats only supports an Xorg (X11) session.\n\n"
    'At the login screen, click the gear icon next to the password field '
    'and choose "Ubuntu on Xorg" (or similar) before signing in, then '
    "launch deskcats again."
)


def _spawn_cats(config: dict, app: QApplication) -> list[Cat]:
    geo = app.primaryScreen().availableGeometry()
    registry = Registry()
    cats = []
    for name, profile in config["cats"].items():
        spots = None
        if profile.get("spots"):
            seed = resolve_seed(profile.get("spot_seed", "daily"))
            spots = generate_spots(seed)
        sprite_set = SpriteSet(ASSETS_SKINS_DIR / profile["skin"], spots=spots)
        frame_size = sprite_set.frame_size
        x = geo.width() * profile["start_frac"] - frame_size / 2
        y = geo.bottom() - frame_size
        speed = profile["speed"] * BASE_SPEED_PX_PER_S
        cats.append(Cat(name, sprite_set, x, y, speed, profile["weights"], registry=registry))

    for cat in cats:
        cat.sibling = next((other for other in cats if other is not cat), None)
    return cats


def _acquire_single_instance_lock(lock_path: Path = LOCK_PATH):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = open(lock_path, "w")
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock_file.close()
        return None
    lock_file.write(str(os.getpid()))
    lock_file.flush()
    return lock_file


def _is_wayland() -> bool:
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return False
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


def _enable_autostart(autostart_path: Path = AUTOSTART_PATH) -> int:
    exec_path = shutil.which("deskcats") or sys.argv[0]
    autostart_path.parent.mkdir(parents=True, exist_ok=True)
    autostart_path.write_text(AUTOSTART_DESKTOP_ENTRY.format(exec_path=exec_path))
    print(f"Autostart enabled: {autostart_path}")
    return 0


def _disable_autostart(autostart_path: Path = AUTOSTART_PATH) -> int:
    autostart_path.unlink(missing_ok=True)
    print("Autostart disabled.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="deskcats")
    parser.add_argument("--demo-slide", action="store_true", help="constant-velocity motion demo")
    parser.add_argument("--smoke-test", action="store_true", help="headless construction check")
    parser.add_argument("--enable-autostart", action="store_true", help="start deskcats on login")
    parser.add_argument("--disable-autostart", action="store_true", help="stop starting deskcats on login")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    if args.enable_autostart:
        return _enable_autostart()
    if args.disable_autostart:
        return _disable_autostart()

    lock_file = _acquire_single_instance_lock()
    if lock_file is None:
        print("The cats are already out.")
        return 1

    app = QApplication(sys.argv[:1])

    if _is_wayland():
        QMessageBox.critical(None, "deskcats needs Xorg", WAYLAND_MESSAGE)
        return 1

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: app.quit())
    signal_pump = QTimer()
    signal_pump.timeout.connect(lambda: None)
    signal_pump.start(SIGNAL_PUMP_INTERVAL_MS)

    config = load_config()
    cats = _spawn_cats(config, app)

    if args.smoke_test:
        for cat in cats:
            for _ in range(100):
                cat._tick_movement()
        return 0

    for cat in cats:
        cat.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
