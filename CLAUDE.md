# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

All 9 build phases in `BUILD_GUIDE.md` are complete and merged to `main` (tags `m1`–`m9`, plus `versions/1.0.0`). The app is feature-complete per `BUILD_GUIDE.md` §5's acceptance criteria; remaining work is bug fixes, polish, or new features on top of the existing implementation. `BUILD_GUIDE.md` is still the authoritative record of *why* the architecture looks the way it does — read it when a change touches the state machine, physics, or social behavior, since it explains design intent that isn't restated in code comments.

## What this project is

Loki & Mike — two autonomous desktop pet cats for Ubuntu/Xorg (X11), built with Python 3.11+ and PyQt6. They walk along the screen bottom, idle/sit/sleep, react to clicks, can be dragged with gravity-based drop physics, have a right-click menu, and occasionally interact with each other. Both cats run in one Python process as frameless, transparent, always-on-top windows.

- **Loki** — solid black cat; fast, restless, wanders often, sleeps little.
- **Mike** — white cat with spots generated procedurally at startup (clipped to his silhouette), so his pattern can vary between runs.

## Ground rules

1. **`main` must always run.** Non-trivial changes should still go on their own branch and pass the checkpoint below before merging.
2. **Commit prefixes:** `feat:` / `fix:` / `art:` / `chore:` / `docs:`.
3. **Dependency budget is fixed:** `PyQt6`, `Pillow` (placeholder sprite generation only), `tomli-w` (config writing), plus stdlib `tomllib` (Python 3.11+) for reading TOML. Do not add other dependencies without discussing it first.
4. **No network calls at runtime** — the app must work fully offline.
5. **GUI testing constraint:** you cannot see the screen. Verify headlessly wherever possible (imports, unit tests, `QT_QPA_PLATFORM=offscreen` smoke tests) and hand off visual verification to the human with precise instructions on what to check. Steps that require an Xorg session or eyes-on verification are human-only.
6. Keep modules under ~300 lines; prefer clarity over cleverness.

## Commands

- Install (editable, in a venv): `pip install -e .`
- Run: `deskcats`
- Headless smoke test (constructs both cats, ticks movement 100x, exits): `QT_QPA_PLATFORM=offscreen deskcats --smoke-test`
- Tests (also force offscreen platform via `tests/conftest.py`): `pytest`
- Run a single test file/case: `pytest tests/test_state_machine.py -k social_nap`
- Regenerate placeholder art: `python -m deskcats.gen_placeholder_art`
- Autostart toggle: `deskcats --enable-autostart` / `deskcats --disable-autostart`
- End-user install/update/uninstall (`install.sh` at repo root, clones to `~/.local/share/deskcats`, wraps entry point at `~/.local/bin/deskcats`):
  - Install: `bash <(curl -fsSL https://raw.githubusercontent.com/riyAdHmobin/loki/main/install.sh)`
  - Update: `bash <(curl -fsSL https://raw.githubusercontent.com/riyAdHmobin/loki/main/install.sh) update`
  - Uninstall: `bash <(curl -fsSL https://raw.githubusercontent.com/riyAdHmobin/loki/main/install.sh) uninstall` (add `--purge` to also remove `~/.config/deskcats`)

## Architecture

```
deskcats/
├── main.py               # bootstrap: arg parsing, single-instance flock, Wayland guard, autostart, spawns cats
├── cat.py                # Cat(QWidget): owns per-cat QTimers (move @33ms, anim), mouse events, painting, right-click menu
├── state_machine.py       # State enum + Brain: pure logic, no Qt, weighted personality-driven transitions
├── physics.py             # step_walk (bounce at screen edges) / step_fall (gravity+terminal velocity) — pure functions, no Qt
├── sprites.py              # SpriteSet: loads a skin dir via meta.toml, slices strips into QPixmap frames, pre-builds flipped variants
├── spots.py                # Mike's procedural spot generator (seeded by date/fixed/random) + alpha-clipped compositing
├── social.py               # Registry: Qt-free dict of {name: CatStatus(x, state, speed)} shared between both cats' brains
├── config.py               # TOML load/save with DEFAULT_CONFIG merge; per-cat speed/start position/state-transition weights
└── gen_placeholder_art.py  # deterministic Pillow-based placeholder sprite generator (used to (re)populate assets/skins/)
assets/skins/{loki-black,mike-white}/  # idle/walk/sleep/sit sprite strips + meta.toml per skin
tests/                     # test_state_machine.py, test_physics.py, test_spots.py, test_social.py, test_interaction.py, test_guards.py, test_gen_placeholder_art.py, test_install_script.py
install.sh                 # standalone curl-pipeable install/update/uninstall script (not part of the Python package)
```

Key points:

- **Qt-free core, Qt shell.** `physics.py`, `state_machine.py` (`Brain`), and `social.py` (`Registry`) have zero PyQt imports and are pure/unit-testable in isolation. `cat.py` is the only place Qt widgets, timers, and events live; it drives the Qt-free `Brain` via `brain.tick(dt, context)` each movement tick and translates state into position/animation.
- **`Brain.tick` vs `Brain.force`.** Self-driven states (`WANDER`, `IDLE`, `SLEEP`, `SIT`, and the two `SOCIAL_*` states) are chosen and timed internally by `tick()`. Externally-triggered states (`DRAGGED`, `FALLING`, `STARTLED`) are imposed on the brain from `cat.py` via `brain.force(state)` — the brain never picks these itself.
- **Social behavior via a shared `Registry`, not direct references.** Each `Cat` pushes its own `(x, state, speed)` into a shared `Registry` every tick and reads the other cat's status back out; `Brain.tick` receives this as a plain `context` dict (`x`, `other_x`, `other_state`), keeping the state machine Qt- and Cat-free. `SOCIAL_APPROACH`/`SOCIAL_NAP` are chosen probabilistically inside `Brain` based on that context, with a cooldown to prevent permanent clumping; `cat.py` separately handles a faster cat stepping aside when about to collide with a slower one (`_maybe_step_aside`), and a startle "chain reaction" between cats within `STARTLE_CHAIN_DISTANCE_PX` (`_propagate_startle_chain`).
- **Personality is data.** Per-cat state-transition weights and speed/start position live in `config.py`'s `DEFAULT_CONFIG` (and are overridable via `~/.config/deskcats/config.toml`), driving the same `Brain` class for both cats — Loki and Mike differ only in the weights/speed passed in, not in code.
- **Sprite flips and spots are precomputed once.** `SpriteSet` builds both normal and horizontally-flipped `QPixmap` variants once per skin load (for facing direction), and — for Mike — applies the per-launch-generated spots (`spots.py`, clipped to the sprite's alpha silhouette via `DestinationIn` compositing) *before* building the flipped variants, so spots mirror for free rather than needing separate flip logic. Per-frame `QPixmap.mask()` gives pixel-accurate click hit-testing (`setMask`) instead of a rectangular hitbox.
- **One `Cat` = one window + its own timers.** Each `Cat` instance owns a `move_timer` (33ms tick — physics/brain/position) and an `anim_timer` (interval derived from the current animation's fps, doubled while `STARTLED`) as separate `QTimer`s, so the two cats animate and move independently even though they share one `QApplication`/process.
- **Single-instance + Wayland guard in `main.py`.** An `flock` on `~/.config/deskcats/deskcats.lock` prevents a second `deskcats` process from spawning duplicate cats; `_is_wayland()` checks `XDG_SESSION_TYPE` (skipped when `QT_QPA_PLATFORM=offscreen`, so headless tests aren't blocked) and shows a `QMessageBox` pointing the user at the Xorg login option instead of starting under Wayland.
- **`install.sh` is independent of the Python package** — it's a plain bash script (not part of `deskcats/`) that clones the repo to `~/.local/share/deskcats` and symlinks/wraps the entry point at `~/.local/bin/deskcats`; it's tested via subprocess in `tests/test_install_script.py` rather than pytest importing it as a module.

## Workflow

`BUILD_GUIDE.md` §5 lists the final human-verified acceptance criteria (both cats visible within 1s, Mike's spots vary per run, Loki wanders more/Mike sleeps more, drag/drop physics, ≥1 social behavior per 15 min with no permanent clumping, CPU/RAM budget, clean quit/relaunch/double-launch handling, and the install/update/uninstall one-liners). When making a nontrivial change: implement, run the relevant headless checks (`pytest`, `QT_QPA_PLATFORM=offscreen deskcats --smoke-test`), then hand off to the human with precise instructions on which of these criteria to re-verify visually on an actual Xorg session before merging.
