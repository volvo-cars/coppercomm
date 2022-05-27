import logging
import threading

from coppercomm.device_adb.adb_interface import DeviceState

_logger = logging.getLogger(__name__)


class AdbStateMonitor:
    """
    State monitor class using ADB protocol to periodically check device state.
    """

    def __init__(self, adb):
        self.adb_connection = adb
        self._timer = None
        self.adb_connection.get_state()
        self.is_running = False
        self.interval = 2
        _logger.info("Starting device state monitor.")
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        try:
            self._stdout = self.adb_connection.get_state(assert_ok=False)
            if self._stdout is not DeviceState.DEVICE:
                _logger.info(self._stdout.name)
        except ValueError:
            pass

    def get_state(self):
        return self._stdout.name

    def start(self):
        if not self.is_running:
            self._timer = threading.Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        _logger.info("Closing device state monitor.")
        self._timer.cancel()
        self.is_running = False
