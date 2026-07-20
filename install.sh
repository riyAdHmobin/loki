#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${DESKCATS_REPO_URL:-https://github.com/riyAdHmobin/loki.git}"
REPO_BRANCH="${DESKCATS_REPO_BRANCH:-main}"
INSTALL_DIR="$HOME/.local/share/deskcats"
BIN_DIR="$HOME/.local/bin"
BIN_LINK="$BIN_DIR/deskcats"
CONFIG_DIR="$HOME/.config/deskcats"
LOCK_PATH="$CONFIG_DIR/deskcats.lock"
AUTOSTART_PATH="$HOME/.config/autostart/deskcats.desktop"
MIN_PYTHON_MINOR=11

ACTION="install"
ASSUME_YES=0
PURGE=0

for arg in "$@"; do
  case "$arg" in
    install|update|uninstall)
      ACTION="$arg"
      ;;
    -y|--yes)
      ASSUME_YES=1
      ;;
    --purge)
      PURGE=1
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 1
      ;;
  esac
done

log() {
  printf '%s\n' "$*"
}

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

confirm() {
  local prompt="$1"
  if [ "$ASSUME_YES" -eq 1 ]; then
    return 0
  fi
  read -r -p "$prompt [y/N] " reply
  case "$reply" in
    y|Y|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

preflight() {
  case "$(uname -s)" in
    Linux) ;;
    *) fail "deskcats only supports Linux." ;;
  esac

  command -v python3 >/dev/null 2>&1 || fail "python3 is required but was not found."
  command -v git >/dev/null 2>&1 || fail "git is required but was not found."

  local minor
  minor="$(python3 -c 'import sys; print(sys.version_info[1])')"
  if [ "$(python3 -c 'import sys; print(sys.version_info[0])')" -ne 3 ] || [ "$minor" -lt "$MIN_PYTHON_MINOR" ]; then
    fail "python3.$MIN_PYTHON_MINOR+ is required (found python$(python3 -c 'import sys; print(\"%d.%d\" % sys.version_info[:2])'))."
  fi
}

stop_running_instance() {
  [ -f "$LOCK_PATH" ] || return 0

  if command -v flock >/dev/null 2>&1 && flock -n "$LOCK_PATH" -c true >/dev/null 2>&1; then
    return 0
  fi

  local pid
  pid="$(cat "$LOCK_PATH" 2>/dev/null || true)"
  if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
    log "Stopping running deskcats (pid $pid)..."
    kill -TERM "$pid" 2>/dev/null || true
    sleep 1
  fi
}

do_install() {
  if [ -d "$INSTALL_DIR" ]; then
    log "deskcats is already installed at $INSTALL_DIR — updating instead."
    do_update
    return
  fi

  log "Cloning $REPO_URL ($REPO_BRANCH) into $INSTALL_DIR..."
  git clone --depth 1 --branch "$REPO_BRANCH" "$REPO_URL" "$INSTALL_DIR"

  log "Creating virtual environment..."
  python3 -m venv "$INSTALL_DIR/.venv"
  "$INSTALL_DIR/.venv/bin/pip" install --upgrade pip -q
  "$INSTALL_DIR/.venv/bin/pip" install -e "$INSTALL_DIR" -q

  mkdir -p "$BIN_DIR"
  cat > "$BIN_LINK" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/.venv/bin/deskcats" "\$@"
EOF
  chmod +x "$BIN_LINK"

  case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *) log "Note: $BIN_DIR is not on your PATH. Add this to your shell rc file:"
       log "  export PATH=\"$BIN_DIR:\$PATH\"" ;;
  esac

  if confirm "Start deskcats automatically on login?"; then
    "$BIN_LINK" --enable-autostart || true
  fi

  log "Done. Launch with: deskcats"
  log "Update later with: bash <(curl -fsSL https://raw.githubusercontent.com/riyAdHmobin/loki/main/install.sh) update"
  log "Uninstall with:    bash <(curl -fsSL https://raw.githubusercontent.com/riyAdHmobin/loki/main/install.sh) uninstall"
}

do_update() {
  [ -d "$INSTALL_DIR" ] || fail "deskcats is not installed — run the installer without an action first."

  stop_running_instance

  log "Updating $INSTALL_DIR..."
  git -C "$INSTALL_DIR" fetch --depth 1 origin "$REPO_BRANCH"
  git -C "$INSTALL_DIR" reset --hard "origin/$REPO_BRANCH"

  "$INSTALL_DIR/.venv/bin/pip" install -e "$INSTALL_DIR" -q

  log "Updated. Relaunch deskcats to pick up the changes."
}

do_uninstall() {
  if [ ! -d "$INSTALL_DIR" ] && [ ! -f "$BIN_LINK" ]; then
    log "Nothing to do — deskcats is not installed."
    return 0
  fi

  stop_running_instance

  if [ -x "$BIN_LINK" ]; then
    "$BIN_LINK" --disable-autostart >/dev/null 2>&1 || true
  fi
  rm -f "$AUTOSTART_PATH"

  : "${BIN_LINK:?}"
  rm -f "$BIN_LINK"

  : "${INSTALL_DIR:?}"
  rm -rf "$INSTALL_DIR"

  if [ "$PURGE" -eq 1 ]; then
    : "${CONFIG_DIR:?}"
    rm -rf "$CONFIG_DIR"
    log "Uninstalled deskcats and removed its config."
  else
    log "Uninstalled deskcats. Config left at $CONFIG_DIR (rerun with --purge to remove it too)."
  fi
}

preflight

case "$ACTION" in
  install) do_install ;;
  update) do_update ;;
  uninstall) do_uninstall ;;
esac
