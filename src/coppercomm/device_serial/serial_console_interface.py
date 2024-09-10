# Copyright 2024 Volvo Cars
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
import pathlib
import re
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Pattern, Union

import serial
from coppercomm.device_common.exceptions import CopperCommConnectionError
from pexpect import EOF, TIMEOUT
from pexpect.fdpexpect import fdspawn

ENCODING = "ascii"
ENCODING_ERR_HANDLING = "ignore"


serial_logger = logging.getLogger("SerialConsole")


class SerialConnectionError(RuntimeError):
    pass


class SerialConsoleInterface(threading.Thread):
    NOT_EXPECTING = -1
    PROMPT_ONLY = -2

    def __init__(
        self,
        connection_address: str,
        connection_name: str,
        prompt: Union[str, List[str], None] = None,
    ) -> None:
        super().__init__()
        self.connection_name = connection_name
        self.logger = serial_logger.getChild(self.connection_name)
        self.logger.propagate = False
        # Data is saved to file. Do not print to stdout.
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                self.logger.removeHandler(handler)
        self._setup_connection(connection_address)
        self._lock = threading.RLock()
        self._running = threading.Event()
        self._running.set()
        self._streaming = threading.Event()
        self._streaming.set()
        self._matched = ""
        self._output_lines: List[str] = []
        self.set_prompt(prompt)

    def set_test_logging(self, path) -> None:
        """Function to modify logging path for serial during test session.

        It swaps old handlers with the new one that has a specified path for current test case.

        :param path: Path to the output file
        """
        file_handler = logging.FileHandler(
            filename=path, mode="a", encoding=None, delay=True
        )
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                self.logger.removeHandler(handler)
        self.logger.addHandler(file_handler)

    def set_prompt(self, prompt: Union[str, List[str], None]) -> None:
        self._prompt_regex = self._get_prompt_regex(prompt)
        self.logger.debug("Prompt regex set to <%s>", self._prompt_regex)

    def get_matched(self) -> str:
        return self._matched

    def get_output(self) -> str:
        if self._prompt_regex:
            return "\n".join(self._output_lines[:-1])
        else:
            return "\n".join(self._output_lines)

    def run(self) -> None:
        try:
            self.logger.debug("Starting thread")
            while self._running.is_set():
                self._lock.acquire()
                while self._streaming.is_set() and self._running.is_set():
                    self._get_line()
                self._lock.release()
                while self._running.is_set():
                    if self._streaming.wait(1.0):
                        break
        except Exception as e:
            self.logger.error("Exception <%s> occurred! Exiting!", e)
        finally:
            try:
                self._lock.release()
                self.logger.debug(
                    "Lock released succesfully while exiting from main loop"
                )
            except RuntimeError:
                self.logger.debug("Lock already released")
            self._streaming.clear()
            self._running.clear()
            self.logger.debug("Flags cleared! Main loop exited!")

    def close_console(self) -> None:
        self._running.clear()
        if self.is_alive():
            self.join()
        self._close_connection()
        self.logger.debug("Console closed")

    def expect(
        self,
        expected: Union[str, List[str]],
        not_expected: Union[str, List[str], None] = None,
        timeout: float = 0,
    ) -> int:
        if not_expected is None:
            not_expected = []
        self._streaming.clear()
        self._lock.acquire()
        try:
            found = self._expect(
                expected,
                not_expected_in_output=not_expected,
                timeout=timeout,
                wait_for_prompt=False,
            )
        finally:
            self._streaming.set()
            self._lock.release()
        return found

    def send_command(
        self,
        command: str,
        max_retypes: int = 2,
        check_echo: bool = True,
        expected_in_output: Union[str, List[str], None] = None,
        not_expected: Union[str, List[str], None] = None,
        timeout: float = 0,
        wait_for_prompt: bool = True,
        prompt: Union[str, List[str], None] = None,
        send_linebreak: bool = True,
    ) -> int:
        """
        Method that sends a command on the console and may expect a pattern or list of patterns
        :param command: command to send on the console
        :param max_retypes: maximum number of resending the command before getting the echo in output
        :param check_echo: wait for the echo of the command
        :param expected_in_output: list of patterns to match - accepts also single pattern (string)
        :param not_expected: list of patterns that will fail the command if found
        :param timeout: time to wait for expected pattern (and prompt if wait_for_prompt is set)
        :param wait_for_prompt: indicates that method should wait for the expected prompt
        :param prompt: expected prompt(s) of the console
        :return: index of the pattern matched in pattern list (returns NOT_EXPECTING if no pattern has been passed
            or PROMPT_ONLY if also no pattern for not_expected was provided)
        """
        if expected_in_output is None:
            expected_in_output = []
        if not_expected is None:
            not_expected = []
        found = self.NOT_EXPECTING
        self._streaming.clear()
        self._lock.acquire()
        try:
            self._send_command(command, max_retypes, check_echo, send_linebreak)
            if expected_in_output or not_expected or wait_for_prompt:
                found = self._expect(
                    expected_in_output=expected_in_output,
                    not_expected_in_output=not_expected,
                    timeout=timeout,
                    wait_for_prompt=wait_for_prompt,
                    prompt=prompt,
                )
        finally:
            self._streaming.set()
            self._lock.release()
        return found

    def _check_connection_address(self, connection_address: str) -> None:
        dev_path = pathlib.Path("/dev")
        tty_list = [p.as_posix() for p in dev_path.glob(pattern="tty*")]
        if not os.path.exists(connection_address):
            self._raise_exception(
                f"Connection address {connection_address} doesn't exists. "
                f"List with available tty serials: {tty_list}",
                CopperCommConnectionError,
                log_level=logging.ERROR,
            )
        if not shutil.which("lsof"):
            self.logger.warning(
                "<lsof> not found. Could not determine if port %s is valid "
                "or open, but flashing operation will proceed if possible.",
                connection_address,
            )
            return
        check_if_file_opened_cmd = "lsof -t {}"
        try:
            result = subprocess.run(
                check_if_file_opened_cmd.format(connection_address),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            returncode = -1

        if returncode == 1:
            self.logger.debug("Address %s is not used in current environment", connection_address)
            return
        elif returncode != 0:
            self.logger.warning(
                "Could not determine if port %s is valid or open [lsof errno %s], but flashing operation will proceed if possible.",
                connection_address,
                returncode,
            )
            return
        self._raise_exception(
            "Connection address {} is used by process with PID: {}".format(
            connection_address,
            result.stdout.decode(sys.getdefaultencoding()).replace("\n", "")),
            exception_cls=SerialConnectionError,
            log_level=logging.ERROR,
        )

    def _setup_connection(self, connection_address: str) -> None:
        self._check_connection_address(connection_address)
        try:
            self.serial_connection = serial.Serial(connection_address, 115200)
            connection_address = self.serial_connection.fileno()
            self.connection = fdspawn(
                connection_address,
                use_poll=True,
                encoding=ENCODING,
                codec_errors=ENCODING_ERR_HANDLING,
            )
        except TypeError as e:
            self.logger.debug("Exception while setting up connection: %s", e)
            self.logger.info("Skipping 'use_poll'")
            self.connection = fdspawn(
                connection_address,
                encoding=ENCODING,
                codec_errors=ENCODING_ERR_HANDLING,
            )
        except (
            serial.SerialException
        ) as exc:  # device may be unavailable even if the device-path exists
            self.logger.error("Failed to setup serial connection: %s", exc)
            raise

    def _close_connection(self) -> None:
        if self.connection.isalive():
            if hasattr(self, "serial_connection"):
                self.serial_connection.close()
            else:
                self.connection.close()

        if self.connection.logfile:
            self.connection.logfile.close()
            self.connection.logfile = None

    def _get_line(self) -> str:
        try:
            self.connection.expect("\n", timeout=0.2)
            line = str(self.connection.before)
            self.logger.debug(line.replace("\r", ""))
        except TIMEOUT:
            line = str(self.connection.before)
        except EOF:
            self.logger.error(
                "EOF occurred - connection with %s lost or occupied by other source",
                self.connection_name,
            )
            self._raise_exception(
                "EOF occurred - connection lost", SerialConnectionError
            )
        return line

    def _send_command(
        self,
        command: str,
        max_retypes: int = 2,
        check_echo: bool = True,
        send_linebreak: bool = True,
    ) -> None:
        self.logger.debug("Sending command <%s>", command)
        if check_echo:
            while max_retypes > 0:
                if send_linebreak:
                    self.connection.sendline(command)
                else:
                    self.connection.send(command)
                end_time = datetime.now(tz=timezone.utc) + timedelta(seconds=2)
                while datetime.now(tz=timezone.utc) < end_time:
                    if re.search(re.escape(command), self._get_line()):
                        return
                max_retypes -= 1
            self._raise_exception(
                f"Echo of command <{command}> not found", CopperCommConnectionError
            )
        else:
            if send_linebreak:
                self.connection.sendline(command)
            else:
                self.connection.send(command)

    def _expect(
        self,
        expected_in_output: Union[str, List[str]],
        not_expected_in_output: Union[str, List[str]],
        timeout: float = 0,
        wait_for_prompt: bool = True,
        prompt: Union[str, List[str], None] = None,
    ) -> int:
        self.logger.debug(
            "Expecting <%s> while <%s> is NOT expected. Prompt: %s, Timeout: %s",
            expected_in_output,
            not_expected_in_output,
            wait_for_prompt,
            timeout,
        )
        expected_not_compiled = (
            expected_in_output
            if isinstance(expected_in_output, list)
            else [expected_in_output]
        )
        not_expected_not_compiled = (
            not_expected_in_output
            if isinstance(not_expected_in_output, list)
            else [not_expected_in_output]
        )
        expected = self._compile_pattern_list(expected_not_compiled)
        not_expected = self._compile_pattern_list(not_expected_not_compiled)
        if not (expected or not_expected or wait_for_prompt):
            raise ValueError(
                "Either 'expected' or 'not_expected' value should be given while wait_for_prompt is disabled"
            )
        if prompt is not None:
            expected_prompt_regex = self._get_prompt_regex(prompt)
        elif self._prompt_regex is not None:
            expected_prompt_regex = self._prompt_regex
        else:
            if wait_for_prompt:
                raise ValueError(
                    "Prompt not provieded while wait_for_prompt is enabled"
                )
            expected_prompt_regex = ""
        self.logger.debug("Expecting prompt with regex <%s>", expected_prompt_regex)
        prompt_found = False if wait_for_prompt else True
        expected_found = None
        self._matched = ""
        end_time = datetime.now(tz=timezone.utc) + timedelta(seconds=timeout)
        self._output_lines.clear()
        while True:
            line = self._get_line()
            self._output_lines.append(line.replace("\r", ""))
            if wait_for_prompt and re.search(expected_prompt_regex, line):
                prompt_found = True
            for not_expected_el in not_expected:
                if not_expected_el is not TIMEOUT:
                    if re.search(not_expected_el, line):
                        self._raise_exception(f"Unexpected <{not_expected_el}> found!")
            for idx, expected_item in enumerate(expected):
                if expected_item is not TIMEOUT:
                    matched = re.search(expected_item, line)
                    if matched and not self._matched:
                        expected_found = idx
                        self._matched = matched.group(0)
            if prompt_found and not (
                expected_found is None and (expected or not_expected)
            ):
                self.logger.debug(
                    "Expected <%s> found!",
                    expected[expected_found]
                    if isinstance(expected_found, int)
                    else None,
                )
                return (
                    expected_found
                    if isinstance(expected_found, int)
                    else self.PROMPT_ONLY
                )
            if timeout > 0 and datetime.now(tz=timezone.utc) > end_time:
                if wait_for_prompt and not prompt_found:
                    self._raise_exception(
                        f"Prompt <{expected_prompt_regex}> not found",
                        CopperCommConnectionError,
                    )
                if not expected:
                    self.logger.debug("Not expected <%s> have not occurred", expected)
                    return self.NOT_EXPECTING
                if TIMEOUT in expected:
                    self.logger.debug("Expected TIMEOUT occured")
                    return expected.index(TIMEOUT)
                self._raise_exception(f"Expected <{expected}> not found!")

    def _get_prompt_regex(self, prompt: Union[str, List[str], None]) -> str:
        if prompt is None:
            return ""
        elif isinstance(prompt, str):
            return prompt if prompt.startswith("\\") else re.escape(prompt)
        else:
            return "|".join([x if x.startswith("\\") else re.escape(x) for x in prompt])

    def _compile_pattern_list(
        self, patterns: Iterable[Union[Pattern, TIMEOUT, str]]
    ) -> List[Union[Pattern, TIMEOUT]]:
        compiled_pattern_list = []
        for pattern in patterns:
            if isinstance(pattern, str):
                compiled_pattern_list.append(re.compile(pattern))
            elif isinstance(pattern, type(re.compile(""))) or pattern is TIMEOUT:
                compiled_pattern_list.append(pattern)
            else:
                self._raise_exception(
                    f"{type(pattern)} is not allowed type for pattern!"
                )
        return compiled_pattern_list

    def _raise_exception(
        self,
        exception_message: str,
        exception_cls=AssertionError,
        log_level: int = logging.DEBUG,
    ) -> None:
        self.logger.log(log_level, "SerialConsoleInterface Exception: %s", exception_message)
        raise exception_cls(f"[{self.connection_name}]: {exception_message}")
