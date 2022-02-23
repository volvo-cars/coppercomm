# /*===========================================================================*\
#  * Copyright 2018 Aptiv, Inc., All Rights Reserved.
#  * Aptiv Confidential
# \*===========================================================================*/

import typing
import logging

from abc import ABCMeta, abstractmethod
from enum import Enum
from time import sleep
from pexpect import ExceptionPexpect
from collections import namedtuple

from one_update.one_update_exceptions import UnavailableOptionError
from one_update.communication.serial_console_interface import SerialConsoleInterface


Expectation = typing.Union[str, ExceptionPexpect]
Expectations = typing.Union[Expectation, typing.List[Expectation]]


ProfileFlagsTuple = namedtuple(
    "ProfileFlagsTuple",
    [
        "userbuild",
        "sm_alw_on",
        "disable_verity",
        "disable_verification",
        "raise_inic_mismatch",
        "project",
        "android_only",
        "vip_autoflashing",
        "flash_secboot",
        "enable_rescue_party",
        "post_flashing_adb_commands",
        "reset_security_constant",
    ],
)


class ProfileFlags(ProfileFlagsTuple):
    def __getattribute__(self, name: str) -> typing.Any:
        val = super().__getattribute__(name)
        if val is None:
            raise UnavailableOptionError("Accessing unavailable option: {}".format(name))
        return val


class UnitMode(Enum):
    DEFAULT = "default"
    FASTBOOT = "fastboot"
    RECOVERY = "recovery"
    DNX = "dnx"


class Projects:
    IHU = "ihu"
    SEM = "sem"
    SEM25 = "sem25"


class SmAlwOnState:
    ENABLE = "enable"
    ENABLE_PERMANENTLY = "enable permanently"
    DISABLE_PERMANENTLY = "disable"


class VipAutoflasingState(Enum):
    ENABLE = "enable"
    DISABLE = "disable"
    DEFAULT = "default"


class Profiles:
    DEVELOPER = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.ENABLE_PERMANENTLY,
        disable_verity=True,
        disable_verification=False,
        raise_inic_mismatch=False,
        project=Projects.IHU,
        android_only=False,
        vip_autoflashing=VipAutoflasingState.ENABLE,
        flash_secboot=False,
        enable_rescue_party="false",
        post_flashing_adb_commands=[],
        reset_security_constant=False,
    )
    DEVELOPER_RIG = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.DISABLE_PERMANENTLY,
        disable_verity=True,
        disable_verification=False,
        raise_inic_mismatch=False,
        project=Projects.IHU,
        android_only=False,
        vip_autoflashing=VipAutoflasingState.ENABLE,
        flash_secboot=False,
        enable_rescue_party="false",
        post_flashing_adb_commands=[],
        reset_security_constant=False,
    )
    SWDL_CI = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.DISABLE_PERMANENTLY,
        disable_verity=False,
        disable_verification=False,
        raise_inic_mismatch=False,
        project=Projects.IHU,
        android_only=False,
        vip_autoflashing=VipAutoflasingState.DISABLE,
        flash_secboot=False,
        enable_rescue_party="true",
        post_flashing_adb_commands=[],
        reset_security_constant=True,
    )
    AS_APTIV_FACTORY = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.DISABLE_PERMANENTLY,
        disable_verity=False,
        disable_verification=False,
        raise_inic_mismatch=False,
        project=Projects.IHU,
        android_only=False,
        vip_autoflashing=VipAutoflasingState.DISABLE,
        flash_secboot=True,
        enable_rescue_party="true",
        post_flashing_adb_commands=[],
        reset_security_constant=False,
    )
    AS_VCC_FACTORY = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.DISABLE_PERMANENTLY,
        disable_verity=False,
        disable_verification=False,
        raise_inic_mismatch=False,
        project=Projects.IHU,
        android_only=False,
        vip_autoflashing=VipAutoflasingState.DISABLE,
        flash_secboot=True,
        enable_rescue_party="true",
        post_flashing_adb_commands=[],
        reset_security_constant=False,
    )
    CI_MACHINERY_IHU = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.DISABLE_PERMANENTLY,
        disable_verity=False,
        disable_verification=False,
        raise_inic_mismatch=False,
        project=Projects.IHU,
        android_only=False,
        vip_autoflashing=VipAutoflasingState.DEFAULT,
        flash_secboot=False,
        enable_rescue_party="true",
        post_flashing_adb_commands=[],
        reset_security_constant=False,
    )
    CI_MACHINERY_IHU_NO_VERITY = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.ENABLE,
        disable_verity=True,
        disable_verification=True,
        raise_inic_mismatch=False,
        project=Projects.IHU,
        android_only=False,
        vip_autoflashing=VipAutoflasingState.DEFAULT,
        flash_secboot=False,
        enable_rescue_party="false",
        post_flashing_adb_commands=[],
        reset_security_constant=False,
    )
    CI_MACHINERY_IHU_RIG = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.DISABLE_PERMANENTLY,
        disable_verity=False,
        disable_verification=False,
        raise_inic_mismatch=False,
        project=Projects.IHU,
        android_only=False,
        vip_autoflashing=VipAutoflasingState.DEFAULT,
        flash_secboot=False,
        enable_rescue_party="true",
        post_flashing_adb_commands=[],
        reset_security_constant=False,
    )
    GOTA = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.DISABLE_PERMANENTLY,
        disable_verity=False,
        disable_verification=False,
        raise_inic_mismatch=False,
        project=Projects.IHU,
        android_only=False,
        vip_autoflashing=VipAutoflasingState.ENABLE,
        flash_secboot=False,
        enable_rescue_party="true",
        post_flashing_adb_commands=[
            "settings put global android.car.BUGREPORT_FLAGS upload_destination=gcs",
            "device_config put car bugreport_upload_destination gcs",
        ],
        reset_security_constant=False,
    )
    BSP_IHU = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.ENABLE_PERMANENTLY,
        disable_verity=False,
        disable_verification=False,
        raise_inic_mismatch=False,
        project=Projects.IHU,
        android_only=True,
        vip_autoflashing=VipAutoflasingState.DEFAULT,
        flash_secboot=False,
        enable_rescue_party="false",
        post_flashing_adb_commands=[],
        reset_security_constant=False,
    )
    USERBUILD_IHU = ProfileFlags(
        userbuild=True,
        sm_alw_on=None,
        disable_verity=False,
        disable_verification=False,
        raise_inic_mismatch=None,
        project=Projects.IHU,
        android_only=None,
        vip_autoflashing=None,
        flash_secboot=None,
        enable_rescue_party=None,
        post_flashing_adb_commands=None,
        reset_security_constant=None,
    )

    # --- TODO: Remove if SEM fully using Aptiv's version ---
    CI_MACHINERY_SEM = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.ENABLE,
        disable_verity=False,
        disable_verification=False,
        raise_inic_mismatch=False,
        project=Projects.SEM,
        android_only=False,
        vip_autoflashing=VipAutoflasingState.DEFAULT,
        flash_secboot=False,
        enable_rescue_party="false",
        post_flashing_adb_commands=[],
        reset_security_constant=False,
    )
    SEM_SWDL_CI = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.ENABLE_PERMANENTLY,
        disable_verity=False,
        disable_verification=False,
        raise_inic_mismatch=False,
        project=Projects.SEM,
        android_only=False,
        vip_autoflashing=VipAutoflasingState.DEFAULT,
        flash_secboot=False,
        enable_rescue_party="false",
        post_flashing_adb_commands=[],
        reset_security_constant=False,
    )
    BSP_SEM = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.ENABLE_PERMANENTLY,
        disable_verity=False,
        disable_verification=False,
        raise_inic_mismatch=False,
        project=Projects.SEM,
        android_only=True,
        vip_autoflashing=VipAutoflasingState.DEFAULT,
        flash_secboot=False,
        enable_rescue_party="false",
        post_flashing_adb_commands=[],
        reset_security_constant=False,
    )
    CI_MACHINERY_SEM25 = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.ENABLE,
        disable_verity=False,
        disable_verification=False,
        raise_inic_mismatch=False,
        project=Projects.SEM25,
        android_only=False,
        vip_autoflashing=VipAutoflasingState.DEFAULT,
        flash_secboot=False,
        enable_rescue_party="false",
        post_flashing_adb_commands=[],
        reset_security_constant=False,
    )
    SEM25_SWDL_CI = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.ENABLE_PERMANENTLY,
        disable_verity=False,
        disable_verification=False,
        raise_inic_mismatch=False,
        project=Projects.SEM25,
        android_only=False,
        vip_autoflashing=VipAutoflasingState.DEFAULT,
        flash_secboot=False,
        enable_rescue_party="false",
        post_flashing_adb_commands=[],
        reset_security_constant=False,
    )
    BSP_SEM25 = ProfileFlags(
        userbuild=False,
        sm_alw_on=SmAlwOnState.ENABLE_PERMANENTLY,
        disable_verity=False,
        disable_verification=False,
        raise_inic_mismatch=False,
        project=Projects.SEM25,
        android_only=True,
        vip_autoflashing=VipAutoflasingState.DEFAULT,
        flash_secboot=False,
        enable_rescue_party="false",
        post_flashing_adb_commands=[],
        reset_security_constant=False,
    )

    @classmethod
    def get_profile_names(cls):
        return list(filter(lambda x: not x.startswith("__") and not x.startswith("get"), cls.__dict__.keys()))

    @classmethod
    def get_profiles_description(cls) -> str:
        profile_names = cls.get_profile_names()

        description = ""
        for profile_name in profile_names:
            profile = getattr(Profiles, profile_name)
            profile_description = ""
            for field in profile._fields:
                try:
                    profile_description += "    {}: {}\n".format(field, getattr(profile, field))
                except UnavailableOptionError:
                    pass

            description += "> {}:\n{}\n".format(profile_name, profile_description)
        return description


class OneUpdateConsoleInterface(object):
    """
    This is a wrapper for different serial communication classes that ensures a common interface
    for sending and expecting data on console
    """

    __metaclass__ = ABCMeta

    def __init__(self, console_object: SerialConsoleInterface) -> None:
        self.console_object = console_object

    @abstractmethod
    def send_line(
        self,
        command: str,
        check_echo: bool = True,
        wait_for_prompt: bool = False,
        timeout: float = 2,
        prompt: typing.Union[str, typing.List[str]] = None,
    ) -> None:
        """
        Method that sends a line on the console (using console_object)
        """
        pass

    @abstractmethod
    def send_line_and_expect(
        self,
        command: str,
        pattern: Expectations,
        timeout: float,
        check_echo: bool = True,
        wait_for_prompt: bool = True,
        prompt: typing.Union[str, typing.List[str]] = None,
    ) -> int:
        """
        Method that send a line on the console and expects a pattern or
        list of patterns (using console_object)
        :param command: command to send on the console
        :param pattern: list of patterns to match - should also accept single pattern (string)
        :param timeout: time to wait for expected pattern
        :param wait_for_prompt: indicates that method should wait for expected prompt
        :param prompt: expected prompt(s)
        :return: index of the pattern matched in pattern list
        """
        pass

    @abstractmethod
    def expect(self, pattern: Expectations, timeout: float) -> int:
        """
        Method that expects a pattern or a list of patterns on the console (using console_object)
        :param pattern: list of patterns to match - should also accept single pattern (string)
        :param timeout: time (in seconds) to wait for expected pattern
        :return: index of the pattern matched in pattern list
        """
        pass

    @abstractmethod
    def get_matched(self) -> typing.Optional[str]:
        """
        :return: output from console matched with pattern
        """
        pass

    @abstractmethod
    def close_console(self) -> None:
        """
        Method that releases connection handlers
        """
        pass

    @abstractmethod
    def set_prompt(self, prompt: typing.Union[str, typing.List[str]]) -> None:
        """
        Method that sets expected prompt
        """
        pass


class OneUpdatePowerController(object):
    """
    This is a wrapper for controlling unit's power.
    """

    __metaclass__ = ABCMeta

    def __init__(self, logger: logging.Logger = None) -> None:
        if logger:
            self.logger = logger
        else:
            self.logger = logging.getLogger(self.__class__.__name__)
            self.logger.setLevel(logging.DEBUG)

    @abstractmethod
    def power_off(self) -> None:
        """
        Method that turns the unit's power off.
        """
        pass

    @abstractmethod
    def power_on(self) -> None:
        """
        Method that turn sthe unit's power on.
        """
        pass

    def power_reset(self, delay: float = 3.0) -> None:
        """
        Method that performs a power cycle restart. By default it just executes power_off() and power_on() with a delay
        in between.
        :param delay: the pause between turning the power off and on.
        """
        self.logger.info("A power reset must be performed.")
        self.power_off()
        while delay > 0:
            self.logger.info("Unit will be powered on after {}s...".format(delay))
            delay_stage = min(delay, 10)
            sleep(delay_stage)
            delay -= delay_stage
        self.power_on()
