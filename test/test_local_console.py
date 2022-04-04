import tempfile
from unittest import mock
import device_common.exceptions as exceptions
import device_common.local_console as local_console
import subprocess


def test_local_console_resolve_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = local_console.resolve_path(tmpdir)
    assert tmpdir == result


def test_local_console_resolve_path_exception():
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            local_console.resolve_path(f"{tmpdir}/empty")
            assert False, "resolve_path should have thrown an exception"
        except RuntimeError:
            assert True


@mock.patch("subprocess.run")
def test_local_console_execute_command(mock_run):
    mock_run.configure_mock(
        **{
            "stdout.decode.return_value": "a.txt b.cpp",
        }
    )
    type(mock_run).returncode = mock.PropertyMock(return_value=0)
    setattr(subprocess, "run", lambda *args, **kargs: mock_run)
    result = local_console.execute_command(command="ls -la")
    assert "a.txt b.cpp" == result


@mock.patch("subprocess.run")
def test_local_console_execute_command_timeout(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="", timeout=1)
    try:
        local_console.execute_command(command="ls -la")
        assert False, "execute_command should have thrown an exception"
    except exceptions.TimeoutExpiredError:
        assert True


@mock.patch("subprocess.run")
def test_local_console_execute_command_failed(mock_run):
    mock_run.configure_mock(
        **{
            "stdout.decode.return_value": "a.txt b.cpp",
        }
    )
    type(mock_run).returncode = mock.PropertyMock(return_value=1)
    setattr(subprocess, "run", lambda *args, **kargs: mock_run)
    try:
        local_console.execute_command(command="ls -la")
        assert False, "execute_command should have thrown an exception"
    except exceptions.CommandFailedError:
        assert True


@mock.patch("subprocess.run")
def test_local_console_execute_command_pattern(mock_run):
    mock_run.configure_mock(
        **{
            "stdout.decode.return_value": "a.txt b.cpp",
        }
    )
    type(mock_run).returncode = mock.PropertyMock(return_value=0)
    setattr(subprocess, "run", lambda *args, **kargs: mock_run)
    result = local_console.execute_command(command="ls -la", pattern=".cpp")
    assert ".cpp" == result


@mock.patch("subprocess.run")
def test_local_console_execute_command_pattern_not_found(mock_run):
    mock_run.configure_mock(
        **{
            "stdout.decode.return_value": "a.txt b.cpp",
        }
    )
    type(mock_run).returncode = mock.PropertyMock(return_value=0)
    setattr(subprocess, "run", lambda *args, **kargs: mock_run)
    try:
        local_console.execute_command(command="ls -la", pattern=".hpp")
        assert False, "execute_command should have thrown an exception"
    except exceptions.PatternNotFoundError:
        assert True


@mock.patch("subprocess.run")
def test_local_console_execute_command_regrep(mock_run):
    mock_run.configure_mock(**{"stdout.decode.return_value": "a.txt\nb.cpp"})
    type(mock_run).returncode = mock.PropertyMock(return_value=0)
    setattr(subprocess, "run", lambda *args, **kargs: mock_run)
    result = local_console.execute_command(command="ls -la", regrep="\\.cp{2}")

    assert "b.cpp" == result


@mock.patch("subprocess.run")
def test_local_console_execute_command_regrep_not_found(mock_run):
    mock_run.configure_mock(**{"stdout.decode.return_value": "a.txt\nb.cpp"})
    type(mock_run).returncode = mock.PropertyMock(return_value=0)
    setattr(subprocess, "run", lambda *args, **kargs: mock_run)
    result = local_console.execute_command(command="ls -la", regrep="\\.cp{3}")

    assert "" == result
