# Copyright 2020-2021 Volvo Car Corporation
# This file is covered by LICENSE file in the root of this project

import pytest
from unittest import mock
from test_manager.devices.device_config_gen import find_device_info, ConfigFileGenerateError

MOCK_CHECK_OUTPUT_STR = "test_manager.devices.device_config_gen.Adb.check_output"
MOCK_ADB_SHELL_STR = "test_manager.devices.device_config_gen.Adb.shell"


@pytest.mark.needs_hardware
def test_device_info_name_with_real_hw():
    device, serial_id = find_device_info()
    assert device == "IHU" or device == "DHU"


@pytest.mark.parametrize("device_type", ("device", "recovery"))
@pytest.mark.parametrize(
    "product_name, expected_device",
    (
        ("moose", "DHU"),
        ("ihu_vcc", "IHU"),
        ("ihu_vcc_china", "IHU"),
        ("ihu_vcc_korea", "IHU"),
        ("ihu_vcc_robot_taxi", "IHU"),
        ("ihu_polestar_base", "IHU"),
        ("ihu_polestar", "IHU"),
        ("ihu_polestar_china", "IHU"),
        ("ihu_polestar_korea", "IHU"),
        ("ihu_vcc_base", "IHU"),
        ("ihu_emulator_volvo_car", "IHU_EMU"),
        ("ihu_emu_v_china_car", "IHU_EMU"),
        ("ihu_emu_v_korea_car", "IHU_EMU"),
        ("ihu_emu_v_base_car", "IHU_EMU"),
        ("ihu_emulator_ps_car", "IHU_EMU"),
        ("ihu_emu_ps_china_car", "IHU_EMU"),
        ("ihu_emu_ps_korea_car", "IHU_EMU"),
        ("ihu_emu_ps_base_car", "IHU_EMU"),
    ),
)
def test_device_info(device_type, product_name, expected_device):
    serial_no = "123"
    adb_device_output = f"List of devices attached\n{serial_no}\t{device_type}\n"

    with mock.patch(MOCK_CHECK_OUTPUT_STR, return_value=adb_device_output) as check_output_mocked, mock.patch(
        MOCK_ADB_SHELL_STR, return_value=product_name
    ) as adb_shell_mock:
        device, serial_id = find_device_info()

    adb_shell_mock.assert_called_once_with(["getprop", "ro.product.name"])
    check_output_mocked.assert_called_once_with(["wait-for-device", "devices"], timeout=60)
    assert device == expected_device
    assert serial_id == serial_no


@pytest.mark.parametrize(
    "adb_device_output_message", ("List of devices attached\n123\tunauthorized", "List of devices attached")
)
def test_device_info_failed_to_recognize(adb_device_output_message):
    adb_device_output = f"{adb_device_output_message}\n"
    with pytest.raises(ConfigFileGenerateError) as e_info, mock.patch(
        MOCK_CHECK_OUTPUT_STR, return_value=adb_device_output
    ) as check_output_mocked:
        find_device_info()

    check_output_mocked.assert_called_once_with(["wait-for-device", "devices"], timeout=60)
    assert f"Failed to recognize any device.\n'adb devices' returned:\n {adb_device_output_message}" == str(
        e_info.value
    )


@pytest.mark.parametrize(
    "connected_devices_names",
    (
        ("ihu_vcc", "ihu_vcc"),
        ("moose", "moose"),
        ("moose", "ihu_vcc"),
        ("ihu_emulator_volvo_car", "ihu_vcc"),
        ("moose", "ihu_emulator_volvo_car"),
        ("ihu_vcc", "ihu_emulator_volvo_car"),
        ("ihu_emulator_volvo_car", "ihu_emulator_ps_car"),
    ),
)
def test_device_info_multiple_relevant_devices(connected_devices_names):
    adb_device_output = f"List of devices attached\n123\tdevice\n456\tdevice"
    with pytest.raises(ConfigFileGenerateError) as e_info, mock.patch(
        MOCK_CHECK_OUTPUT_STR, return_value=adb_device_output
    ) as check_output_mocked, mock.patch(MOCK_ADB_SHELL_STR, side_effect=connected_devices_names) as adb_shell_mock:
        find_device_info()

    adb_shell_calls = [mock.call(["getprop", "ro.product.name"]), mock.call(["getprop", "ro.product.name"])]
    adb_shell_mock.assert_has_calls(adb_shell_calls)
    check_output_mocked.assert_called_once_with(["wait-for-device", "devices"], timeout=60)
    assert (
        "More than one relevant device recognized. Out of scope of device framework.\n"
        f"'adb devices' returned:\n {adb_device_output}"
    ) == str(e_info.value)


def test_device_info_multiple_devices_only_one_relevant():
    relevant_id = "456"
    adb_device_output = f"List of devices attached\n123\tdevice\n{relevant_id}\tdevice"
    with mock.patch(MOCK_CHECK_OUTPUT_STR, return_value=adb_device_output) as check_output_mocked, mock.patch(
        MOCK_ADB_SHELL_STR, side_effect=("phone_name", "ihu_vcc")
    ) as adb_shell_mock:
        device, device_id = find_device_info()

    adb_shell_calls = [mock.call(["getprop", "ro.product.name"]), mock.call(["getprop", "ro.product.name"])]
    adb_shell_mock.assert_has_calls(adb_shell_calls)
    check_output_mocked.assert_called_once_with(["wait-for-device", "devices"], timeout=60)
    assert device == "IHU"
    assert device_id == relevant_id


def test_device_info_deamon_not_running():
    adb_device_output = (
        "* daemon not running; starting now at tcp:5037\n* daemon started successfully\n"
        f"List of devices attached\n123\tdevice"
    )
    with mock.patch(MOCK_CHECK_OUTPUT_STR, return_value=adb_device_output) as check_output_mocked, mock.patch(
        MOCK_ADB_SHELL_STR, return_value="ihu_vcc"
    ) as adb_shell_mock:
        device, device_id = find_device_info()

    adb_shell_calls = [mock.call(["getprop", "ro.product.name"])]
    adb_shell_mock.assert_has_calls(adb_shell_calls)
    check_output_mocked.assert_called_once_with(["wait-for-device", "devices"], timeout=60)
    assert device == "IHU"
    assert device_id == "123"
