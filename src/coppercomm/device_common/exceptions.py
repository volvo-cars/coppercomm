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

class CommandExecutionError(AssertionError):
    pass


class TimeoutExpiredError(CommandExecutionError):
    pass


class CommandFailedError(CommandExecutionError):
    pass


class PatternNotFoundError(CommandExecutionError):
    pass


class CopperCommmError(AssertionError):
    pass


class RemountError(Exception):
    """Unable to mount the filesystem"""


class CopperCommConnectionError(CopperCommmError):
    def __init__(self, message="Unknown error"):
        message += "\nCheck if serial ports (UART) and ADB are correctly connected"
        super().__init__(message)
