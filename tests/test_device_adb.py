# Copyright 2022 Volvo Cars
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#    http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
        ["adb", "-s", test_adb_id, "ls", "-la"], assert_ok=True, regrep=None, timeout=30, log_output=True
    )
    assert "a.txt b.txt" == result


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_check_output_shell(mock_execute):
    mock_execute.return_value = None
    adb_interface.Adb(adb_device_id=test_adb_id).check_output(command="ls", shell=True)
    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "shell", "ls"], assert_ok=True, regrep=None, timeout=30, log_output=True
    )


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_shell(mock_execute):
    mock_execute.return_value = None
    adb_interface.Adb(adb_device_id=test_adb_id).shell(command="ls")
    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "shell", "ls"], assert_ok=True, regrep=None, timeout=30, log_output=True
    )


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_gain_root_permissions(mock_execute):
    mock_execute.side_effect = ["device", "shell", None, "device", "root"]
    adb_interface.Adb(adb_device_id=test_adb_id).gain_root_permissions()

    calls = [
        call(["adb", "-s", test_adb_id, "get-state"], assert_ok=False, regrep=None, timeout=5, log_output=False),
        call(["adb", "-s", test_adb_id, "shell", "whoami"], assert_ok=True, regrep=None, timeout=30, log_output=True),
        call(["adb", "-s", test_adb_id, "root"], assert_ok=False, regrep=None, timeout=30, log_output=True),
        call(["adb", "-s", test_adb_id, "get-state"], assert_ok=False, regrep=None, timeout=5, log_output=False),
        call(["adb", "-s", test_adb_id, "shell", "whoami"], assert_ok=True, regrep=None, timeout=30, log_output=True),
    ]
    mock_execute.assert_has_calls(calls)


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_gain_root_permissions_already_root(mock_execute):
    mock_execute.side_effect = ["device", "root"]
    adb_interface.Adb(adb_device_id=test_adb_id).gain_root_permissions()

    calls = [
        call(["adb", "-s", test_adb_id, "get-state"], assert_ok=False, regrep=None, timeout=5, log_output=False),
        call(["adb", "-s", test_adb_id, "shell", "whoami"], assert_ok=True, regrep=None, timeout=30, log_output=True),
    ]
    mock_execute.assert_has_calls(calls)


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_get_state(mock_execute):
    mock_execute.return_value = "device"

    result = adb_interface.Adb(adb_device_id=test_adb_id).get_state()

    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "get-state"], assert_ok=False, regrep=None, timeout=5, log_output=False
    )
    assert DeviceState.DEVICE == result


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_get_state_no_device(mock_execute):
    mock_execute.return_value = f"device {test_adb_id} not found"

    result = adb_interface.Adb(adb_device_id=test_adb_id).get_state()

    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "get-state"], assert_ok=False, regrep=None, timeout=5, log_output=False
    )
    assert DeviceState.NO_ADB_DEVICE == result


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_wait_for_state(mock_execute):
    mock_execute.return_value = "recovery"
    adb_interface.Adb(adb_device_id=test_adb_id).wait_for_state(state=DeviceState.RECOVERY)
    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "get-state"], assert_ok=False, regrep=None, timeout=5, log_output=False
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
            timeout=30,
            log_output=True,
        ),
        call(
            ["adb", "-s", test_adb_id, "push", tmpdir, "/dev/disk/test"],
            assert_ok=True,
            regrep=None,
            timeout=60,
            log_output=True,
        ),
        call(["adb", "-s", test_adb_id, "shell", "sync"], assert_ok=True, regrep=None, timeout=60, log_output=True),
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
        adb_interface.Adb(adb_device_id=test_adb_id).pull(local_path=tmpdir1, on_device_path=tmpdir2)

    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "pull", tmpdir2, tmpdir1], assert_ok=True, regrep=None, timeout=60, log_output=True
    )


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_get_boot_id(mock_execute):
    mock_execute.return_value = "123"

    result = adb_interface.Adb(adb_device_id=test_adb_id).get_boot_id()

    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "shell", "cat", "/proc/sys/kernel/random/boot_id"],
        assert_ok=True,
        regrep=None,
        timeout=30,
        log_output=True,
    )
    assert "123" == result


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_trigger_reboot(mock_execute):
    mock_execute.return_value = None
    adb_interface.Adb(adb_device_id=test_adb_id).trigger_reboot()
    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "reboot"], assert_ok=True, regrep=None, timeout=30, log_output=True
    )


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_reboot_and_wait(mock_execute):
    mock_execute.side_effect = ["123", "device", "shell", None, None, None, "456"]
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
            timeout=30,
            log_output=True,
        ),
        call(["adb", "-s", test_adb_id, "reboot"], assert_ok=True, regrep=None, timeout=30, log_output=True),
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
            timeout=30,
            log_output=False,
        ),
    ]

    mock_execute.assert_has_calls(calls)


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_reboot_and_wait_unable_to_reboot(mock_execute):
    mock_execute.side_effect = ["123", "device", "shell", None, None, None, "123"]
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
            timeout=30,
            log_output=True,
        ),
        call(["adb", "-s", test_adb_id, "reboot"], assert_ok=True, regrep=None, timeout=30, log_output=True),
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
            timeout=30,
            log_output=False,
        ),
    ]

    mock_execute.assert_has_calls(calls)


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_mount_filesytem_as_root(mock_execute):
    mock_execute.side_effect = ["device", "shell", None, "device", "root", None, "remount succeeded"]
    adb_interface.Adb(adb_device_id=test_adb_id).mount_filesytem_as_root()

    calls = [
        call(["adb", "-s", test_adb_id, "get-state"], assert_ok=False, regrep=None, timeout=5, log_output=False),
        call(["adb", "-s", test_adb_id, "shell", "whoami"], assert_ok=True, regrep=None, timeout=30, log_output=True),
        call(["adb", "-s", test_adb_id, "root"], assert_ok=False, regrep=None, timeout=30, log_output=True),
        call(["adb", "-s", test_adb_id, "get-state"], assert_ok=False, regrep=None, timeout=5, log_output=False),
        call(["adb", "-s", test_adb_id, "shell", "whoami"], assert_ok=True, regrep=None, timeout=30, log_output=True),
        call(
            ["adb", "-s", test_adb_id, "shell", "disable-verity"],
            assert_ok=False,
            regrep=None,
            timeout=30,
            log_output=True,
        ),
        call(["adb", "-s", test_adb_id, "shell", "remount"], assert_ok=False, regrep=None, timeout=30, log_output=True),
    ]
    mock_execute.assert_has_calls(calls)


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_mount_filesytem_as_root_unable_to_remount(mock_execute):
    mock_execute.side_effect = [
        "device",
        "shell",
        None,
        "device",
        "root",
        None,
        "remount failed",
        "123",
        None,
        "321",
        "1",
        "device",
        "shell",
        None,
        "device",
        "root",
        "remount failed",
    ]
    try:
        adb_interface.Adb(adb_device_id=test_adb_id).mount_filesytem_as_root()
        assert False, "adb.mount_filesytem_as_root should have raised an exception"
    except RemountError:
        assert True

    calls = [
        call(["adb", "-s", test_adb_id, "get-state"], assert_ok=False, regrep=None, timeout=5, log_output=False),
        call(["adb", "-s", test_adb_id, "shell", "whoami"], assert_ok=True, regrep=None, timeout=30, log_output=True),
        call(["adb", "-s", test_adb_id, "root"], assert_ok=False, regrep=None, timeout=30, log_output=True),
        call(["adb", "-s", test_adb_id, "get-state"], assert_ok=False, regrep=None, timeout=5, log_output=False),
        call(["adb", "-s", test_adb_id, "shell", "whoami"], assert_ok=True, regrep=None, timeout=30, log_output=True),
        call(
            ["adb", "-s", test_adb_id, "shell", "disable-verity"],
            assert_ok=False,
            regrep=None,
            timeout=30,
            log_output=True,
        ),
        call(["adb", "-s", test_adb_id, "shell", "remount"], assert_ok=False, regrep=None, timeout=30, log_output=True),
        # REBOOT AND WAIT
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
            timeout=30,
            log_output=True,
        ),
        call(["adb", "-s", test_adb_id, "reboot"], assert_ok=True, regrep=None, timeout=30, log_output=True),
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
            timeout=30,
            log_output=False,
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "getprop", "sys.boot_completed"],
            assert_ok=False,
            regrep=None,
            timeout=30,
            log_output=False,
        ),
        call(["adb", "-s", test_adb_id, "get-state"], assert_ok=False, regrep=None, timeout=5, log_output=False),
        call(["adb", "-s", test_adb_id, "shell", "whoami"], assert_ok=True, regrep=None, timeout=30, log_output=True),
        call(["adb", "-s", test_adb_id, "root"], assert_ok=False, regrep=None, timeout=30, log_output=True),
        call(["adb", "-s", test_adb_id, "get-state"], assert_ok=False, regrep=None, timeout=5, log_output=False),
        call(["adb", "-s", test_adb_id, "shell", "whoami"], assert_ok=True, regrep=None, timeout=30, log_output=True),
        call(["adb", "-s", test_adb_id, "shell", "remount"], assert_ok=False, regrep=None, timeout=30, log_output=True),
    ]
    mock_execute.assert_has_calls(calls)
