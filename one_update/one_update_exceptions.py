class OneUpdateError(AssertionError):
    pass


class UnavailableOptionError(OneUpdateError):
    pass


class OneUpdateScriptFailureError(OneUpdateError):
    def __init__(self, message="Unknown error"):
        message = "OneUpdate failed with error: {}".format(message) + (
            "\nIf you are sure one_update failed unexpectedly please follow these instructions:\r\n"
            "-- For VCC:\r\n"
            '\tSubmit ticket to ARTINFO. Use component "Aptiv - SWDL" and leading workgroup "ARTINFO Team - Scavengers"\r\n'
            "-- For Aptiv (if happened while flashing IHU):\r\n"
            '\tSubmit Bug to JIRA http://jiraprod1.delphiauto.net:8080/browse/AFJ for component "SWDL" and label "IHU"\r\n'
            "-- For Aptiv (if happened while flashing SEM:\r\n"
            '\tSubmit Bug to JIRA http://jiraprod1.delphiauto.net:8080/browse/AII for component "SWDL" and label "SEM"\r\n'
            "Please make sure to attach files located in directory/file pointed by script!\r\n"
        )
        super().__init__(message)


class OneUpdateConnectionError(OneUpdateError):
    def __init__(self, message="Unknown error"):
        message += "\nCheck if serial ports (UART) and ADB are correctly connected"
        super().__init__(message)


class AutoflashingError(OneUpdateError):
    pass


class BootloaderCorruptedError(Exception):  # TODO: Remove
    pass


class FailedToPutMpInFastboot(OneUpdateError):
    pass


class AblUpdateFailedError(OneUpdateError):
    pass
