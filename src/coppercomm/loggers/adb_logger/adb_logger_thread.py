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
import os
import re
import subprocess
import tempfile
import threading
import typing
from datetime import datetime
from time import sleep
from coppercomm.device_adb import adb_interface

SUPER_DEBUG_LEVEL = 5

logger = logging.getLogger("adb_logger")
logger.setLevel(logging.DEBUG)


class AdbLoopStoppedException(Exception):
    pass


class TimestampedFile(object):
    def __init__(self, file: typing.IO) -> None:
        self.name = file.name
        self._file = file
        self._log_line_regex = re.compile("(.*\n)")
        self._incomplete_log_line_regex = re.compile(".*$(?!\n)")
        self._tailing_log_entry = ""

    def __str__(self) -> str:
        return self._file.__str__()

    def write(self, data: str) -> int:
        log_entries = self._log_line_regex.findall(self._tailing_log_entry + data)
        self._tailing_log_entry = ""

        for log in log_entries:
            timestamp = "[" + datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f") + "] "
            self._file.write(timestamp + log)

        match = self._incomplete_log_line_regex.search(data)
        if match:
            self._tailing_log_entry = match.group()
        return len(data)

    def flush(self) -> None:
        self._file.flush()

    def close(self) -> None:
        self._file.close()

    def fileno(self) -> int:
        return self._file.fileno()


class LogFileProvider(object):
    def __init__(
        self, filename: str, single_file: bool, timestamped: bool, mode: str, encoding: typing.Optional[str] = None
    ) -> None:
        self._name, self._extension = os.path.splitext(filename)
        self._filename = filename
        self._timestamped = timestamped
        self._mode = mode
        self._encoding = encoding
        self._counter = 0
        self._single_file = single_file

    def provide(self) -> typing.Union[TimestampedFile, typing.IO]:
        self._counter += 1
        if self._timestamped:
            return TimestampedFile(open(self._get_next_logfile_name(), self._mode, encoding=self._encoding))
        else:
            return open(self._get_next_logfile_name(), self._mode, encoding=self._encoding)

    def _get_next_logfile_name(self) -> str:
        if self._single_file:
            return self._filename
        return "{}_nr_{}_logs{}".format(self._name, self._counter, self._extension)


class AdbLoggerThread(threading.Thread):
    _establishing_connection_lock = threading.Lock()

    def __init__(
        self, file_provider: LogFileProvider, command: str, adb_prefix: str, append_after_interrupt: bool = True
    ) -> None:
        super().__init__()
        self._logger = logger.getChild(self.name)
        self._file_provider = file_provider
        self._log_filenames_list: typing.List[str] = []
        self._command = command
        self._adb_prefix = adb_prefix
        self._append_after_interrupt = append_after_interrupt
        self._connection = None  # type: typing.Optional[subprocess.Popen]
        self._stop_adb_loop = False
        self._file = None  # type: typing.Union[typing.IO, TimestampedFile, None]
        self._logger_started_event = threading.Event()
        self._max_adb_hiccups = 10
        self._adb_hiccup_counter = 0
        self._adb_version = adb_interface.Adb.get_adb_version()

    def run(self) -> None:
        try:
            self._adb_loop()
        except AdbLoopStoppedException:
            self._logger.debug("Adb loop stopped")
        finally:
            if self._connection is not None:
                self._connection.terminate()
                try:
                    self._connection.wait(15)
                except subprocess.SubprocessError:
                    try:
                        self._connection.kill()
                        self._connection.wait(15)
                    except subprocess.SubprocessError:
                        self._logger.error("Couldn't terminate subprocess: {}".format(self._command))

            if self._file is not None:
                self._file.close()

    def stop_logging(self) -> None:
        if not self._stop_adb_loop:
            self._logger.debug("Stopping adb loop")
            self._stop_adb_loop = True

    def get_collected_file_paths(self) -> typing.List[str]:
        return self._log_filenames_list

    def get_current_file_path(self) -> typing.Union[str, None]:
        return os.path.abspath(self._file.name) if self._file else None

    def wait_for_logging_start(self, timeout: typing.Optional[float] = None) -> bool:
        return self._logger_started_event.wait(timeout)

    def _adb_loop(self) -> None:
        while True:
            try:
                if self._stop_adb_loop:
                    self._logger_started_event.clear()
                    raise AdbLoopStoppedException()
                if not self._is_logging():
                    self._logger_started_event.clear()
                    if not self._append_after_interrupt:
                        self._stop_if_cmd_consequently_exits_before_adb_looses_connection()
                    self._connection = None
                    self._setup_adb_connection()
                    self._setup_file()
                    self._start_logging()
                    self._logger_started_event.set()
                sleep(0.5)
            except subprocess.CalledProcessError as e:
                if not self._append_after_interrupt:
                    self._stop_if_cmd_consequently_exits_before_adb_looses_connection()
                self._logger.debug("%s returned %s stdout:%s stderr:%s", e.cmd, e.returncode, e.stdout, e.stderr)
                sleep(0.3)
            except subprocess.TimeoutExpired as e:
                self._logger.debug(
                    "Timeout %ss expired on %s, stdout: %s stderr: %s", e.timeout, e.cmd, e.stdout, e.stderr
                )
                self.stop_logging()

    def _stop_if_cmd_consequently_exits_before_adb_looses_connection(self) -> None:
        """
        Prevents creating infinite number of files if command returns very quickly like "ls" while adb connection
        is established.
        """
        if self._connection and self._connection.poll() and self._is_connection_established():
            self._logger.debug(
                "{} returned {} before adb lost connection. Wrong command or adb hiccup. "
                "Retries left: {}. Stderr: {}".format(
                    self._command,
                    self._connection.poll(),
                    self._max_adb_hiccups - self._adb_hiccup_counter,
                    self._connection.stderr.read(),  # type: ignore[union-attr]
                )
            )
            self._adb_hiccup_counter += 1
            sleep(0.5)  # give unit extra time for startup
            if self._adb_hiccup_counter > self._max_adb_hiccups:
                self._logger.warning(
                    "Stopping thread for: {} because command exited consequently before adb lost connection {} times".format(
                        self._command, self._max_adb_hiccups
                    )
                )
                raise AdbLoopStoppedException()
        else:
            self._adb_hiccup_counter = 0

    def _is_logging(self) -> bool:
        return self._connection is not None and self._connection.poll() is None

    def _start_logging(self) -> None:
        self._logger.debug("Sending {}".format(self._full_cmd_as_list(self._command)))
        self._connection = subprocess.Popen(
            self._full_cmd_as_list(self._command), stdout=self._file, stderr=subprocess.STDOUT  # type: ignore[arg-type]
        )

    def _setup_file(self) -> None:
        if not self._append_after_interrupt or self._file is None:
            if self._file is not None:
                self._file.close()
            self._file = self._file_provider.provide()
            self._log_filenames_list.append(os.path.abspath(self._file.name))
            self._logger.debug("Created next file with name {}".format(self._file.name))

    def _setup_adb_connection(self) -> None:
        # establishing connection on only one console at a time is less bug-prone for adb
        with AdbLoggerThread._establishing_connection_lock:
            self._logger.debug("Setup adb connection start")
            self._logged_subprocess_run("start-server", logging_level=SUPER_DEBUG_LEVEL)
            if self._adb_version >= 34:
                self._logged_subprocess_run("wait-for-device",logging_level=SUPER_DEBUG_LEVEL)
            else:
                self._logged_subprocess_run("wait-for-any",logging_level=SUPER_DEBUG_LEVEL)
            self._logged_subprocess_run("root", logging_level=SUPER_DEBUG_LEVEL)
            # immediate start-server after one thread established connection resulted in "adb server didn't ack"
            sleep(0.1)
            self._logged_subprocess_run("get-state", logging_level=SUPER_DEBUG_LEVEL)

    def _is_connection_established(self) -> bool:
        self._logger.debug("Checking if adb alive after {} returned".format(self._command))
        if AdbLoggerThread._establishing_connection_lock.locked():
            return False
        return self._is_adb_shell_working()

    def _is_adb_shell_working(self) -> bool:
        try:
            result = self._logged_subprocess_run("shell whoami", timeout=0.5, logging_level=SUPER_DEBUG_LEVEL)
            if result.returncode == 0:
                return True
            return False
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return False

    def _full_cmd_as_list(self, command: str) -> typing.List[str]:
        return self._adb_prefix.split() + command.split()

    def _logged_subprocess_run(
        self, command: str, check: bool = True, timeout: float = 15, logging_level: int = logging.INFO
    ) -> subprocess.CompletedProcess:
        result = self._subprocess_run_with_pipe_output_that_wont_pollute_behave_console(
            self._full_cmd_as_list(command), check=check, timeout=timeout
        )
        self._logger.log(
            level=logging_level,
            msg="{} returned {} stdout:{} stderr:{}".format(command, result.returncode, result.stdout, result.stderr),
            stacklevel=2,
        )
        return result

    def _subprocess_run_with_pipe_output_that_wont_pollute_behave_console(
        self,
        command: typing.List[str],
        input: typing.Union[str, bytes, None] = None,
        timeout: typing.Optional[float] = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess:
        """
        Behave was printing subprocess.run stdout and stderr on console when subprocess.PIPE or subprocess.DEVNULL was used
        only redirecting to file seems to work.
        This function behaves just like subprocess.run with stdout and stderr set to PIPE.
        Throws TypeError if stdout or stderr is passed.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "out_file"), "w+b") as out_file, open(
                os.path.join(tmp_dir, "err_file"), "w+b"
            ) as err_file:
                timeout_occurred = False
                return_code = 0
                try:
                    return_code = subprocess.run(
                        command, stdout=out_file, stderr=err_file, timeout=timeout, input=input
                    ).returncode
                except subprocess.CalledProcessError as e:
                    return_code = e.returncode
                except subprocess.TimeoutExpired:
                    timeout_occurred = True
                out_file.seek(0)
                err_file.seek(0)
                out_file.flush()
                err_file.flush()
                stdout = out_file.read()
                stderr = err_file.read()
                if timeout_occurred:
                    raise subprocess.TimeoutExpired(command, timeout, output=stdout, stderr=stderr)  # type: ignore
                elif return_code != 0 and check:
                    raise subprocess.CalledProcessError(return_code, cmd=command, output=stdout, stderr=stderr)
                return subprocess.CompletedProcess(command, return_code, stdout, stderr)
