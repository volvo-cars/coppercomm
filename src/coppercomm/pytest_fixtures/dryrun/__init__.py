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

import pytest
import traceback
import functools
import logging

# Test functions and fixtures with this decorator will run,
# but fails and errors will be treated as xfails instead
# Use this to test run your test functions in CI to ensure that the perfom as expected.
# Once they are stable in CI, @dryrun can be removed.
# Usage:
#     @dryrun
#     test_func(some_fixture):
#         ...
#


def dryrun(func):
    logger = logging.getLogger(func.__name__)

    @functools.wraps(func)
    @pytest.mark.xfail
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error("XFAIL - " + str(e) + "\n" + traceback.format_exc())
            pytest.xfail(str(e) + "\n" + traceback.format_exc())

    return wrapper
