# Copyright 2023 Volvo Cars
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

import logging
import typing
from contextlib import contextmanager

if typing.TYPE_CHECKING:  # pragma: nocover
    from pathlib import Path

    from coppercomm.device_common.interfaces import ConsoleInterface


@contextmanager
def conditional_qnx_serial_logging(qnx_serial: typing.Optional[ConsoleInterface], log_path: typing.Optional[Path]):
    """Enter QNX serial logging context only if log path is provided

    :param qnx_serial: Instance of QNX serial console.
    :param log_path: path to log file
    """
    if qnx_serial and log_path:
        qnx_serial.console_object.set_test_logging(log_path)
        yield
    else:
        yield


@contextmanager
def duplicate_console_logs_to_file(serial: typing.Optional[ConsoleInterface], log_path: typing.Optional[Path]):
    """Add a logging handler to an existing console object logger

    :param serial: Instance of serial console.
    :param log_path: path to log file
    """
    try:
        if serial and log_path:
            log_path_handler = logging.FileHandler(log_path)
            log_path_handler.setLevel(logging.DEBUG)
            serial.console_object.logger.addHandler(log_path_handler)
            yield
        else:
            log_path_handler = None
            yield
    finally:
        if serial and log_path_handler:
            serial.console_object.logger.removeHandler(log_path_handler)
