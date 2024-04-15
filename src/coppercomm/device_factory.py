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
from pathlib import Path

from coppercomm.config_file_parser import Config, ConfigFileParseError, load_config
from coppercomm.device_adb.adb_interface import Adb
from coppercomm.device_serial.device_serial import SerialConnection
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
        return [Adb(phone["ADB_DEVICE_ID"]) for phone in self.config.get_extra_devices(device_type="android_phone")]

    def create_ssh_over_adb(self, adb: Adb) -> SSHConnection:
        # try to wait a bit for adb in case unit was just rebooted
        adb.wait_for_state(timeout=10)
        # forward port to host, android have ssh tunnel to qnx.
        # localhost <--> android <--> qnx:
        local_ssh_port = self.config.get_host_adb_sshport()
        adb.check_output(f"forward tcp:{local_ssh_port} tcp:22")
        return SSHConnection(ip="127.0.0.1", port=local_ssh_port)

    def create_broadrreach_ssh(self) -> SSHConnection:
        try:
            port = self.config.get_qnx_port()
        except ConfigFileParseError:
            port = "22"
        return SSHConnection(ip=self.config.get_qnx_ip(), port=port)

    def create_serial(self, serial_device_type: str) -> SerialConnection:
        if serial_device_type not in self.config.get_name_of_available_serials_in_config():
            raise DeviceResourceUnavailableError(f"{serial_device_type}")
        return SerialConnection(self.config, serial_device_type)

    def create_serial_devices(self):
        return {t: SerialConnection(self.config, t) for t in self.config.get_name_of_available_serials_in_config()}
