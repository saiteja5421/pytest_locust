import logging
import os
import shutil
import requests
from lib.common.config.config_manager import ConfigManager
from requests import codes
from lib.common.common import get
from lib.common.users.user import User

logger = logging.getLogger()


class SoftwareRelease:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlas_api = config["ATLAS-API"]
        self.dscc = config["CLUSTER"]
        self.url = f"{self.dscc['url']}/api/{self.dscc['version']}"
        self.software_releases = "software-releases"
        self.download_url = f"{self.dscc['url']}/software-index/{self.dscc['version']}/downloads"

    def get_all_software_releases(self):
        """This method helps user to get all the available software releases in the catalogue

        Returns:
            response from the software-release API
        """
        response = get(self.url, self.software_releases, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, (
            f"Software Releases not fetched properly got status code: {response.status_code}, and response:"
            f"{response.text}"
        )
        return response

    def get_latest_software_details(self):
        """This method helps user to fetch latest software release details, it uses the sort and filter in the requesting url.

        Returns:
            response from the software-releases API.
        """
        api_string_filter_latest = f"{self.software_releases}?sort=releaseDate desc&limit=1&filter=softwareComponent.name eq 'HPE Backup and Recovery Service Data Orchestrator' and releaseType eq'INSTALL'"
        response = get(self.url, api_string_filter_latest, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, (
            f"Latest Software Releases not fetched properly got status code: {response.status_code}, and response: "
            f"{response.text}"
        )
        return response

    def get_latest_software_id_and_file_name(self):
        """This method returns both id and filename of latest software release.

        Returns:
            id: uuid: Id of the latest software release
            filename: str: .ova filename of the latest software release
        """
        output = self.get_latest_software_details().json()
        return output.get("items")[0].get("id"), output.get("items")[0].get("filename")

    def download_latest_software(self, id, file_name):
        """This method helps user to download the software from the software-releases API POST request.

        Args:
            id (uuid): latest software release id
            file_name (str): latest software .ova file name

        Returns:
            True: This method returns True if there is a successfull download of software, if not method return False
        """
        logger.info(f"Started Downloading Latest Software {file_name} file")
        path_to_download = f"{self.software_releases}/{id}/download"
        try:
            with requests.post(
                url=f"{self.url}/{path_to_download}",
                headers=self.user.authentication_header,
                data="",
                params="",
                json="",
                verify=False,
                auth=None,
                timeout=(20, 20),
                allow_redirects=True,
                stream=True,
            ) as req_download:
                with open(file_name, "wb") as write_file:
                    shutil.copyfileobj(req_download.raw, write_file)
            logger.info(f"Successfully Downloaded and Saved the file {file_name}")
            return True
        except Exception as exp:
            logger.error(f"Exception occured while requesting to download software: {exp}")
