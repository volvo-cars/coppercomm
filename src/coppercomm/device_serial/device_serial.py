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

from collections.abc import Mapping

from coppercomm.config_file_parser import Config, SerialDeviceType
from coppercomm.device_serial.serial_console_interface import SerialConsoleInterface
from coppercomm.device_serial.console import Console


class InvalidSerialDeviceError(Exception):
    pass


class SerialConnection(Console):
    def __init__(self, config: Config, serial_device: SerialDeviceType) -> None:
        self._logger = logging.getLogger(__name__)
        self.console_object = SerialConsoleInterface(
            config.get_serial_device_path(serial_device),
            connection_name=serial_device.value,
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


class SerialConnectionMapping(Mapping):
    def __init__(self) -> None:
        self._devices: typing.Dict[SerialDeviceType, SerialConnection] = {}

    def __getitem__(self, serial_device_type: SerialDeviceType) -> SerialConnection:
        try:
            return self._devices[serial_device_type]
        except KeyError as ke:
            raise InvalidSerialDeviceError(
                f"Invalid serial device: {ke}. Available devices: {list(self.keys())}"
            ) from None

    def __setitem__(
        self, serial_device_type: SerialDeviceType, serial_connection: SerialConnection
    ) -> None:
        self._devices[serial_device_type] = serial_connection

    def __iter__(self) -> typing.Iterator[SerialDeviceType]:
        return self._devices.__iter__()

    def __len__(self) -> int:
        return len(self._devices)
