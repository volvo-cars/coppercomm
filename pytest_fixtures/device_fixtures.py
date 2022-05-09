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

from coppercomm.device_factory import DeviceFactory
from coppercomm.device import Device
from coppercomm.ci_config import Config
from coppercomm.device_adb.adb_interface import Adb
from coppercomm.device_serial.device_serial import SerialConnection, SerialDeviceType
from coppercomm.device_state_monitor.adb_state_monitor import AdbStateMonitor
from coppercomm.ssh_connection.ssh_connection import SSHConnection
from coppercomm.device_state_monitor.ssh_state_monitor import SshStateMonitor


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
def adb_connection_state_monitor(adb: Adb):
    connection_monitor = AdbStateMonitor(adb)
    yield
    connection_monitor.stop()


@pytest.fixture(scope="session")
def ssh_connection_state_monitor(qnx_broadrreach_ssh):
    connection_monitor = SshStateMonitor(qnx_broadrreach_ssh=qnx_broadrreach_ssh)
    yield
    connection_monitor.stop()


@pytest.fixture(scope="session")
def qnx_serial(device_factory: DeviceFactory) -> SerialConnection:
    return device_factory.create_serial(SerialDeviceType.QNX)


@pytest.fixture(scope="session")
def support_cpu_serial(device_factory: DeviceFactory) -> SerialConnection:
    return device_factory.create_serial(SerialDeviceType.SupportCPU)


@pytest.fixture(scope="session")
def hkp_serial(device_factory: DeviceFactory) -> SerialConnection:
    return device_factory.create_serial(SerialDeviceType.HKP)


@pytest.fixture(scope="function")
def device_config(device_factory: DeviceFactory) -> Config:
    return device_factory.config
