from logging import exception
from threading import RLock
from typing import List

from py_eureka_client import constants, exceptions, instance
from py_eureka_client.logger import get_logger

_logger = get_logger("eureka_client")


class Application:
    def __init__(self, name="", instances=None):
        self.name: str = name
        if isinstance(instances, list):
            for ins in instances:
                self.add_instance(ins)
        self.__instances_dict = {}
        self.__inst_lock = RLock()

    @property
    def instances(self) -> List[instance.Instance]:
        with self.__inst_lock:
            return list(self.__instances_dict.values())

    @property
    def up_instances(self) -> List[instance.Instance]:
        with self.__inst_lock:
            return [
                item
                for item in self.__instances_dict.values()
                if item.status == constants.InstanceStatus.INSTANCE_STATUS_UP
            ]

    def get_instance(self, instance_id: str) -> instance.Instance:
        with self.__inst_lock:
            if instance_id in self.__instances_dict:
                return self.__instances_dict[instance_id]
            else:
                raise exceptions.InstanceDoesNotExistError(
                    instance_id, "Error instance is not listed in known instances!"
                )

    def add_instance(self, instance: instance.Instance) -> None:
        with self.__inst_lock:
            self.__instances_dict[instance.instanceId] = instance

    def update_instance(self, instance: instance.Instance) -> None:
        with self.__inst_lock:
            _logger.debug(f"update instance {instance.instanceId}")
            self.__instances_dict[instance.instanceId] = instance

    def remove_instance(self, instance: instance.Instance) -> None:
        with self.__inst_lock:
            if instance.instanceId in self.__instances_dict:
                del self.__instances_dict[instance.instanceId]

    def up_instances_in_zone(self, zone: str) -> List[instance.Instance]:
        with self.__inst_lock:
            _zone = zone if zone else constants.Constant.DEFAULT_ZONE
            return [
                item
                for item in self.__instances_dict.values()
                if item.status == constants.InstanceStatus.INSTANCE_STATUS_UP
                and item.zone == _zone
            ]

    def up_instances_not_in_zone(self, zone: str) -> List[instance.Instance]:
        with self.__inst_lock:
            _zone = zone if zone else constants.Constant.DEFAULT_ZONE
            return [
                item
                for item in self.__instances_dict.values()
                if item.status == constants.InstanceStatus.INSTANCE_STATUS_UP
                and item.zone != _zone
            ]


class Applications:
    def __init__(self, apps__hashcode="", versions__delta="", applications=None):
        self.apps__hashcode: str = apps__hashcode
        self.versions__delta: str = versions__delta
        self.__applications = applications if applications is not None else []
        self.__application_name_dic = {}
        self.__app_lock = RLock()

    @property
    def appsHashcode(self) -> str:
        return self.apps__hashcode

    @property
    def applications(self) -> List[Application]:
        return self.__applications

    @property
    def versionsDelta(self) -> str:
        return self.versions__delta

    def add_application(self, application: Application) -> None:
        with self.__app_lock:
            self.__applications.append(application)
            self.__application_name_dic[application.name] = application

    def get_application(self, app_name: str = "") -> Application:
        with self.__app_lock:
            aname = app_name.upper()
            if app_name in self.__application_name_dic:
                return self.__application_name_dic[aname]
            else:
                return Application(name=aname)
