# /*===========================================================================*\
#  * Copyright 2018 Aptiv, Inc., All Rights Reserved.
#  * Delphi Confidential
# \*===========================================================================*/
import typing

from .one_update_interfaces import OneUpdateConsoleInterface, Expectations
from .communication.serial_console_interface import SerialConsoleInterface


class OneUpdateConsole(OneUpdateConsoleInterface):
    def __init__(
        self, connection_address: str, prompt: typing.Union[str, typing.List[str]], connection_name: str
    ) -> None:
        console_object = SerialConsoleInterface(
            connection_address=connection_address, connection_name=connection_name, prompt=prompt
        )
        super().__init__(console_object)

    def send_line(
        self,
        command: str,
        check_echo: bool = True,
        wait_for_prompt: bool = False,
        timeout: float = 1,
        prompt: typing.Union[str, typing.List[str]] = None,
    ) -> None:
        self.console_object.send_command(
            command, check_echo=check_echo, wait_for_prompt=wait_for_prompt, timeout=timeout, prompt=prompt
        )

    def send_line_and_expect(
        self,
        command: str,
        pattern: Expectations,
        timeout: float,
        check_echo: bool = True,
        wait_for_prompt: bool = True,
        prompt: typing.Union[str, typing.List[str]] = None,
    ) -> int:
        return self.console_object.send_command(
            command,
            check_echo=check_echo,
            expected_in_output=pattern,
            timeout=timeout,
            wait_for_prompt=wait_for_prompt,
            prompt=prompt,
        )

    def expect(self, pattern: Expectations, timeout: float) -> int:
        return self.console_object.expect(expected=pattern, timeout=timeout)

    def get_matched(self) -> str:
        return self.console_object.get_matched()

    def close_console(self) -> None:
        self.console_object.close_console()

    def set_prompt(self, prompt: typing.Union[str, typing.List[str]]) -> None:
        self.console_object.set_prompt(prompt)
