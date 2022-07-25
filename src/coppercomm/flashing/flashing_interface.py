from abc import ABC, abstractmethod
import logging


class FlashingInterface(ABC):
    """Interface with methods for flashing various device types"""

    @abstractmethod
    def __init__(self, *args, **kwargs) -> None:
        pass

    FLASHER_FILE_HANDLER_NAME = "flasher_file_handler"

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

    @staticmethod
    def setup_flasher_logger(log_file) -> None:
        """Static method that configures logger to use the output of all logs flashing to the log file."""
        flasher_logger = logging.getLogger()
        flasher_logger.setLevel(logging.DEBUG)
        flasher_logger.propagate = False

        flasher_logger.info("Using logfile: %s", log_file)
        flasher_file_handler = logging.FileHandler(log_file, mode="w+")
        flasher_file_handler.set_name(FlashingInterface.FLASHER_FILE_HANDLER_NAME)
        flasher_file_handler.setLevel(logging.DEBUG)
        flasher_formatter = logging.Formatter(
            "%(asctime)s :: %(levelname)s :: %(module)s.%(funcName)s - line %(lineno)s :: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        flasher_file_handler.setFormatter(flasher_formatter)
        flasher_logger.addHandler(flasher_file_handler)

    @staticmethod
    def flashing_info(pipe, logger) -> None:
        """Static method that adds logger to each line of subprocess"""
        for line in iter(pipe.readline, ""):  # '\n'-separated lines
            logger.info(f"SUBPROCESS INFO: {line}")
