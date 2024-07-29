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
import datetime
import enum
import glob
import logging
import os
import pathlib
import re
import shlex
import subprocess
import time
import typing
from typing import Collection, Union

from coppercomm.device_common.exceptions import CommandFailedError, CopperCommError, RemountError
from coppercomm.device_common.local_console import execute_command

_logger = logging.getLogger("adb_interface")
_logger.setLevel(logging.DEBUG)

_kernel_boot_id_path = "/proc/sys/kernel/random/boot_id"

Pathish = Union[str, os.PathLike]


class DeviceState(enum.Enum):
    DEVICE = "device"
    RECOVERY = "recovery"
    OFFLINE = "offline"
    UNAUTHORIZED = "unauthorized"
    NO_ADB_DEVICE = "not found"


class Adb:
    """
    Interact with adb using subprocess. All methods may rise TimeoutExpiredError if
    command execution exceeded provided 'timeout' limit or CommandFailedError if assert_ok
    is True and exit code not equal to 0

    :param adb_device_id: Serial number / ID of adb-compatible device. If None or empty then
        '-s' flag will NOT be used at all.
    :param ignore_ids: Collection of ADB device IDs to ignore them while checking for device state.
            Prevents from reading state of wrong device.
    """

    def __init__(
        self, adb_device_id: typing.Optional[str] = None, ignore_ids: typing.Optional[typing.Collection[str]] = None
    ) -> None:
        Adb._validate_attributes(adb_device_id, ignore_ids)
        self._adb_device_id = adb_device_id
        self._adb_cmd = ["adb"]
        if adb_device_id:
            self._adb_cmd.extend(["-s", adb_device_id])
        self._ignore_ids = set(ignore_ids) if ignore_ids is not None else set()

    @staticmethod
    def _validate_attributes(adb_device_id: typing.Optional[str], ignore_ids: typing.Optional[typing.Collection[str]]):
        if adb_device_id and ignore_ids:
            raise CopperCommError("Cannot specify both 'adb_device_id' and 'ignore_ids' at the same time.")

    @property
    def ignore_ids(self):
        return self._ignore_ids

    @ignore_ids.setter
    def ignore_ids(self, ignore_ids: typing.Optional[typing.Collection[str]]):
        """Set ignore_ids and check if it is not set together with adb_device_id, otherwise raise an error."""
        Adb._validate_attributes(self._adb_device_id, ignore_ids)
        self._ignore_ids = set(ignore_ids) if ignore_ids is not None else set()

    @staticmethod
    def get_all_devices() -> typing.Set[str]:
        """Get all adb devices"""
        adb_devices_output = execute_command(["adb", "devices"], timeout=60).strip()

        # Example output:
        # List of devices attached
        # 172.20.21.253:5550	device
        # emulator-5554	device
        pattern = r"""
                        ([\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}\.[\d]{1,3}:[\d]{1,5}|\w+|\w+\-\w+)
                        # Matches a ip:port or device id or emulator id with "-" in the middle
                        \t                     # One tab
                        (?:device|recovery)    # Non capturing group for one of allowed device state.
                        (?:\Z|\n)              # Non capturing group for end of string or end of line
                        """

        return set(re.findall(pattern, adb_devices_output, re.VERBOSE))

    def check_output(
        self,
        command: typing.Union[str, typing.List[str]],
        *,
        shell: bool = False,
        assert_ok: bool = True,
        regrep: typing.Union[str, typing.Pattern[str], None] = None,
        timeout: typing.Optional[float] = 30,
        log_output: bool = True,
        valid_exit_codes: Collection = (0,),
    ) -> str:
        """
        Execute command on adb device. If 'command' passed as a string it will be splitted by shlex.split

        :param command: Command to be executed
        :param shell: Use 'shell' subcommand to execute 'command' if True
        :param assert_ok: If True - check the exit code and raise an exception if command failed
        :param regrep: Filter lines in the output of the command with regex
        :param timeout: Timeout for a command
        :param log_output: Whether to send output to the logger
        :param valid_exit_codes: List of exit codes to consider command successful
        :returns: Command's output (stdout and stderr combined)
        """

        if isinstance(command, str):
            command = shlex.split(command)
        if shell:
            command.insert(0, "shell")

        adb_command = self._adb_cmd + command
        return execute_command(
            adb_command,
            assert_ok=assert_ok,
            regrep=regrep,
            timeout=timeout,
            log_output=log_output,
            valid_exit_codes=valid_exit_codes,
        )

    def shell(
        self,
        command: typing.Union[str, typing.List[str]],
        *,
        assert_ok: bool = True,
        regrep: typing.Union[str, typing.Pattern[str], None] = None,
        timeout: typing.Optional[float] = 30,
        log_output: bool = True,
        valid_exit_codes: Collection = (0,),
    ) -> str:
        """
        Same as using check_output with shell=True argument

        :param command: Command to be executed
        :param assert_ok: If True - check the exit code and raise an exception if command failed
        :param regrep: Filter lines in the output of the command with regex
        :param timeout: Timeout for a command
        :param log_output: Whether to send output to the logger
        :param valid_exit_codes: List of exit codes to consider command successful
        :returns: Command's output (stdout and stderr combined)
        """
        return self.check_output(
            command,
            shell=True,
            assert_ok=assert_ok,
            regrep=regrep,
            timeout=timeout,
            log_output=log_output,
            valid_exit_codes=valid_exit_codes,
        )

    def is_userdebug(self) -> bool:
        """Check the build type of the device. If userdebug return True, otherwise False."""
        return True if self.shell("getprop ro.build.type").strip() == "userdebug" else False

    def _change_root_permissions(self, *, timeout: float, retries: int, root: bool) -> None:
        requested_user = "root" if root else "shell"
        command = "root" if root else "unroot"
        self._log(f"Restarting ADB in {requested_user} user mode...")
        current_state = self.get_state()
        is_nothing_to_do = self.shell("whoami").strip() == requested_user
        if is_nothing_to_do:
            self._log(f"Already running as {requested_user}, no need to do anything")
            return

        self.check_output(command, shell=False, assert_ok=False)
        # Give some time for device to go offline
        time.sleep(0.25)
        # Wait for device to come back again on ADB
        self.wait_for_state(current_state, timeout=timeout)
        # Ensure right user and ADB commands working after devices comes back online
        for attempt in range(1, retries + 1):
            try:
                new_user = self.shell("whoami").strip()
                if new_user != requested_user:
                    raise CommandFailedError(f"Switching ADB to {requested_user} user failed: got {new_user} instead")
                return
            except AssertionError as exc:
                self._log(f"User verification attempt {attempt} failed: {exc}")
                time.sleep(1)
        raise CommandFailedError(f"Switching ADB to {requested_user} failed.")

    def gain_root_permissions(self, *, timeout: float = 10.0, retries: int = 3) -> None:
        """
        Gain root permissions (adb root). Make sure device is ready to accept ADB commands after.

        :param timeout: Timeout for device to be available in current state AFTER requesting
            for root permissions
        :param retries: Retries for 'root' command - the command may failed sometimes, but passes
            after retried
        """
        self._change_root_permissions(timeout=timeout, retries=retries, root=True)

    def remove_root_permissions(self, *, timeout: float = 10.0, retries: int = 3):
        """
        Remove root permissions (adb unroot). Make sure device is ready to accept ADB commands after.

        :param timeout: Timeout for device to be available in current state AFTER requesting
            for root permissions
        :param retries: Retries for 'root' command - the command may failed sometimes, but passes
            after retried
        """
        self._change_root_permissions(timeout=timeout, retries=retries, root=False)

    def get_state(self) -> DeviceState:
        """
        Get current device state

        If _adb_device_id is not set, check for connected devices.
        Use the device if only one is available; otherwise, raise an error if multiple devices are connected.
        :returns: Current DeviceState
        """
        if not self._adb_device_id:
            all_adb_devices = Adb.get_all_devices()
            all_adb_devices.difference_update(self.ignore_ids)
            if len(all_adb_devices) > 1:
                raise CopperCommError("More than one ADB unknown device is connected.")
            elif len(all_adb_devices) == 1:
                adb_serial_id = all_adb_devices.pop()
                self._adb_device_id = adb_serial_id
                self._adb_cmd = ["adb", "-s", adb_serial_id]
            else:
                return DeviceState.NO_ADB_DEVICE
        current_state = self.check_output("get-state", shell=False, timeout=5, assert_ok=False, log_output=False)
        if "daemon started successfully" in current_state:
            current_state = self.check_output("get-state", shell=False, timeout=5, assert_ok=False, log_output=False)
        max_retries = 10
        while max_retries > 0 and "device still authorizing" in current_state:
            time.sleep(1)
            current_state = self.check_output("get-state", shell=False, timeout=5, assert_ok=False, log_output=False)
            max_retries -= 1
        if "more than one" in current_state:
            raise CopperCommError(
                "More than one ADB device is connected. 'adb_device_id' must be specified to read device state!"
            )
        if "unauthorized" in current_state:
            return DeviceState.UNAUTHORIZED
        if "offline" in current_state:
            return DeviceState.OFFLINE
        if (
            "no devices/emulators found" in current_state
            or "not found" in current_state
            or "cannot connect to daemon" in current_state
        ):
            return DeviceState.NO_ADB_DEVICE
        return DeviceState(current_state.strip())

    def kill_server(self, log_output: bool = True) -> str:
        """Kill adb server.

        :param log_output: Whether to print logs.
        :return: Commands stdout
        """
        return self.check_output("kill-server", log_output=log_output)

    def start_server(self, log_output: bool = True) -> str:
        """Start adb server.

        :param log_output: whether to print logs.
        :return: Commands stdout
        """
        with contextlib.suppress(CommandFailedError):
            return self.check_output("start-server", log_output=log_output)
        # This helps in case of "connection reset by peer" error
        time.sleep(2)
        return self.check_output("start-server", log_output=log_output)

    def restart_server(self, log_output: bool = True):
        """Restart adb server.

        :param log_output: whether to print logs.
        """
        self.kill_server(log_output)

        # Wait until ADB port is released to prevent
        # Connection reset by peer error
        res = subprocess.check_output(["ss", "-tl"])
        while b"127.0.0.1:5037" in res:
            time.sleep(0.001)
            res = subprocess.check_output(["ss", "-tl"])

        self.start_server(log_output)

    def wait_for_state(
        self,
        state: typing.Union[str, DeviceState] = DeviceState.DEVICE,
        *,
        timeout: float = 120,
        polling_interval: float = 2,
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
            with contextlib.suppress(CommandFailedError, ValueError):
                cur_state = self.get_state()
                if cur_state == DeviceState.UNAUTHORIZED:
                    self.restart_server(log_output=False)
                elif cur_state == expected_state:
                    self._log("Device in {} state".format(expected_state))
                    return
            time.sleep(polling_interval)
        raise Exception(f"Android state '{cur_state}' != {expected_state} after {timeout}s!")

    def wait_for_boot_complete(self, timeout: float = 240, log_output=False) -> None:
        """Wait for android to completely boot up.

        Waits for property: sys.boot_completed == 1
        """
        _logger.debug(
            "Waiting for android property sys.boot_completed == 1 (timeout %ds)..",
            timeout,
        )

        monotonic_timeout = time.monotonic() + timeout

        while time.monotonic() < monotonic_timeout:
            with contextlib.suppress(CommandFailedError):
                output = self.shell("getprop sys.boot_completed", log_output=log_output, assert_ok=False).strip()
                if "device unauthorized" in output:
                    self.restart_server(log_output=log_output)
                elif output == "1":
                    return
            time.sleep(2)
        raise Exception(f"Android property 'sys.boot_completed' != 1 after {timeout}s!")

    def wait_for_desktop(self, timeout: float = 60) -> None:
        """Wait for android desktop is fully loaded
        Wait for logcat event from system buffer: Finished processing BOOT_COMPLETED for u10
        """
        _logger.debug("Waiting for android desktop is fully loaded (timeout %ds)..", timeout)
        self.wait_for_log(
            log_buffer="system",
            log_tag="ActivityManager",
            log_text="Finished processing BOOT_COMPLETED for u10",
            timeout=60,
        )

    def wait_for_log(
        self,
        log_buffer: str,
        log_tag: str,
        log_text: typing.Union[str, None] = None,
        timeout: float = 60,
    ) -> None:
        """Wait for an android logcat message or event with specific text
        :param log_buffer: filter the log by buffer name (main, system, events, etc.)
        :param log_tag: specify the log tag
        :param log_text: an optional parameter to specify the log text
        :param timeout: Timeout for waiting for a log message or event with specific text
        """
        _logger.debug(
            "Wait for android log: %s with text: %s (timeout %ds)..",
            log_tag,
            log_text,
            timeout,
        )

        monotonic_timeout = time.monotonic() + timeout
        while time.monotonic() < monotonic_timeout:
            if log_text is not None:
                logcat_cmd = f"logcat -b {log_buffer} -d | grep {log_tag} | grep '\"{log_text}\"'"
            else:
                logcat_cmd = f"logcat -b {log_buffer} -d | grep {log_tag}"
            output = self.shell(command=logcat_cmd, assert_ok=False)
            if len(output) != 0:
                _logger.info(f"log: {log_tag} with text: {log_text} received")
                return
            _logger.warning(f"log: {log_tag} with text: {log_text} not received yet")
            time.sleep(2)
        raise Exception(f"Android log: {log_tag} with text: {log_text} not received after {timeout}s!")

    def push(
        self,
        local_path: Pathish,
        on_device_path: Pathish,
        *,
        create_dest_dir: bool = False,
        sync: bool = False,
        timeout: typing.Optional[float] = 60,
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
                "push {} {}".format(to_push_element, str(on_device_path)),
                timeout=timeout,
            )

        if sync:
            self.shell("sync", timeout=60)

    def pull(
        self,
        on_device_path: str,
        local_path: str,
        *,
        timeout: typing.Optional[float] = 60,
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
        """Trigger adb reboot.

        :param mode: Allows to specify reboot mode e.g. recovery or fastboot
        """
        _logger.info("Triggering reboot over adb")
        if mode:
            self.check_output(f"reboot {mode}")
        else:
            self.check_output("reboot")

    def reboot_and_wait(self, timeout=120, mode=None):
        initial_boot_id = self.get_boot_id()

        datetime_timeout = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=timeout)

        self.trigger_reboot(mode)

        last_e = None
        _logger.info("Waiting for new android boot_id (timeout %ds)", timeout)
        while datetime.datetime.now(tz=datetime.timezone.utc) < datetime_timeout:
            try:
                time.sleep(1)
                if initial_boot_id != (boot_id := self.get_boot_id(log_output=False)):
                    _logger.info("Kernel boot_id changed to %s. Reboot completed.", boot_id)
                    return
            except AssertionError as e:
                last_e = e

        raise AssertionError("Failed to restart over adb") from last_e

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

        if "remount succeeded" not in out.lower():
            self.reboot_and_wait()
            self.wait_for_boot_complete()
            self.gain_root_permissions()
            out = self.shell(command="remount", assert_ok=False).strip()

            if "remount succeeded" not in out.lower():
                raise RemountError(f"Failed to mount filesystem as root: {out}")

    def perform_factory_reset(self):
        """Perform factory reset by wiping data in recovery mode.

        Wait for system restart and complete boot.
        """
        _logger.info("Performing factory reset through recovery..")
        self.reboot_and_wait(mode="recovery")
        self.wait_for_state(DeviceState.RECOVERY, timeout=120)
        self.gain_root_permissions()
        # When device is restarted adbd looses connection and returns 255.
        self.shell("recovery --wipe_data", timeout=120, valid_exit_codes=(0, 255))
        self.wait_for_state(DeviceState.DEVICE)
        self.wait_for_boot_complete()

    def take_screencap(self, dest_file: pathlib.Path):
        """Create screenshoot and store it in dest_path file.

        :param dest_path: Where to save file on host.
        """
        tmp_file = pathlib.Path(f"/sdcard/screenshot-{round(time.time())}.png")
        if dest_file.is_dir():
            dest_file = dest_file / tmp_file.name
        self.check_output(f"screencap -p {tmp_file.as_posix()}", shell=True)
        self.pull(tmp_file.as_posix(), dest_file.as_posix())
        self.check_output(f"rm {tmp_file.as_posix()}", shell=True)

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

    def list_available_system_services(self) -> typing.List[str]:
        """Get available system services on the device.

        :return: List of available system services
        """
        output = self.shell("service list", assert_ok=False, log_output=False)
        # Output is of the form:
        # Found 123 services:
        # 0   service: [android.ab.cd]
        return [line.split()[1].rstrip(":") for line in output.split("\n")[1:] if line.strip()]

    def wait_for_system_service_availability(self, service, timeout: int = 5) -> None:
        """Wait for a system service to become available on the device.

        :param service: Name of the service to wait for
        :param timeout: Timeout in seconds
        :raises: Exception if service is not available after timeout
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            available_services = self.list_available_system_services()
            if service in available_services:
                return
            time.sleep(0.5)
        raise AssertionError(f"Service {service} is not available after {timeout}s.")
