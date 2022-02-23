# /*===========================================================================*\
# * Copyright © 2019 Aptiv. All Rights Reserved.
# * Aptiv Confidential
# \*===========================================================================*/

import enum
import glob
import logging
import os
import shlex
import time
import typing

from .local_console import CommandFailedError, execute_command


_logger = logging.getLogger("one_update.adb_interface")
_logger.setLevel(logging.DEBUG)


class DeviceState(enum.Enum):
    ANY = "any"
    DEVICE = "device"
    RECOVERY = "recovery"


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
    ) -> str:
        """
        Execute command on adb device. If 'command' passed as a string it will be splitted by shlex.split

        :param command: Command to be executed
        :param shell: Use 'shell' subcommand to execute 'command' if True
        :param assert_ok: If True - check the exit code and raise an exception if command failed
        :param regrep: Filter lines in the output of the command with regex
        :param timeout: Timeout for a command
        :returns: Command's output (stdout and stderr combined)
        """

        if isinstance(command, str):
            command = shlex.split(command)
        if shell:
            command.insert(0, "shell")

        adb_command = self._adb_cmd + command
        return execute_command(adb_command, assert_ok=assert_ok, regrep=regrep, timeout=timeout)

    def shell(
        self,
        command: typing.Union[str, typing.List[str]],
        *,
        assert_ok: bool = True,
        regrep: typing.Union[str, typing.Pattern[str], None] = None,
        timeout: typing.Optional[float] = None,
    ) -> str:
        """
        Same as using check_output with shell=True argument

        :param command: Command to be executed
        :param assert_ok: If True - check the exit code and raise an exception if command failed
        :param regrep: Filter lines in the output of the command with regex
        :param timeout: Timeout for a command
        :returns: Command's output (stdout and stderr combined)
        """
        return self.check_output(command, shell=True, assert_ok=assert_ok, regrep=regrep, timeout=timeout)

    def gain_root_permissions(self, *, timeout: float = 60.0, retries: int = 3) -> None:
        """
        Gain root permissions (adb root). Wait for device in any state before and after
        requesting for root permissions

        :param timeout: Timeout for device to be available in ANY state BEFORE requesting
            for root permissions
        :param retries: Retries for 'root' command - the command may failed sometimes, but passes
            after retried
        """
        self._log("Gain ADB root permissions")

        # no point to try root access if device is not available
        self.wait_for_state(DeviceState.ANY, timeout=timeout)

        # hard to get rid of retries :/
        # it's far more robust this way
        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                # time needed for 'root' cmd vary and hard to say if 10s is enough so 20s is set to be sure
                self.check_output("root", shell=False, assert_ok=True, timeout=20)
            except AssertionError as exc:
                self._log("Gaining root permissions attempt {} failed: {}".format(attempt, exc))
                time.sleep(3)
                last_exc = exc
            else:
                # Device may be unavailable for some time after 'adb root' command
                self.wait_for_state(DeviceState.ANY, timeout=10)
                return

        raise CommandFailedError("Gaining root permissions failed") from last_exc

    def get_state(self) -> DeviceState:
        """
        Get current device state

        :returns: Current DeviceState (DeviceState.DEVICE/DeviceState.RECOVERY)
        """
        current_state = self.check_output("get-state", shell=False, assert_ok=True, timeout=3)
        return DeviceState(current_state.strip())

    def wait_for_state(
        self,
        state: typing.Union[str, DeviceState] = DeviceState.ANY,
        *,
        timeout: typing.Optional[float] = None,
    ) -> None:
        """
        Wait for device in given state (adb wait-for-*)

        :param state: Desired state of the device. Default is ANY
        :param timeout: Timeout for waiting
        """
        device_state = DeviceState(state)
        self.check_output("wait-for-{}".format(device_state.value), timeout=timeout)
        self._log("Device in {} state".format(device_state))

    def push(
        self,
        local_path: str,
        on_device_path: str,
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
        path_resolved = os.path.expandvars(os.path.expanduser(local_path))
        to_push_list = glob.glob(path_resolved)
        if not to_push_list:
            raise ValueError("No files found to be pushed: {}".format(local_path))

        if create_dest_dir:
            self.check_output("mkdir -p {}".format(on_device_path), shell=True)
        for to_push_element in to_push_list:
            self._log("Pushing {} to {}".format(to_push_element, on_device_path))
            self.check_output("push {} {}".format(to_push_element, on_device_path), timeout=timeout)

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
        self._log("Pulling {} to {}".format(on_device_path, local_path))
        pull_cmd = "pull {} {}".format(on_device_path, local_path)
        self.check_output(pull_cmd, timeout=timeout)

    def _log(self, msg: str) -> None:
        _logger.debug("{}: {}".format(self._adb_device_id or "ADB_DEVICE", msg))
