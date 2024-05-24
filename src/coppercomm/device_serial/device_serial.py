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
import typing

from coppercomm.config_file_parser import Config
from coppercomm.device_serial.serial_console_interface import SerialConsoleInterface
from coppercomm.device_serial.console import Console


class InvalidSerialDeviceError(Exception):
    pass


class SerialConnection(Console):
    def __init__(self, config: Config, serial_device: str) -> None:
        self._logger = logging.getLogger(__name__)
        self.console_object = SerialConsoleInterface(
            config.get_serial_device_path(serial_device),
            connection_name=serial_device,
            prompt=config.get_serial_prompt(serial_device),
        )

    def __enter__(self) -> "SerialConnection":
        self._logger.info(f"Starting the serial connection: {self}")
        self.console_object.start()
        return self

    def __exit__(self, *args, **kwargs) -> typing.Literal[False]:
        self.console_object.close_console()
        return False

    def set_test_logging(self, path):
        self.console_object.set_test_logging(path=path)
