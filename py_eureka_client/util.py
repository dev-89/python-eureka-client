import time
import xml.etree.ElementTree as ElementTree
from typing import List
from urllib.parse import quote

from py_eureka_client import (
    application,
    constants,
    dataclasses,
    exceptions,
    http_client,
    instance,
)


def get_applications(
    eureka_server: str, regions: List[str]
) -> application.Applications:
    return _get_applications_(f"{format_url(eureka_server)}apps/", regions)


def format_url(url):
    if url.endswith("/"):
        return url
    else:
        return url + "/"


def _get_applications_(url, regions: List[str]) -> application.Applications:
    _url = url
    if len(regions) > 0:
        _url = _url + ("&" if "?" in _url else "?") + "regions=" + (",".join(regions))

    txt = http_client.load(_url, timeout=constants.Constant.DEFAULT_TIME_OUT)[0]
    return _build_applications(
        ElementTree.fromstring(txt.encode(constants.Constant.DEFAULT_ENCODING))
    )


def _build_applications(xml_node) -> application.Applications:
    if xml_node.tag != "applications":
        raise exceptions.WrongXMLNodeError(
            xml_node.tag, "Error while building application. XML node is of wrong type!"
        )
    applications = application.Applications()
    for child_node in list(xml_node):
        if child_node.tag == "versions__delta" and child_node.text is not None:
            applications.versions__delta = child_node.text
        elif child_node.tag == "apps__hashcode" and child_node.text is not None:
            applications.apps__hashcode = child_node.text
        elif child_node.tag == "application":
            applications.add_application(_build_application(child_node))

    return applications


def _build_application(xml_node) -> application.Application:
    if xml_node.tag != "application":
        raise exceptions.WrongXMLNodeError(
            xml_node.tag, "Error while building application. XML node is of wrong type!"
        )
    _application = application.Application()
    for child_node in xml_node:
        if child_node.tag == "name":
            _application.name = child_node.text
        elif child_node.tag == "instance":
            _application.add_instance(_build_instance(child_node))
    return _application


def _build_instance(xml_node) -> instance.Instance:
    if xml_node.tag != "instance":
        raise exceptions.WrongXMLNodeError(
            xml_node.tag, "Error while building application. XML node is of wrong type!"
        )
    _instance = instance.Instance()
    for child_node in xml_node:
        if child_node.tag == "instanceId":
            _instance.instanceId = child_node.text
        elif child_node.tag == "sid":
            _instance.sid = child_node.text
        elif child_node.tag == "app":
            _instance.app = child_node.text
        elif child_node.tag == "appGroupName":
            _instance.appGroupName = child_node.text
        elif child_node.tag == "ipAddr":
            _instance.ipAddr = child_node.text
        elif child_node.tag == "port":
            _instance.port = _build_port(child_node)
        elif child_node.tag == "securePort":
            _instance.securePort = _build_port(child_node)
        elif child_node.tag == "homePageUrl":
            _instance.homePageUrl = child_node.text
        elif child_node.tag == "statusPageUrl":
            _instance.statusPageUrl = child_node.text
        elif child_node.tag == "healthCheckUrl":
            _instance.healthCheckUrl = child_node.text
        elif child_node.tag == "secureHealthCheckUrl":
            _instance.secureHealthCheckUrl = child_node.text
        elif child_node.tag == "vipAddress":
            _instance.vipAddress = child_node.text
        elif child_node.tag == "secureVipAddress":
            _instance.secureVipAddress = child_node.text
        elif child_node.tag == "countryId":
            _instance.countryId = int(child_node.text)
        elif child_node.tag == "dataCenterInfo":
            _instance.dataCenterInfo = _build_data_center_info(child_node)
        elif child_node.tag == "hostName":
            _instance.hostName = child_node.text
        elif child_node.tag == "status":
            _instance.status = child_node.text
        elif child_node.tag == "overriddenstatus":
            _instance.overriddenstatus = child_node.text
        elif child_node.tag == "leaseInfo":
            _instance.leaseInfo = _build_lease_info(child_node)
        elif child_node.tag == "isCoordinatingDiscoveryServer":
            _instance.isCoordinatingDiscoveryServer = child_node.text == "true"
        elif child_node.tag == "metadata":
            _instance.metadata = _build_metadata(child_node)
        elif child_node.tag == "lastUpdatedTimestamp":
            _instance.lastUpdatedTimestamp = int(child_node.text)
        elif child_node.tag == "lastDirtyTimestamp":
            _instance.lastDirtyTimestamp = int(child_node.text)
        elif child_node.tag == "actionType":
            _instance.actionType = child_node.text
        elif child_node.tag == "asgName":
            _instance.asgName = child_node.text

    return _instance


def _build_data_center_info(xml_node):
    class_name = xml_node.attrib["class"]
    name = ""
    metadata = {}
    for child_node in xml_node:
        if child_node.tag == "name":
            name = child_node.text
        elif child_node.tag == "metadata":
            metadata = _build_metadata(child_node)

    return dataclasses.DataCenterInfo(
        name=name, className=class_name, metadata=metadata
    )


def _build_metadata(xml_node):
    metadata = {}
    for child_node in list(xml_node):
        metadata[child_node.tag] = child_node.text
    return metadata


def _build_lease_info(xml_node):
    leaseInfo = dataclasses.LeaseInfo()
    for child_node in list(xml_node):
        if child_node.tag == "renewalIntervalInSecs":
            leaseInfo.renewalIntervalInSecs = int(child_node.text)
        elif child_node.tag == "durationInSecs":
            leaseInfo.durationInSecs = int(child_node.text)
        elif child_node.tag == "registrationTimestamp":
            leaseInfo.registrationTimestamp = int(child_node.text)
        elif child_node.tag == "lastRenewalTimestamp":
            leaseInfo.lastRenewalTimestamp = int(child_node.text)
        elif child_node.tag == "renewalTimestamp":
            leaseInfo.renewalTimestamp = int(child_node.text)
        elif child_node.tag == "evictionTimestamp":
            leaseInfo.evictionTimestamp = int(child_node.text)
        elif child_node.tag == "serviceUpTimestamp":
            leaseInfo.serviceUpTimestamp = int(child_node.text)

    return leaseInfo


def _build_port(xml_node):
    port = dataclasses.PortWrapper()
    port.port = int(xml_node.text)
    port.enabled = xml_node.attrib["enabled"] == "true"
    return port


def get_delta(eureka_server: str, regions: List[str]) -> application.Applications:
    return _get_applications_(f"{format_url(eureka_server)}apps/delta", regions)


def get_vip(
    eureka_server: str, vip: str, regions: List[str]
) -> application.Applications:
    return _get_applications_(f"{format_url(eureka_server)}vips/{vip}", regions)


def get_secure_vip(
    eureka_server: str, svip: str, regions: List[str]
) -> application.Applications:
    return _get_applications_(f"{format_url(eureka_server)}svips/{svip}", regions)


def get_application(eureka_server: str, app_name: str) -> application.Application:
    url = f"{format_url(eureka_server)}apps/{quote(app_name)}"
    txt = http_client.load(url, timeout=constants.Constant.DEFAULT_TIME_OUT)[0]
    return _build_application(ElementTree.fromstring(txt))


def get_app_instance(
    eureka_server: str, app_name: str, instance_id: str
) -> instance.Instance:
    return _get_instance_(
        f"{format_url(eureka_server)}apps/{quote(app_name)}/{quote(instance_id)}"
    )


def get_instance(eureka_server: str, instance_id: str) -> instance.Instance:
    return _get_instance_(f"{format_url(eureka_server)}instances/{quote(instance_id)}")


def _get_instance_(url):
    txt = http_client.load(url, timeout=constants.Constant.DEFAULT_TIME_OUT)[0]
    return _build_instance(ElementTree.fromstring(txt))


def current_time_millis():
    return int(time.time() * 1000)
