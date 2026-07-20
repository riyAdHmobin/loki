from deskcats.main import _acquire_single_instance_lock, _disable_autostart, _enable_autostart


def test_single_instance_lock_blocks_a_second_acquire(tmp_path):
    lock_path = tmp_path / "deskcats.lock"

    first = _acquire_single_instance_lock(lock_path)
    assert first is not None

    second = _acquire_single_instance_lock(lock_path)
    assert second is None

    first.close()

    third = _acquire_single_instance_lock(lock_path)
    assert third is not None
    third.close()


def test_enable_and_disable_autostart_writes_and_removes_file(tmp_path):
    autostart_path = tmp_path / "deskcats.desktop"

    assert _enable_autostart(autostart_path) == 0
    assert autostart_path.exists()
    content = autostart_path.read_text()
    assert "Type=Application" in content
    assert "Exec=" in content

    assert _disable_autostart(autostart_path) == 0
    assert not autostart_path.exists()

    assert _disable_autostart(autostart_path) == 0
