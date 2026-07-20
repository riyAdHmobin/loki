# deskcats — Loki & Mike

Two autonomous desktop pet cats for Ubuntu (Xorg/X11 only), built with
PyQt6. They walk along the bottom of the screen, idle, sit, sleep, react
to clicks, can be dragged and dropped (with gravity), have a right-click
menu, and occasionally interact with each other.

- **Loki** — solid black. Fast, restless, wanders a lot, sleeps little.
- **Mike** — white with ever-changing spots. Professional napper.

## Requirements

- Ubuntu Linux, an **Xorg (X11) session** — Wayland is not supported;
  deskcats detects it and shows a message explaining how to switch at
  login rather than starting.
- Python 3.11+

## Install

Clone the repo, then from the repo root:

```bash
pipx install .
```

This installs the `deskcats` command:

```bash
deskcats
```

## Controls

| Action | Effect |
| --- | --- |
| Left-click | Startles the cat briefly |
| Left-click + drag | Pick up and move the cat; release above the floor and it falls |
| Right-click | Menu: Sleep, Wake up, About \<name\>, Quit all |

## Autostart

```bash
deskcats --enable-autostart    # start deskcats on login
deskcats --disable-autostart   # stop starting deskcats on login
```

## Replacing the placeholder art

The sprites under `deskcats/assets/skins/` are procedurally generated
placeholders (`python -m deskcats.gen_placeholder_art`, see
`deskcats/assets/CREDITS.md`). 🧑 To use real art, replace the `idle.png`,
`walk.png`, `sleep.png`, `sit.png` sprite strips and `meta.toml` in each
skin folder with a recolored CC0 sprite pack — keep the same frame size
and file names — then update `deskcats/assets/CREDITS.md` with
attribution for the new pack.

## Credits

See `deskcats/assets/CREDITS.md`.
