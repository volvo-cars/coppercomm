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

from coppercomm.config_file_parser import Config, SerialDeviceType, load_config
from coppercomm.device_adb.adb_interface import Adb
from coppercomm.device_serial.device_serial import SerialConnection
from coppercomm.ssh_connection.ssh_connection import SSHConnection


class DeviceResourceUnavailableError(AssertionError):
    def __init__(self, resource: str):
        super().__init__(f"{resource} not available. Is the device type correct in configuration file?")


class DeviceFactory:
    def __init__(self):
        self.config: Config = load_config()

    def create_adb(self) -> Adb:
        return Adb(self.config.get_adb_device_id())

    def create_phone_adb(self) -> Adb | list[Adb]:
        if type(self.config.get_adb_extra_device_id()) == list:
            return [Adb(device_id) for device_id in self.config.get_adb_extra_device_id()]
        return Adb(self.config.get_adb_extra_device_id())

    def create_ssh_over_adb(self, adb: Adb) -> SSHConnection:
        # try to wait a bit for adb in case unit was just rebooted
        adb.wait_for_state(timeout=10)
        # forward port to host, android have ssh tunnel to qnx.
        # localhost <--> android <--> qnx:
        local_ssh_port = self.config.get_host_adb_sshport()
        adb.check_output(f"forward tcp:{local_ssh_port} tcp:22")
        return SSHConnection(ip="127.0.0.1", port=local_ssh_port)

    def create_broadrreach_ssh(self) -> SSHConnection:
        return SSHConnection(self.config.get_qnx_ip())

    def create_serial_devices(
        self,
    ) -> typing.Mapping[SerialDeviceType, SerialConnection]:
        return {t: SerialConnection(self.config, t) for t in self.available_serials()}

    def create_serial(self, serial_device_type: SerialDeviceType) -> SerialConnection:
        if serial_device_type not in self.available_serials():
            raise DeviceResourceUnavailableError(f"{serial_device_type}")

        return SerialConnection(self.config, serial_device_type)

    def available_serials(self) -> typing.Sequence[SerialDeviceType]:
        serials = {
            "device1": (SerialDeviceType.SupportCPU, SerialDeviceType.QNX),
            "DHU": (SerialDeviceType.SupportCPU, SerialDeviceType.QNX),
        }
        return serials[self.config.get_device_name()]
