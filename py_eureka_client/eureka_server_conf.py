from copy import copy
from typing import Dict, List
from urllib.parse import quote

from py_eureka_client import constants
from py_eureka_client.__dns_txt_resolver import get_txt_dns_record


class EurekaServerConf(object):
    def __init__(
        self,
        eureka_server=constants.Constant.DEFAULT_EUREKA_SERVER_URL,
        eureka_domain="",
        eureka_protocol="http",
        eureka_basic_auth_user="",
        eureka_basic_auth_password="",
        eureka_context="eureka/v2",
        eureka_availability_zones={},
        region="",
        zone="",
    ):
        self.__servers: Dict = {}
        self.region: str = region
        self.__zone = zone
        self.__eureka_availability_zones = eureka_availability_zones
        _zone = zone if zone else constants.Constant.DEFAULT_ZONE
        if eureka_domain:
            zone_urls = get_txt_dns_record(f"txt.{region}.{eureka_domain}")
            for zone_url in zone_urls:
                zone_name = zone_url.split(".")[0]
                eureka_urls = get_txt_dns_record(f"txt.{zone_url}")
                self.__servers[zone_name] = [
                    self._format_url(
                        eureka_url.strip(),
                        eureka_protocol,
                        eureka_basic_auth_user,
                        eureka_basic_auth_password,
                        eureka_context,
                    )
                    for eureka_url in eureka_urls
                ]
        elif eureka_availability_zones:
            for zone_name, v in eureka_availability_zones.items():
                if isinstance(v, list):
                    eureka_urls = v
                else:
                    eureka_urls = str(v).split(",")
                self.__servers[zone_name] = [
                    self._format_url(
                        eureka_url.strip(),
                        eureka_protocol,
                        eureka_basic_auth_user,
                        eureka_basic_auth_password,
                        eureka_context,
                    )
                    for eureka_url in eureka_urls
                ]
        else:
            self.__servers[_zone] = [
                self._format_url(
                    eureka_url.strip(),
                    eureka_protocol,
                    eureka_basic_auth_user,
                    eureka_basic_auth_password,
                    eureka_context,
                )
                for eureka_url in eureka_server.split(",")
            ]
        self.__servers_not_in_zone = copy(self.__servers)
        if _zone in self.__servers_not_in_zone:
            del self.__servers_not_in_zone[_zone]

    @property
    def zone(self) -> str:
        if self.__zone:
            return self.__zone
        elif self.__eureka_availability_zones:
            return self.__eureka_availability_zones.keys()[0]
        else:
            return constants.Constant.DEFAULT_ZONE

    def _format_url(
        self,
        server_url="",
        eureka_protocol="http",
        eureka_basic_auth_user="",
        eureka_basic_auth_password="",
        eureka_context="eureka/v2",
    ):
        url = server_url
        if url.endswith("/"):
            url = url[0:-1]
        if url.find("://") > 0:
            prtl, url = tuple(url.split("://"))
        else:
            prtl = eureka_protocol

        if url.find("@") > 0:
            basic_auth, url = tuple(url.split("@"))
            if basic_auth.find(":") > 0:
                user, password = tuple(basic_auth.split(":"))
            else:
                user = basic_auth
                password = ""
        else:
            user = quote(eureka_basic_auth_user)
            password = quote(eureka_basic_auth_password)

        basic_auth = ""
        if user:
            if password:
                basic_auth = f"{user}:{password}"
            else:
                basic_auth = user
            basic_auth += "@"

        if url.find("/") > 0:
            ctx = ""
        else:
            ctx = (
                eureka_context
                if eureka_context.startswith("/")
                else "/" + eureka_context
            )

        return f"{prtl}://{basic_auth}{url}{ctx}"

    @property
    def servers(self) -> Dict:
        return self.__servers

    @property
    def servers_in_zone(self) -> List[str]:
        if self.zone in self.servers:
            return self.servers[self.zone]
        else:
            return []

    @property
    def servers_not_in_zone(self) -> Dict[str, str]:
        return self.__servers_not_in_zone
