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

if typing.TYPE_CHECKING:
    from pathlib import Path

    from coppercomm.device_serial.device_serial import SerialConnection


@contextmanager
def conditional_qnx_serial_logging(qnx_serial: typing.Optional[SerialConnection], log_path: typing.Optional[Path]):
    """Enter QNX serial logging context only if log path is provided

    :param device: device factory
    :param log_path: path to log file
    """
    if qnx_serial and log_path:
        qnx_serial.set_test_logging(log_path)
        yield
    else:
        yield
