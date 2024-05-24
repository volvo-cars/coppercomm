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
