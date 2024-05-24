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
import pytest

from coppercomm.loggers.device_logger import DeviceLoggerViaAdb
from coppercomm.loggers.utils.log_dir import LogDir


@pytest.fixture(scope="function")
def log_dir(request) -> LogDir:
    dir_name = request.function.__name__
    log_dir = LogDir(dir_name)
    return log_dir


@pytest.fixture(scope="session")
def log_dir_session() -> LogDir:
    dir_name = "session"
    log_dir = LogDir(dir_name)
    return log_dir


@pytest.fixture(scope="function")
def adb_logcat_logger(adb, log_dir):
    logger = DeviceLoggerViaAdb(adb.device_id, "logcat", test_log_dir=log_dir.name, shell=True)
    with logger:
        yield


@pytest.fixture(scope="session")
def adb_logcat_logger_session(adb, log_dir_session):
    logger = DeviceLoggerViaAdb(adb.device_id, "logcat", test_log_dir=log_dir_session.name, shell=True)
    with logger:
        yield


@pytest.fixture(scope="function")
def adb_dmesg_logger(adb, log_dir):
    logger = DeviceLoggerViaAdb(adb.device_id, "dmesg -w", test_log_dir=log_dir.name, shell=True)
    with logger:
        yield
