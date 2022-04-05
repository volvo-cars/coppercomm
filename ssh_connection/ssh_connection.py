import socket
import time
import typing
import logging
import threading
from time import sleep
from paramiko import Channel, SFTPClient, MissingHostKeyPolicy, SSHException, SFTPClient
from paramiko.channel import ChannelFile, ChannelStderrFile
from paramiko.ssh_exception import NoValidConnectionsError
from paramiko.client import SSHClient


logger = logging.getLogger("SSHConnection")


class SSHCommandFailed(SSHException):
    def __init__(
        self,
        exit_code: int,
        stdout: ChannelFile,
        stderr: ChannelStderrFile,
        cmd: str = "",
    ):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.cmd = cmd
        self.error_message = f"Command {cmd} resulted in nonzero exitcode: {exit_code}"
        super(SSHCommandFailed, self).__init__(self.error_message)


class SSHNoExitCode(SSHException):
    def __init__(self, stdout: ChannelFile, stderr: ChannelStderrFile, cmd: str = ""):
        self.stdout = stdout
        self.stderr = stderr
        self.cmd = cmd
        self.error_message = f"Command {cmd} returned no exit code"
        super(SSHNoExitCode, self).__init__(self.error_message)


class SSHConnectionError(SSHException):
    pass


class SFTPTransferFailed(Exception):
    pass


class IgnoreHostKeys(MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        """Do nothing with the host key. Do not even warn.

        Host key can change during flashing. This policy will ignore it.
        This policy expects no known host keys. (Do not use with SSHClient.load_system_host_keys())"""
        pass


class SSHConnection:
    _ssh_mutex = threading.Lock()

    def __init__(
        self, ip: str, port: str = "22", username: str = "root", password: str = ""
    ) -> None:
        with SSHConnection._ssh_mutex:
            self.sshclient = SSHClient()
            self.ip = ip
            self.port = int(port)
            self.username = username
            self.password = password
            self.sshclient.set_missing_host_key_policy(IgnoreHostKeys())

    def connect(
        self,
        timeout: typing.Optional[int] = None,
        keepalive_interval: typing.Optional[int] = 5,
    ) -> None:
        if not self.connected:
            try:
                with SSHConnection._ssh_mutex:
                    self.sshclient.connect(
                        hostname=self.ip,
                        port=self.port,
                        username=self.username,
                        password=self.password,
                        timeout=timeout,
                    )
                    if keepalive_interval is not None:
                        transport = self.sshclient.get_transport()
                        transport.set_keepalive(keepalive_interval)

            except (NoValidConnectionsError, OSError, socket.timeout):
                raise SSHConnectionError(f"Failed to connect to {self.ip}:{self.port}")

    def disconnect(self) -> None:
        if self.connected:
            self.sshclient.close()

    @property
    def connected(self):
        transport = self.sshclient.get_transport()
        if transport is not None:
            return transport.is_active()
        else:
            return False

    def __del__(self) -> None:
        if self.connected:
            self.sshclient.close()

    def _is_exit_status_ready(
        self, channel: Channel, timeout: typing.Optional[int] = 5
    ) -> bool:
        if timeout is None:
            return False
        start_time = time.monotonic()
        while time.monotonic() < start_time + timeout:
            if channel.exit_status_ready() is True:
                return True
            sleep(1)
        return False

    def _create_and_setup_channel(
        self,
        command_exec_timeout: typing.Optional[int] = 10,
        open_channel_timeout: int = 10,
    ) -> typing.Tuple[Channel, ChannelFile, ChannelStderrFile]:
        with SSHConnection._ssh_mutex:
            # Channels are used directly because there is no possibility set "open channel timeout" which is 3600s by default
            channel = self.sshclient.get_transport().open_channel(
                kind="session", timeout=open_channel_timeout
            )
            channel.settimeout(command_exec_timeout)
            stdout = channel.makefile()
            stderr = channel.makefile_stderr()
            return (channel, stdout, stderr)

    def _execute_cmd(
        self,
        command: str,
        handle_return_code: bool = True,
        command_exec_timeout: typing.Optional[int] = 10,
        open_channel_timeout: int = 10,
    ) -> typing.Tuple[ChannelFile, ChannelStderrFile, typing.Optional[int]]:

        try:
            (channel, stdout, stderr) = self._create_and_setup_channel(
                command_exec_timeout=command_exec_timeout,
                open_channel_timeout=open_channel_timeout,
            )
            channel.exec_command(command=command)
        except (NoValidConnectionsError, OSError, socket.timeout, EOFError):
            raise SSHConnectionError(
                f"Failed to open channel or execute command: '{command}'"
            )

        if self._is_exit_status_ready(channel=channel, timeout=command_exec_timeout):
            exitcode = channel.recv_exit_status()
            if exitcode != 0 and handle_return_code is True:
                raise SSHCommandFailed(exitcode, stdout, stderr, command)
            return stdout, stderr, exitcode
        else:
            if command_exec_timeout is not None:
                raise SSHNoExitCode(stdout=stdout, stderr=stderr, cmd=command)
        return stdout, stderr, None

    def execute_cmd(
        self,
        command: str,
        handle_return_code: bool = True,
        command_exec_timeout: typing.Optional[int] = 10,
        tries=1,
        open_channel_timeout: int = 10,
    ) -> typing.Tuple[
        typing.Optional[ChannelFile],
        typing.Optional[ChannelStderrFile],
        typing.Optional[int],
    ]:
        assert tries >= 1
        for tries_left in reversed(range(tries)):
            try:
                self.connect()
                return self._execute_cmd(
                    command,
                    handle_return_code,
                    open_channel_timeout=open_channel_timeout,
                    command_exec_timeout=command_exec_timeout,
                )
            except SSHException as e:
                logger.debug(f"Command '{command}' failed with '{e}'")
                self.disconnect()
                if tries_left == 0:
                    raise
        return (None, None, None)

    def get(self, remotepath: str, localpath: str) -> None:
        self.connect()
        if self.connected:
            with SFTPClient.from_transport(self.sshclient.get_transport()) as sftp:
                sftp.get(remotepath, localpath)
        else:
            raise SFTPTransferFailed(f"Failed to get {remotepath} to {localpath}")

    def put(self, localpath: str, remotepath: str) -> None:
        self.connect()
        if self.connected:
            with SFTPClient.from_transport(self.sshclient.get_transport()) as sftp:
                sftp.put(localpath, remotepath)
        else:
            raise SFTPTransferFailed(f"Failed to put {localpath} to {remotepath}")
