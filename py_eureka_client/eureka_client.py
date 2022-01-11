# -*- coding: utf-8 -*-

"""
Copyright (c) 2018 Keijack Wu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import atexit
import inspect
import json
import random
import re
import socket
import ssl
import time
from threading import RLock, Thread, Timer
from typing import Callable, Dict, List, Union

import py_eureka_client.http_client as http_client
import py_eureka_client.netint_utils as netint
from py_eureka_client import (
    application,
    constants,
    eureka_server_conf,
    exceptions,
    registry,
    util,
)
from py_eureka_client.__aws_info_loader import AmazonInfo
from py_eureka_client.logger import get_logger

_logger = get_logger("eureka_client")


class EurekaClient:
    """
    Example:

    >>> client = EurekaClient(
            eureka_server="http://my_eureka_server_peer_1/eureka/v2,http://my_eureka_server_peer_2/eureka/v2",
            app_name="python_module_1",
            instance_port=9090)
    >>> client.start()
    >>> result = client.do_service("APP_NAME", "/context/path", return_type="json")

    EIPs support:

    You can configure EIP using `eureka_availability_zones` and specify the `zone` of your instance. But please aware, that the client won't fill up the metadata atomatically,
    You should put it to the `metadata` when creating the object.

    >>> client = EurekaClient(eureka_availability_zones={
                "us-east-1c": "http://ec2-552-627-568-165.compute-1.amazonaws.com:7001/eureka/v2/,http://ec2-368-101-182-134.compute-1.amazonaws.com:7001/eureka/v2/",
                "us-east-1d": "http://ec2-552-627-568-170.compute-1.amazonaws.com:7001/eureka/v2/",
                "us-east-1e": "http://ec2-500-179-285-592.compute-1.amazonaws.com:7001/eureka/v2/"},
                zone="us-east-1c",
                app_name="python_module_1",
                instance_port=9090,
                data_center_name="Amazon")

    EurekaClient supports DNS discovery feature.

    For instance, following is a DNS TXT record created in the DNS server that lists the set of available DNS names for a zone.

    >>> txt.us-east-1.mydomaintest.netflix.net="us-east-1c.mydomaintest.netflix.net" "us-east-1d.mydomaintest.netflix.net" "us-east-1e.mydomaintest.netflix.net"

    Then, you can define TXT records recursively for each zone similar to the following (if more than one hostname per zone, space delimit)

    >>> txt.us-east-1c.mydomaintest.netflix.net="ec2-552-627-568-165.compute-1.amazonaws.com" "ec2-368-101-182-134.compute-1.amazonaws.com"
    >>> txt.us-east-1d.mydomaintest.netflix.net="ec2-552-627-568-170.compute-1.amazonaws.com"
    >>> txt.us-east-1e.mydomaintest.netflix.net="ec2-500-179-285-592.compute-1.amazonaws.com"

    And then you can create the client like:

    >>> client = EurekaClient(eureka_domain="mydomaintest.netflix.net",
                region="us-east-1",
                zone="us-east-1c",
                app_name="python_module_1",
                instance_port=9090,
                data_center_name="Amazon")

    Eureka client also supports setting up the protocol, basic authentication and context path of your eureka server.

    >>> client = EurekaClient(eureka_domain="mydomaintest.netflix.net",
                region="us-east-1",
                zone="us-east-1c",
                eureka_protocol="https",
                eureka_basic_auth_user="keijack",
                eureka_basic_auth_password="kjauthpass",
                eureka_context="/eureka/v2",
                app_name="python_module_1",
                instance_port=9090,
                data_center_name="Amazon")

    or

    >>> client = EurekaClient(eureka_server="my_eureka_server_peer_1,my_eureka_server_peer_2",
                eureka_protocol="https",
                eureka_basic_auth_user="keijack",
                eureka_basic_auth_password="kjauthpass",
                eureka_context="/eureka/v2",
                app_name="python_module_1",
                instance_port=9090)

    You can use `do_service`, `do_service_async`, `wall_nodes`, `wall_nodes_async` to call the remote services.

    >>> res = eureka_client.do_service("OTHER-SERVICE-NAME", "/service/context/path")

    >>> def success_callabck(data):
            ...

        def error_callback(error):
            ...

        client.do_service_async("OTHER-SERVICE-NAME", "/service/context/path", on_success=success_callabck, on_error=error_callback)

    >>> def walk_using_your_own_urllib(url):
            ...

        res = client.walk_nodes("OTHER-SERVICE-NAME", "/service/context/path", walker=walk_using_your_own_urllib)

    >>> client.walk_nodes("OTHER-SERVICE-NAME", "/service/context/path",
                          walker=walk_using_your_own_urllib,
                          on_success=success_callabck,
                          on_error=error_callback)
    """

    def __init__(
        self,
        # The eureka server url, if you want have deploy a cluster to do the failover, use `,` to separate the urls.
        eureka_server: str = constants.Constant.DEFAULT_EUREKA_SERVER_URL,
        # The domain name when using the DNS discovery.
        eureka_domain: str = "",
        # The region when using DNS discovery.
        region: str = "",
        # Which zone your instances belong to, default is `default`.
        zone: str = "",
        # The zones' url configurations.
        eureka_availability_zones: Dict[str, str] = {},
        # The protocol of the eureka server, if the url include this part, this protocol will not add to the url.
        eureka_protocol: str = "http",
        # User name of the basic authentication of the eureka server, if the url include this part, this protocol will not add to the url.
        eureka_basic_auth_user: str = "",
        # Password of the basic authentication of the eureka server, if the url include this part, this protocol will not add to the url.
        eureka_basic_auth_password: str = "",
        # The context path of the eureka server, if the url include this part, this protocol will not add to the url, default is `/eureka`
        # which meets the spring-boot eureka context but not the Netflix eureka server url.
        eureka_context: str = "/eureka",
        # When set to True, will first find the eureka server in the same zone to register, and find the instances in the same zone to do
        # the service. Or it will randomly choose the eureka server  to register and instances to do the services, default is `True`.
        prefer_same_zone: bool = True,
        # When set to False, will not register this instance to the eureka server, default is `True`.
        should_register: bool = True,
        # When set to False, will not pull registry from the eureka server, default is `True`.
        should_discover: bool = True,
        #
        on_error: Callable = None,
        ## The following parameters all the properties of this instances, all this fields will be sent to the eureka server.
        # The application name of this instance.
        app_name: str = "",
        # The id of this instance, if not specified, will generate one by app_name and instance_host/instance_ip and instance_port.
        instance_id: str = "",
        # The host of this instance.
        instance_host: str = "",
        # The ip of this instance. If instance_host and instance_ip are not specified, will try to find the ip via connection to the eureka server.
        instance_ip: str = "",
        # The ip network of this instance. If instance_host and instance_ip are not specified, will try to find the ip from the avaiable network adapters that matches the specified network. For example 192.168.1.0/24.
        instance_ip_network: str = "",
        # The port of this instance.
        instance_port: int = constants.Constant.DEFAULT_INSTANCE_PORT,
        # Set whether enable the instance's unsecure port, default is `True`.
        instance_unsecure_port_enabled: bool = True,
        # The secure port of this instance.
        instance_secure_port: int = constants.Constant.DEFAULT_INSTANCE_SECURE_PORT,
        # Set whether enable the instance's secure port, default is `False`.
        instance_secure_port_enabled: bool = False,
        # Accept `Netflix`, `Amazon`, `MyOwn`, default is `MyOwn`
        data_center_name: str = constants.Constant.DEFAULT_DATA_CENTER_INFO,
        # Will send heartbeat and pull registry in this time interval, defalut is 30 seconds
        renewal_interval_in_secs: int = constants.Constant.RENEWAL_INTERVAL_IN_SECS,
        # Sets the client specified setting for eviction (e.g. how long to wait without renewal event).
        duration_in_secs: int = constants.Constant.DURATION_IN_SECS,
        # The home page url of this instance.
        home_page_url: str = "",
        # The status page url of this instance.
        status_page_url: str = "",
        # The health check url of this instance.
        health_check_url: str = "",
        # The secure health check url of this instance.
        secure_health_check_url: str = "",
        # The virtual ip address of this instance.
        vip_adr: str = "",
        # The secure virtual ip address of this instance.
        secure_vip_addr: str = "",
        # Sets a flag if this instance is the same as the discovery server that is
        # return the instances. This flag is used by the discovery clients to
        # identity the discovery server which is coordinating/returning the
        # information.
        is_coordinating_discovery_server: bool = False,
        # The metadata map of this instances
        metadata: Dict = {},
        # Will also find the services that belongs to these regions.
        remote_regions: List[str] = [],
        # Specify the strategy how to choose a instance when there are more than one instanse of an App.
        ha_strategy: int = constants.HAStrategy.HA_STRATEGY_RANDOM,
    ):
        assert (
            app_name is not None and app_name != "" if should_register else True
        ), "application name must be specified."
        assert instance_port > 0 if should_register else True, "port is unvalid"
        assert isinstance(metadata, dict), "metadata must be dict"
        assert (
            ha_strategy
            in (
                constants.HAStrategy.HA_STRATEGY_RANDOM,
                constants.HAStrategy.HA_STRATEGY_STICK,
                constants.HAStrategy.HA_STRATEGY_OTHER,
            )
            if should_discover
            else True
        ), f"do not support strategy {ha_strategy}"

        self.__net_lock = RLock()
        self.__eureka_server_conf = eureka_server_conf.EurekaServerConf(
            eureka_server=eureka_server,
            eureka_domain=eureka_domain,
            eureka_protocol=eureka_protocol,
            eureka_basic_auth_user=eureka_basic_auth_user,
            eureka_basic_auth_password=eureka_basic_auth_password,
            eureka_context=eureka_context,
            eureka_availability_zones=eureka_availability_zones,
            region=region,
            zone=zone,
        )
        self.__cache_eureka_url = {}
        self.__should_register = should_register
        self.__should_discover = should_discover
        self.__prefer_same_zone = prefer_same_zone
        self.__alive = False
        self.__heartbeat_interval = renewal_interval_in_secs
        self.__heartbeat_timer = Timer(renewal_interval_in_secs, self.__heartbeat)
        self.__heartbeat_timer.daemon = True
        self.__instance_ip = instance_ip
        self.__instance_ip_network = instance_ip_network
        self.__instance_host = instance_host
        self.__aws_metadata = {}
        self.__on_error_callback = on_error

        # For Registery
        if should_register:
            if data_center_name == "Amazon":
                self.__aws_metadata = self.__load_ec2_metadata_dict()
            if self.__instance_host == "" and self.__instance_ip == "":
                self.__instance_ip, self.__instance_host = self.__get_ip_host(
                    self.__instance_ip_network
                )
            elif self.__instance_host != "" and self.__instance_ip == "":
                self.__instance_ip = netint.get_ip_by_host(self.__instance_host)
                if not EurekaClient.__is_ip(self.__instance_ip):

                    def try_to_get_client_ip(url):
                        self.__instance_ip = EurekaClient.__get_instance_ip(url)

                    self.__connect_to_eureka_server(try_to_get_client_ip)
            elif self.__instance_host == "" and self.__instance_ip != "":
                self.__instance_host = netint.get_host_by_ip(self.__instance_ip)

            mdata = {"management.port": str(instance_port)}
            if zone:
                mdata["zone"] = zone
            mdata.update(metadata)
            ins_id = (
                instance_id
                if instance_id != ""
                else f"{self.__instance_ip}:{app_name.lower()}:{instance_port}"
            )
            _logger.debug(f"register instance using id [#{ins_id}]")
            self.__instance = {
                "instanceId": ins_id,
                "hostName": self.__instance_host,
                "app": app_name.upper(),
                "ipAddr": self.__instance_ip,
                "port": {
                    "$": instance_port,
                    "@enabled": str(instance_unsecure_port_enabled).lower(),
                },
                "securePort": {
                    "$": instance_secure_port,
                    "@enabled": str(instance_secure_port_enabled).lower(),
                },
                "countryId": 1,
                "dataCenterInfo": {
                    "@class": constants.Constant.AMAZON_DATA_CENTER_INFO_CLASS
                    if data_center_name == "Amazon"
                    else constants.Constant.DEFAULT_DATA_CENTER_INFO_CLASS,
                    "name": data_center_name,
                },
                "leaseInfo": {
                    "renewalIntervalInSecs": renewal_interval_in_secs,
                    "durationInSecs": duration_in_secs,
                    "registrationTimestamp": 0,
                    "lastRenewalTimestamp": 0,
                    "evictionTimestamp": 0,
                    "serviceUpTimestamp": 0,
                },
                "metadata": mdata,
                "homePageUrl": EurekaClient.__format_url(
                    home_page_url, self.__instance_host, instance_port
                ),
                "statusPageUrl": EurekaClient.__format_url(
                    status_page_url, self.__instance_host, instance_port, "info"
                ),
                "healthCheckUrl": EurekaClient.__format_url(
                    health_check_url, self.__instance_host, instance_port, "health"
                ),
                "secureHealthCheckUrl": secure_health_check_url,
                "vipAddress": vip_adr if vip_adr != "" else app_name.lower(),
                "secureVipAddress": secure_vip_addr
                if secure_vip_addr != ""
                else app_name.lower(),
                "isCoordinatingDiscoveryServer": str(
                    is_coordinating_discovery_server
                ).lower(),
            }
            if data_center_name == "Amazon":
                self.__instance["dataCenterInfo"]["metadata"] = self.__aws_metadata
        else:
            self.__instance = {}

        # For discovery
        self.__remote_regions = remote_regions if remote_regions is not None else []
        self.__applications: application.Applications
        self.__delta: application.Applications
        self.__ha_strategy = ha_strategy
        self.__ha_cache = {}

        self.__application_mth_lock = RLock()

    def __get_ip_host(self, network):
        ip, host = netint.get_ip_and_host(network)
        if (
            self.__aws_metadata
            and "local-ipv4" in self.__aws_metadata
            and self.__aws_metadata["local-ipv4"]
        ):
            ip = self.__aws_metadata["local-ipv4"]
        if (
            self.__aws_metadata
            and "local-hostname" in self.__aws_metadata
            and self.__aws_metadata["local-hostname"]
        ):
            host = self.__aws_metadata["local-hostname"]
        return ip, host

    def __load_ec2_metadata_dict(self):
        # instance metadata
        amazon_info = AmazonInfo()
        mac = amazon_info.get_ec2_metadata("mac")
        if mac:
            vpc_id = amazon_info.get_ec2_metadata(
                f"network/interfaces/macs/{mac}/vpc-id"
            )
        else:
            vpc_id = ""
        metadata = {
            "instance-id": amazon_info.get_ec2_metadata("instance-id"),
            "ami-id": amazon_info.get_ec2_metadata("ami-id"),
            "instance-type": amazon_info.get_ec2_metadata("instance-type"),
            "local-ipv4": amazon_info.get_ec2_metadata("local-ipv4"),
            "local-hostname": amazon_info.get_ec2_metadata("local-hostname"),
            "availability-zone": amazon_info.get_ec2_metadata(
                "placement/availability-zone", ignore_error=True
            ),
            "public-hostname": amazon_info.get_ec2_metadata(
                "public-hostname", ignore_error=True
            ),
            "public-ipv4": amazon_info.get_ec2_metadata(
                "public-ipv4", ignore_error=True
            ),
            "mac": mac,
            "vpcId": vpc_id,
        }
        # accountId
        doc = amazon_info.get_instance_identity_document()
        if doc and "accountId" in doc:
            metadata["accountId"] = doc["accountId"]
        return metadata

    @property
    def should_register(self) -> bool:
        return self.__should_register

    @property
    def should_discover(self) -> bool:
        return self.__should_discover

    @property
    def zone(self) -> str:
        return self.__eureka_server_conf.zone

    @property
    def applications(self) -> application.Applications:
        if not self.should_discover:
            raise exceptions.DiscoverException(
                "should_discover set to False, no registry is pulled, cannot find any applications."
            )
        with self.__application_mth_lock:
            if self.__applications is None:
                self.__pull_full_registry()
            return self.__applications

    def __try_eureka_server_in_cache(self, fun):
        ok = False
        invalid_keys = []
        for z, url in self.__cache_eureka_url.items():
            try:
                _logger.debug(
                    f"Try to do {fun.__name__} in zone[{z}] using cached url {url}. "
                )
                fun(url)
            except (http_client.HTTPError, http_client.URLError):
                _logger.warn(
                    f"Eureka server [{url}] is down, use next url to try.",
                    exc_info=True,
                )
                invalid_keys.append(z)
            else:
                ok = True
        if invalid_keys:
            _logger.debug(f"Invalid keys::{invalid_keys} will be removed from cache.")
            for z in invalid_keys:
                del self.__cache_eureka_url[z]
        if not ok:
            raise exceptions.EurekaServerConnectionException(
                "All eureka servers in cache are down!"
            )

    def __try_eureka_server_in_zone(self, fun):
        self.__try_eureka_servers_in_list(
            fun, self.__eureka_server_conf.servers_in_zone, self.zone
        )

    def __try_eureka_server_not_in_zone(self, fun):
        for zone, urls in self.__eureka_server_conf.servers_not_in_zone.items():
            try:
                self.__try_eureka_servers_in_list(fun, urls, zone)
            except exceptions.EurekaServerConnectionException:
                _logger.warn(
                    f"try eureka servers in zone[{zone}] error!", exc_info=True
                )
            else:
                return
        raise exceptions.EurekaServerConnectionException(
            "All eureka servers in all zone are down!"
        )

    def __try_eureka_server_regardless_zones(self, fun):
        for zone, urls in self.__eureka_server_conf.servers.items():
            try:
                self.__try_eureka_servers_in_list(fun, urls, zone)
            except exceptions.EurekaServerConnectionException:
                _logger.warn(
                    f"try eureka servers in zone[{zone}] error!", exc_info=True
                )
            else:
                return
        raise exceptions.EurekaServerConnectionException(
            "All eureka servers in all zone are down!"
        )

    def __try_all_eureka_servers(self, fun):
        if self.__prefer_same_zone:
            try:
                self.__try_eureka_server_in_zone(fun)
            except exceptions.EurekaServerConnectionException:
                self.__try_eureka_server_not_in_zone(fun)
        else:
            self.__try_eureka_server_regardless_zones(fun)

    def __try_eureka_servers_in_list(
        self, fun, eureka_servers=[], zone=constants.Constant.DEFAULT_ZONE
    ):
        with self.__net_lock:
            ok = False
            _zone = zone if zone else constants.Constant.DEFAULT_ZONE
            for url in eureka_servers:
                url = url.strip()
                try:
                    _logger.debug(
                        f"try to do {fun.__name__} in zone[{_zone}] using url {url}. "
                    )
                    fun(url)
                except (http_client.HTTPError, http_client.URLError):
                    _logger.warn(
                        f"Eureka server [{url}] is down, use next url to try.",
                        exc_info=True,
                    )
                else:
                    ok = True
                    self.__cache_eureka_url[_zone] = url
                    break

            if not ok:
                if _zone in self.__cache_eureka_url:
                    del self.__cache_eureka_url[_zone]
                raise exceptions.EurekaServerConnectionException(
                    f"All eureka servers in zone[{_zone}] are down!"
                )

    def __connect_to_eureka_server(self, fun):
        if self.__cache_eureka_url:
            try:
                self.__try_eureka_server_in_cache(fun)
            except exceptions.EurekaServerConnectionException:
                self.__try_all_eureka_servers(fun)
        else:
            self.__try_all_eureka_servers(fun)

    @staticmethod
    def __format_url(url, host, port, defalut_ctx=""):
        if url != "":
            if url.startswith("http"):
                _url = url
            elif url.startswith("/"):
                _url = f"http://{host}:{port}{url}"
            else:
                _url = f"http://{host}:{port}/{url}"
        else:
            _url = f"http://{host}:{port}/{defalut_ctx}"
        return _url

    @staticmethod
    def __is_ip(ip_str):
        return re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ip_str)

    @staticmethod
    def __get_instance_ip(eureka_server):
        url_obj = http_client.parse_url(eureka_server)
        target_ip = url_obj["host"]
        target_port = url_obj["port"]
        if target_port is None:
            if url_obj["schema"] == "http":
                target_port = 80
            else:
                target_port = 443

        if url_obj["ipv6"] is not None:
            target_ip = url_obj["ipv6"]
            socket_family = socket.AF_INET6
        else:
            socket_family = socket.AF_INET

        s = socket.socket(socket_family, socket.SOCK_DGRAM)
        s.connect((target_ip, target_port))
        ip = s.getsockname()[0]
        s.close()
        return ip

    def _on_error(self, error_type: str, exception: Exception):
        if self.__on_error_callback and callable(self.__on_error_callback):
            self.__on_error_callback(error_type, exception)

    def register(
        self,
        status: str = constants.InstanceStatus.INSTANCE_STATUS_UP,
        overriddenstatus: str = constants.InstanceStatus.INSTANCE_STATUS_UNKNOWN,
    ) -> None:
        self.__instance["status"] = status
        self.__instance["overriddenstatus"] = overriddenstatus
        self.__instance["lastUpdatedTimestamp"] = str(util.current_time_millis())
        self.__instance["lastDirtyTimestamp"] = str(util.current_time_millis())
        try:

            def do_register(url):
                registry.send_registry(url, self.__instance)

            self.__connect_to_eureka_server(do_register)
        except Exception as e:
            self.__alive = False
            _logger.warn("Register error! Will try in next heartbeat. ", exc_info=True)
            self._on_error(constants.ErrorTypes.ERROR_REGISTER, e)
        else:
            _logger.debug("register successfully!")
            self.__alive = True

    def cancel(self) -> None:
        try:

            def do_cancel(url):
                registry.cancel(
                    url, self.__instance["app"], self.__instance["instanceId"]
                )

            self.__connect_to_eureka_server(do_cancel)
        except Exception as e:
            _logger.warn("Cancel error!", exc_info=True)
            self._on_error(constants.ErrorTypes.ERROR_STATUS_UPDATE, e)
        else:
            self.__alive = False

    def send_heartbeat(self, overridden_status: str = "") -> None:
        if not self.__alive:
            self.register()
            return
        try:
            _logger.debug("sending heartbeat to eureka server. ")

            def do_send_heartbeat(url):
                registry.send_heartbeat(
                    url,
                    self.__instance["app"],
                    self.__instance["instanceId"],
                    self.__instance["lastDirtyTimestamp"],
                    status=self.__instance["status"],
                    overriddenstatus=overridden_status,
                )

            self.__connect_to_eureka_server(do_send_heartbeat)
        except Exception as e:
            _logger.warn(
                "Cannot send heartbeat to server, try to register. ", exc_info=True
            )
            self._on_error(constants.ErrorTypes.ERROR_STATUS_UPDATE, e)
            self.register()

    def status_update(self, new_status: str) -> None:
        self.__instance["status"] = new_status
        try:

            def do_status_update(url):
                registry.status_update(
                    url,
                    self.__instance["app"],
                    self.__instance["instanceId"],
                    self.__instance["lastDirtyTimestamp"],
                    new_status,
                )

            self.__connect_to_eureka_server(do_status_update)
        except Exception as e:
            _logger.warn("update status error!", exc_info=True)
            self._on_error(constants.ErrorTypes.ERROR_STATUS_UPDATE, e)

    def delete_status_override(self) -> None:
        try:
            self.__connect_to_eureka_server(
                lambda url: registry.delete_status_override(
                    url,
                    self.__instance["app"],
                    self.__instance["instanceId"],
                    self.__instance["lastDirtyTimestamp"],
                )
            )
        except Exception as e:
            _logger.warn("delete status overrid error!", exc_info=True)
            self._on_error(constants.ErrorTypes.ERROR_STATUS_UPDATE, e)

    def __start_register(self):
        _logger.debug("start to registry client...")
        self.register()

    def __stop_registery(self):
        if self.__alive:
            self.register(status=constants.InstanceStatus.INSTANCE_STATUS_DOWN)
            self.cancel()

    def __heartbeat(self):
        while True:
            if self.__should_register:
                _logger.debug("sending heartbeat to eureka server ")
                self.send_heartbeat()
            if self.__should_discover:
                _logger.debug("loading services from  eureka server")
                self.__fetch_delta()
            time.sleep(self.__heartbeat_interval)

    def __pull_full_registry(self):
        def do_pull(url):  # the actual function body
            self.__applications = util.get_applications(url, self.__remote_regions)
            self.__delta = self.__applications

        try:
            self.__connect_to_eureka_server(do_pull)
        except Exception as e:
            _logger.warn("pull full registry from eureka server error!", exc_info=True)
            self._on_error(constants.ErrorTypes.ERROR_DISCOVER, e)

    def __fetch_delta(self):
        def do_fetch(url):
            if (
                self.__applications is None
                or len(self.__applications.applications) == 0
            ):
                self.__pull_full_registry()
                return
            delta = util.get_delta(url, self.__remote_regions)
            _logger.debug(f"delta got: v.{delta.versionsDelta}::{delta.appsHashcode}")
            if (
                self.__delta is not None
                and delta.versionsDelta == self.__delta.versionsDelta
                and delta.appsHashcode == self.__delta.appsHashcode
            ):
                return
            self.__merge_delta(delta)
            self.__delta = delta
            if not self.__is_hash_match():
                self.__pull_full_registry()

        try:
            self.__connect_to_eureka_server(do_fetch)
        except Exception as e:
            _logger.warn("fetch delta from eureka server error!", exc_info=True)
            self._on_error(constants.ErrorTypes.ERROR_DISCOVER, e)

    def __is_hash_match(self):
        app_hash = self.__get_applications_hash()
        _logger.debug(
            f"check hash, local[{app_hash}], remote[{self.__delta.appsHashcode}]"
        )
        return app_hash == self.__delta.appsHashcode

    def __merge_delta(self, delta):
        _logger.debug(
            f"merge delta...length of application got from delta::{len(delta.applications)}"
        )
        for application in delta.applications:
            for instance in application.instances:
                _logger.debug(
                    f"instance [{instance.instanceId}] has {instance.actionType}"
                )
                if instance.actionType in (
                    constants.ActionType.ACTION_TYPE_ADDED,
                    constants.ActionType.ACTION_TYPE_MODIFIED,
                ):
                    existingApp = self.applications.get_application(application.name)
                    if existingApp is None:
                        self.applications.add_application(application)
                    else:
                        existingApp.update_instance(instance)
                elif instance.actionType == constants.ActionType.ACTION_TYPE_DELETED:
                    existingApp = self.applications.get_application(application.name)
                    if existingApp is None:
                        self.applications.add_application(application)
                    existingApp.remove_instance(instance)

    def __get_applications_hash(self):
        app_hash = ""
        app_status_count = {}
        for application in self.__applications.applications:
            for instance in application.instances:
                if instance.status not in app_status_count:
                    app_status_count[instance.status.upper()] = 0
                app_status_count[instance.status.upper()] = (
                    app_status_count[instance.status.upper()] + 1
                )

        sorted_app_status_count = sorted(
            app_status_count.items(), key=lambda item: item[0]
        )
        for item in sorted_app_status_count:
            app_hash = f"{app_hash}{item[0]}_{item[1]}_"
        return app_hash

    def walk_nodes_async(
        self,
        app_name: str = "",
        service: str = "",
        prefer_ip: bool = False,
        prefer_https: bool = False,
        walker: Callable = None,
        on_success: Callable = None,
        on_error: Callable = None,
    ) -> None:
        def async_thread_target():
            try:
                res = self.walk_nodes(
                    app_name=app_name,
                    service=service,
                    prefer_ip=prefer_ip,
                    prefer_https=prefer_https,
                    walker=walker,
                )
                if on_success is not None and (
                    inspect.isfunction(on_success) or inspect.ismethod(on_success)
                ):
                    on_success(res)
            except http_client.HTTPError as e:
                if on_error is not None and (
                    inspect.isfunction(on_error) or inspect.ismethod(on_error)
                ):
                    on_error(e)

        async_thread = Thread(target=async_thread_target)
        async_thread.daemon = True
        async_thread.start()

    def walk_nodes(
        self,
        app_name: str = "",
        service: str = "",
        prefer_ip: bool = False,
        prefer_https: bool = False,
        walker: Callable = None,
    ) -> Union[str, Dict, http_client.HTTPResponse]:
        assert (
            app_name is not None and app_name != ""
        ), "application_name should not be null"
        assert inspect.isfunction(walker) or inspect.ismethod(
            walker
        ), "walker must be a method or function"
        error_nodes = []
        app_name = app_name.upper()
        node = self.__get_available_service(app_name)

        while node is not None:
            try:
                url = self.__generate_service_url(node, prefer_ip, prefer_https)
                if service.startswith("/"):
                    url = url + service[1:]
                else:
                    url = url + service
                _logger.debug("do service with url::" + url)
                return walker(url)
            except (http_client.HTTPError, http_client.URLError):
                _logger.warn(
                    f"do service {service} in node [{node.instanceId}] error, use next node."
                )
                error_nodes.append(node.instanceId)
                node = self.__get_available_service(app_name, error_nodes)

        raise http_client.URLError("Try all up instances in registry, but all fail")

    def do_service_async(
        self,
        app_name: str = "",
        service: str = "",
        return_type: str = "string",
        prefer_ip: bool = False,
        prefer_https: bool = False,
        on_success: Callable = None,
        on_error: Callable = None,
        method: str = "GET",
        headers: Dict[str, str] = None,
        data: Union[bytes, str, Dict] = None,
        timeout: float = constants.Constant.DEFAULT_TIME_OUT,
        cafile: str = None,
        capath: str = None,
        cadefault: bool = False,
        context: ssl.SSLContext = None,
    ) -> None:
        def async_thread_target():
            try:
                res = self.do_service(
                    app_name=app_name,
                    service=service,
                    return_type=return_type,
                    prefer_ip=prefer_ip,
                    prefer_https=prefer_https,
                    method=method,
                    headers=headers,
                    data=data,
                    timeout=timeout,
                    cafile=cafile,
                    capath=capath,
                    cadefault=cadefault,
                    context=context,
                )
                if on_success is not None and (
                    inspect.isfunction(on_success) or inspect.ismethod(on_success)
                ):
                    on_success(res)
            except http_client.HTTPError as e:
                if on_error is not None and (
                    inspect.isfunction(on_error) or inspect.ismethod(on_error)
                ):
                    on_error(e)

        async_thread = Thread(target=async_thread_target)
        async_thread.daemon = True
        async_thread.start()

    def do_service(
        self,
        app_name: str = "",
        service: str = "",
        return_type: str = "string",
        prefer_ip: bool = False,
        prefer_https: bool = False,
        method: str = "GET",
        headers: Dict[str, str] = None,
        data: Union[bytes, str, Dict] = None,
        timeout: float = constants.Constant.DEFAULT_TIME_OUT,
        cafile: str = None,
        capath: str = None,
        cadefault: bool = False,
        context: ssl.SSLContext = None,
    ) -> Union[str, Dict, http_client.HTTPResponse]:
        _data: bytes
        if data and isinstance(data, dict):
            _data = json.dumps(data).encode()
        elif data and isinstance(data, str):
            _data = data.encode()
        else:
            _data = data

        def walk_using_urllib(url):
            req = http_client.Request(url, method=method)
            heads = headers if headers is not None else {}
            for k, v in heads.items():
                req.add_header(k, v)

            res_txt, res = http_client.load(
                req,
                data=_data,
                timeout=timeout,
                cafile=cafile,
                capath=capath,
                cadefault=cadefault,
                context=context,
            )
            if return_type.lower() in ("json", "dict", "dictionary"):
                return json.loads(res_txt)
            elif return_type.lower() == "response_object":
                return res
            else:
                return res_txt

        return self.walk_nodes(
            app_name, service, prefer_ip, prefer_https, walk_using_urllib
        )

    def __get_service_not_in_ignore_list(self, instances, ignores):
        ign = ignores if ignores else []
        return [item for item in instances if item.instanceId not in ign]

    def __get_available_service(self, application_name, ignore_instance_ids=None):
        apps = self.applications
        if not apps:
            raise exceptions.DiscoverException(
                "Cannot load registry from eureka server, please check your configurations. "
            )
        app = apps.get_application(application_name)
        if app is None:
            return None
        up_instances = []
        if self.__prefer_same_zone:
            ups_same_zone = app.up_instances_in_zone(self.zone)
            up_instances = self.__get_service_not_in_ignore_list(
                ups_same_zone, ignore_instance_ids
            )
            if not up_instances:
                ups_not_same_zone = app.up_instances_not_in_zone(self.zone)
                _logger.debug(
                    f"app[{application_name}]'s up instances not in same zone are all down, using the one that's not in the same zone: {[ins.instanceId for ins in ups_not_same_zone]}"
                )
                up_instances = self.__get_service_not_in_ignore_list(
                    ups_not_same_zone, ignore_instance_ids
                )
        else:
            up_instances = self.__get_service_not_in_ignore_list(
                app.up_instances, ignore_instance_ids
            )

        if len(up_instances) == 0:
            # no up instances
            return None
        elif len(up_instances) == 1:
            # only one available instance, then doesn't matter which strategy is.
            instance = up_instances[0]
            self.__ha_cache[application_name] = instance.instanceId
            return instance

        def random_one(instances):
            if len(instances) == 1:
                idx = 0
            else:
                idx = random.randint(0, len(instances) - 1)
            selected_instance = instances[idx]
            self.__ha_cache[application_name] = selected_instance.instanceId
            return selected_instance

        if self.__ha_strategy == constants.HAStrategy.HA_STRATEGY_RANDOM:
            return random_one(up_instances)
        elif self.__ha_strategy == constants.HAStrategy.HA_STRATEGY_STICK:
            if application_name in self.__ha_cache:
                cache_id = self.__ha_cache[application_name]
                cahce_instance = app.get_instance(cache_id)
                if (
                    cahce_instance is not None
                    and cahce_instance.status
                    == constants.InstanceStatus.INSTANCE_STATUS_UP
                ):
                    return cahce_instance
                else:
                    return random_one(up_instances)
            else:
                return random_one(up_instances)
        elif self.__ha_strategy == constants.HAStrategy.HA_STRATEGY_OTHER:
            if application_name in self.__ha_cache:
                cache_id = self.__ha_cache[application_name]
                other_instances = []
                for up_instance in up_instances:
                    if up_instance.instanceId != cache_id:
                        other_instances.append(up_instance)
                return random_one(other_instances)
            else:
                return random_one(up_instances)
        else:
            return None

    def __generate_service_url(self, instance, prefer_ip, prefer_https) -> str:
        if instance is None:
            raise exceptions.InstanceDoesNotExistError(
                instance,
                "Could not generate service URL, since instance does not exist!",
            )
        schema = "http"
        port = 0
        if instance.port.port and not instance.securePort.enabled:
            schema = "http"
            port = instance.port.port
        elif not instance.port.port and instance.securePort.enabled:
            schema = "https"
            port = instance.securePort.port
        elif instance.port.port and instance.securePort.enabled:
            if prefer_https:
                schema = "https"
                port = instance.securePort.port
            else:
                schema = "http"
                port = instance.port.port
        else:
            assert False, "generate_service_url error: No port is available"

        host = instance.ipAddr if prefer_ip else instance.hostName

        return f"{schema}://{host}:{port}/"

    def __start_discover(self):
        self.__pull_full_registry()

    def start(self) -> None:
        if self.should_register:
            self.__start_register()
        if self.should_discover:
            self.__start_discover()
        self.__heartbeat_timer.start()

    def stop(self) -> None:
        if self.__heartbeat_timer.is_alive():
            self.__heartbeat_timer.cancel()
        if self.__should_register:
            self.__stop_registery()
