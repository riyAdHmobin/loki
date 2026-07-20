# BUILD_GUIDE.md
## Project: Loki & Mike — Desktop Pet Cats for Ubuntu (X11)
### This file is written to be executed by Claude Code. Follow it phase by phase.

**Repo:** `git@github.com:riyAdHmobin/loki.git`
**Owner:** riyAdHmobin
**Target platform:** Ubuntu Linux, Xorg (X11) session, Python 3.10+, PyQt6

---

## 1. What we are building

Two autonomous desktop pet cats that live on the user's screen:

- **Loki** — solid black cat. Personality: fast, restless, wanders a lot, sleeps little.
- **Mike** — white cat with **randomly generated black spots** (spots are drawn in code at startup, clipped to his body silhouette, so his pattern can change between runs).

Both cats: walk along the bottom of the screen, idle, sit, sleep, react to clicks, can be dragged and dropped (with gravity), have a right-click menu, and occasionally interact with each other (approach, nap side by side). Frameless transparent always-on-top windows. One Python process runs both cats.

---

## 2. Ground rules for Claude Code

1. **`main` must always run.** Work on a branch per phase (`phase-1-skeleton`, `phase-2-engine`, ...), merge to `main` only when the phase checkpoint passes.
2. **Commit style:** `feat:` / `fix:` / `art:` / `chore:` / `docs:` prefixes. Commit at every checkpoint. Tag milestones: `m1`, `m2`, ... `v1.0`.
3. **Do not add dependencies** beyond: `PyQt6`, `Pillow` (placeholder sprite generation only), `tomli-w` (config writing). Python 3.11+ `tomllib` for reading TOML.
4. **No network calls at runtime.** The app is fully offline.
5. **Human-only steps** are marked 🧑 — stop and ask the user to do these; you cannot (switching to Xorg at the login screen, visually verifying cats on screen, replacing placeholder art).
6. **GUI testing constraint:** you may not be able to see the screen. Verify what you can headlessly (imports, unit tests, `QT_QPA_PLATFORM=offscreen` smoke tests), then hand visual checkpoints to the human with exact instructions on what to look for.
7. Keep modules under ~300 lines. Prefer clarity over cleverness.

---

## 3. Target repository layout

```
loki/
├── BUILD_GUIDE.md            # this file
├── README.md
├── install.sh                # curl-pipeable install / update / uninstall script (Phase 9)
├── pyproject.toml            # entry point: deskcats = deskcats.main:main
├── requirements.txt
├── .gitignore                # .venv/, __pycache__/, *.pyc, *.egg-info/, dist/, build/
├── deskcats/
│   ├── __init__.py
│   ├── main.py               # bootstrap: config load, single-instance lock, Wayland guard, spawn cats
│   ├── cat.py                # Cat class: window + sprites + brain wiring (one instance per cat)
│   ├── state_machine.py      # states, weighted transitions, per-cat weights
│   ├── physics.py            # walk velocity, gravity, screen clamping
│   ├── sprites.py            # sheet loading, frame slicing, flipped variants
│   ├── spots.py              # Mike's random spot generator
│   ├── social.py             # cat-to-cat behaviors
│   ├── config.py             # TOML config load/save with defaults
│   └── gen_placeholder_art.py  # generates simple placeholder sprites with Pillow
├── assets/
│   ├── CREDITS.md
│   └── skins/
│       ├── loki-black/       # idle.png walk.png sleep.png sit.png + meta.toml
│       └── mike-white/       # same filenames (white base, NO spots baked in)
└── tests/
    ├── test_state_machine.py
    ├── test_spots.py
    ├── test_physics.py
    └── test_config.py
```

---

## 4. Build phases

### Phase 1 — Repo skeleton & tooling
**Branch:** `phase-1-skeleton`

1. Clone `git@github.com:riyAdHmobin/loki.git`, create the layout above with empty/stub modules.
2. Write `.gitignore`, `requirements.txt` (`PyQt6`, `Pillow`, `tomli-w`), `pyproject.toml` with console script `deskcats = deskcats.main:main`.
3. `python -m venv .venv`, install requirements.
4. Stub `main.py` that prints `deskcats: Loki & Mike` and exits 0.

**Checkpoint (headless):** `pip install -e .` succeeds; `deskcats` runs and exits 0; `pytest` collects 0 tests without error. Commit `chore: project skeleton`, merge, tag `m1`.

---

### Phase 2 — Placeholder sprites (so no human art is needed to develop)
**Branch:** `phase-2-art`

1. Implement `gen_placeholder_art.py` using Pillow. Generate, for each skin folder, horizontal sprite strips of **64×64 px frames** with transparent background:
   - `idle.png` — 4 frames: simple cat silhouette (ellipse body, circle head, 2 triangle ears, tail curve); tail tip shifts a few px per frame.
   - `walk.png` — 6 frames: same silhouette, legs alternating (2–3 px offsets), slight body bob.
   - `sleep.png` — 4 frames: curled ellipse, "z" dots appearing progressively.
   - `sit.png` — 4 frames: upright silhouette, minor sway.
2. Colors: `loki-black` → fill `#111111`, eyes `#3fd12c`. `mike-white` → fill `#f2f2ef`, outline `#4a4a4a` (1 px), eyes `#e8a13c`. **Do not draw spots on Mike.**
3. Each skin gets `meta.toml`: `frame_size = 64`, per-animation `frames = N`, `fps = 10` (sleep `fps = 4`).
4. Make generation deterministic (fixed seed) and add a CLI: `python -m deskcats.gen_placeholder_art`.
5. `assets/CREDITS.md`: note art is generated placeholder, to be replaced by the user (🧑) with a recolored CC0 pack later.

**Checkpoint (headless):** running the generator produces all 8 PNGs + 2 meta.toml; a unit test opens each PNG and asserts width == frames × 64, height == 64, alpha channel present. Commit `art: generated placeholder sprite sets`, merge, tag `m2`.

---

### Phase 3 — Engine: two cats on screen
**Branch:** `phase-3-engine`

1. `sprites.py`: `SpriteSet` class — loads a skin folder using `meta.toml`, slices strips into `QPixmap` frame lists, pre-builds horizontally flipped variants.
2. `cat.py`: `Cat` class holding its own `QWidget` with flags `FramelessWindowHint | WindowStaysOnTopHint | Tool`, attributes `WA_TranslucentBackground`, `WA_ShowWithoutActivating`; fixed size from meta; `paintEvent` draws current frame; movement `QTimer` 33 ms; animation `QTimer` per-animation fps.
3. `physics.py`: pure functions — `step_walk(x, vx, dt, bounds)`, `step_fall(y, vy, dt, floor_y)` returning new values; unit-testable, no Qt imports.
4. `config.py`: defaults embedded; load/save `~/.config/deskcats/config.toml`; profiles for `loki` (speed 1.2, skin loki-black, start_frac 0.25) and `mike` (speed 0.8, skin mike-white, spots true, start_frac 0.75).
5. `main.py`: load config → for each cat profile spawn a `Cat` → temporary test mode `--demo-slide` that gives both cats constant velocity so the human can verify motion.
6. Floor: `primaryScreen().availableGeometry().bottom() - frame_size`.

**Checkpoint:** headless — `QT_QPA_PLATFORM=offscreen deskcats --smoke-test` constructs both cats, runs 100 movement ticks, exits 0; physics unit tests pass. 🧑 Human: run `deskcats --demo-slide` on Xorg and confirm two cats slide independently at screen bottom and clicks outside them reach other apps. Commit `feat: two independent animated cat windows (M3)`, merge, tag `m3`.

---

### Phase 4 — Mike's random spots
**Branch:** `phase-4-spots`

1. `spots.py`: `generate_spots(seed, n_min=2, n_max=4)` → list of `Spot(cx, cy, rx, ry, rotation)` with positions/radii as fractions of frame size (radii 0.08–0.18); `apply_spots(frame_qimage, spots)` → paints black ellipses on an overlay, then clips the overlay to the frame's alpha channel (`CompositionMode_DestinationIn`) and composites onto the frame.
2. In `SpriteSet`, when profile has `spots = true`: generate ONE spot list per launch and apply to every frame of every animation **before** building flipped variants (so spots mirror correctly for free).
3. Config: `spot_seed = "random" | "daily" | "fixed:<int>"` — `daily` derives the seed from today's date; default `daily`.
4. Tests: with a fixed seed, spot list is reproducible; applied spots never set alpha where the base frame's alpha was 0 (i.e., no spots floating outside the silhouette).

**Checkpoint:** headless tests pass. 🧑 Human: launch twice with `spot_seed = "random"` and confirm Mike's pattern differs between runs and spots stay on his body while walking. Commit `feat: procedural spots for Mike (M4)`, merge, tag `m4`.

---

### Phase 5 — Brains: state machine & personalities
**Branch:** `phase-5-brain`

1. `state_machine.py`: `State` enum — `IDLE, WANDER, SLEEP, SIT, DRAGGED, FALLING, STARTLED, SOCIAL_APPROACH, SOCIAL_NAP`. `Brain` class: pure logic, no Qt — takes personality weights + RNG, exposes `tick(dt, context) -> actions`. Durations: IDLE 3–15 s, SLEEP 30–180 s, SIT 5–12 s; WANDER picks a random target x and ends on arrival.
2. Weights from config:
   - Loki: `{wander: 45, sleep: 10, sit: 20, idle: 25}`
   - Mike: `{wander: 25, sleep: 30, sit: 25, idle: 20}`
3. Wire `Brain` into `Cat`; sprite flips to face travel direction; screen edges force turn-around; random initial brain-timer offset per cat so they desync.
4. While SLEEPing, drop that cat's animation timer to 500 ms (CPU saving).
5. Tests: simulate 10,000 brain ticks per cat with seeded RNG → assert Loki's WANDER time share > Mike's, Mike's SLEEP share > Loki's, all states reachable, no state lasts forever.

**Checkpoint:** headless tests pass; smoke test runs 2,000 ticks without exceptions. 🧑 Human: watch 10 min — organic, non-mirrored behavior. Commit `feat: state machine with per-cat personalities (M5)`, merge, tag `m5`.

---

### Phase 6 — Interaction
**Branch:** `phase-6-interaction`

1. Left-click (no drag) → STARTLED ~1 s (reuse idle frames at 2× fps), then IDLE.
2. Left-press + move → DRAGGED: window follows cursor minus press offset; brain paused.
3. Release above floor → FALLING: gravity 1500 px/s², terminal 1200 px/s; on landing → brief squash (draw frame vertically scaled 0.8 for 100 ms) → IDLE.
4. Right-click → `QMenu` per cat: `Sleep`, `Wake up`, `About {name}` (dialog: name + one-line bio), `Quit all`.
5. Pixel-accurate input: `setMask` from the current frame's alpha each time the frame changes, so clicks between the ears pass through.

**Checkpoint:** headless — physics fall tests pass; mask exists for a sample frame. 🧑 Human: drag Mike onto Loki, drop from top of screen, verify fall + land; verify menu names show "Loki"/"Mike"; Quit all removes both. Commit `feat: click, drag, gravity, menus (M6)`, merge, tag `m6`.

---

### Phase 7 — Cat society
**Branch:** `phase-7-social`

1. `social.py`: a shared `Registry` (both cats' positions/states) injected into each brain's tick context.
2. Behaviors: (a) from IDLE, 10% chance → SOCIAL_APPROACH: walk to within 40 px of the other cat, SIT facing it; (b) if other cat SLEEPs and this cat ends WANDER within 150 px → 30% chance walk over and SLEEP 30 px beside it; (c) startle chain: startling one startles the other 300 ms later if within 100 px; (d) if overlapping < 20 px outside social states, the faster cat steps aside.
3. Cooldown 60–180 s after any social interaction (per cat) so they don't clump permanently.
4. Tests: seeded 50,000-tick two-brain simulation → at least one SOCIAL_NAP occurs; social states never exceed 25% of total time; cooldowns respected.

**Checkpoint:** headless tests pass. 🧑 Human: 15-min watch — at least one side-by-side nap. Commit `feat: social behaviors with cooldowns (M7)`, merge, tag `m7`.

---

### Phase 8 — Guards, polish, packaging
**Branch:** `phase-8-release`

1. Single instance: `fcntl.flock` on `~/.config/deskcats/deskcats.lock`; second launch prints "The cats are already out." and exits 1.
2. Wayland guard: if `XDG_SESSION_TYPE == "wayland"`, show a `QMessageBox` explaining the Xorg requirement (with the login-screen gear instructions) and exit gracefully.
3. `deskcats --enable-autostart` / `--disable-autostart` writes/removes `~/.config/autostart/deskcats.desktop` pointing at the installed `deskcats` entry point.
4. Clean SIGINT/SIGTERM handling — no orphan windows.
5. README.md: install (`pipx install .` from clone), Xorg requirement, controls table, cat bios (Loki: black, fast, restless / Mike: white, ever-changing spots, professional napper), how to replace placeholder art with a CC0 pack (🧑), credits.
6. Performance: with both cats idle/sleep mix, target < 3% CPU, < 90 MB RAM (🧑 human verifies with `htop`).

**Checkpoint:** headless — lockfile test (second process exits 1), autostart file written/removed correctly, `pipx install .` works in a temp env. 🧑 Human: full 15-min acceptance run per §5. Commit `chore: guards, autostart, packaging (M8)`, merge, tag `v1.0`, push tags, create GitHub Release.

---

### Phase 9 — One-line install / update / uninstall script
**Branch:** `phase-9-installer`

Goal: a single self-contained `install.sh` at the repo root, runnable via:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/riyAdHmobin/loki/main/install.sh)                  # install
bash <(curl -fsSL https://raw.githubusercontent.com/riyAdHmobin/loki/main/install.sh) update            # update
bash <(curl -fsSL https://raw.githubusercontent.com/riyAdHmobin/loki/main/install.sh) uninstall          # uninstall
```

1. **Script skeleton:** `#!/usr/bin/env bash`, `set -euo pipefail`. First positional arg selects the action: `install` (default if omitted), `update`, `uninstall`. Support `-y`/`--yes` (skip prompts) and, for `uninstall`, `--purge` (also remove `~/.config/deskcats`).
2. **Layout constants:**
   - `REPO_URL="https://github.com/riyAdHmobin/loki.git"`
   - `INSTALL_DIR="$HOME/.local/share/deskcats"` (cloned repo + its own `.venv`)
   - `BIN_LINK="$HOME/.local/bin/deskcats"` (wrapper script exec'ing `"$INSTALL_DIR/.venv/bin/deskcats" "$@"`)
   - Config/lock dir stays `~/.config/deskcats` (already defined in Phase 8), untouched by plain `install`/`update`.
3. **Preflight checks (all actions):** Linux only; `python3` present and `>= 3.10`; `git` present. Fail with a clear one-line message and non-zero exit if not — do not attempt to auto-install system packages.
4. **`install`:**
   - If `INSTALL_DIR` already exists, treat this as an `update` (idempotent re-run of the one-liner) instead of erroring.
   - `git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"`.
   - `python3 -m venv "$INSTALL_DIR/.venv"`; upgrade `pip`; `pip install -e "$INSTALL_DIR"`.
   - Write the `BIN_LINK` wrapper, `chmod +x`; if `~/.local/bin` isn't on `PATH`, print (don't silently edit shell rc files) the export line the user needs to add.
   - Prompt (or auto-yes with `-y`) to run `deskcats --enable-autostart`.
   - Print a short "done" summary: binary location, how to launch, how to update/uninstall later.
5. **`update`:**
   - Error clearly if `INSTALL_DIR` doesn't exist yet ("not installed — run the installer without an action first"), do not silently install.
   - If a `deskcats` process is running (check the Phase 8 lockfile/PID), stop it gracefully (`SIGTERM`) before touching files, and note that it needs relaunching afterward.
   - `git -C "$INSTALL_DIR" fetch --depth 1 origin main && git -C "$INSTALL_DIR" reset --hard origin/main`.
   - Reinstall: `"$INSTALL_DIR/.venv/bin/pip" install -e "$INSTALL_DIR"` (picks up new/changed deps against the Phase-1 dependency budget only).
   - Leave `~/.config/deskcats` (config + skins overrides) untouched.
6. **`uninstall`:**
   - Stop any running `deskcats` process (same lockfile/PID check as `update`).
   - If the entry point still works, run `deskcats --disable-autostart`; otherwise remove `~/.config/autostart/deskcats.desktop` directly.
   - Remove `BIN_LINK`, then remove `INSTALL_DIR` entirely.
   - With `--purge`, also remove `~/.config/deskcats`; without it, print that config was left behind and how to remove it manually.
7. **Idempotency & safety:** every action must be safe to re-run (re-`install` == `update`, re-`uninstall` on a clean system is a no-op that exits 0 with a "nothing to do" message, not an error). Never `rm -rf` a path that isn't exactly `INSTALL_DIR`, `BIN_LINK`, or (with `--purge`) the config dir — no globs, no `$HOME` fallbacks if a variable is unexpectedly empty (`: "${INSTALL_DIR:?}"` style guards before any `rm -rf`).
8. Add a short "Install / Update / Uninstall" section to `README.md` with the three one-liners above.

**Checkpoint (headless):** `shellcheck install.sh` passes with no warnings. A local dry run against a scratch `HOME` (e.g. `HOME=$(mktemp -d) bash install.sh -y`, then `... update`, then `... uninstall --purge`) completes each step with exit 0 and leaves no files behind after `uninstall --purge`. 🧑 Human: run the real one-liner from a fresh shell against the published `main` branch, confirm `deskcats` launches, then run the `update` and `uninstall` one-liners and confirm each behaves as described. Commit `feat: curl-pipeable install/update/uninstall script (M9)`, merge, tag `m9`.

---

## 5. Final acceptance criteria (human-verified on Xorg)

1. Both cats visible within 1 s of `deskcats`.
2. Mike's spots: on-body only; differ across runs with `spot_seed = "random"`.
3. Loki observably wanders more; Mike observably sleeps more (10 min).
4. Independent drag/drop with believable falls; other cat unaffected.
5. ≥ 1 social behavior in 15 min; no permanent clumping.
6. < 3% combined CPU, < 90 MB combined RAM.
7. Right-click → Quit all leaves no processes/windows; relaunch works; double-launch refuses politely.
8. `bash <(curl -fsSL https://raw.githubusercontent.com/riyAdHmobin/loki/main/install.sh)` installs cleanly on a fresh machine; the `update` and `uninstall` (and `uninstall --purge`) one-liners each work as documented.

## 6. Suggested Claude Code session prompts

- Phase start: "Read BUILD_GUIDE.md. Execute Phase N on branch phase-N-…, run the headless checkpoint, and stop before merging so I can do the visual check."
- After human check passes: "Visual checkpoint for Phase N passed. Merge to main, tag mN, push, and start Phase N+1."
- If a visual check fails: describe exactly what you saw; Claude Code should fix on the same phase branch and re-run headless tests before handing back.
