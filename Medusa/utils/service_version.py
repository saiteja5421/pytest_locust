import logging
from requests import get, codes
from lib.common.config.config_manager import ConfigManager

logger = logging.getLogger()


class ServiceVersion:
    """Class ServiceVersion and its methods are used to fetch microservice
    version details from sc-info portal and log version details everytime
    the main context is initialized.
    """

    def __init__(self):
        self.services: list = [
            "csp-dataprotection",
            "csp-inventory",
            "csp-rds-inventory-manager",
            "csp-scheduler",
            "cloud-account-manager",
            "atlas-ui",
            "atlas-template-api",
            "cvsa-manager",
            "subscription",
            "tasks",
            "authz",
            "shell",
            "atlas-reports-api",
        ]
        self.clusters: dict = {
            "scdev01": "scdev01-us-west-2",
            "filepoc": "filepoc-us-west-2",
            "scint": "scint-us-west-2",
            "eu1": "scprodeu-eu-central-1",
            "jp1": "scprodjp-ap-northeast-1",
            "us1": "scprodus-us-west-2",
        }
        config = ConfigManager.get_config()
        self.dscc = config["CLUSTER"]
        self.sc_info = config["SERVICE-VERSION"]
        self.cluster = [cluster for cluster in list(self.clusters.keys()) if cluster in self.dscc["atlantia-url"]]
        self.cluster = self.clusters.get(self.cluster[-1] if self.cluster else "scdev01")
        self.url = self.sc_info["url"]
        self.sort_by = '{"sortKey":"run_on","sortDir":"desc","sortColumn":"run_on"}'
        self.filters = '[{"columnName":"application","type":"search","value":"%s"},{"columnName":"cluster","type":"search","value":"%s"}]'
        self.pagination = '{"startRow":0,"endRow":1}'

    def get_current_version(self, cluster: str, service: str, return_string: bool = False) -> dict:
        filters = self.filters % (service, cluster)
        path = f"{self.url}?=&sortBy={self.sort_by}&filters={filters}&pagination={self.pagination}"
        response = get(url=path, headers={})
        if response.status_code == codes.ok:
            version_details = response.json()
            if len(version_details["dbObjects"]) == 1:
                if return_string:
                    return version_details["dbObjects"][0]["version"]
                else:
                    return {service: version_details["dbObjects"][0]["version"]}
        else:
            return

    def log_all_atlantia_services_version_info(self):
        logger.info(f"****** Atlantia MicroService Version Details - {self.cluster.upper()} ******\n")
        logger.info("Note: Sometimes the version info captured here may not be the current version")
        logger.info("this is the current limitation of the sc-info dashboard.")
        for service in self.services:
            version = self.get_current_version(cluster=self.cluster, service=service)
            if version:
                logger.info(f"{service.upper()}: {version[service]}\n")
            else:
                logger.warning(f"Unable to retrieve version info for service - {service}. Moving forward...\n")
                continue
