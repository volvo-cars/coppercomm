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
import logging
import logging.config
import os
import typing

from coppercomm.loggers.adb_logger.adb_logger import AdbLogger

_logger = logging.getLogger("device.loggers")


class DeviceLogger(typing.Protocol):
    def __enter__(self) -> "DeviceLogger":
        pass

    def __exit__(self, *args, **kwargs) -> None:
        pass


class DeviceLoggerViaAdb(DeviceLogger):
    adb_logger: AdbLogger

    def __init__(self, adb_id: str, command: str, test_log_dir: str = "", shell: bool = True):
        self.adb_id = adb_id
        self.command = command
        self.shell = shell
        self.test_log_dir: typing.Final[str] = test_log_dir

    def __enter__(self) -> "DeviceLogger":
        test_log_name = os.path.join(self.test_log_dir, f"{self.command.split(' ')[0]}.log")
        self.adb_logger = self._create_adb_logger(test_log_name=test_log_name)
        _logger.debug(f"Starting ADB logger for device {self.adb_id} with command {self.command}")
        if not self.adb_logger.start(timeout=60.0):
            _logger.warning(f"Starting ADB logger for device {self.adb_id} with command {self.command} failed")
        return self

    def __exit__(self, *args, **kwargs) -> None:
        self.adb_logger.stop()

    def _create_adb_logger(self, test_log_name: str) -> AdbLogger:
        adb_prefix = "adb "
        if self.adb_id:
            adb_prefix += f"-s {self.adb_id} "

        return AdbLogger(
            command=self.command,
            log_filename=test_log_name,
            shell=self.shell,
            adb_prefix=adb_prefix,
        )


class GeneralDeviceLogger(DeviceLogger):
    """Captures log messages from device and oneupdate modules"""

    def __init__(self, log_dir: str):
        self._log_dir = log_dir

    def __enter__(self) -> "DeviceLogger":
        with open(os.path.join(os.path.dirname(__file__), "device_logging.json"), "rt") as f:
            log_config = json.load(f)

        log_name = "device.log"
        log_config["handlers"]["file_handler"]["filename"] = os.path.join(self._log_dir, log_name)
        logging.config.dictConfig(log_config)
        return self

    def __exit__(self, *args, **kwargs) -> None:
        pass
