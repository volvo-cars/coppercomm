# Copyright 2018-2021 Volvo Car Corporation
# This file is covered by LICENSE file in the root of this project

import logging
import typing

from collections.abc import Mapping

from test_manager.devices.ci_config import Config, SerialDeviceType
from one_update.communication.serial_console_interface import SerialConsoleInterface
from one_update.one_update_console import OneUpdateConsole


# TODO: Inherit from framework-common exception type when available
class InvalidSerialDeviceError(Exception):
    pass


class SerialConnection(OneUpdateConsole):
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

    def __setitem__(self, serial_device_type: SerialDeviceType, serial_connection: SerialConnection) -> None:
        self._devices[serial_device_type] = serial_connection

    def __iter__(self) -> typing.Iterator[SerialDeviceType]:
        return self._devices.__iter__()

    def __len__(self) -> int:
        return len(self._devices)
