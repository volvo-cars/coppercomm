import pytest


pytest_plugins = "pytest_fixtures.device_fixtures"


def test_example(adb, support_cpu_serial, adb_logcat_logger):
    adb.gain_root_permissions(timeout=60)
    assert "asd" == adb.shell("ls")
    support_cpu_serial.send_line("help")


def test_example_whoami(adb, qnx_serial, qnx_broadrreach_ssh, adb_dmesg_logger):
    adb.shell("whoami")
    qnx_serial.send_line("whoami")
    asd, _, _ = qnx_broadrreach_ssh.execute_cmd("ls")
    assert "asd" == asd.readlines()
