import logging
import threading

from coppercomm.ssh_connection.ssh_connection import SSHConnection

_logger = logging.getLogger(__name__)


class SshStateMonitor:
    """
    State monitor class using ssh protocol wrapped in paramiko to periodically check connection state.
    """

    def __init__(self, qnx_broadrreach_ssh: SSHConnection):
        self._timer = None
        self.is_running = False
        self.interval = 2
        self.connection = qnx_broadrreach_ssh
        _logger.info("Staring ssh state monitor.")
        self.connection.connect()
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self._get_state()

    def get_state(self):
        if not self.connection.connected:
            self.connection.connect()
        return self.connection.connected

    def start(self):
        if not self.is_running:
            self._timer = threading.Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        _logger.info("Closing ssh state monitor.")
        self._timer.cancel()
        self.is_running = False

    def _get_state(self):
        if not self.connection.connected:
            _logger.info("SSH sonnection state: {}".format(self.connection.connected))
