from enum import IntEnum
from re import I

from strenum import StrEnum


class InstanceStatus(StrEnum):
    """
    Status of instances
    """

    INSTANCE_STATUS_UP: str = "UP"
    INSTANCE_STATUS_DOWN: str = "DOWN"
    INSTANCE_STATUS_STARTING: str = "STARTING"
    INSTANCE_STATUS_OUT_OF_SERVICE: str = "OUT_OF_SERVICE"
    INSTANCE_STATUS_UNKNOWN: str = "UNKNOWN"


class ActionType(StrEnum):
    """
    Action type of instances
    """

    ACTION_TYPE_ADDED: str = "ADDED"
    ACTION_TYPE_MODIFIED: str = "MODIFIED"
    ACTION_TYPE_DELETED: str = "DELETED"


class HAStrategy(IntEnum):
    """
    This is for the DiscoveryClient, when this strategy is set, get_service_url will random choose one of the UP instance and return its url
    This is the default strategy
    """

    HA_STRATEGY_RANDOM = 1
    """

    This is for the DiscoveryClient, when this strategy is set, get_service_url will always return one instance until it is down
    """
    HA_STRATEGY_STICK = 2

    """
    This is for the DiscoveryClient, when this strategy is set, get_service_url will always return a new instance if any other instances are up
    """
    HA_STRATEGY_OTHER = 3


class ErrorTypes(StrEnum):
    """
    The error types that will send back to on_error callback function
    """

    ERROR_REGISTER: str = "EUREKA_ERROR_REGISTER"
    ERROR_DISCOVER: str = "EUREKA_ERROR_DISCOVER"
    ERROR_STATUS_UPDATE: str = "EUREKA_ERROR_STATUS_UPDATE"


class Constant(object):
    @staticmethod
    def _constant(f):
        def fset(self, value):
            raise TypeError

        def fget(self):
            return f()

        return property(fget, fset)

    @_constant
    def DEFAULT_TIME_OUT() -> int:
        """The timeout seconds that all http request to the eureka server"""
        return 5

    @_constant
    def DEFAULT_EUREKA_SERVER_URL() -> str:
        """
        Default eureka server url.
        """
        return "http://127.0.0.1:8761/eureka/"

    @_constant
    def DEFAULT_INSTANCE_PORT() -> int:
        return 9090

    @_constant
    def DEFAULT_INSTANCE_SECURE_PORT() -> int:
        return 9443

    @_constant
    def RENEWAL_INTERVAL_IN_SECS() -> int:
        return 30

    @_constant
    def DURATION_IN_SECS() -> int:
        return 90

    @_constant
    def DEFAULT_DATA_CENTER_INFO() -> str:
        return "MyOwn"

    @_constant
    def DEFAULT_DATA_CENTER_INFO_CLASS() -> str:
        return "com.netflix.appinfo.InstanceInfo$DefaultDataCenterInfo"

    @_constant
    def AMAZON_DATA_CENTER_INFO_CLASS() -> str:
        return "com.netflix.appinfo.AmazonInfo"

    @_constant
    def DEFAULT_ENCODING() -> str:
        return "utf-8"

    @_constant
    def DEFAULT_ZONE() -> str:
        return "default"
