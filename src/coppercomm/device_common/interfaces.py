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
import logging

from abc import ABCMeta, abstractmethod
from time import sleep
from pexpect import ExceptionPexpect

from coppercomm.device_serial.serial_console_interface import SerialConsoleInterface


Expectation = typing.Union[str, ExceptionPexpect]
Expectations = typing.Union[Expectation, typing.List[Expectation]]


class ConsoleInterface(object):
    """
    This is a wrapper for different serial communication classes that ensures a common interface
    for sending and expecting data on console
    """

    __metaclass__ = ABCMeta

    def __init__(self, console_object: SerialConsoleInterface) -> None:
        self.console_object = console_object

    @abstractmethod
    def send_line(
        self,
        command: str,
        check_echo: bool = True,
        wait_for_prompt: bool = False,
        timeout: float = 2,
        prompt: typing.Union[str, typing.List[str], None] = None,
    ) -> None:
        """
        Method that sends a line on the console (using console_object)
        """
        pass

    @abstractmethod
    def send_line_and_expect(
        self,
        command: str,
        pattern: Expectations,
        timeout: float,
        check_echo: bool = True,
        wait_for_prompt: bool = True,
        prompt: typing.Union[str, typing.List[str], None] = None,
    ) -> int:
        """
        Method that send a line on the console and expects a pattern or
        list of patterns (using console_object)
        :param command: command to send on the console
        :param pattern: list of patterns to match - should also accept single pattern (string)
        :param timeout: time to wait for expected pattern
        :param wait_for_prompt: indicates that method should wait for expected prompt
        :param prompt: expected prompt(s)
        :return: index of the pattern matched in pattern list
        """
        pass

    @abstractmethod
    def expect(self, pattern: Expectations, timeout: float) -> int:
        """
        Method that expects a pattern or a list of patterns on the console (using console_object)
        :param pattern: list of patterns to match - should also accept single pattern (string)
        :param timeout: time (in seconds) to wait for expected pattern
        :return: index of the pattern matched in pattern list
        """
        pass

    @abstractmethod
    def get_matched(self) -> typing.Optional[str]:
        """
        :return: output from console matched with pattern
        """
        pass

    @abstractmethod
    def close_console(self) -> None:
        """
        Method that releases connection handlers
        """
        pass

    @abstractmethod
    def set_prompt(self, prompt: typing.Union[str, typing.List[str]]) -> None:
        """
        Method that sets expected prompt
        """
        pass


class PowerController(object):
    """
    This is a wrapper for controlling unit's power.
    """

    __metaclass__ = ABCMeta

    def __init__(self, logger: typing.Union[logging.Logger, None] = None) -> None:
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(self.__class__.__name__)
            self.logger.setLevel(logging.DEBUG)

    @abstractmethod
    def power_off(self) -> None:
        """
        Method that turns the unit's power off.
        """
        pass

    @abstractmethod
    def power_on(self) -> None:
        """
        Method that turn sthe unit's power on.
        """
        pass

    def power_reset(self, delay: float = 3.0) -> None:
        """
        Method that performs a power cycle restart. By default it just executes power_off() and power_on() with a delay
        in between.
        :param delay: the pause between turning the power off and on.
        """
        self.logger.info("A power reset must be performed.")
        self.power_off()
        while delay > 0:
            self.logger.info("Unit will be powered on after {}s...".format(delay))
            delay_stage = min(delay, 10)
            sleep(delay_stage)
            delay -= delay_stage
        self.power_on()
