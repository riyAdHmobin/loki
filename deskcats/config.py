import copy
import tomllib
from pathlib import Path

import tomli_w

CONFIG_DIR = Path.home() / ".config" / "deskcats"
CONFIG_PATH = CONFIG_DIR / "config.toml"

BASE_SPEED_PX_PER_S = 80.0

DEFAULT_CONFIG = {
    "cats": {
        "loki": {
            "skin": "loki-black",
            "speed": 1.2,
            "start_frac": 0.25,
            "spots": False,
            "weights": {"wander": 45, "sleep": 10, "sit": 20, "idle": 25},
        },
        "mike": {
            "skin": "mike-white",
            "speed": 0.8,
            "start_frac": 0.75,
            "spots": True,
            "spot_seed": "daily",
            "weights": {"wander": 25, "sleep": 30, "sit": 25, "idle": 20},
        },
    },
}


def load_config(path: Path = CONFIG_PATH) -> dict:
    merged = copy.deepcopy(DEFAULT_CONFIG)
    if path.exists():
        _deep_update(merged, tomllib.loads(path.read_text()))
    return merged


def save_config(config: dict, path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(tomli_w.dumps(config).encode("utf-8"))


def _deep_update(base: dict, updates: dict) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
