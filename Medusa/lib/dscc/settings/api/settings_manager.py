# Standard libraries
import requests
import logging
from requests import Response

from lib.common.common import get, patch
from lib.common.config.config_manager import ConfigManager
from lib.common.users.user import User
from lib.dscc.tasks.api.tasks import TaskManager

from lib.dscc.settings.payload.patch_settings import PatchSettings
from lib.dscc.settings.models.settings import SettingsList

logger = logging.getLogger()


class SettingsManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlantia_api = config["ATLANTIA-API"]
        self.dscc = config["CLUSTER"]
        #  https://scdev01-app.qa.cds.hpe.com/api/v1
        self.url = f"{self.dscc['atlantia-url']}/api/{self.dscc['version']}"
        self.settings = self.atlantia_api["settings"]

        self.tasks = TaskManager(user)

    # PATCH ../api/v1/settings/1
    def patch_settings(self, setting: int, auth_payload: PatchSettings) -> Response:
        """API to update settings to be enabled/disabled; as of now only Dual Auth Setting is available.
        Args:
            setting (int): setting to be enabled/disabled
            auth_payload (PatchDualAuthSettings): On/OFF of current value

        Returns:
            Response: returns response
        """

        path: str = f"{self.settings}/{setting}"
        payload = auth_payload.to_json()
        response: Response = patch(
            self.url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == requests.codes.accepted, response.content
        return response
        # TODO- retrun taskuri if possible

    # GET /api/v1/settings
    def get_settings(self) -> SettingsList:
        """List describing settings are enabled or disbled

        Returns:
            SettingsList
        """
        path: str = f"{self.settings}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.ok, response.content
        return SettingsList.from_json(response.text)
