import tempfile
from unittest import mock
from unittest.mock import call
from coppercomm.device_adb import adb_interface
from coppercomm.device_adb.adb_interface import DeviceState
from coppercomm.device_common.exceptions import RemountError

test_adb_id = "xyz"


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_check_output(mock_execute):
    mock_execute.return_value = "a.txt b.txt"
    result = adb_interface.Adb(adb_device_id=test_adb_id).check_output(command="ls -la")
    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "ls", "-la"],
        assert_ok=True,
        regrep=None,
        timeout=None,
    )
    assert "a.txt b.txt" == result


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_check_output_shell(mock_execute):
    mock_execute.return_value = None
    adb_interface.Adb(adb_device_id=test_adb_id).check_output(command="ls", shell=True)
    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "shell", "ls"],
        assert_ok=True,
        regrep=None,
        timeout=None,
    )


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_shell(mock_execute):
    mock_execute.return_value = None
    adb_interface.Adb(adb_device_id=test_adb_id).shell(command="ls")
    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "shell", "ls"],
        assert_ok=True,
        regrep=None,
        timeout=None,
    )


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_gain_root_permissions(mock_execute):
    mock_execute.return_value = None

    adb_interface.Adb(adb_device_id=test_adb_id).gain_root_permissions()

    calls = [
        call(
            ["adb", "-s", test_adb_id, "wait-for-any"],
            assert_ok=True,
            regrep=None,
            timeout=60.0,
        ),
        call(
            ["adb", "-s", test_adb_id, "root"], assert_ok=True, regrep=None, timeout=20
        ),
        call(
            ["adb", "-s", test_adb_id, "wait-for-any"],
            assert_ok=True,
            regrep=None,
            timeout=10,
        ),
    ]
    mock_execute.assert_has_calls(calls)


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_get_state(mock_execute):
    mock_execute.return_value = "device"

    result = adb_interface.Adb(adb_device_id=test_adb_id).get_state()

    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "get-state"], assert_ok=True, regrep=None, timeout=3
    )
    assert DeviceState.DEVICE == result


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_wait_for_state(mock_execute):
    mock_execute.return_value = None
    adb_interface.Adb(adb_device_id=test_adb_id).wait_for_state(
        state=DeviceState.RECOVERY
    )
    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "wait-for-recovery"],
        assert_ok=True,
        regrep=None,
        timeout=None,
    )


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_push(mock_execute):
    mock_execute.return_value = None

    with tempfile.TemporaryDirectory() as tmpdir:
        adb_interface.Adb(adb_device_id=test_adb_id).push(
            local_path=tmpdir,
            on_device_path="/dev/disk/test",
            create_dest_dir=True,
            sync=True,
        )

    calls = [
        call(
            ["adb", "-s", test_adb_id, "shell", "mkdir", "-p", "/dev/disk/test"],
            assert_ok=True,
            regrep=None,
            timeout=None,
        ),
        call(
            ["adb", "-s", test_adb_id, "push", tmpdir, "/dev/disk/test"],
            assert_ok=True,
            regrep=None,
            timeout=None,
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "sync"],
            assert_ok=True,
            regrep=None,
            timeout=60,
        ),
    ]
    mock_execute.assert_has_calls(calls)


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_push_no_files(mock_execute):
    mock_execute.return_value = None

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            adb_interface.Adb(adb_device_id=test_adb_id).push(
                local_path=f"{tmpdir}/empty",
                on_device_path="/dev/disk/test",
                create_dest_dir=True,
                sync=True,
            )
            assert False, "adb.push should have raised an exception"
        except ValueError:
            assert True

    mock_execute.assert_not_called()


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_pull(mock_execute):
    mock_execute.return_value = None

    with tempfile.TemporaryDirectory() as tmpdir1, tempfile.TemporaryDirectory() as tmpdir2:
        adb_interface.Adb(adb_device_id=test_adb_id).pull(
            local_path=tmpdir1, on_device_path=tmpdir2
        )

    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "pull", tmpdir2, tmpdir1],
        assert_ok=True,
        regrep=None,
        timeout=None,
    )


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_get_boot_id(mock_execute):
    mock_execute.return_value = "123"

    result = adb_interface.Adb(adb_device_id=test_adb_id).get_boot_id()

    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "shell", "cat", "/proc/sys/kernel/random/boot_id"],
        assert_ok=True,
        regrep=None,
        timeout=None,
    )
    assert "123" == result


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_trigger_reboot(mock_execute):
    mock_execute.return_value = None
    adb_interface.Adb(adb_device_id=test_adb_id).trigger_reboot()
    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "shell", "reboot"],
        assert_ok=True,
        regrep=None,
        timeout=None,
    )


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_reboot_and_wait(mock_execute):
    mock_execute.side_effect = ["123", None, None, None, None, "456"]
    adb_interface.Adb(adb_device_id=test_adb_id).reboot_and_wait()

    calls = [
        call(
            [
                "adb",
                "-s",
                test_adb_id,
                "shell",
                "cat",
                "/proc/sys/kernel/random/boot_id",
            ],
            assert_ok=True,
            regrep=None,
            timeout=None,
        ),
        call(
            ["adb", "-s", test_adb_id, "wait-for-any"],
            assert_ok=True,
            regrep=None,
            timeout=10,
        ),
        call(
            ["adb", "-s", test_adb_id, "root"], assert_ok=True, regrep=None, timeout=20
        ),
        call(
            ["adb", "-s", test_adb_id, "wait-for-any"],
            assert_ok=True,
            regrep=None,
            timeout=10,
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "reboot"],
            assert_ok=True,
            regrep=None,
            timeout=None,
        ),
        call(
            [
                "adb",
                "-s",
                test_adb_id,
                "shell",
                "cat",
                "/proc/sys/kernel/random/boot_id",
            ],
            assert_ok=True,
            regrep=None,
            timeout=None,
        ),
    ]

    mock_execute.assert_has_calls(calls)


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_reboot_and_wait_unable_to_reboot(mock_execute):
    mock_execute.side_effect = ["123", None, None, None, None, "123"]
    try:
        adb_interface.Adb(adb_device_id=test_adb_id).reboot_and_wait(timeout=1)
        assert False, "adb.reboot_and_wait should have raised an exception"
    except AssertionError:
        assert True

    calls = [
        call(
            [
                "adb",
                "-s",
                test_adb_id,
                "shell",
                "cat",
                "/proc/sys/kernel/random/boot_id",
            ],
            assert_ok=True,
            regrep=None,
            timeout=None,
        ),
        call(
            ["adb", "-s", test_adb_id, "wait-for-any"],
            assert_ok=True,
            regrep=None,
            timeout=10,
        ),
        call(
            ["adb", "-s", test_adb_id, "root"], assert_ok=True, regrep=None, timeout=20
        ),
        call(
            ["adb", "-s", test_adb_id, "wait-for-any"],
            assert_ok=True,
            regrep=None,
            timeout=10,
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "reboot"],
            assert_ok=True,
            regrep=None,
            timeout=None,
        ),
        call(
            [
                "adb",
                "-s",
                test_adb_id,
                "shell",
                "cat",
                "/proc/sys/kernel/random/boot_id",
            ],
            assert_ok=True,
            regrep=None,
            timeout=None,
        ),
    ]

    mock_execute.assert_has_calls(calls)


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_mount_filesytem_as_root(mock_execute):
    mock_execute.side_effect = [None, None, None, None, "remount succeeded "]
    adb_interface.Adb(adb_device_id=test_adb_id).mount_filesytem_as_root()

    calls = [
        call(
            ["adb", "-s", test_adb_id, "wait-for-any"],
            assert_ok=True,
            regrep=None,
            timeout=60.0,
        ),
        call(
            ["adb", "-s", test_adb_id, "root"], assert_ok=True, regrep=None, timeout=20
        ),
        call(
            ["adb", "-s", test_adb_id, "wait-for-any"],
            assert_ok=True,
            regrep=None,
            timeout=10,
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "disable-verity"],
            assert_ok=False,
            regrep=None,
            timeout=None,
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "remount"],
            assert_ok=False,
            regrep=None,
            timeout=None,
        ),
    ]

    mock_execute.assert_has_calls(calls)


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_mount_filesytem_as_root_unable_to_remount(mock_execute):
    mock_execute.side_effect = [
        None,
        None,
        None,
        None,
        "remount failed ",
        "123",
        None,
        None,
        None,
        None,
        "456",
        None,
        None,
        None,
        "remount failed ",
    ]
    try:
        adb_interface.Adb(adb_device_id=test_adb_id).mount_filesytem_as_root()
        assert False, "adb.mount_filesytem_as_root should have raised an exception"
    except RemountError:
        assert True

    calls = [
        call(
            ["adb", "-s", test_adb_id, "wait-for-any"],
            assert_ok=True,
            regrep=None,
            timeout=60.0,
        ),
        call(
            ["adb", "-s", test_adb_id, "root"], assert_ok=True, regrep=None, timeout=20
        ),
        call(
            ["adb", "-s", test_adb_id, "wait-for-any"],
            assert_ok=True,
            regrep=None,
            timeout=10,
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "disable-verity"],
            assert_ok=False,
            regrep=None,
            timeout=None,
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "remount"],
            assert_ok=False,
            regrep=None,
            timeout=None,
        ),
        call(
            [
                "adb",
                "-s",
                test_adb_id,
                "shell",
                "cat",
                "/proc/sys/kernel/random/boot_id",
            ],
            assert_ok=True,
            regrep=None,
            timeout=None,
        ),
        call(
            ["adb", "-s", test_adb_id, "wait-for-any"],
            assert_ok=True,
            regrep=None,
            timeout=10,
        ),
        call(
            ["adb", "-s", test_adb_id, "root"], assert_ok=True, regrep=None, timeout=20
        ),
        call(
            ["adb", "-s", test_adb_id, "wait-for-any"],
            assert_ok=True,
            regrep=None,
            timeout=10,
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "reboot"],
            assert_ok=True,
            regrep=None,
            timeout=None,
        ),
        call(
            [
                "adb",
                "-s",
                test_adb_id,
                "shell",
                "cat",
                "/proc/sys/kernel/random/boot_id",
            ],
            assert_ok=True,
            regrep=None,
            timeout=None,
        ),
        call(
            ["adb", "-s", test_adb_id, "wait-for-any"],
            assert_ok=True,
            regrep=None,
            timeout=60.0,
        ),
        call(
            ["adb", "-s", test_adb_id, "root"], assert_ok=True, regrep=None, timeout=20
        ),
        call(
            ["adb", "-s", test_adb_id, "wait-for-any"],
            assert_ok=True,
            regrep=None,
            timeout=10,
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "remount"],
            assert_ok=False,
            regrep=None,
            timeout=None,
        ),
    ]

    mock_execute.assert_has_calls(calls)
