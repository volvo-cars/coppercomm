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

import contextlib
import enum
import glob
import logging
import os
import shlex
import subprocess
import time
import typing
from typing import Union
import datetime

from coppercomm.device_common.exceptions import RemountError, CommandFailedError
from coppercomm.device_common.local_console import execute_command


_logger = logging.getLogger("adb_interface")
_logger.setLevel(logging.DEBUG)

_kernel_boot_id_path = "/proc/sys/kernel/random/boot_id"

Pathish = Union[str, os.PathLike]

class DeviceState(enum.Enum):
    DEVICE = "device"
    RECOVERY = "recovery"
    OFFLINE = "offline"


class Adb:
    """
    Interact with adb using subprocess. All methods may rise TimeoutExpiredError if
    command execution exceeded provided 'timeout' limit or CommandFailedError if assert_ok
    is True and exit code not equal to 0

    :param adb_device_id: Serial number / ID of adb-compatible device. If None or empty then
        '-s' flag will NOT be used at all.
    """

    def __init__(self, adb_device_id: typing.Optional[str] = None) -> None:
        self._adb_device_id = adb_device_id
        self._adb_cmd = ["adb"]
        if adb_device_id:
            self._adb_cmd.extend(["-s", adb_device_id])

    def check_output(
        self,
        command: typing.Union[str, typing.List[str]],
        *,
        shell: bool = False,
        assert_ok: bool = True,
        regrep: typing.Union[str, typing.Pattern[str], None] = None,
        timeout: typing.Optional[float] = None,
        log_output: bool = True
    ) -> str:
        """
        Execute command on adb device. If 'command' passed as a string it will be splitted by shlex.split

        :param command: Command to be executed
        :param shell: Use 'shell' subcommand to execute 'command' if True
        :param assert_ok: If True - check the exit code and raise an exception if command failed
        :param regrep: Filter lines in the output of the command with regex
        :param timeout: Timeout for a command
        :param log_output: Whether to send output to the logger
        :returns: Command's output (stdout and stderr combined)
        """

        if isinstance(command, str):
            command = shlex.split(command)
        if shell:
            command.insert(0, "shell")

        adb_command = self._adb_cmd + command
        return execute_command(
            adb_command, assert_ok=assert_ok, regrep=regrep, timeout=timeout, log_output=log_output
        )

    def shell(
        self,
        command: typing.Union[str, typing.List[str]],
        *,
        assert_ok: bool = True,
        regrep: typing.Union[str, typing.Pattern[str], None] = None,
        timeout: typing.Optional[float] = None,
        log_output: bool = True
    ) -> str:
        """
        Same as using check_output with shell=True argument

        :param command: Command to be executed
        :param assert_ok: If True - check the exit code and raise an exception if command failed
        :param regrep: Filter lines in the output of the command with regex
        :param timeout: Timeout for a command
        :param log_output: Whether to send output to the logger
        :returns: Command's output (stdout and stderr combined)
        """
        return self.check_output(
            command, shell=True, assert_ok=assert_ok, regrep=regrep, timeout=timeout, log_output=log_output
        )

    def gain_root_permissions(self, *, timeout: float = 60.0, retries: int = 3) -> None:
        """
        Gain root permissions (adb root). Wait for device in current state after
        requesting for root permissions

        :param timeout: Timeout for device to be available in current state AFTER requesting
            for root permissions
        :param retries: Retries for 'root' command - the command may failed sometimes, but passes
            after retried
        """
        self._log("Gaining ADB root permissions...")
        current_state = self.get_state()

        is_already_root = self.shell("whoami").strip() == "root"
        if is_already_root:
            self._log("User is already root, no need to gain permissions")
            return

        # hard to get rid of retries :/
        # it's far more robust this way
        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                # time needed for 'root' cmd vary and hard to say if 10s is enough so 20s is set to be sure
                self.check_output("root", shell=False, assert_ok=True, timeout=20)
            except AssertionError as exc:
                self._log(
                    "Gaining root permissions attempt {} failed: {}".format(
                        attempt, exc
                    )
                )
                time.sleep(3)
                last_exc = exc
            else:
                # Device may be unavailable for some time after 'adb root' command
                self.wait_for_state(current_state, timeout=10)
                return

        raise CommandFailedError("Gaining root permissions failed") from last_exc

    def get_state(self, assert_ok=True) -> DeviceState:
        """
        Get current device state

        :returns: Current DeviceState (DeviceState.DEVICE/DeviceState.RECOVERY)
        """
        current_state = self.check_output(
            "get-state", shell=False, assert_ok=assert_ok, timeout=3
        )
        return DeviceState(current_state.strip())

    def kill_server(self, log_output: bool = True) -> str:
        """Kill adb server.

        :param log_output: Whether to print logs.
        :return: Commands stdout
        """
        return self.check_output("kill-server", log_output=log_output)

    def wait_for_state(
        self,
        state: typing.Union[str, DeviceState] = DeviceState.DEVICE,
        *,
        timeout: float = 120,
    ) -> None:
        """
        Wait for device in given state (adb wait-for-*)

        :param state: Desired state of the device. Default is DEVICE
        :param timeout: Timeout for waiting
        """
        expected_state = DeviceState(state)
        monotonic_timeout = time.monotonic() + timeout

        cur_state = None
        while time.monotonic() < monotonic_timeout:
            with contextlib.suppress(CommandFailedError):
                output = self.check_output("get-state", log_output=False, assert_ok=False).strip()
                if "device unauthorized" in output:
                    self.kill_server(log_output=False)
                    time.sleep(2)
                elif (cur_state := DeviceState(output)) == expected_state:
                    self._log("Device in {} state".format(expected_state))
                    return
            time.sleep(2)
        raise Exception(f"Android state '{cur_state}' != {expected_state} after {timeout}s!")

    def wait_for_boot_complete(self, timeout: float = 240) -> None:
        """Wait for android to completely boot up.

        Waits for property: sys.boot_completed == 1
        """
        _logger.debug("Waiting for android property sys.boot_completed == 1 (timeout %ds)..", timeout)

        monotonic_timeout = time.monotonic() + timeout

        while time.monotonic() < monotonic_timeout:
            with contextlib.suppress(CommandFailedError):
                output = self.shell("getprop sys.boot_completed", log_output=False, assert_ok=False).strip()
                if "device unauthorized" in output:
                    self.kill_server(log_output=False)
                    time.sleep(2)
                elif output == "1":
                    return
            time.sleep(2)
        raise Exception(f"Android property 'sys.boot_completed' != 1 after {timeout}s!")

    def push(
        self,
        local_path: Pathish,
        on_device_path: Pathish,
        *,
        create_dest_dir: bool = False,
        sync: bool = False,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """
        Push files/directory to the device - glob pattern and env variables are resolved.

        :param local_path: Files/Directory to be pushed to the device
        :param on_device_path: Destination path to store files/directory pushed to the device
        :param create_dest_dir: Create directory 'on_device_path' before pushing
            the file/directory - avoiding the file/directory to be renamed and pushed as
            'on_device_path' if pushing to nonexisting directory
        :param sync: If True - run sync command after pushing all the data finished
        :param timeout: Timeout for push operation for each element if pushing multiple
        """
        path_resolved = os.path.expandvars(os.path.expanduser(str(local_path)))
        to_push_list = glob.glob(path_resolved)
        if not to_push_list:
            raise ValueError("No files found to be pushed: {}".format(local_path))

        if create_dest_dir:
            self.check_output("mkdir -p {}".format(str(on_device_path)), shell=True)
        for to_push_element in to_push_list:
            self._log("Pushing {} to {}".format(to_push_element, str(on_device_path)))
            self.check_output(
                "push {} {}".format(to_push_element, str(on_device_path)), timeout=timeout
            )

        if sync:
            self.shell("sync", timeout=60)

    def pull(
        self,
        on_device_path: str,
        local_path: str,
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """
        Pull files/directory from the device

        :param on_device_path: Files/Directory to be pulled from the device
        :param local_path: Destination path to store files/directory pulled from the device
        :param timeout: Timeout for the operation to complete
        """
        self._log(f"Pulling {on_device_path} to {local_path}")
        pull_cmd = f"pull {shlex.quote(on_device_path)} {shlex.quote(local_path)}"
        self.check_output(pull_cmd, timeout=timeout)

    def _log(self, msg: str) -> None:
        _logger.debug("{}: {}".format(self._adb_device_id or "ADB_DEVICE", msg))

    def get_boot_id(self, log_output=True):
        boot_id = self.shell(f"cat {_kernel_boot_id_path}", log_output=log_output)
        if log_output:
            _logger.debug(f"Current boot_id: {boot_id}")
        return boot_id

    def trigger_reboot(self, mode=None):
        """Trigger adb shell reboot.

        :param mode: Allows to specify reboot mode e.g. recovery or fastboot
        """
        _logger.info("Triggering reboot over adb")
        if mode:
            self.shell(f"reboot {mode}")
        else:
            self.shell("reboot")

    def reboot_and_wait(self, timeout=120, mode=None):
        initial_boot_id = self.get_boot_id()

        datetime_timeout = datetime.datetime.now() + datetime.timedelta(seconds=timeout)

        self.gain_root_permissions(timeout=10)
        self.trigger_reboot(mode)

        last_e = None
        _logger.info(f"Waiting for new android boot_id (timeout %ds)", timeout)
        while datetime.datetime.now() < datetime_timeout:
            try:
                time.sleep(1)
                if initial_boot_id != (boot_id := self.get_boot_id(log_output=False)):
                    _logger.info("Kernel boot_id changed to %s. Reboot completed.", boot_id)
                    return
            except AssertionError as e:
                last_e = e

        raise AssertionError(f"Failed to restart over adb") from last_e

    @property
    def device_id(self):
        return self._adb_device_id

    @device_id.setter
    def device_id(self, value: str):
        self._adb_device_id = value
        self._adb_cmd = ["adb", "-s", value]

    def mount_filesytem_as_root(self):
        self.gain_root_permissions()
        self.shell(command="disable-verity", assert_ok=False)
        out = self.shell(command="remount", assert_ok=False).strip()

        if out != "remount succeeded":
            self.reboot_and_wait()
            self.gain_root_permissions()
            out = self.shell(command="remount", assert_ok=False).strip()

            if out != "remount succeeded":
                raise RemountError("Failed to mount filesystem as root: {}".format(out))

    def perform_factory_reset(self):
        """Perform factory reset by wiping data in recovery mode.

        Wait for system restart and complete boot.
        """
        _logger.info("Performing factory reset through recovery..")
        self.reboot_and_wait(mode="recovery")
        self.wait_for_state(DeviceState.RECOVERY, timeout=120)
        self.gain_root_permissions()
        self.shell("recovery --wipe_data")
        self.wait_for_state(DeviceState.DEVICE)
        self.wait_for_boot_complete()

    @staticmethod
    def get_adb_version() -> int:
        """Read Adb main version.

        Example printout:

            Android Debug Bridge version 1.0.41
            Version 34.0.0-9570255
            Installed as /usr/local/bin/adb

        Expected result: 34
        """
        output = subprocess.check_output(["adb", "--version"])
        version = int(output.splitlines()[1].split()[1].partition(b".")[0])
        return version
