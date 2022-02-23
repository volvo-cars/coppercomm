# Copyright 2018-2021 Volvo Car Corporation
# This file is covered by LICENSE file in the root of this project

from one_update.communication.adb_interface import Adb as OneUpdateAdb

import datetime
import time
import logging

_logger = logging.getLogger("one_update.adb_interface")
_logger.setLevel(logging.DEBUG)

_kernel_boot_id_path = "/proc/sys/kernel/random/boot_id"


class RemountError(Exception):
    """Unable to mount the filesystem"""


class Adb(OneUpdateAdb):
    def get_boot_id(self):
        boot_id = self.shell(f"cat {_kernel_boot_id_path}")
        _logger.debug(f"Current boot_id: {boot_id}")
        return boot_id

    def trigger_reboot(self):
        _logger.info("Triggering reboot over adb")
        self.shell("reboot")

    def reboot_and_wait(self, timeout=120):
        initial_boot_id = self.get_boot_id()

        datetime_timeout = datetime.datetime.now() + datetime.timedelta(seconds=timeout)

        self.gain_root_permissions(timeout=10)
        self.trigger_reboot()

        while datetime.datetime.now() < datetime_timeout:
            try:
                time.sleep(1)
                if initial_boot_id != self.get_boot_id():
                    _logger.info("Kernel boot_id changed. Reboot completed.")
                    return
            except AssertionError as e:
                _logger.debug(f"Failed to read boot_id: {e}")

        raise AssertionError(f"Failed to restart over adb")

    @property
    def device_id(self):
        return self._adb_device_id

    def mount_filessytem_as_root(self):
        self.gain_root_permissions()
        self.shell(command="disable-verity", assert_ok=False)
        out = self.shell(command="remount", assert_ok=False).strip()

        if out != "remount succeeded":
            self.reboot_and_wait()
            self.gain_root_permissions()
            out = self.shell(command="remount", assert_ok=False).strip()

            if out != "remount succeeded":
                raise RemountError("Failed to mount filesystem as root: {}".format(out))
