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

import contextlib
import logging.config
import typing
from contextlib import ExitStack
from dataclasses import dataclass

from coppercomm.config_file_parser import Config
from coppercomm.device_adb.adb_interface import Adb
from coppercomm.device_factory import DeviceFactory
from coppercomm.device_serial.device_serial import SerialConnection
from coppercomm.loggers.device_logger import DeviceLoggerViaAdb
from coppercomm.loggers.utils.log_dir import LogDir
from coppercomm.ssh_connection.ssh_connection import SSHConnection

_logger = logging.getLogger("device")


class DeviceError(Exception):
    pass


@dataclass
class Device:
    """Aggregates all components available in device under test."""

    config: Config
    adb: Adb
    serial_devices: typing.Mapping[str, SerialConnection]
    ssh: typing.Mapping[str, SSHConnection]
    test_log_dir: LogDir

    @property
    def device_type(self):
        """
        Returns the name of the current device.
        """
        _logger.info(f"The device type is: {self.config.get_device_name()}")

        return self.config.get_device_name()

    def adb_logger(self, command: str, *, shell: bool = True) -> DeviceLoggerViaAdb:
        return DeviceLoggerViaAdb(
            self.config.get_adb_device_id(),
            command,
            test_log_dir=self.test_log_dir.name,
            shell=shell,
        )

    @staticmethod
    @contextlib.contextmanager
    def managed(*, test_log_dir="") -> typing.Generator["Device", None, None]:
        """Convenience "constructor" internally managing all device resources. To be used in `with` statement."""
        with ExitStack() as exitstack:
            factory = DeviceFactory()
            adb = factory.create_adb()
            device = Device(
                config=factory.config,
                adb=adb,
                ssh=_create_ssh_connections(factory, adb),
                serial_devices=factory.create_serial_devices(),
                test_log_dir=test_log_dir
            )
            for serial_connection in device.serial_devices.values():
                exitstack.enter_context(serial_connection)
            yield device


def _create_ssh_connections(device_factory: DeviceFactory, adb: Adb) -> typing.Mapping[str, SSHConnection]:
    class _LazyDict(typing.Mapping[str, SSHConnection]):
        def __init__(self, loaders: typing.Mapping[str, typing.Callable[[], SSHConnection]]):
            self._cached: typing.Dict[str, SSHConnection] = dict()
            self._loaders = loaders

        def __getitem__(self, key: str) -> SSHConnection:
            if key not in self._cached:
                loader = self._loaders[key]
                self._cached[key] = loader()

            return self._cached[key]

        def __len__(self) -> int:
            return len(self._loaders)

        def __iter__(self) -> typing.Iterator[str]:
            return iter(self._loaders)

    return _LazyDict(
        {
            "broadrreach": lambda: device_factory.create_broadrreach_ssh(),
        }
    )
