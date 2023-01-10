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
from __future__ import annotations

import functools
import json
import logging
import os
from enum import Enum
from pathlib import Path

DEFAULT_CONFIG_ENV_VARIABLE = "DEVICE_CONFIG_FILE"
DEFAULT_CONFIG_FILENAME = "device_config.json"

_logger = logging.getLogger(__name__)


class ConfigFileParseError(Exception):
    pass


class SerialDeviceType(Enum):
    QNX = "QNX"
    SupportCPU = "SupportCPU"
    HKP = "HKP"  # TODO: Should be removed. Use SupportCPU instead.


class Config:
    """Class that contains device configuration information."""

    def __init__(self, data: dict) -> None:
        self.device_config_data = data

    def get_serial_device_path(self, serial_device: SerialDeviceType) -> str:
        return self.device_config_data[serial_device.value]["tty"]

    def get_serial_prompt(self, serial_device: SerialDeviceType) -> str | list[str]:
        return ""

    def get_adb_device_id(self) -> str:
        return self.device_config_data["ADB"]["adb_device_id"]

    def get_extra_devices_ids(self) -> list[str]:
        """Get the list with extra devices ids."""

        try:
            return [device["ADB_DEVICE_ID"] for device in self.device_config_data["EXTRA_DEVICES"]]
        except KeyError as e:
            raise ConfigFileParseError("Reading config was failed or no extra devices connected") from e

    def get_device_name(self) -> str:
        return self.device_config_data["DEVICE"]

    def get_extra_devices_product_names(self) -> list[str]:
        """Get the list with extra devices product names."""

        try:
            return [device["PRODUCT_NAME"] for device in self.device_config_data["EXTRA_DEVICES"]]
        except KeyError as e:
            raise ConfigFileParseError("Reading config was failed or no extra devices connected") from e

    def get_extra_devices_types(self) -> list[str]:
        """Get the list with extra devices types."""

        try:
            return [device["TYPE"] for device in self.device_config_data["EXTRA_DEVICES"]]
        except KeyError as e:
            raise ConfigFileParseError("Reading config was failed or no extra devices connected") from e

    def get_qnx_ip(self) -> str:
        return self.device_config_data["QNX"]["ip"]

    def get_config_version(self) -> str:
        return self.device_config_data.get("version", "1")

    def get_host_adb_sshport(self) -> str:
        return self.device_config_data["HOST"]["adb_ssh_port"]

    def get_host_broadrreach_ethernet_interface_name(self) -> str:
        return self.device_config_data["NETWORK"]["interface"]


def _config_file_from_variable(env_variable: str, filename: str) -> Path | None:
    if device_config_file_variable := os.getenv(env_variable):
        _logger.debug("Trying config file from env var %s", env_variable)
        device_config_path = Path(device_config_file_variable).expanduser()
        if device_config_path.is_file():
            return device_config_path
        elif device_config_path.is_dir():
            file = device_config_path / filename
            if file.is_file():
                return file
    return None


def _config_file_from_path(path: Path | None, filename: str) -> Path | None:
    if path is None:
        return None
    path = path.expanduser()
    _logger.debug("Trying config file from path: %s", path)
    if path.is_file():
        return path
    elif path.is_dir():
        file = path / filename
        if file.is_file():
            return file
    return None


def _config_file_from_cwd(filename: str) -> Path | None:
    file_path = Path.cwd() / filename
    _logger.debug("Trying config file from CWD: %s", file_path)
    if file_path.is_file():
        return file_path
    return None


def _config_file_from_home_dir(filename: str) -> Path | None:
    device_config_path = Path.home() / filename
    _logger.debug("Trying config file from HOME: %s", device_config_path)
    if device_config_path.is_file():
        return device_config_path
    return None


@functools.lru_cache()
def load_config(
    path: Path | None = None,
    filename: str = DEFAULT_CONFIG_FILENAME,
    env_variable: str = DEFAULT_CONFIG_ENV_VARIABLE,
):
    """Load configuration file from different places.

    Configuraiton file is search by predefined order:

      - Path set in Environment variable ``CONFIGFILE_ENV_NAME``
      - Path given to function by user
      - ``filename`` in Curent Working Directory
      - ``filename`` in Users Home directory

    :param path: Path to config file or directory with config file with given ``filename``.
    :param filename: Name of the config file to look for in directories.
    :param env_variable: Name of the environment variable to use.
    :raise ConfigFileParseError: When config file can't be found.
    """
    config_file: Path | None = (
        _config_file_from_variable(env_variable, filename)
        or _config_file_from_path(path, filename)
        or _config_file_from_cwd(filename)
        or _config_file_from_home_dir(filename)
    )

    if not config_file:
        raise ConfigFileParseError(
            f"'{filename}' file not found. " f"Either export '{env_variable}' or put file in CWD or HOME folder."
        )

    with config_file.open("r") as fh:
        device_config_data: dict = json.load(fh)

    return Config(device_config_data)
