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

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import IO


class FlashingInterface(ABC):
    """Interface with methods for flashing various device types"""

    @abstractmethod
    def __init__(self, *args, **kwargs) -> None:
        pass

    FLASHER_FILE_HANDLER_NAME = "coppercomm.flasher_file_handler"
    FLASHING_OUTPUT_LOGGER_NAME = "flashing_output_logger"

    @abstractmethod
    def flash_all(self) -> bool:
        """
        Abstract method to trigger flashing process of the whole device
        :return: True if flashing was successful
        """

    @abstractmethod
    def flash_android(self) -> bool:
        """
        Abstract method to trigger Android flashing process on a device
        :return: True if flashing was successful
        """

    @abstractmethod
    def flash_gsi(self, gsi_path: Path) -> None:
        """Abstract method to trigger flashing GSI firmware.

        :param gsi_path: Path to gsi_firmware.
        """

    @staticmethod
    def setup_flasher_logger(log_file) -> None:
        """Static method that configures logger to use the output of all logs flashing to the log file."""
        flasher_logger = logging.getLogger(
            FlashingInterface.FLASHING_OUTPUT_LOGGER_NAME
        )
        flasher_logger.setLevel(logging.DEBUG)
        flasher_logger.propagate = False

        output_handler = logging.StreamHandler()
        output_handler.setLevel(logging.DEBUG)
        output_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s :: %(message)s", datefmt=r"%Y-%m-%d %H:%M:%S"
            )
        )
        flasher_logger.addHandler(output_handler)

        flasher_file_handler = logging.FileHandler(log_file, mode="w+")
        flasher_file_handler.set_name(FlashingInterface.FLASHER_FILE_HANDLER_NAME)
        flasher_file_handler.setLevel(logging.DEBUG)
        flasher_formatter = logging.Formatter(
            "%(asctime)s :: %(message)s", datefmt=r"%Y-%m-%d %H:%M:%S"
        )
        flasher_file_handler.setFormatter(flasher_formatter)
        flasher_logger.addHandler(flasher_file_handler)

    @staticmethod
    def flashing_info(pipe, logger) -> None:
        # Deprecated. Use send_to_logger instead. Method will be removed when
        # all classes switch to sent_to_logger
        """Static method that adds logger to each line of subprocess"""
        for line in iter(pipe.readline, ""):  # '\n'-separated lines
            logger.info(f"SUBPROCESS INFO: {line}")

    @staticmethod
    def send_to_logger(pipe: IO, logger: logging.Logger) -> None:
        """Static method that send data from pipe to logger.

        :param pipe: IO like object
        :param logger: Logger to write data to
        """
        for line in iter(pipe.readline, ""):
            logger.info(line.rstrip("\n"))  # logger also add's new line
