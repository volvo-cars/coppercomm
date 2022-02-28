import glob
import logging
import os
import re
import shlex
import subprocess
import sys
import typing

from .exceptions import CommandFailedError, TimeoutExpiredError, PatternNotFoundError


_logger = logging.getLogger("local_console")


def resolve_path(path: str) -> str:
    path = os.path.expanduser(os.path.expandvars(path))
    candidates = glob.glob(path)
    if len(candidates) != 1:
        raise RuntimeError("Path {} expanded to {} candidates when exactly 1 expected!".format(path, len(candidates)))
    return candidates[0]


def execute_command(
    command: typing.Union[str, typing.List[str]],
    *,
    assert_ok: bool = True,
    timeout: typing.Optional[float] = None,
    cwd: typing.Optional[str] = None,
    pattern: typing.Optional[str] = None,
    regrep: typing.Union[str, typing.Pattern[str], None] = None,
) -> str:
    """
    Execute command with subprocess and search for given pattern if provided

    :param command: command to execute
    :param assert_ok: raise exception if command failed (nonzero exit status)
    :param timeout: timeout for command (The command won't be timeouted if None)
    :param cwd: path where the command will be executed
    :param pattern: pattern to search for in output
    :param regrep: Regex/string to use to filter the output of the command
    :return: output of command if pattern is None - matched fragment otherwise
    :raises: CommandFailedError if assert_ok is True and returncode != 0
        TimeoutExpiredError if timeout expired and command not finished
        PatternNotFoundError if pattern provided and not found in output
    """
    _logger.debug("Executing command: {}".format(command))

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
        if e.output:
            cmd_output = e.stdout.decode(sys.getdefaultencoding(), errors="replace")

        _logger.debug("Cmd {} timeouted, captured output:\n{}".format(command, cmd_output))
        raise TimeoutExpiredError("Timeout {}s for {} exceeded".format(timeout, command))

    if completed_process.stdout:
        cmd_output = completed_process.stdout.decode(sys.getdefaultencoding(), errors="replace")

    if regrep:
        cmd_output_lines = cmd_output.splitlines()
        cmd_output_lines = [line for line in cmd_output_lines if re.search(regrep, line)]
        cmd_output = "\n".join(cmd_output_lines)

    _logger.debug("Output of {}:\n{}".format(command, cmd_output))
    if assert_ok and completed_process.returncode != 0:
        raise CommandFailedError("Cmd {} failed with returncode {}".format(command, completed_process.returncode))

    if pattern is None:
        return cmd_output

    found = re.search(pattern, cmd_output)
    if found:
        return found.group(0)

    raise PatternNotFoundError("Pattern {} not found!".format(pattern))
