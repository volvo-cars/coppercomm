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
from coppercomm.device_common.exceptions import CopperCommError, RemountError

test_adb_id = "xyz"

import pytest

ADB_ATTRIBUTES_CONFLICT_ERROR = "Cannot specify both 'adb_device_id' and 'ignore_ids' at the same time."


def test_adb_consturctor_device_id_passed():
    adb_instance = adb_interface.Adb(adb_device_id=mock.sentinel.adb_device_id)

    assert adb_instance._adb_device_id == mock.sentinel.adb_device_id
    assert adb_instance._adb_cmd == ["adb", "-s", mock.sentinel.adb_device_id]
    assert adb_instance.ignore_ids == set()


def test_adb_consturctor_pass_ignore_ids():
    adb_instance = adb_interface.Adb(ignore_ids={"id1", "id2"})

    assert adb_instance._adb_device_id == None
    assert adb_instance._adb_cmd == ["adb"]
    assert adb_instance.ignore_ids == {"id1", "id2"}


def test_adb_consturctor_raise_error():
    with pytest.raises(CopperCommError, match=ADB_ATTRIBUTES_CONFLICT_ERROR):
        adb_interface.Adb(adb_device_id=mock.sentinel.adb_device_id, ignore_ids={"id1", "id2"})


def test_adb_consturctor_raise_error_while_set_ignore_ids():
    adb_instance = adb_interface.Adb(adb_device_id=mock.sentinel.adb_device_id)

    with pytest.raises(CopperCommError, match=ADB_ATTRIBUTES_CONFLICT_ERROR):
        adb_instance.ignore_ids = {"id1", "id2"}


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_check_output(mock_execute):
    mock_execute.return_value = "a.txt b.txt"
    result = adb_interface.Adb(adb_device_id=test_adb_id).check_output(command="ls -la")
    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "ls", "-la"],
        assert_ok=True,
        regrep=None,
        timeout=30,
        log_output=True,
        valid_exit_codes=(0,),
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
        timeout=30,
        log_output=True,
        valid_exit_codes=(0,),
    )


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_shell(mock_execute):
    mock_execute.return_value = None
    adb_interface.Adb(adb_device_id=test_adb_id).shell(command="ls")
    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "shell", "ls"],
        assert_ok=True,
        regrep=None,
        timeout=30,
        log_output=True,
        valid_exit_codes=(0,),
    )


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_gain_root_permissions(mock_execute):
    mock_execute.side_effect = ["device", "shell", None, "device", "root"]
    adb_interface.Adb(adb_device_id=test_adb_id).gain_root_permissions()

    calls = [
        call(
            ["adb", "-s", test_adb_id, "get-state"],
            assert_ok=False,
            regrep=None,
            timeout=5,
            log_output=False,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "whoami"],
            assert_ok=True,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "root"],
            assert_ok=False,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "get-state"],
            assert_ok=False,
            regrep=None,
            timeout=5,
            log_output=False,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "whoami"],
            assert_ok=True,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
    ]
    mock_execute.assert_has_calls(calls)


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_gain_root_permissions_already_root(mock_execute):
    mock_execute.side_effect = ["device", "root"]
    adb_interface.Adb(adb_device_id=test_adb_id).gain_root_permissions()

    calls = [
        call(
            ["adb", "-s", test_adb_id, "get-state"],
            assert_ok=False,
            regrep=None,
            timeout=5,
            log_output=False,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "whoami"],
            assert_ok=True,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
    ]
    mock_execute.assert_has_calls(calls)


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_get_state(mock_execute):
    mock_execute.return_value = "device"

    result = adb_interface.Adb(adb_device_id=test_adb_id).get_state()

    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "get-state"],
        assert_ok=False,
        regrep=None,
        timeout=5,
        log_output=False,
        valid_exit_codes=(0,),
    )
    assert DeviceState.DEVICE == result


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_get_state_no_device(mock_execute):
    mock_execute.return_value = f"device {test_adb_id} not found"

    result = adb_interface.Adb(adb_device_id=test_adb_id).get_state()

    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "get-state"],
        assert_ok=False,
        regrep=None,
        timeout=5,
        log_output=False,
        valid_exit_codes=(0,),
    )
    assert DeviceState.NO_ADB_DEVICE == result


@mock.patch("coppercomm.device_adb.adb_interface.Adb.get_all_devices")
@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_get_state_ignore_ids(mock_execute, all_devices_m):
    mock_execute.return_value = "device"
    all_devices_m.return_value = {test_adb_id, "id1", "id2"}

    result = adb_interface.Adb(ignore_ids={"id1", "id2"}).get_state()

    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "get-state"],
        assert_ok=False,
        regrep=None,
        timeout=5,
        log_output=False,
        valid_exit_codes=(0,),
    )
    assert DeviceState.DEVICE == result


@mock.patch("coppercomm.device_adb.adb_interface.Adb.get_all_devices")
def test_adb_get_state_ignore_ids_more_than_one_unknown(all_devices_m):
    all_devices_m.return_value = {test_adb_id, "id1", "id2"}

    with pytest.raises(CopperCommError, match="More than one ADB unknown device is connected."):
        adb_interface.Adb(ignore_ids={"id1"}).get_state()


@mock.patch("coppercomm.device_adb.adb_interface.Adb.get_all_devices")
def test_adb_get_state_ignore_ids_no_adb_devices(all_devices_m):
    all_devices_m.return_value = set()

    result = adb_interface.Adb(ignore_ids={"id1"}).get_state()

    assert DeviceState.NO_ADB_DEVICE == result


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_wait_for_state(mock_execute):
    mock_execute.return_value = "recovery"
    adb_interface.Adb(adb_device_id=test_adb_id).wait_for_state(state=DeviceState.RECOVERY)
    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "get-state"],
        assert_ok=False,
        regrep=None,
        timeout=5,
        log_output=False,
        valid_exit_codes=(0,),
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
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "push", tmpdir, "/dev/disk/test"],
            assert_ok=True,
            regrep=None,
            timeout=60,
            log_output=True,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "sync"],
            assert_ok=True,
            regrep=None,
            timeout=60,
            log_output=True,
            valid_exit_codes=(0,),
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
        adb_interface.Adb(adb_device_id=test_adb_id).pull(local_path=tmpdir1, on_device_path=tmpdir2)

    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "pull", tmpdir2, tmpdir1],
        assert_ok=True,
        regrep=None,
        timeout=60,
        log_output=True,
        valid_exit_codes=(0,),
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
        valid_exit_codes=(0,),
    )
    assert "123" == result


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_trigger_reboot(mock_execute):
    mock_execute.return_value = None
    adb_interface.Adb(adb_device_id=test_adb_id).trigger_reboot()
    mock_execute.assert_called_once_with(
        ["adb", "-s", test_adb_id, "reboot"],
        assert_ok=True,
        regrep=None,
        timeout=30,
        log_output=True,
        valid_exit_codes=(0,),
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
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "reboot"],
            assert_ok=True,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
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
            timeout=30,
            log_output=False,
            valid_exit_codes=(0,),
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
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "reboot"],
            assert_ok=True,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
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
            timeout=30,
            log_output=False,
            valid_exit_codes=(0,),
        ),
    ]

    mock_execute.assert_has_calls(calls)


@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_adb_mount_filesytem_as_root(mock_execute):
    mock_execute.side_effect = [
        "device",
        "shell",
        None,
        "device",
        "root",
        None,
        "remount succeeded",
    ]
    adb_interface.Adb(adb_device_id=test_adb_id).mount_filesytem_as_root()

    calls = [
        call(
            ["adb", "-s", test_adb_id, "get-state"],
            assert_ok=False,
            regrep=None,
            timeout=5,
            log_output=False,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "whoami"],
            assert_ok=True,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "root"],
            assert_ok=False,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "get-state"],
            assert_ok=False,
            regrep=None,
            timeout=5,
            log_output=False,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "whoami"],
            assert_ok=True,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "disable-verity"],
            assert_ok=False,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "remount"],
            assert_ok=False,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
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
        call(
            ["adb", "-s", test_adb_id, "get-state"],
            assert_ok=False,
            regrep=None,
            timeout=5,
            log_output=False,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "whoami"],
            assert_ok=True,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "root"],
            assert_ok=False,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "get-state"],
            assert_ok=False,
            regrep=None,
            timeout=5,
            log_output=False,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "whoami"],
            assert_ok=True,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "disable-verity"],
            assert_ok=False,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "remount"],
            assert_ok=False,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
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
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "reboot"],
            assert_ok=True,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
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
            timeout=30,
            log_output=False,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "getprop", "sys.boot_completed"],
            assert_ok=False,
            regrep=None,
            timeout=30,
            log_output=False,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "get-state"],
            assert_ok=False,
            regrep=None,
            timeout=5,
            log_output=False,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "whoami"],
            assert_ok=True,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "root"],
            assert_ok=False,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "get-state"],
            assert_ok=False,
            regrep=None,
            timeout=5,
            log_output=False,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "whoami"],
            assert_ok=True,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
        call(
            ["adb", "-s", test_adb_id, "shell", "remount"],
            assert_ok=False,
            regrep=None,
            timeout=30,
            log_output=True,
            valid_exit_codes=(0,),
        ),
    ]
    mock_execute.assert_has_calls(calls)


@pytest.mark.parametrize(
    "device_ids, device_states, expected_devices",
    [
        (["172.20.21.253:5550", "emulator-5554"], ["device", "device"], {"172.20.21.253:5550", "emulator-5554"}),
        (["device1", "device11", "device111"], ["device", "recovery", "offline"], {"device1", "device11"}),
        (["device1"], ["unauthorized"], {}),
    ],
)
@mock.patch("coppercomm.device_adb.adb_interface.execute_command")
def test_get_all_devices(mock_execute, device_ids, device_states, expected_devices):
    mock_execute.return_value = "List of devices attached\n" + "\n".join(
        f"{device_id}\t{device_state}" for device_id, device_state in zip(device_ids, device_states)
    )

    result = adb_interface.Adb.get_all_devices()

    assert result.difference(expected_devices) == set()
