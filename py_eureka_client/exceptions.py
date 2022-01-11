from logging import exception

import py_eureka_client.http_client as http_client
from py_eureka_client import instance


class EurekaServerConnectionException(http_client.URLError):
    pass


class DiscoverException(http_client.URLError):
    pass


class WrongXMLNodeError(Exception):
    """Custom error that is raised when XML node is of wrong type"""

    def __init__(self, node_type: str, message: str) -> None:
        self.node_type: str = node_type
        self.message: str = message
        super().__init__(message)


class InstanceDoesNotExistError(Exception):
    """Custom error if an instance id is queried, which does not exist"""

    def __init__(self, instance_id: str, message: str) -> None:
        self.instance_id: str = instance_id
        self.message: str = message
        super().__init__(message)
