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

import typing
import time
from coppercomm.device_common.interfaces import ConsoleInterface, Expectations
from coppercomm.device_serial.serial_console_interface import SerialConsoleInterface


class Console(ConsoleInterface):
    def __init__(
        self,
        connection_address: str,
        prompt: typing.Union[str, typing.List[str], None],
        connection_name: str,
    ) -> None:
        console_object = SerialConsoleInterface(
            connection_address=connection_address,
            connection_name=connection_name,
            prompt=prompt,
        )
        super().__init__(console_object)

    def send_line(
        self,
        command: str,
        check_echo: bool = True,
        wait_for_prompt: bool = False,
        timeout: float = 1,
        prompt: typing.Union[str, typing.List[str], None] = None,
        send_linebreak: bool = True
    ) -> None:
        self.console_object.send_command(
            command,
            check_echo=check_echo,
            wait_for_prompt=wait_for_prompt,
            timeout=timeout,
            prompt=prompt,
            send_linebreak=send_linebreak,
        )

    def send_line_and_expect(
        self,
        command: str,
        pattern: Expectations,
        timeout: float,
        check_echo: bool = True,
        wait_for_prompt: bool = True,
        prompt: typing.Union[str, typing.List[str], None] = None,
        send_linebreak: bool = True,
        number_of_attempts: int = 1,
        attempt_delay: float = 2,
    ) -> int:
        """
        :param number_of_attempts: Number of attempts to run command.
        :param attempt_delay: Delay between attempts in seconds.
        """
        for _ in range(number_of_attempts):
            try:
                return self.console_object.send_command(
                    command,
                    check_echo=check_echo,
                    expected_in_output=pattern,
                    timeout=timeout,
                    wait_for_prompt=wait_for_prompt,
                    prompt=prompt,
                    send_linebreak=send_linebreak,
                )
            except AssertionError as e:
                time.sleep(attempt_delay)
                error = e
        raise error

    def expect(self, pattern: Expectations, timeout: float) -> int:
        return self.console_object.expect(expected=pattern, timeout=timeout)

    def get_matched(self) -> str:
        return self.console_object.get_matched()

    def close_console(self) -> None:
        self.console_object.close_console()

    def set_prompt(self, prompt: typing.Union[str, typing.List[str]]) -> None:
        self.console_object.set_prompt(prompt)

    def get_output(self):
        return self.console_object.get_output()
