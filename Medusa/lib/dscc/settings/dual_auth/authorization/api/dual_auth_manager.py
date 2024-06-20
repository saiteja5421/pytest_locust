# Standard libraries
import requests
import logging
from requests import Response

from lib.common.common import get, patch
from lib.common.config.config_manager import ConfigManager
from lib.common.enums.dual_auth_request import DualAuthSettingValue
from lib.common.users.user import User
from lib.dscc.settings.dual_auth.authorization.models.dual_auth_settings import DualAuthSettings
from lib.dscc.tasks.api.tasks import TaskManager
from lib.dscc.settings.dual_auth.authorization.models.dual_auth_operation import (
    DualAuthOperation,
    DualAuthOperationList,
)
from lib.dscc.settings.dual_auth.authorization.payload.patch_request_approve_deny import (
    PatchRequestApproveDeny,
    UpdateDualAuthSetting,
)

logger = logging.getLogger()


class DualAuthManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlantia_api = config["ATLANTIA-API"]
        self.dscc = config["CLUSTER"]
        #  https://scdev01-app.qa.cds.hpe.com/api/v1
        self.url = f"{self.dscc['atlantia-url']}/api/{self.dscc['version']}"
        self.dual_auth_operations = self.atlantia_api["dual-auth-operations"]
        self.settings = self.atlantia_api["settings"]
        self.tasks = TaskManager(user)

    def update_dual_auth_settings(self, enable: bool = True) -> DualAuthSettings:
        """Toggles DualAuth setting to ON / OFF
        If setting to OFF, another authorized user needs to approve the pending request

        Args:
            enable (bool, optional): Sets DualAuth setting to 'ON' when set to 'True'. Defaults to True.

        Returns:
            DualAuthSettings: DualAuthSettings object
        """
        current_value = DualAuthSettingValue.ON if enable else DualAuthSettingValue.OFF
        update_dual_auth_setting = UpdateDualAuthSetting(current_value=current_value)

        path: str = f"{self.settings}/1"

        response: Response = patch(
            self.url,
            path,
            json_data=update_dual_auth_setting.to_json(),
            headers=self.user.authentication_header,
        )
        assert response.status_code == requests.codes.accepted, response.content
        return DualAuthSettings.from_json(response.text)

    # GET api/v1/dual-auth-operations?filter=state+in+%28%27Pending%27%29
    def get_dual_auth_operations(self, request_state: str = "Pending", filter: str = "") -> DualAuthOperationList:
        """Return requests in Pending state for approval or denial

        Args:
            request_state (str, optional): Valid request_state value ex. Pending
                                    default value 'Pending'
            filter (str, optional): Parameter to filter results based on name and other applicable fields

        Returns:
            DualAuthRequestsList
        """
        pending_operations_filter = f"state eq '{request_state}'"

        if filter:
            pending_operations_filter = f"{pending_operations_filter} and {filter}"

        path: str = f"{self.dual_auth_operations}?filter={pending_operations_filter}"
        response: Response = get(self.url, path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.ok, response.content
        return DualAuthOperationList.from_json(response.text)

    def patch_request_approve_deny(self, id: str, request_payload: PatchRequestApproveDeny) -> DualAuthOperation:
        """Takes action to approve/deny requests which are waiting in Pending state

        Args:
            id (str): request ID
            request_payload (PatchRequestApproveDeny): current value

        Returns:
            DualAuthOperation: Authorized DualAuth request
        """

        path: str = f"{self.dual_auth_operations}/{id}"
        payload = request_payload.to_json()
        response: Response = patch(
            self.url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == requests.codes.ok, response.content
        return DualAuthOperation.from_json(response.text)
