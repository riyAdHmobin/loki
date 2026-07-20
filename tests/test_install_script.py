import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALL_SH = REPO_ROOT / "install.sh"


def _current_branch() -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _run_install_sh(args: list[str], home: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["DESKCATS_REPO_URL"] = f"file://{REPO_ROOT}/.git"
    env["DESKCATS_REPO_BRANCH"] = _current_branch()
    return subprocess.run(
        ["bash", str(INSTALL_SH), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_install_update_uninstall_purge_round_trip(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    install_dir = home / ".local" / "share" / "deskcats"
    bin_link = home / ".local" / "bin" / "deskcats"
    config_dir = home / ".config" / "deskcats"

    install_result = _run_install_sh(["-y"], home)
    assert install_result.returncode == 0, install_result.stderr
    assert install_dir.is_dir()
    assert bin_link.is_file()

    update_result = _run_install_sh(["-y", "update"], home)
    assert update_result.returncode == 0, update_result.stderr

    uninstall_result = _run_install_sh(["-y", "uninstall", "--purge"], home)
    assert uninstall_result.returncode == 0, uninstall_result.stderr
    assert not install_dir.exists()
    assert not bin_link.exists()
    assert not config_dir.exists()


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_uninstall_without_install_is_a_safe_no_op(tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    result = _run_install_sh(["-y", "uninstall"], home)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_update_without_install_fails_clearly(tmp_path):
    home = tmp_path / "home"
    home.mkdir()

    result = _run_install_sh(["-y", "update"], home)
    assert result.returncode != 0
    assert "not installed" in result.stderr
