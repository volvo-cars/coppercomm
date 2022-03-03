"""
For use in pytest test
Register fixtures as plugins, do not import them directly!
https://docs.pytest.org/en/latest/how-to/writing_plugins.html?highlight=plugin#requiring-loading-plugins-in-a-test-module-or-conftest-file

Example:

pytest_plugins = "pytest_fixtures.device_fixtures"


def test_ping_android_dev_interface(qnx_serial_device):
    pass
"""
import pytest
import typing

from device_factory import DeviceFactory
from device import Device
from ci_config import Config
from device_adb.adb_interface import Adb
from device_serial.device_serial import SerialConnection, SerialDeviceType
from ssh_connection.ssh_connection import SSHConnection

@pytest.fixture(scope="session")
def device_factory() -> DeviceFactory:
    return DeviceFactory()


@pytest.fixture(scope="session")
def adb(device_factory: DeviceFactory) -> Adb:
    return device_factory.create_adb()


@pytest.fixture(scope="session")
def qnx_ssh_over_adb(device_factory: DeviceFactory, adb: Adb) -> SSHConnection:
    return device_factory.create_ssh_over_adb(adb)


@pytest.fixture(scope="session")
def qnx_broadrreach_ssh(device_factory: DeviceFactory) -> SSHConnection:
    return device_factory.create_broadrreach_ssh()


@pytest.fixture(scope="session")
def qnx_serial(device_factory: DeviceFactory) -> SerialConnection:
    return device_factory.create_serial(SerialDeviceType.QNX)


@pytest.fixture(scope="session")
def hkp_serial(device_factory: DeviceFactory) -> SerialConnection:
    return device_factory.create_serial(SerialDeviceType.SupportCPU)


@pytest.fixture(scope="function")
def device_config(device_factory: DeviceFactory) -> Config:
    return device_factory.config


@pytest.fixture
def test_device(
    device_factory: DeviceFactory,
    adb: Adb,
    support_cpu_serial: SerialConnection,
    qnx_serial: SerialConnection,
    qnx_broadrreach_ssh: SSHConnection,
) -> Device:
    ssh = {"broadrreach": qnx_broadrreach_ssh}
    serial = {
        SerialDeviceType.QNX: qnx_serial,
        SerialDeviceType.SupportCPU: support_cpu_serial,
    }
    return Device(config=device_factory.config, adb=adb, ssh=ssh, serial_devices=serial)
