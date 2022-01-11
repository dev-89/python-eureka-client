import json
from typing import Dict
from urllib.parse import quote

from py_eureka_client import constants, http_client, instance, util


def register(eureka_server: str, _instance: instance.Instance) -> None:
    instance_dic = {
        "instanceId": _instance.instanceId,
        "hostName": _instance.hostName,
        "app": _instance.app,
        "ipAddr": _instance.ipAddr,
        "status": _instance.status,
        "overriddenstatus": _instance.overriddenstatus,
        "port": {
            "$": _instance.port.port,
            "@enabled": str(_instance.port.enabled).lower(),
        },
        "securePort": {
            "$": _instance.securePort.port,
            "@enabled": str(_instance.securePort.enabled).lower(),
        },
        "countryId": _instance.countryId,
        "dataCenterInfo": {
            "@class": _instance.dataCenterInfo.className,
            "name": _instance.dataCenterInfo.name,
        },
        "leaseInfo": {
            "renewalIntervalInSecs": _instance.leaseInfo.renewalIntervalInSecs,
            "durationInSecs": _instance.leaseInfo.durationInSecs,
            "registrationTimestamp": _instance.leaseInfo.registrationTimestamp,
            "lastRenewalTimestamp": _instance.leaseInfo.lastRenewalTimestamp,
            "evictionTimestamp": _instance.leaseInfo.evictionTimestamp,
            "serviceUpTimestamp": _instance.leaseInfo.serviceUpTimestamp,
        },
        "metadata": _instance.metadata,
        "homePageUrl": _instance.homePageUrl,
        "statusPageUrl": _instance.statusPageUrl,
        "healthCheckUrl": _instance.healthCheckUrl,
        "secureHealthCheckUrl": _instance.secureHealthCheckUrl,
        "vipAddress": _instance.vipAddress,
        "secureVipAddress": _instance.secureVipAddress,
        "lastUpdatedTimestamp": str(_instance.lastUpdatedTimestamp),
        "lastDirtyTimestamp": str(_instance.lastDirtyTimestamp),
        "isCoordinatingDiscoveryServer": str(
            _instance.isCoordinatingDiscoveryServer
        ).lower(),
    }
    if _instance.dataCenterInfo.metadata:
        instance_dic["dataCenterInfo"]["metadata"] = _instance.dataCenterInfo.metadata
    send_registry(eureka_server, instance_dic)


def send_registry(eureka_server: str, instance_dic: Dict) -> None:
    req = http_client.Request(
        f"{util.format_url(eureka_server)}apps/{quote(instance_dic['app'])}",
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    http_client.load(
        req,
        json.dumps({"instance": instance_dic}).encode(
            constants.Constant.DEFAULT_ENCODING
        ),
        timeout=constants.Constant.DEFAULT_TIME_OUT,
    )[0]


def cancel(eureka_server: str, app_name: str, instance_id: str) -> None:
    req = http_client.Request(
        f"{util.format_url(eureka_server)}apps/{quote(app_name)}/{quote(instance_id)}",
        method="DELETE",
    )
    http_client.load(req, timeout=constants.Constant.DEFAULT_TIME_OUT)[0]


def send_heartbeat(
    eureka_server: str,
    app_name: str,
    instance_id: str,
    last_dirty_timestamp: int,
    status: str = constants.InstanceStatus.INSTANCE_STATUS_UP,
    overriddenstatus: str = "",
) -> None:
    url = f"{util.format_url(eureka_server)}apps/{quote(app_name)}/{quote(instance_id)}?status={status}&lastDirtyTimestamp={last_dirty_timestamp}"
    if overriddenstatus != "":
        url += f"&overriddenstatus={overriddenstatus}"

    req = http_client.Request(url, method="PUT")
    http_client.load(req, timeout=constants.Constant.DEFAULT_TIME_OUT)[0]


def status_update(
    eureka_server: str,
    app_name: str,
    instance_id: str,
    last_dirty_timestamp,
    status: str = constants.InstanceStatus.INSTANCE_STATUS_OUT_OF_SERVICE,
    overriddenstatus: str = "",
):
    url = f"{util.format_url(eureka_server)}apps/{quote(app_name)}/{quote(instance_id)}/status?value={status}&lastDirtyTimestamp={last_dirty_timestamp}"
    if overriddenstatus != "":
        url += f"&overriddenstatus={overriddenstatus}"

    req = http_client.Request(url, method="PUT")
    http_client.load(req, timeout=constants.Constant.DEFAULT_TIME_OUT)[0]


def delete_status_override(
    eureka_server: str, app_name: str, instance_id: str, last_dirty_timestamp: str
) -> None:
    url = f"{util.format_url(eureka_server)}apps/{quote(app_name)}/{quote(instance_id)}/status?lastDirtyTimestamp={last_dirty_timestamp}"

    req = http_client.Request(url, method="DELETE")
    http_client.load(req, timeout=constants.Constant.DEFAULT_TIME_OUT)[0]
