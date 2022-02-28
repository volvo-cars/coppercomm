import logging
import typing

from device_serial.device_serial import SerialConnection
from device_adb.adb_interface import Adb
from ci_config import Config, SerialDeviceType
from ssh_connection.ssh_connection import SSHConnection

_logger = logging.getLogger(__name__)


class DeviceResourceUnavailableError(AssertionError):
    def __init__(self, resource: str):
        super().__init__(f"{resource} not available. Is the device type correct in configuration file?")


class DeviceFactory:
    def __init__(self):
        # read config file on NUC and return Object based on the device stated in the JSON file("IHU", "DHU")
        self.config = Config(directory="~")

    def create_adb(self) -> Adb:
        return Adb(self.config.get_adb_device_id())

    def create_ssh_over_adb(self, adb: Adb) -> SSHConnection:
        if self.config.get_device_name() == "DHU":
            # try to wait a bit for adb in case unit was just rebooted
            adb.wait_for_state(timeout=10)
            # forward port to host, android have ssh tunnel to qnx.
            # localhost <--> android <--> qnx:
            local_ssh_port = self.config.get_host_adb_sshport()
            adb.check_output(f"forward tcp:{local_ssh_port} tcp:22")
            return SSHConnection(ip="127.0.0.1", port=local_ssh_port)
        else:
            raise DeviceResourceUnavailableError("SSH over ADB")

    def create_broadrreach_ssh(self) -> SSHConnection:
        if self.config.get_device_name() != "DHU":
            raise DeviceResourceUnavailableError("Broadrreach SSH")

        return SSHConnection(self.config.get_qnx_ip())

    def create_serial_devices(self) -> typing.Mapping[SerialDeviceType, SerialConnection]:
        return {t: SerialConnection(self.config, t) for t in self.available_serials()}

    def create_serial(self, serial_device_type: SerialDeviceType) -> SerialConnection:
        if serial_device_type not in self.available_serials():
            raise DeviceResourceUnavailableError(f"{serial_device_type}")

        return SerialConnection(self.config, serial_device_type)

    def available_serials(self) -> typing.Sequence[SerialDeviceType]:
        serials = {
            "IHU": (SerialDeviceType.VIP, SerialDeviceType.MP),
            "DHU": (SerialDeviceType.HKP, SerialDeviceType.QNX),
            "IHU_EMU": (),
        }
        return serials[self.config.get_device_name()]
