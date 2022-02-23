class CommandExecutionError(AssertionError):
    pass


class TimeoutExpiredError(CommandExecutionError):
    pass


class CommandFailedError(CommandExecutionError):
    pass


class PatternNotFoundError(CommandExecutionError):
    pass
