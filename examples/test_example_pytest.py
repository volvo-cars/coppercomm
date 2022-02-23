# Copyright 2021 Volvo Car Corporation
# This file is covered by LICENSE file in the root of this project

# See how run example tests by looking into test_plan.py on tests with name that starts with DeviceFrameworkExample.

import pytest

from test_manager.devices.ci_config import SerialDeviceType
from test_manager.devices.device import Device, Adb

pytest_plugins = "test_manager.test_lib.dhu.pytest_fixtures.device_fixtures"


# We can use adb_*_logger fixtures like this to implicitly add them to all tests
# in this module. We could also use them directly in test funcitons which gives
# more control. Preferably @pytest.mark.usefixtures("adb_dmesg_logger") should
# be used in that case as we do not need to refer to the logger fixtures in the
# test body.
# @pytest.fixture(autouse=True)
# def adb_loggers(test_device: Device, adb_dmesg_logger, adb_logcat_logger):
#     pass


@pytest.fixture(autouse=True)
def adb_dmesg_logger(adb_dmesg_logger):
    pass


@pytest.fixture(autouse=True)
def adb_logcat_logger(adb_logcat_logger):
    pass


@pytest.mark.hkp  # Registered marks can be used from test_plan level to filter tests.
def test_example(test_device: Device):
    test_device.adb.gain_root_permissions(timeout=60)
    test_device.adb.shell("ls")
    test_device.serial_devices[SerialDeviceType.HKP].send_line("help")


@pytest.mark.qnx
def test_example_whoami(test_device: Device):
    test_device.adb.shell("whoami")
    test_device.serial_devices[SerialDeviceType.QNX].send_line("whoami")


def test_example_using_interface_directly(adb: Adb):
    """When there is no need for test_device fixture, it is possible to directly use fixture for specific interface."""
    adb.shell("whoami")
