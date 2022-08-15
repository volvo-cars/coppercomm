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

import os
import typing

from coppercomm.loggers.adb_logger.adb_logger_thread import AdbLoggerThread, LogFileProvider


class LoggerStartupError(RuntimeError):
    def __init__(self, command: str):
        super().__init__("Logger'" + command + "' startup failed!")


class AdbLogger:
    def __init__(
        self,
        command: str,
        log_filename: str,
        shell: bool = False,
        adb_prefix: str = "adb",
        append_after_interrupt: bool = True,
        file_encoding: str = "utf-8",
        file_open_mode: str = "a",
        timestamped_file: bool = True,
    ):
        self.__command = "shell " + command if shell else command
        self.__log_filename = log_filename
        self.__adb_prefix = adb_prefix
        self.__append_after_interrupt = append_after_interrupt
        self.__file_encoding = file_encoding
        self.__file_open_mode = file_open_mode
        self.__timestamped_file = timestamped_file
        self.__adb_logger_thread: typing.Optional[AdbLoggerThread] = None

    @property
    def command(self) -> str:
        return self.__command

    @property
    def log_filename(self) -> str:
        return self.__log_filename

    @property
    def adb_prefix(self) -> str:
        return self.__adb_prefix

    @property
    def append_after_interrupt(self) -> bool:
        return self.__append_after_interrupt

    @property
    def file_encoding(self) -> str:
        return self.__file_encoding

    @property
    def file_open_mode(self) -> str:
        return self.__file_open_mode

    @property
    def timestamped_file(self) -> bool:
        return self.__timestamped_file

    def start(self, timeout: typing.Optional[float] = None) -> bool:
        if self.__is_thread_running():
            return False

        file_provider = LogFileProvider(
            self.__log_filename,
            self.__append_after_interrupt,
            self.__timestamped_file,
            self.__file_open_mode,
            self.__file_encoding,
        )
        self.__adb_logger_thread = AdbLoggerThread(
            file_provider, self.__command, self.__adb_prefix, self.__append_after_interrupt
        )
        self.__adb_logger_thread.start()
        return self.__adb_logger_thread.wait_for_logging_start(timeout)

    def wait_for_thread_logging_start(self, timeout: typing.Optional[float] = None) -> bool:
        return self.__adb_logger_thread is not None and self.__adb_logger_thread.wait_for_logging_start(timeout)

    def stop(self) -> None:
        if self.__is_thread_running() and self.__adb_logger_thread is not None:  # __adb_logger_thread check for mypy
            self.__adb_logger_thread.stop_logging()
            self.__adb_logger_thread.join()

    def clean(self) -> None:
        if self.__is_thread_stopped() and self.__adb_logger_thread is not None:  # __adb_logger_thread check for mypy
            for log_file in self.__adb_logger_thread.get_collected_file_paths():
                try:
                    os.remove(log_file)
                except OSError:
                    pass

    def __is_thread_running(self) -> bool:
        return self.__adb_logger_thread is not None and self.__adb_logger_thread.is_alive()

    def __is_thread_stopped(self) -> bool:
        return self.__adb_logger_thread is not None and not self.__adb_logger_thread.is_alive()
