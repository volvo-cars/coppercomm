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

import typing
from contextlib import contextmanager

from coppercomm.config_file_parser import SerialDeviceType

if typing.TYPE_CHECKING:
    from pathlib import Path

    from coppercomm.device_factory import DeviceFactory
    from coppercomm.device_serial.device_serial import SerialConnection


def get_qnx_serial_logger(device: DeviceFactory, log_path: Path) -> SerialConnection:
    """Get SerialConnection object for QNX with enabled logging

    :param device: device factory
    :param log_path: path to log file
    :return: serial connection object for QNX with logging
    """
    qnx_serial = device.create_serial(SerialDeviceType.QNX)
    qnx_serial.set_test_logging(log_path)
    return qnx_serial


@contextmanager
def conditional_qnx_serial_logging(device: DeviceFactory, log_path: typing.Optional[Path]):
    """Enter QNX serial logging context only if log path is provided

    :param device: device factory
    :param log_path: path to log file
    """
    if log_path:
        with get_qnx_serial_logger(device, log_path):
            yield
    else:
        yield
