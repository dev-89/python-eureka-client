from typing import Dict

from py_eureka_client import constants


class LeaseInfo:
    def __init__(
        self,
        renewalIntervalInSecs: int = constants.Constant.RENEWAL_INTERVAL_IN_SECS,
        durationInSecs: int = constants.Constant.DURATION_IN_SECS,
        registrationTimestamp: int = 0,
        lastRenewalTimestamp: int = 0,
        renewalTimestamp: int = 0,
        evictionTimestamp: int = 0,
        serviceUpTimestamp: int = 0,
    ):
        self.renewalIntervalInSecs: int = renewalIntervalInSecs
        self.durationInSecs: int = durationInSecs
        self.registrationTimestamp: int = registrationTimestamp
        self.lastRenewalTimestamp: int = lastRenewalTimestamp
        self.renewalTimestamp: int = renewalTimestamp
        self.evictionTimestamp: int = evictionTimestamp
        self.serviceUpTimestamp: int = serviceUpTimestamp


class DataCenterInfo:
    def __init__(
        self,
        name=constants.Constant.DEFAULT_DATA_CENTER_INFO,  # Netflix, Amazon, MyOwn
        className=constants.Constant.DEFAULT_DATA_CENTER_INFO_CLASS,
        metadata={},
    ):
        self.name: str = name
        self.className: str = className
        self.metadata: Dict = metadata if metadata else {}


class PortWrapper:
    def __init__(self, port=0, enabled=False):
        self.port: int = port
        self.enabled: bool = enabled
