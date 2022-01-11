from typing import Dict

from py_eureka_client import constants, dataclasses


class Instance:
    def __init__(
        self,
        instanceId="",
        sid="",  # @deprecated
        app="",
        appGroupName="",
        ipAddr="",
        port=dataclasses.PortWrapper(
            port=constants.Constant.DEFAULT_INSTANCE_PORT, enabled=True
        ),
        securePort=dataclasses.PortWrapper(
            port=constants.Constant.DEFAULT_INSTANCE_SECURE_PORT, enabled=False
        ),
        homePageUrl="",
        statusPageUrl="",
        healthCheckUrl="",
        secureHealthCheckUrl="",
        vipAddress="",
        secureVipAddress="",
        countryId: int = 1,
        dataCenterInfo=dataclasses.DataCenterInfo(),
        hostName="",
        status="",  # UP, DOWN, STARTING, OUT_OF_SERVICE, UNKNOWN
        overriddenstatus="",  # UP, DOWN, STARTING, OUT_OF_SERVICE, UNKNOWN
        leaseInfo=dataclasses.LeaseInfo(),
        isCoordinatingDiscoveryServer=False,
        metadata=None,
        lastUpdatedTimestamp=0,
        lastDirtyTimestamp=0,
        actionType=constants.ActionType.ACTION_TYPE_ADDED,  # ADDED, MODIFIED, DELETED
        asgName="",
    ):
        self.__instanceId: str = instanceId
        self.sid: str = sid
        self.app: str = app
        self.appGroupName: str = appGroupName
        self.ipAddr: str = ipAddr
        self.port: dataclasses.PortWrapper = port
        self.securePort: dataclasses.PortWrapper = securePort
        self.homePageUrl: str = homePageUrl
        self.statusPageUrl: str = statusPageUrl
        self.healthCheckUrl: str = healthCheckUrl
        self.secureHealthCheckUrl: str = secureHealthCheckUrl
        self.vipAddress: str = vipAddress
        self.secureVipAddress: str = secureVipAddress
        self.countryId: int = countryId
        self.dataCenterInfo: dataclasses.DataCenterInfo = dataCenterInfo
        self.hostName: str = hostName
        self.status: str = status
        self.overriddenstatus: str = overriddenstatus
        self.leaseInfo: dataclasses.LeaseInfo = leaseInfo
        self.isCoordinatingDiscoveryServer: bool = isCoordinatingDiscoveryServer
        self.metadata: Dict = metadata if metadata is not None else {}
        self.lastUpdatedTimestamp: int = lastUpdatedTimestamp
        self.lastDirtyTimestamp: int = lastDirtyTimestamp
        self.actionType: int = actionType
        self.asgName: int = asgName

    @property
    def instanceId(self):
        return (
            self.__instanceId
            if self.__instanceId
            else f"{self.hostName}:{self.ipAddr}:{self.app}:{self.port.port if self.port else 0}"
        )

    @instanceId.setter
    def instanceId(self, new_id):
        self.__instanceId = new_id

    @property
    def zone(self) -> str:
        if (
            self.dataCenterInfo
            and self.dataCenterInfo.name == "Amazon"
            and self.dataCenterInfo.metadata
            and "availability-zone" in self.dataCenterInfo.metadata
        ):
            return self.dataCenterInfo.metadata["availability-zone"]
        if self.metadata and "zone" in self.metadata and self.metadata["zone"]:
            return self.metadata["zone"]
        else:
            return constants.Constant.DEFAULT_ZONE
