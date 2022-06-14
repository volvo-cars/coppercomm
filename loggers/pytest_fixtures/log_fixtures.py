import typing

import pytest

from coppercomm.loggers.device_logger import DeviceLoggerViaAdb
from coppercomm.loggers.utils.log_dir import LogDir


@pytest.fixture(scope="function")
def log_dir(request) -> typing.Iterator[LogDir]:
    dir_name = request.function.__name__
    log_dir = LogDir(dir_name)
    yield log_dir


@pytest.fixture
def adb_logcat_logger(adb, log_dir):
    logger = DeviceLoggerViaAdb(adb.device_id, "logcat", test_log_dir=log_dir.name, shell=True)
    with logger:
        yield


@pytest.fixture
def adb_dmesg_logger(adb, log_dir):
    logger = DeviceLoggerViaAdb(adb.device_id, "dmesg -w", test_log_dir=log_dir.name, shell=True)
    with logger:
        yield
