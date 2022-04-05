import pytest

from ci_config import SerialDeviceType
from device import Device

pytest_plugins = "pytest_fixtures.device_fixtures"


def test_example(test_device: Device):
    test_device.adb.gain_root_permissions(timeout=60)
    assert "asd" == test_device.adb.shell("ls")
    test_device.serial_devices[SerialDeviceType.SupportCPU].send_line("help")


@pytest.mark.qnx
def test_example_whoami(test_device: Device):
    test_device.adb.shell("whoami")
    test_device.serial_devices[SerialDeviceType.QNX].send_line("whoami")
    asd, _, _ = test_device.ssh["broadrreach"].execute_cmd("ls")
    assert "asd" == asd.readlines()
