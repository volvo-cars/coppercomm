# Copyright 2018-2021 Volvo Car Corporation
# This file is covered by LICENSE file in the root of this project

import contextlib
import logging.config
import typing

from contextlib import ExitStack
from dataclasses import dataclass

from test_manager.devices.ci_config import Config, SerialDeviceType
from test_manager.devices.device_adb.device_adb import Adb
from test_manager.devices.device_factory import DeviceFactory
from test_manager.devices.device_serial.device_serial import SerialConnection
from test_manager.devices.loggers.device_logger import DeviceLoggerViaAdb
from test_manager.devices.ssh_connection.ssh_connection import SSHConnection
from test_manager.test_lib.grassland.library.log.log_dir import LogDir

_logger = logging.getLogger("device")


class DeviceError(Exception):
    # TODO create a framework exception layer to inherit from, to see difference between testing error or framework error
    pass


@dataclass
class Device:
    """Aggregates all components available in device under test."""

    config: Config
    adb: Adb
    serial_devices: typing.Mapping[SerialDeviceType, SerialConnection]
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
                test_log_dir=LogDir(test_log_dir),
                serial_devices=factory.create_serial_devices(),
            )
            for serial_connection in device.serial_devices.values():
                exitstack.enter_context(serial_connection)
            yield device


# TODO: remove when HKP tests are switched to use splitted fixtures instead of complete test_device fixture
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
            "adb_ssh": lambda: device_factory.create_ssh_over_adb(adb),
        }
    )
