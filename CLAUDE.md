# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

This repository currently contains only `BUILD_GUIDE.md` — no source code has been written yet. `BUILD_GUIDE.md` is the authoritative, phase-by-phase build plan for this project and **must be read in full before doing any work here**. Everything below is a condensed summary of it; when in doubt, defer to `BUILD_GUIDE.md`.

## What this project is

Loki & Mike — two autonomous desktop pet cats for Ubuntu/Xorg (X11), built with Python 3.10+ and PyQt6. They walk along the screen bottom, idle/sit/sleep, react to clicks, can be dragged with gravity-based drop physics, have a right-click menu, and occasionally interact with each other. Both cats run in one Python process as frameless, transparent, always-on-top windows.

- **Loki** — solid black cat; fast, restless, wanders often, sleeps little.
- **Mike** — white cat with spots generated procedurally at startup (clipped to his silhouette), so his pattern can vary between runs.

## Ground rules

1. **`main` must always run.** Work each build phase on its own branch (`phase-1-skeleton`, `phase-2-art`, ...); only merge to `main` once that phase's checkpoint passes.
2. **Commit prefixes:** `feat:` / `fix:` / `art:` / `chore:` / `docs:`. Commit at every checkpoint; tag milestones (`m1`, `m2`, ... `v1.0`).
3. **Dependency budget is fixed:** `PyQt6`, `Pillow` (placeholder sprite generation only), `tomli-w` (config writing), plus stdlib `tomllib` (Python 3.11+) for reading TOML. Do not add other dependencies.
4. **No network calls at runtime** — the app must work fully offline.
5. **Steps marked 🧑 in BUILD_GUIDE.md are human-only** (switching to an Xorg session, visual verification on screen, swapping in real art) — stop and hand these to the user rather than attempting them.
6. **GUI testing constraint:** you cannot see the screen. Verify headlessly wherever possible (imports, unit tests, `QT_QPA_PLATFORM=offscreen` smoke tests) and hand off visual checkpoints to the human with precise instructions on what to check.
7. Keep modules under ~300 lines; prefer clarity over cleverness.

## Target architecture

The build guide specifies this eventual layout (build incrementally, phase by phase — don't create it all at once):

```
deskcats/
├── main.py               # bootstrap: config load, single-instance lock, Wayland guard, spawn cats
├── cat.py                # Cat class: window + sprites + brain wiring (one instance per cat)
├── state_machine.py      # State enum + Brain class: pure logic, no Qt, weighted state transitions
├── physics.py            # pure functions: step_walk, step_fall — no Qt imports, unit-testable
├── sprites.py            # SpriteSet: loads a skin folder via meta.toml, slices strips into QPixmap frames
├── spots.py              # Mike's procedural spot generator, clipped to silhouette alpha
├── social.py             # shared Registry + cat-to-cat behaviors (approach, co-sleep, startle chains)
├── config.py             # TOML config load/save with defaults, per-cat personality profiles
└── gen_placeholder_art.py  # deterministic Pillow-based placeholder sprite generator
assets/skins/{loki-black,mike-white}/  # idle/walk/sleep/sit sprite strips + meta.toml per skin
tests/                    # test_state_machine.py, test_spots.py, test_physics.py, test_config.py
```

Key architectural points from the guide:
- `physics.py` and `state_machine.py`'s `Brain` are pure logic with **no Qt imports**, so they're unit-testable in isolation from the GUI.
- Personality is data: per-cat state-transition weights in `config.py` (e.g. Loki wanders more, Mike sleeps more) drive the same `Brain` class.
- Sprite flips (for facing direction) are pre-built once per `SpriteSet` load; Mike's spots are generated once per launch and painted onto every animation frame *before* flipped variants are built, so spots mirror for free.
- Per-frame alpha masks (`setMask`) give pixel-accurate click hit-testing.
- One `Cat` instance = one window + its own movement/animation `QTimer`s; a shared `social.Registry` lets each cat's brain see the other cat's state.

## Commands (per BUILD_GUIDE.md, once each phase exists)

- Install (editable): `pip install -e .`
- Run: `deskcats` (console-script entry point → `deskcats.main:main`)
- Headless smoke test: `QT_QPA_PLATFORM=offscreen deskcats --smoke-test`
- Tests: `pytest`
- Regenerate placeholder art: `python -m deskcats.gen_placeholder_art`
- Autostart toggle: `deskcats --enable-autostart` / `--disable-autostart`
- End-user install/update/uninstall (Phase 9, `install.sh` at repo root, clones to `~/.local/share/deskcats`, wraps entry point at `~/.local/bin/deskcats`):
  - Install: `bash <(curl -fsSL https://raw.githubusercontent.com/riyAdHmobin/loki/main/install.sh)`
  - Update: `bash <(curl -fsSL https://raw.githubusercontent.com/riyAdHmobin/loki/main/install.sh) update`
  - Uninstall: `bash <(curl -fsSL https://raw.githubusercontent.com/riyAdHmobin/loki/main/install.sh) uninstall` (add `--purge` to also remove `~/.config/deskcats`)

## Workflow

Work is driven phase-by-phase from `BUILD_GUIDE.md` §4. For each phase: create the phase branch, implement, run that phase's headless checkpoint, then stop before merging so the human can do the 🧑 visual check described in the guide. Only merge to `main` and tag the milestone after that check passes.
