# Copyright 2021-2022 Volvo Car Corporation
# This file is covered by LICENSE file in the root of this project

import json
import os

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Union

from test_manager.devices.device_config_gen import create_device_config


CONFIGFILE_ENV_NAME = "DEVICE_CONFIG_FILE"
DEFAULT_CONFIG_FILENAME = "device_config.json"

COMMON_MANDATORY_KEYS_IN_JSON_FILE = {"ADB"}
DHU_MANDATORY_KEYS_IN_JSON_FILE = {"HKP", "QNX"}
IHU_MANDATORY_KEYS_IN_JSON_FILE = {"VIP", "MP"}

MANDATORY_KEYS = {
    "IHU": IHU_MANDATORY_KEYS_IN_JSON_FILE | COMMON_MANDATORY_KEYS_IN_JSON_FILE,
    "DHU": DHU_MANDATORY_KEYS_IN_JSON_FILE | COMMON_MANDATORY_KEYS_IN_JSON_FILE,
    "IHU_EMU": COMMON_MANDATORY_KEYS_IN_JSON_FILE,
}


class ConfigFileParseError(Exception):
    pass


# TODO QNX serial -> Dhum
# TODO HKP serial -> Dhuh
class SerialDeviceType(Enum):
    QNX = "QNX"
    HKP = "HKP"
    VIP = "VIP"
    MP = "MP"


@dataclass
class Config:
    """
    Class that contains device configuration information. Requires either `directory`
    to be provided or DEVICE_CONFIG_FILE env variable to be set. Environment variable
    overrides provided argument(s) and should point directly to the config file or
    the directory which contains the config named as provided by `filename`.

    Parameters:
        directory: Path of the directory containing the config file
        filename: Name of the config file (located in the 'directory')
        update: NYI - Re-generate config file if a newer version exists.
        force_generate: Generate new config file even if one already exists.
    """

    directory: str = ""
    filename: str = DEFAULT_CONFIG_FILENAME
    update: bool = False
    force_generate: bool = False

    def __post_init__(self) -> None:
        # TODO add version information
        self.directory = os.path.expanduser(os.path.expandvars(self.directory))

        # override self.directory/self.filename if env variable set
        filepath_from_env = os.getenv(CONFIGFILE_ENV_NAME)
        if filepath_from_env:
            filepath_from_env = os.path.expanduser(os.path.expandvars(filepath_from_env))
            if os.path.isdir(filepath_from_env):
                self.directory = filepath_from_env
                self.filename = DEFAULT_CONFIG_FILENAME
            else:
                # interpret environment variable path as file
                self.directory = os.path.dirname(filepath_from_env)
                self.filename = os.path.basename(filepath_from_env)

        if not self.directory:
            raise ConfigFileParseError(
                f"Device config file not specified. Either export {CONFIGFILE_ENV_NAME} or specify the directory."
            )

        device_config_file_path = self.get_device_config_path()
        with open(device_config_file_path, "r") as device_config:
            self.device_config_data: Dict = json.load(device_config)

        if not MANDATORY_KEYS[self.device_config_data["DEVICE"]].issubset(self.device_config_data.keys()):
            raise ConfigFileParseError(
                f"Mandatory keys are not present in config file. "
                f"Mandatory keys: {MANDATORY_KEYS[self.device_config_data['DEVICE']]} "
                f"for device: {self.device_config_data['DEVICE']}"
            )

    def get_device_config_path(self) -> str:
        file_path = os.path.join(self.directory, self.filename)
        if not self.force_generate and os.path.exists(file_path):
            return file_path

        return create_device_config(dir=self.directory, name=self.filename)

    def get_serial_device_path(self, serial_device: SerialDeviceType) -> str:
        return self.device_config_data[serial_device.value]["tty"]

    def get_serial_prompt(self, serial_device: SerialDeviceType) -> Union[str, List[str]]:
        return ""  # ToDo: return value from config

    def get_adb_device_id(self) -> str:
        return self.device_config_data["ADB"]["adb_device_id"]

    def get_device_name(self) -> str:
        return self.device_config_data["DEVICE"]

    def get_qnx_ip(self) -> str:
        return self.device_config_data["QNX"]["ip"]

    def get_config_version(self):
        # TODO: Add version to device config file
        return self.device_config_data.get("version", "1")

    def get_host_adb_sshport(self) -> str:
        return self.device_config_data["HOST"]["adb_ssh_port"]

    def get_host_broadrreach_ethernet_interface_name(self) -> str:
        return self.device_config_data["NETWORK"]["interface"]
