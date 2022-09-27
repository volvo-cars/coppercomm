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

import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Union

CONFIGFILE_ENV_NAME = "DEVICE_CONFIG_FILE"
DEFAULT_CONFIG_FILENAME = "device_config.json"


class ConfigFileParseError(Exception):
    pass


class SerialDeviceType(Enum):
    QNX = "QNX"
    SupportCPU = "SupportCPU"
    HKP = "HKP"


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
        self.directory = os.path.expanduser(os.path.expandvars(self.directory))

        # override self.directory/self.filename if env variable set
        filepath_from_env = os.getenv(CONFIGFILE_ENV_NAME)
        if filepath_from_env:
            filepath_from_env = os.path.expanduser(
                os.path.expandvars(filepath_from_env)
            )
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

    def get_device_config_path(self) -> str:
        file_path = os.path.join(self.directory, self.filename)
        return file_path

    def get_serial_device_path(self, serial_device: SerialDeviceType) -> str:
        return self.device_config_data[serial_device.value]["tty"]

    def get_serial_prompt(
        self, serial_device: SerialDeviceType
    ) -> Union[str, List[str]]:
        return ""

    def get_adb_device_id(self) -> str:
        return self.device_config_data["ADB"]["adb_device_id"]

    def get_adb_phone_device_id(self, element_no: int = 0) -> str:
        try:
            return self.device_config_data["EXTRA_DEVICES"][element_no]["ADB_DEVICE_ID"]
        except IndexError:
            raise ConfigFileParseError(f"Can't find device with given index: [{element_no}].")

    def get_device_name(self) -> str:
        return self.device_config_data["DEVICE"]

    def get_phone_product_name(self, element_no: int = 0) -> str:
        try:
            return self.device_config_data["EXTRA_DEVICES"][element_no]["PRODUCT_NAME"]
        except IndexError:
            raise ConfigFileParseError(f"Can't find device with given index: [{element_no}].")

    def get_type_extra_device(self, element_no: int = 0) -> str:
        try:
            return self.device_config_data["EXTRA_DEVICES"][element_no]["TYPE"]
        except IndexError:
            raise ConfigFileParseError(f"Can't find device with given index: [{element_no}].")

    def get_qnx_ip(self) -> str:
        return self.device_config_data["QNX"]["ip"]

    def get_config_version(self) -> str:
        return self.device_config_data.get("version", "1")

    def get_host_adb_sshport(self) -> str:
        return self.device_config_data["HOST"]["adb_ssh_port"]

    def get_host_broadrreach_ethernet_interface_name(self) -> str:
        return self.device_config_data["NETWORK"]["interface"]
