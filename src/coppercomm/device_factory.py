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

import functools
import typing
from pathlib import Path

from coppercomm.config_file_parser import Config, ConfigFileParseError, load_config
from coppercomm.device_adb.adb_interface import Adb
from coppercomm.device_serial.device_serial import SerialConnection
from coppercomm.fastboot_interface import Fastboot
from coppercomm.ssh_connection.ssh_connection import SSHConnection


class DeviceResourceUnavailableError(AssertionError):
    def __init__(self, resource: str):
        super().__init__(f"{resource} not available. Is the device type correct in configuration file?")


class DeviceFactory:
    def __init__(self, device_config: typing.Optional[Path] = None):
        config, config_file = load_config(device_config)
        self.config: Config = config
        self.config_file: Path = config_file

    def create_adb(self) -> Adb:
        return Adb(self.config.get_adb_device_id())

    def create_phone_adb(self) -> typing.List[Adb]:
        android_phones = self.config.get_extra_devices(device_type="phone", device_os="android")
        return [Adb(phone["adb_device_id"]) for phone in android_phones]

    @functools.lru_cache
    def create_ssh_over_adb(self) -> SSHConnection:
        port = self.config.get("QNX.port", 22)
        proxy_command = self.config["QNX.proxy_command"]
        return SSHConnection(ip=self.config.get_qnx_ip(), port=port, proxy_command=proxy_command)

    @functools.lru_cache
    def create_broadrreach_ssh(self) -> SSHConnection:
        if self.config.has_entry("QNX.proxy_command"):
            # Network adapter is not connected. Use SSH over ADB.
            raise ConfigFileParseError("No network data defined in the config.")
        ip = self.config["QNX.ip"]
        port = self.config.get("QNX.port", 22)
        return SSHConnection(ip=ip, port=port)

    @functools.lru_cache
    def create_qnx_ssh(self) -> SSHConnection:
        """Create SSHConnection object based on the config file.

        :return: Object that use either SSH over network adapter or SSH over ADB.
        :raises ConfigFileParseError: If nothing is available.
        """
        try:
            return self.create_broadrreach_ssh()
        except ConfigFileParseError:
            return self.create_ssh_over_adb()

    @functools.lru_cache
    def create_serial(self, serial_device_type: str) -> SerialConnection:
        if serial_device_type not in self.config.get_name_of_available_serials_in_config():
            raise DeviceResourceUnavailableError(f"{serial_device_type}")
        return SerialConnection(self.config, serial_device_type)

    def create_serial_devices(self):
        return {t: self.create_serial(t) for t in self.config.get_name_of_available_serials_in_config()}

    def create_fastboot(self) -> Fastboot:
        return Fastboot(self.config.get_fastboot_device_id())
