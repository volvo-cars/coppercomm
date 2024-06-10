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

import glob
import logging
import os
import re
import shlex
import subprocess
import sys
import typing
from typing import Union, Collection

from coppercomm.device_common.exceptions import CommandFailedError, TimeoutExpiredError, PatternNotFoundError


_logger = logging.getLogger(__name__)
Pathish = Union[str, os.PathLike]

def resolve_path(path: str) -> str:
    path = os.path.expanduser(os.path.expandvars(path))
    candidates = glob.glob(path)
    if len(candidates) != 1:
        raise RuntimeError(
            "Path {} expanded to {} candidates when exactly 1 expected!".format(
                path, len(candidates)
            )
        )
    return candidates[0]


def execute_command(
    command: typing.Union[str, typing.List[str]],
    *,
    assert_ok: bool = True,
    timeout: typing.Optional[float] = None,
    cwd: typing.Optional[Pathish] = None,
    pattern: typing.Optional[str] = None,
    regrep: typing.Union[str, typing.Pattern[str], None] = None,
    log_output: bool = True,
    valid_exit_codes: Collection[int] =(0,)
) -> str:
    """
    Execute command with subprocess and search for given pattern if provided

    :param command: command to execute
    :param assert_ok: raise exception if command failed (nonzero exit status)
    :param timeout: timeout for command (The command won't be timeouted if None)
    :param cwd: path where the command will be executed
    :param pattern: pattern to search for in output
    :param regrep: Regex/string to use to filter the output of the command
    :param log_output: Whether to send command output to the logger
    :param valid_exit_codes: list of exit codes to consider command successful
    :return: output of command if pattern is None - matched fragment otherwise
    :raises: CommandFailedError if assert_ok is True and returncode != 0
        TimeoutExpiredError if timeout expired and command not finished
        PatternNotFoundError if pattern provided and not found in output
    """
    if log_output:
        _logger.debug("Executing command: %s", command)

    if isinstance(command, str):
        command = shlex.split(command)

    cmd_output = ""
    try:
        completed_process = subprocess.run(
            command,
            shell=False,  # shell=True + redirected output ignores timeout for py3.6 and lower
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired as e:
        if e.output and _logger.isEnabledFor(logging.DEBUG):
            cmd_output = e.output.decode(sys.getdefaultencoding(), errors="replace")
            _logger.debug("Cmd %s timeouted, captured output:\n%s", command, cmd_output)
        raise TimeoutExpiredError(
            "Timeout {}s for {} exceeded".format(timeout, command)
        )

    if completed_process.stdout:
        cmd_output = completed_process.stdout.decode(
            sys.getdefaultencoding(), errors="replace"
        )

    if regrep:
        cmd_output_lines = cmd_output.splitlines()
        cmd_output_lines = [
            line for line in cmd_output_lines if re.search(regrep, line)
        ]
        cmd_output = "\n".join(cmd_output_lines)

    if log_output:
        _logger.debug("Output of %s:\n%s", command, cmd_output)
    if assert_ok and completed_process.returncode not in valid_exit_codes:
        raise CommandFailedError(
            "Cmd {} failed with returncode {}".format(
                command, completed_process.returncode
            )
        )

    if pattern is None:
        return cmd_output

    found = re.search(pattern, cmd_output)
    if found:
        return found.group(0)

    raise PatternNotFoundError("Pattern {} not found!".format(pattern))
