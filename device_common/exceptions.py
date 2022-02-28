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