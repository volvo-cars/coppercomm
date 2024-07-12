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
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

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


class Config:
    """Class that contains device configuration information."""

    def __init__(self, data: dict) -> None:
        self.device_config_data = data

    def has_entry(self, entry_path: str) -> bool:
        """Allow to check if given entry exists in config file without throwing error.

        Example:
            >>> config.has_entry("ADB.adb_device_id")
            True

        param: entry_path: Path to entry in config file. Path parts are separated by dot.
        return: True if entry exists, False otherwise.
        """
        path_parts = entry_path.split(".")
        pos_pointer = self.device_config_data
        for part_name in path_parts:
            if isinstance(pos_pointer, dict):
                if part_name not in pos_pointer:
                    return False
                pos_pointer = pos_pointer[part_name]
            else:
                try:
                    index = int(part_name)
                    pos_pointer = pos_pointer[index]
                except ValueError:
                    return False
        return True

    def get(self, entry_path: str, default=None):
        """Get entry under given path or return default value.

        Example:
            >>> config.get("ADB.adb_device_id")
            "123456"

        param: entry_path: Path to entry in config file. Path parts are separated by dot.
        return: value if entry exists, default value otherwise.
        """
        try:
            return self[entry_path]
        except ConfigFileParseError:
            return default

    @throw_config_error_on_value_missing_in_config
    def __getitem__(self, entry_path: str):
        """Get item at given entry_path or raise ConfigFileParseError if not found.

        Example:
            >>> config["ADB.adb_device_id"]
            "123456"
        """
        path_parts = entry_path.split(".")
        pos_pointer = self.device_config_data
        for part_name in path_parts:
            if isinstance(pos_pointer, dict):
                if part_name not in pos_pointer:
                    raise KeyError(f"{part_name} not in {pos_pointer}")
                pos_pointer = pos_pointer[part_name]
            else:
                try:
                    index = int(part_name)
                    pos_pointer = pos_pointer[index]
                except ValueError:
                    raise KeyError(f"{part_name} is not a valid index")
        return pos_pointer

    @throw_config_error_on_value_missing_in_config
    def get_serial_device_path(self, serial_device: str) -> str:
        return self.device_config_data[serial_device]["tty"]

    def get_serial_prompt(self, serial_device: str) -> Union[str, List[str]]:
        return ""

    @throw_config_error_on_value_missing_in_config
    def get_adb_device_id(self) -> str:
        return self.device_config_data["ADB"]["adb_device_id"]

    @throw_config_error_on_value_missing_in_config
    def get_fastboot_device_id(self) -> str:
        return self.device_config_data["FASTBOOT"]["fastboot_device_id"]

    @throw_config_error_on_value_missing_in_config
    def get_device_name(self) -> str:
        return self.device_config_data["DEVICE"]

    @throw_config_error_on_value_missing_in_config
    def get_product_name(self) -> str:
        return self.device_config_data["PRODUCT_NAME"]

    def get_extra_devices(
        self, device_type: Optional[str] = None, **kwargs: Any
    ) -> Generator[Dict[str, Any], None, None]:
        """Get the list with extra devices.

        Each extra device is a dictionary with the mandatory TYPE key.

        :param device_type: Type of the extra device to get e.g. phone, dhu etc...
        :param kwargs: Additional key-value pairs to filter devices.
        """

        def _device_matches(device_param: Dict[str, Any]) -> bool:
            if device_type and device_param["device_type"] != device_type:
                return False
            return all(device_param.get(field) == value for field, value in kwargs.items())

        @throw_config_error_on_value_missing_in_config
        def _get_extra_devices() -> List[Dict[str, Any]]:
            return self.device_config_data["EXTRA_DEVICES"]

        extra_devices = _get_extra_devices()

        for device in extra_devices:
            if _device_matches(device):
                yield device

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
    def get_host_ip_address(self) -> str:
        return self.device_config_data["NETWORK"]["HOST"][0]["ip"]

    @throw_config_error_on_value_missing_in_config
    def get_oem(self) -> str:
        return self.device_config_data["OEM"]

    @throw_config_error_on_value_missing_in_config
    def get_network_configuraiton_data(self) -> dict:
        return self.device_config_data["NETWORK"]

    @throw_config_error_on_value_missing_in_config
    def get_fuse_key_type(self) -> str:
        return self.device_config_data["FUSED_WITH_KEY"]

    def get_name_of_available_serials_in_config(self):
        serials = []
        for attr in self.device_config_data:
            if "tty" in self.device_config_data[attr]:  # tty mean its serial_device
                serials.append(attr)
        return serials


def _config_file_from_variable(env_variable: str, filename: str) -> Optional[Path]:
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


def _config_file_from_path(path: Optional[Path], filename: str) -> Optional[Path]:
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


def _config_file_from_cwd(filename: str) -> Optional[Path]:
    file_path = Path.cwd() / filename
    _logger.debug("Trying config file from CWD: %s", file_path)
    if file_path.is_file():
        return file_path
    return None


def _config_file_from_home_dir(filename: str) -> Optional[Path]:
    device_config_path = Path.home() / filename
    _logger.debug("Trying config file from HOME: %s", device_config_path)
    if device_config_path.is_file():
        return device_config_path
    return None


def find_config_file(
    path: Optional[Path] = None,
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

    config_file: Optional[Path] = (
        _config_file_from_path(path, filename)
        or _config_file_from_variable(env_variable, filename)
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
    path: Optional[Path] = None,
    filename: str = DEFAULT_CONFIG_FILENAME,
    env_variable: str = DEFAULT_CONFIG_ENV_VARIABLE,
) -> Tuple[Config, Path]:
    """Load configuration file from different places.

    :param path: Path to config file or directory with config file with given ``filename``.
    :param filename: Name of the config file to look for in directories.
    :param env_variable: Name of the environment variable to use.
    :return: Config instance, path to source file
    """
    config_file: Path = find_config_file(path, filename, env_variable)

    with config_file.open("r") as fh:
        device_config_data: dict = json.load(fh)

    return Config(device_config_data), config_file
