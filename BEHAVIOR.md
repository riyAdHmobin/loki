# Cat Behavior Reference

This documents the observable and logical behavior of Loki and Mike, as implemented in
`deskcats/state_machine.py` (`Brain`), `deskcats/cat.py` (`Cat`), `deskcats/physics.py`,
`deskcats/social.py` (`Registry`), and `deskcats/config.py`. It's a behavior reference, not
an architecture doc — see `CLAUDE.md` for how the pieces fit together in code.

## States

| State | Driven by | Animation | Ends when |
|---|---|---|---|
| `IDLE` | Brain (weighted, timed) | `idle` | timer elapses, or a social approach starts |
| `WANDER` | Brain (weighted, target-based) | `walk` | reaches its target x, or hits a screen edge |
| `SLEEP` | Brain (weighted, timed) | `sleep` | timer elapses |
| `SIT` | Brain (weighted, timed) | `sit` | timer elapses |
| `SOCIAL_APPROACH` | Brain (probabilistic, target-based) | `walk` | reaches the other cat, then becomes `SIT` |
| `SOCIAL_NAP` | Brain (probabilistic, target-based) | `walk` | reaches the other cat, then becomes `SLEEP` |
| `DRAGGED` | Forced by mouse input | `idle` | mouse released |
| `FALLING` | Forced on drag release above the floor | `idle` (squash on landing) | hits the floor, becomes `IDLE` |
| `STARTLED` | Forced by a left-click (no drag) | `idle`, 2x fps | 1.0s elapses, becomes `IDLE` |

`IDLE`, `WANDER`, `SLEEP`, and `SIT` are the four "weighted" states — when one of them ends
on a timer (or `WANDER` arrives/hits an edge), the Brain rolls a new one from this set using
per-cat weights, excluding the state it's leaving. `DRAGGED`/`FALLING`/`STARTLED` are never
chosen by the Brain itself — they're only ever imposed from outside via `Brain.force()`.

## Timers (self-driven states)

- `IDLE`: 3–15s (random per entry)
- `SLEEP`: 30–180s
- `SIT`: 5–12s
- `WANDER`: no timer — ends on arrival at a randomly picked x target, or on hitting either
  screen edge, whichever comes first

## Personality weights

Weights bias which of the four idle-ish states gets picked next; they don't affect duration.

| | wander | sleep | sit | idle |
|---|---|---|---|---|
| **Loki** | 45 | 10 | 20 | 25 |
| **Mike** | 25 | 30 | 25 | 20 |

Loki is roughly 4.5x as likely to pick wander over sleep as Mike is — restless, wanders a lot,
naps rarely. Mike is 3x as likely to pick sleep as Loki — a professional napper.

Speed (base 80 px/s, `config.py:BASE_SPEED_PX_PER_S`):
- Loki: 1.2x → **96 px/s**
- Mike: 0.8x → **64 px/s**

These weights/speeds are just `config.toml` defaults (`~/.config/deskcats/config.toml`
overrides them) — the Brain class itself has no per-cat special-casing.

## Social behavior

Both cats' `(x, state, speed)` are published every tick into a shared `Registry`; each cat's
Brain reads the *other* cat's status back out as plain data (no direct object reference), and
can spontaneously start one of two social interactions:

### Social approach
- Rolled only when a cat's `IDLE` timer elapses (10% chance, `SOCIAL_APPROACH_CHANCE`), and
  only if not on cooldown.
- Walks to within 40px (`SOCIAL_APPROACH_STOP_DISTANCE`) of the other cat, approaching from
  whichever side is closer.
- On arrival: sits down (`SIT`), and starts a cooldown.

### Social nap
- Rolled whenever a cat's `WANDER` ends (reaches its target or hits an edge) *and* the other
  cat is currently `SLEEP` *and* within 150px (`SOCIAL_NAP_TRIGGER_DISTANCE`) — 30% chance
  (`SOCIAL_NAP_CHANCE`), and only if not on cooldown.
- Walks to within 30px (`SOCIAL_NAP_STOP_DISTANCE`) of the sleeping cat.
- On arrival: falls asleep (`SLEEP`), and starts a cooldown.

### Cooldown
After either social interaction ends, that cat can't initiate another for 60–180s
(`SOCIAL_COOLDOWN_RANGE`, re-rolled each time) — this is what prevents the two cats from
permanently clumping together.

### Stepping aside
Outside of social states, if the faster of the two cats gets within 20px
(`STEP_ASIDE_DISTANCE_PX`) of the slower one, the faster cat nudges past it in whichever
direction it was already heading, so they don't get stuck standing on top of each other.

### Startle chain reaction
Startling one cat (see below) propagates to the other cat if they're within 100px
(`STARTLE_CHAIN_DISTANCE_PX`) at that moment: the sibling gets startled too, after a 300ms
delay (`STARTLE_CHAIN_DELAY_MS`) — unless it's currently being dragged or is falling.

## Mouse interaction

| Input | Effect |
|---|---|
| Left-click (press+release, < 4px movement) | `STARTLED` for 1.0s; animation plays at 2x fps; may chain-startle the other cat |
| Left-click + drag (> 4px movement) | `DRAGGED`: cat follows the cursor exactly, no physics |
| Release while dragging, cat is at/near the floor | Lands immediately → `IDLE` |
| Release while dragging, cat is above the floor | `FALLING`: gravity-driven drop (1500 px/s² gravity, 1200 px/s terminal velocity) until it hits the floor, then a 100ms squash-and-stretch on landing → `IDLE` |
| Right-click | Context menu: **Sleep**, **Wake up**, **About \<name\>**, **Quit all** |

"Sleep"/"Wake up" from the menu force the Brain straight into `SLEEP`/`IDLE`, bypassing the
normal weighted selection and any cooldown.

## Movement mechanics

- Cats are confined to `[0, screen_width - frame_size]` on x, and rest on
  `screen_bottom - frame_size` when not falling.
- While `WANDER`/`SOCIAL_APPROACH`/`SOCIAL_NAP`, the cat walks directly toward its Brain-picked
  target x at its personality speed, flipping sprite facing to match direction — there's no
  edge-bounce involved in normal wandering (`WANDER` ends *at* the edge rather than bouncing
  off it).
- `physics.step_walk` (edge-bounce at a boundary) exists and is unit-tested
  (`tests/test_physics.py`) but isn't called from `cat.py`'s movement loop — day-to-day wander
  movement is computed directly against the Brain's target, not via this function. The
  `--demo-slide` CLI flag is likewise parsed in `main.py` but not currently wired to any demo
  behavior.
- `physics.step_fall` *is* the live gravity implementation used for `FALLING`.

## Spots (Mike only)

Mike's spots are generated once per process launch (`spots.py:generate_spots`), not per
animation frame, so they stay consistent across all his sprites for that run but can differ
between launches:

- 2–4 elliptical spots, random position/size/rotation, seeded by `spot_seed`:
  - `"daily"` (default): seeded from today's date — same spots all day, new spots tomorrow
  - `"random"`: a fresh seed every launch
  - `"fixed:<n>"`: always the same spots
- Spots are clipped to the sprite's alpha silhouette (so they never draw outside the cat's
  body) and applied before flipped sprite variants are built, so they mirror correctly for
  free when Mike faces left.
