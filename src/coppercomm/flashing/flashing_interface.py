from abc import ABC, abstractmethod


class FlashingInterface(ABC):
    """
    Interface with methods for flashing various device types
    """

    @abstractmethod
    def flash_all(self) -> bool:
        """
        Abstract method to trigger flashing process of the whole device
        :return: True if flashing was successful
        """

    @abstractmethod
    def flash_android(self) -> bool:
        """
        Abstract method to trigger Android flashing process on a device
        :return: True if flashing was successful
        """
