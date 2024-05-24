import logging
import shlex
import typing
import enum
from coppercomm.device_common.local_console import execute_command

logger = logging.getLogger(__name__)


class FastbootState(enum.Enum):
    FASTBOOT = "fastboot"
    FASTBOOTD = "fastbootd"
    NO_FASTBOOT_DEVICE = "not found"


class Fastboot:

    def __init__(self, device_id: typing.Optional[str] = None) -> None:
        self._device_id: typing.Optional[str]  = device_id
        self._fastboot_cmd = ["fastboot"]
        if device_id:
            self._fastboot_cmd.extend(("-s", device_id))

    def check_output(
        self,
        command: typing.Union[str, typing.List[str]],
        *,
        shell: bool = False,
        assert_ok: bool = True,
        regrep: typing.Union[str, typing.Pattern[str], None] = None,
        timeout: typing.Optional[float] = 30,
        log_output: bool = True,
    ) -> str:
        """Execute command on adb device. If 'command' passed as a string it will be splitted by shlex.split

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

        full_command = self._fastboot_cmd + command
        return execute_command(
            full_command,
            assert_ok=assert_ok,
            regrep=regrep,
            timeout=timeout,
            log_output=log_output,
        )

    def get_state(self) -> FastbootState:
        resp = self.check_output(["devices",], shell=False, timeout=5, assert_ok=False, log_output=False)
        if self.device_id:
            for line in resp.splitlines():
                if self.device_id in line:
                    return FastbootState[line.split()[1].upper()]
        else:  # assume that first device found in fastboot is our device
            for line in resp.splitlines():
                if "fastboot" in line:
                    device_id, mode = line.split()
                    # Assume adb.device_id is same as fastboot id
                    self.device_id = device_id.strip()
                    return FastbootState[mode.strip().upper()]
        return FastbootState.NO_FASTBOOT_DEVICE

    def reboot(self, new_state: typing.Optional[str] = None):
        """Perform fastboot reboot.

        :param new_state: Optional destination state. If not provided, device will boot into Android.
        """
        if new_state:
            self.check_output(["reboot", new_state])
        else:
            self.check_output(["reboot"])

    def erase(self, partition: str, timeout: float = 10):
        """Erase partition

        :param partition: Partition to erase
        """
        self.check_output(["erase", partition], timeout=timeout)

    def flash(self, partition: str, image: str, timeout: float = 60):
        """Flash image to partition

        :param partition: Partition to flash image to
        :param image: Image to flash
        """
        self.check_output(["flash", partition, image], timeout=timeout)

    @property
    def device_id(self):
        return self._device_id

    @device_id.setter
    def device_id(self, value: str):
        self._device_id = value
        self._fastboot_cmd = ["fastboot", "-s", value]
