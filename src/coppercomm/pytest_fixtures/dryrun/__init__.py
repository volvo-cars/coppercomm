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
