#!/usr/bin/env python3.8

# Copyright 2021-2022 Volvo Car Corporation
# This file is covered by LICENSE file in the root of this project

import logging
import subprocess
import json
import serial
import re
import os
import copy
import time
import psutil  # type: ignore
import ipaddress
import serial.tools.list_ports
from typing import Dict, List, Tuple

from test_manager.utils.test_env import AOSP_ROOT
from test_manager.devices.device_adb.device_adb import Adb

_logger = logging.getLogger(__name__)


class ConfigFileGenerateError(Exception):
    pass


DEVICE_CONFIG_TEMPLATE = {"ADB": {"adb_device_id": ""}, "DEVICE": "", "HOST": {"adb_ssh_port": 49900}, "NETWORK": {}}


def find_port_info(tty: serial.Serial, device: str) -> str:
    ihu_commands = [b"getprop ro.serialno \r\n", b"version \r\n"]
    dhu_commands = [b"version \r\n", b"\r\n"]
    ihu_responses = [
        ["VIP", r"\s*Project_ID.*VCC_IHU.*VIP"],
        ["VIP", r"\s*Project Name\/Version: VCC_IHU.*BOOTLOADER"],
        ["MP", r"USB for fastboot transport layer selected"],
        ["MP", r"S0J*"],
        ["MP", r"R1J*"],
        ["MP", r".*/sh: version: not found"],
    ]
    dhu_responses = [
        ["HKP", r"\s*jenkins.*moose.*hkp"],
        ["HKP", r".*hkp"],
        ["QNX", r"USB for fastboot transport layer selected"],
        ["QNX", r"(.*)QNX(.*?) .*"],
    ]
    reponses = {"IHU": ihu_responses, "DHU": dhu_responses}
    commands = {"IHU": ihu_commands, "DHU": dhu_commands}

    platform = None
    for cmd in commands[device]:
        platform = serial_send_and_find(tty, cmd, reponses[device], lines=30)
        if platform is not None:
            break
    return platform


def serial_send_and_find(
    port: serial.Serial,
    input_str: bytes,
    match_strings: List[List[str]],
    lines: int = 10,
) -> str:
    port.flush()
    port.write(input_str)

    device = None
    for _ in range(lines):
        line = port.readline().decode("utf-8", errors="replace")
        if len(line) == 0:
            break
        for pos, s in match_strings:
            if (re.match(s, line)) is not None:
                device = pos
                return device
    return device


def find_device_info() -> Tuple[str, str]:
    """
    Get device info by first detecting all adb devices and then asking each individually about detailed info.

    Only relevant devices (ihu or dhu) are considered. Other devices are ignored, emulators are also ignored.

    Example output of adb devices:
    List of devices attached
    R58N23PJ5NE	unauthorized
    R58N23PJ5VP	device
    S0J59X12e92667 device
    """

    def _get_device_if_supported_product(product: str) -> str:
        product_starts_with_to_device_mapping = {
            "ihu_vcc": "IHU",
            "ihu_polestar": "IHU",
            "moose": "DHU",
            "ihu_emu": "IHU_EMU",
        }
        for product_starts_with, device_name in product_starts_with_to_device_mapping.items():
            if product.startswith(product_starts_with):
                return device_name
        return ""

    # TODO: Handle an edge case, where Rig has IHU & Phone connected, but only Phone is discoverable
    #       and we need to wait for IHU to be discoverable
    adb_devices_output = Adb().check_output(["wait-for-device", "devices"], timeout=60).strip()
    pattern = r"""
    (\w+|\w+\-\w+)          # Matches a device id or emulator id with "-" in the middle
    \t                      # One tab
    (?:device|recovery)     # Non capturing group for one of allowed device state.
    (?:\Z|\n)               # Non capturing group for end of string or end of line
    """
    all_adb_devices = re.findall(pattern, adb_devices_output, re.VERBOSE)

    relevant_devices = []

    for device_id in all_adb_devices:
        product_name = Adb(device_id).shell(["getprop", "ro.product.name"]).strip()
        device = _get_device_if_supported_product(product_name)
        if device:
            relevant_devices.append((device, device_id))

    if len(relevant_devices) > 1:
        raise ConfigFileGenerateError(
            "More than one relevant device recognized. Out of scope of device framework.\n"
            f"'adb devices' returned:\n {adb_devices_output}"
        )
    elif not relevant_devices:
        raise ConfigFileGenerateError(
            f"Failed to recognize any device.\n'adb devices' returned:\n {adb_devices_output}"
        )

    return relevant_devices[0]


def find_usb_serial_id(serial: str) -> str:
    """Calls "udevadm info -a -n /dev/..." then looks for "{serial}" attribute"""
    udevadm_info = subprocess.check_output(["udevadm", "info", "-a", "-n", serial], timeout=5).decode("utf-8")
    serial_id = None
    m = re.search(r'ATTRS{serial}=="([A-Z0-9]+)"', udevadm_info)
    if m:
        serial_id = m.group(1)

    return serial_id


def export_to_json(config: dict, dir: str = "", name: str = "device_config.json") -> str:
    full_name = os.path.join(dir, name)
    with open(full_name, "w") as f:
        print(f"Export to {full_name}")
        f.write(json.dumps(config, indent=2))
    return full_name


def update_config_template(config: dict, device: str) -> Dict:
    updated_config = config
    if device == "IHU":
        updated_config["MP"] = dict()
        updated_config["VIP"] = dict()
    elif device == "DHU":
        updated_config["QNX"] = dict()
        updated_config["HKP"] = dict()

    return updated_config


def add_network_interface(config: dict):
    ip_addresses = {
        "IHU": [{"type": "simulated", "ip": "198.18.32.1"}, {"type": "TCAM", "ip": "169.254.4.10"}],
        # TODO: IP's for DHU are most likely wrong, fix
        "DHU": [{"type": "simulated", "ip": "198.19.60.2"}, {"type": "TCAM", "ip": "198.19.56.0"}],
    }
    addrs = psutil.net_if_addrs()
    if "ethtcam" in addrs:
        if_ip = addrs["ethtcam"][0].address
        for interface in ip_addresses[config["DEVICE"]]:
            if ipaddress.ip_address(interface["ip"]) in ipaddress.ip_network(f"{if_ip}/22", strict=False):
                config["NETWORK"] = interface

        config["NETWORK"]["interface"] = "ethtcam"
    else:
        print("Ethernet interface not detected")


def check_connected_processor(ser: str, device: str) -> str:
    """Checks the processor connected to serial port"""
    with serial.Serial(ser, 115200, timeout=10) as tty:
        # Send some dummy string
        tty.write(b"device_config_generator\r\n")
        for attempt in range(1, 11):
            processor = find_port_info(tty, device)
            _logger.info(f"Attempt {attempt} to detect device connected to {ser}. Result: {processor}")
            if processor:
                break
            time.sleep(1)
    return processor


def generate_config() -> Dict:
    _logger.debug("Generate new config file.")
    config: Dict = copy.deepcopy(DEVICE_CONFIG_TEMPLATE)
    serials = ["/dev/ttyUSB0", "/dev/ttyUSB1"]
    connected_ports = [(p.device) for p in list(serial.tools.list_ports.comports())]
    known_processors: List[str] = []

    device, serial_no = find_device_info()
    config["DEVICE"] = device
    config["ADB"]["adb_device_id"] = serial_no

    config = update_config_template(config, device)

    for ser in serials:
        if ser not in connected_ports:
            print(f"{ser} not connected")
        else:
            processor = check_connected_processor(ser, device)
            if processor in known_processors:
                raise ConfigFileGenerateError(
                    f"Failed to detect processor type. Multiple match for {processor}\n{config}"
                )
            elif processor is None:
                print(f"Failed to detect processor type for {ser}")
                raise ConfigFileGenerateError(f"Failed to detect processor type\n{config}")

            known_processors.append(processor)
            serial_id = find_usb_serial_id(ser)
            config[processor]["usb_serial_id"] = serial_id
            config[processor]["tty"] = ser

    add_network_interface(config)
    if device == "DHU":
        config["QNX"]["ip"] = "198.19.60.204"

    return config


def create_device_config(dir: str = AOSP_ROOT, name: str = "device_config.json") -> str:
    config = generate_config()
    return export_to_json(config, dir, name)


if __name__ == "__main__":
    create_device_config(dir="")
