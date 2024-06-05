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

import logging
import socket
import threading
import time
import typing
from pathlib import Path
from time import sleep
import fnmatch

from paramiko import Channel, MissingHostKeyPolicy, SFTPClient, SSHException, ProxyCommand
from paramiko.channel import ChannelFile, ChannelStderrFile
from paramiko.client import SSHClient
from paramiko.ssh_exception import AuthenticationException, NoValidConnectionsError

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


class SSHTimeoutReached(SSHException):
    def __init__(self, stdout: ChannelFile, stderr: ChannelStderrFile, cmd: str = ""):
        self.stdout = stdout
        self.stderr = stderr
        self.cmd = cmd
        self.error_message = f"Command {cmd} returned no exit code"
        super(SSHTimeoutReached, self).__init__(self.error_message)


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
        self,
        ip: str,
        port: str = "22",
        username: str = "root",
        password: str = "",
        proxy_command: typing.Optional[str] = None,
    ) -> None:
        with SSHConnection._ssh_mutex:
            self.sshclient = SSHClient()
            self.ip = ip
            self.port = int(port)
            self.username = username
            self.password = password
            self.proxy_command = proxy_command
            self.sshclient.set_missing_host_key_policy(IgnoreHostKeys())

    def _wait_for_connection(self, timeout: float = 30, retry_delay: float = 2.0, tcp_timeout: float = 5.0):
        """Retry connection attempt until it is successfull or timeout occures."""
        end_time = time.monotonic() + timeout

        while time.monotonic() < end_time:
            try:
                self.sshclient.connect(
                    hostname=self.ip,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=tcp_timeout,
                    banner_timeout=60,
                    sock=typing.cast(Channel, ProxyCommand(self.proxy_command)) if self.proxy_command else None
                )
                if self.connected:
                    return
            except (
                NoValidConnectionsError,
                AuthenticationException,
                OSError,
                socket.timeout,
            ) as err:
                time.sleep(retry_delay)
                last_e = err
        raise last_e

    def connect(
        self,
        timeout: float = 30.0,
        tcp_timeout: float = 5.0,
        keepalive_interval: int = 5,
        retry_delay: float = 2.0,
    ) -> None:
        if not self.connected:
            try:
                with SSHConnection._ssh_mutex:
                    self._wait_for_connection(timeout=timeout, retry_delay=retry_delay, tcp_timeout=tcp_timeout)
                    if keepalive_interval is not None:
                        transport = self.sshclient.get_transport()
                        if transport:
                            transport.set_keepalive(keepalive_interval)
                        else:
                            raise OSError("Can't get transport from ssh client!")

            except (
                NoValidConnectionsError,
                AuthenticationException,
                OSError,
                socket.timeout,
            ):
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

    def _is_exit_status_ready(self, channel: Channel, timeout: typing.Optional[int] = 5) -> bool:
        if timeout is None:
            return False
        start_time = time.monotonic()
        while time.monotonic() < start_time + timeout:
            if channel.exit_status_ready() is True:
                return True
            sleep(0.05)
        return False

    def _create_and_setup_channel(
        self,
        command_exec_timeout: typing.Optional[int] = 10,
        open_channel_timeout: int = 10,
    ) -> typing.Tuple[Channel, ChannelFile, ChannelStderrFile]:
        with SSHConnection._ssh_mutex:
            # Channels are used directly because there is no possibility set "open channel timeout" which is 3600s by default
            transport = self.sshclient.get_transport()
            if transport is None:
                raise OSError("Can't get transport from ssh client!")
            channel = transport.open_channel(kind="session", timeout=open_channel_timeout)
            channel.settimeout(command_exec_timeout)
            stdout = channel.makefile("rb")
            stderr = channel.makefile_stderr("rb")
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
            raise SSHConnectionError(f"Failed to open channel or execute command: '{command}'")

        if self._is_exit_status_ready(channel=channel, timeout=command_exec_timeout):
            exitcode = channel.recv_exit_status()
            if exitcode != 0 and handle_return_code is True:
                raise SSHCommandFailed(exitcode, stdout, stderr, command)
            return stdout, stderr, exitcode
        else:
            if command_exec_timeout is not None:
                raise SSHTimeoutReached(stdout=stdout, stderr=stderr, cmd=command)
        return stdout, stderr, None

    def execute_cmd(
        self,
        command: str,
        handle_return_code: bool = True,
        command_exec_timeout: typing.Optional[int] = 10,
        tries=1,
        open_channel_timeout: int = 10,
        connect_timeout: float = 30.0,
    ) -> typing.Tuple[
        ChannelFile,
        ChannelStderrFile,
        typing.Optional[int],
    ]:
        if tries < 1:
            raise ValueError("Number of 'tries' must be >= 1")
        for _ in range(tries):
            try:
                self.connect(timeout=connect_timeout)
                return self._execute_cmd(
                    command,
                    handle_return_code,
                    open_channel_timeout=open_channel_timeout,
                    command_exec_timeout=command_exec_timeout,
                )
            except SSHException as e:
                logger.debug("Command '%s' failed with '%s'", command, e)
                self.disconnect()
                last_e = e
        raise last_e

    def _execute_cmd_pty(
        self,
        command: str,
    ) -> typing.Tuple[Channel, ChannelFile, ChannelStderrFile, typing.Optional[int]]:

        try:
            (channel, stdout, stderr) = self._create_and_setup_channel()
            channel.get_pty()
            channel.exec_command(command=command)
        except (NoValidConnectionsError, OSError, socket.timeout, EOFError):
            raise SSHConnectionError(f"Failed to open channel or execute command: '{command}'")

        return channel, stdout, stderr, None

    def execute_cmd_pty(
        self, command: str, tries=1, connect_timeout: float = 30.0
    ) -> typing.Tuple[Channel, ChannelFile, ChannelStderrFile, typing.Optional[int]]:
        if tries < 1:
            raise ValueError("Number of 'tries' must be >= 1")
        for _ in range(tries):
            try:
                self.connect(timeout=connect_timeout)
                return self._execute_cmd_pty(
                    command,
                )
            except SSHException as e:
                logger.error(f"Command '{command}' failed with '{e}'")
                self.disconnect()
                last_e = e
        raise last_e

    def get(self, remotepath: str, localpath: str) -> None:
        self.connect(tcp_timeout=10)
        if self.connected:
            transport = self.sshclient.get_transport()
            if transport:
                client = SFTPClient.from_transport(transport)
                if client:
                    with client as sftp:
                        sftp.get(remotepath, localpath)
                        return
        raise SFTPTransferFailed(f"Failed to get {remotepath} to {localpath}")

    def get_all(self, remote_path: Path, local_dir: Path) -> None:
        """Get all files from remote path to the given local directory.

        Examples:
            /etc/vsomeip    ./tmp      - copy whole vsomeip folder to tmp dir
            /etc/vsomeip/*.json  ./tmp - copy all json files to tmp dir
            /etc/vapm.conf  ./tmp  - copy vamp.conf file to the tmp dir
        """
        self.connect(tcp_timeout=10)
        if not self.connected:
            raise SFTPTransferFailed(f"Failed to connect to {self.ip}!")
        if not (transport := self.sshclient.get_transport()):
            raise SFTPTransferFailed("Failed to get transport layer!")
        if not (sftp_client := SFTPClient.from_transport(transport)):
            raise SFTPTransferFailed("Failed to create SFTP channel!")
        with sftp_client as sftp:
            try:
                if _is_file(remote_path, sftp):
                    local_dir.mkdir(parents=True, exist_ok=True)
                    return self.get(remote_path.as_posix(), local_dir.joinpath(remote_path.name).as_posix())
            except IOError:  # Pattern or dir was given?
                pass
            _get_all(remote_path, local_dir, sftp)

    def put(self, localpath: str, remotepath: str, chmod: typing.Optional[int] = None) -> None:
        """Copy file to remote path.

        Note: SFTPClient requires that file name must be included in remote path.
        """
        self.connect(tcp_timeout=10)
        if self.connected:
            transport = self.sshclient.get_transport()
            if transport:
                client = SFTPClient.from_transport(transport)
                if client:
                    with client as sftp:
                        _put(Path(localpath), Path(remotepath), sftp, chmod)
                        return
        raise SFTPTransferFailed(f"Failed to put {localpath} to {remotepath}")

    def put_all(self, source: Path, remote_dir: Path, chmod: typing.Optional[int] = None):
        """Copy file or whole directory to remote path.

        If remote directory already exists:
         - Directories are merged
         - then files are overwritten

        :param source: Source dir or file to copy
        :param remote_dir: Where to copy source to
        :param chmod: When defined, set given permission to all files/dirs.
        """
        if source.is_file():
            return self.put(source.as_posix(), remote_dir.joinpath(source.name).as_posix())

        self.connect(tcp_timeout=10)
        if not self.connected:
            raise SFTPTransferFailed(f"Failed to connect to {self.ip}!")
        if not (transport := self.sshclient.get_transport()):
            raise SFTPTransferFailed("Failed to get transport layer!")
        if not (sftp_client := SFTPClient.from_transport(transport)):
            raise SFTPTransferFailed("Failed to create SFTP channel!")
        with sftp_client as sftp:
            dest_dir_str: str = remote_dir.joinpath(source.name).as_posix()
            try:
                sftp.lstat(dest_dir_str)  # check if dir exists
            except IOError:
                logger.debug("Make remote dir: %s", dest_dir_str)
                sftp.mkdir(dest_dir_str)
            _put_all(source, remote_dir / source.name, sftp, chmod)
            sftp.chmod(dest_dir_str, chmod if chmod else (source.stat().st_mode & 0o777))


def _put(
    local_path: Path,
    remotepath: Path,
    sftp: SFTPClient,
    chmod: typing.Optional[int] = None,
):
    logger.debug("Copy %s to %s", local_path, remotepath)
    sftp.put(local_path.as_posix(), remotepath.as_posix())
    sftp.chmod(remotepath.as_posix(), chmod if chmod else (local_path.stat().st_mode & 0o777))


def _put_all(
    local_path: Path,
    remotepath: Path,
    sftp: SFTPClient,
    chmod: typing.Optional[int] = None,
):
    for path in local_path.iterdir():
        relative_path: Path = path.relative_to(local_path)
        dest_path_str: str = remotepath.joinpath(relative_path).as_posix()
        if path.is_dir():
            logger.debug("Make remote dir: %s", dest_path_str)
            try:
                sftp.lstat(dest_path_str)  # check if dir exists
            except IOError:
                sftp.mkdir(dest_path_str)
            _put_all(path, remotepath.joinpath(relative_path), sftp)
            sftp.chmod(dest_path_str, chmod if chmod else (path.stat().st_mode & 0o777))
        elif path.is_file():
            _put(path, remotepath.joinpath(relative_path), sftp, chmod)
        else:
            logger.warning("SFTP dont know how to copy path: %s", path)


def _is_dir(remote_path, sftp):
    stat = sftp.stat(remote_path.as_posix())
    return stat.st_mode >> 9 == 32


def _is_file(remote_path, sftp):
    stat = sftp.stat(remote_path.as_posix())
    return stat.st_mode >> 9 == 64


def _get_all(remote_path: Path, local_dir: Path, sftp: SFTPClient) -> None:
    """Get files from remote_path to local_dir.

    scp /etc/dir /local_dir  - copy dir and its all content to the /local_dir
    scp /etc/some* /local_dir - copy everything that starts with 'some*' to the /local_dir
    """
    pattern = remote_path.name
    for name in sftp.listdir(remote_path.parent.as_posix()):
        if not fnmatch.fnmatch(name, pattern):
            continue
        _remote = remote_path.parent.joinpath(name)
        local_dir.mkdir(parents=True, exist_ok=True)
        if _is_file(_remote, sftp):
            sftp.get(_remote.as_posix(), local_dir.joinpath(name).as_posix())
        elif _is_dir(_remote, sftp):
            _local = local_dir.joinpath(name)
            _get_all(_remote.joinpath("*"), _local, sftp)
        else:
            logger.warning("Skipping copying of unknown object at: %s", _remote)
