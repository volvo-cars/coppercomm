from unittest.mock import Mock, patch

import pytest
from coppercomm import fastboot_interface


class TestFastboot:

    def test_constructor(self):
        fastboot = fastboot_interface.Fastboot()

        assert fastboot.device_id is None
        assert fastboot._fastboot_cmd == ["fastboot"]

    def test_constructor_with_device_id(self):
        device_id = "1234abc"
        fastboot = fastboot_interface.Fastboot(device_id=device_id)

        assert fastboot.device_id == device_id
        assert fastboot._fastboot_cmd == ["fastboot", "-s", device_id]

    @pytest.fixture()
    def fastboot_m(self):
        m = Mock(fastboot_interface.Fastboot)
        m._device_id = "1234abc"
        m.device_id = m._device_id
        m._fastboot_cmd = ["fastboot", "-s", m.device_id]
        return m

    @patch("coppercomm.fastboot_interface.execute_command")
    def test_check_output(self, execute_command, fastboot_m):

        resp = fastboot_interface.Fastboot.check_output(fastboot_m, "command arg1")

        assert resp == execute_command.return_value
        execute_command.assert_called_once_with(
            ["fastboot", "-s", "1234abc", "command", "arg1"],
            assert_ok=True,
            regrep=None,
            timeout=30,
            log_output=True,
        )

    def test_get_state_with_device_id(self, fastboot_m):
        fastboot_m.check_output.return_value = ("674sdf\tfastbootd\n"
                                                f"{fastboot_m.device_id}\tfastboot\n")

        state = fastboot_interface.Fastboot.get_state(fastboot_m)

        assert state == fastboot_interface.FastbootState.FASTBOOT


    def test_get_state_without_device_id(self, fastboot_m):
        fastboot_m.device_id = None

        fastboot_m.check_output.return_value = ("674sdf\tfastbootd\n"
                                                f"{fastboot_m.device_id}\tfastboot\n")

        state = fastboot_interface.Fastboot.get_state(fastboot_m)

        assert state == fastboot_interface.FastbootState.FASTBOOTD


    def test_reboot_without_new_state(self, fastboot_m):
        fastboot_interface.Fastboot.reboot(fastboot_m)

        fastboot_m.check_output.assert_called_once_with(["reboot"])

    def test_reboot_with_new_state(self, fastboot_m):
        fastboot_interface.Fastboot.reboot(fastboot_m, "fastbootd")

        fastboot_m.check_output.assert_called_once_with(["reboot", "fastbootd"])

    def test_erase(self, fastboot_m):
        fastboot_interface.Fastboot.erase(fastboot_m, "partition")

        fastboot_m.check_output.assert_called_once_with(["erase", "partition"], timeout=10)

    def test_flash(self, fastboot_m):
        fastboot_interface.Fastboot.flash(fastboot_m, "partition", "image")

        fastboot_m.check_output.assert_called_once_with(["flash", "partition", "image"], timeout=60)
