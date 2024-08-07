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
from pathlib import Path

from coppercomm.config_file_parser import Config, ConfigFileParseError
from coppercomm.device_adb.adb_interface import Adb
from coppercomm.device_factory import DeviceFactory
from coppercomm.device_serial.device_serial import SerialConnection
from coppercomm.ssh_connection.ssh_connection import SSHConnection


@pytest.fixture(scope="session")
def device_factory(create_device_config: Path) -> DeviceFactory:
    return DeviceFactory(create_device_config)


@pytest.fixture(scope="session")
def adb(device_factory: DeviceFactory) -> typing.Optional[Adb]:
    try:
        return device_factory.create_adb()
    except ConfigFileParseError:
        return None


@pytest.fixture(scope="session")
def adb_phone(device_factory: DeviceFactory) -> typing.List[Adb]:
    """This fixture will return list with adb interface for each extra device."""
    return device_factory.create_phone_adb()


@pytest.fixture(scope="session")
def qnx_ssh_over_adb(device_factory: DeviceFactory) -> typing.Optional[SSHConnection]:
    """SSH connection to QNX over ADB."""
    try:
        return device_factory.create_ssh_over_adb()
    except Exception:
        return None


@pytest.fixture(scope="session")
def qnx_broadrreach_ssh(device_factory: DeviceFactory) -> typing.Optional[SSHConnection]:
    """SSH connection to QNX over BroadR-Reach."""
    try:
        return device_factory.create_broadrreach_ssh()
    except Exception:
        return None


@pytest.fixture(scope="session")
def qnx_ssh(
    qnx_broadrreach_ssh: typing.Optional[SSHConnection], qnx_ssh_over_adb: typing.Optional[SSHConnection]
) -> typing.Optional[SSHConnection]:
    """Pick one of the available SSH connections."""
    if qnx_broadrreach_ssh:
        return qnx_broadrreach_ssh
    if qnx_ssh_over_adb:
        return qnx_ssh_over_adb
    return None


@pytest.fixture(scope="session")
def qnx_serial(device_factory: DeviceFactory) -> typing.Optional[SerialConnection]:
    try:
        return device_factory.create_serial("QNX")
    except Exception:
        return None


@pytest.fixture(scope="session")
def support_cpu_serial(device_factory: DeviceFactory) -> typing.Optional[SerialConnection]:
    try:
        return device_factory.create_serial("SupportCPU")
    except Exception:
        return None


@pytest.fixture(scope="session")
def device_config(device_factory: DeviceFactory) -> Config:
    return device_factory.config
