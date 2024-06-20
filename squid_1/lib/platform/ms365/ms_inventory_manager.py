import logging
from tests.ms365.config import MS365Paths
from common import helpers
import requests
from lib.platform.ms365.models.csp_ms_users import MS365CSPUserList
from requests import Response

logger = logging.getLogger(__name__)
headers = helpers.gen_token()
proxies = helpers.set_proxy()


class MSInventoryManager:
    def __init__(self):
        config = helpers.read_config()

    def get_ms365_csp_users_list(
        limit: int = 20,
        offset: int = 0,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> MS365CSPUserList:
        url = f"{helpers.get_locust_host()}{MS365Paths.LIST_MS365_CSP_USERS}"
        path: str = f"{url}?offset={offset}&limit={limit}&sort={sort}"
        if filter:
            path += f"&filter={filter}"
        response = requests.request("GET", path, headers=headers.authentication_header)
        logger.info(response)
        if response.status_code == expected_status_code:
            logger.debug(f"response from get_ms365_csp_users_list: {response.text}")
            return MS365CSPUserList.from_json(response.text)
        else:
            logger.error(response.text)
