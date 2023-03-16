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


def throw_config_error_on_value_missing_in_config(func):
    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyError as e:
            raise ConfigFileParseError("Unable to retrieve value from config.") from e

    return wrap


class SerialDeviceType(Enum):
    QNX = "QNX"
    SupportCPU = "SupportCPU"
    HKP = "HKP"  # TODO: Should be removed. Use SupportCPU instead.


class Config:
    """Class that contains device configuration information."""

    def __init__(self, data: dict) -> None:
        self.device_config_data = data

    @throw_config_error_on_value_missing_in_config
    def get_serial_device_path(self, serial_device: SerialDeviceType) -> str:
        return self.device_config_data[serial_device.value]["tty"]

    def get_serial_prompt(self, serial_device: SerialDeviceType) -> str | list[str]:
        return ""

    @throw_config_error_on_value_missing_in_config
    def get_adb_device_id(self) -> str:
        return self.device_config_data["ADB"]["adb_device_id"]

    @throw_config_error_on_value_missing_in_config
    def get_extra_devices_ids(self) -> list[str]:
        """Get the list with extra devices ids."""
        return [device["ADB_DEVICE_ID"] for device in self.device_config_data["EXTRA_DEVICES"]]

    @throw_config_error_on_value_missing_in_config
    def get_device_name(self) -> str:
        return self.device_config_data["DEVICE"]

    @throw_config_error_on_value_missing_in_config
    def get_product_name(self) -> str:
        return self.device_config_data["PRODUCT_NAME"]

    @throw_config_error_on_value_missing_in_config
    def get_extra_devices_product_names(self) -> list[str]:
        """Get the list with extra devices product names."""
        return [device["PRODUCT_NAME"] for device in self.device_config_data["EXTRA_DEVICES"]]

    @throw_config_error_on_value_missing_in_config
    def get_extra_devices_types(self) -> list[str]:
        """Get the list with extra devices types."""
        return [device["TYPE"] for device in self.device_config_data["EXTRA_DEVICES"]]

    @throw_config_error_on_value_missing_in_config
    def get_qnx_ip(self) -> str:
        return self.device_config_data["QNX"]["ip"]

    @throw_config_error_on_value_missing_in_config
    def get_qnx_port(self) -> str:
        return self.device_config_data["QNX"]["port"]

    @throw_config_error_on_value_missing_in_config
    def get_config_version(self) -> str:
        return self.device_config_data.get("version", "1")

    @throw_config_error_on_value_missing_in_config
    def get_host_adb_sshport(self) -> str:
        return self.device_config_data["HOST"]["adb_ssh_port"]

    @throw_config_error_on_value_missing_in_config
    def get_host_ip_address(self) -> str:
        return self.device_config_data["HOST"]["ip"]

    @throw_config_error_on_value_missing_in_config
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


def find_config_file(
    path: Path | None = None,
    filename: str = DEFAULT_CONFIG_FILENAME,
    env_variable: str = DEFAULT_CONFIG_ENV_VARIABLE,
) -> Path:
    """Find configuration file from different places.

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
            f"'{filename}' file not found. Either export '{env_variable}' or put file in CWD or HOME folder."
        )

    return config_file


@functools.lru_cache()
def load_config(
    path: Path | None = None,
    filename: str = DEFAULT_CONFIG_FILENAME,
    env_variable: str = DEFAULT_CONFIG_ENV_VARIABLE,
):
    """Load configuration file from different places.

    :param path: Path to config file or directory with config file with given ``filename``.
    :param filename: Name of the config file to look for in directories.
    :param env_variable: Name of the environment variable to use.
    """
    config_file: Path = find_config_file(path, filename, env_variable)

    with config_file.open("r") as fh:
        device_config_data: dict = json.load(fh)

    return Config(device_config_data)
