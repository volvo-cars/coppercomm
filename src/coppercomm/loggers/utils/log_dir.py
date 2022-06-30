import logging
import os
from contextlib import ExitStack
from datetime import datetime

_logger = logging.getLogger(__name__)


class LogDir:
    def __init__(self, suffix: str = "") -> None:
        """
        Creates the log directory at standard location. Provides created
        directory name through member field.

        :param suffix: string that will be added to the default directory name
            following underscore separator
        """
        self.name = self._make_dir_name(suffix)
        self.full_path = os.path.abspath(self.name)

        _logger.info(f"Creating log directory {self.name}")
        os.makedirs(self.name, exist_ok=True)

    @staticmethod
    def _make_dir_name(suffix: str = ""):
        dir_name = f"test_run_logs/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

        if suffix:
            dir_name = f"{dir_name}_{suffix}"
        return dir_name
