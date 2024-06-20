import os
from datetime import datetime
import uuid
from lib.common.config.config_manager import ConfigManager
from utils.auth_token import set_atlantia_token, set_token
from lib.common.users.user_model import APIClientCredential


class ApiHeader:
    def __init__(
        self,
        api_credential: APIClientCredential,
        oauth2_server: str = "https://sso.common.cloud.hpe.com/as/token.oauth2",
        static_token=None,
    ):
        self.oauth2_server = oauth2_server
        self.user = api_credential
        self.token = None
        self.token_generate_time = None
        self._authentication_header: dict
        # In dev sandbox (ccs-dev) static token will be used
        self.static_token = static_token

    @property
    def authentication_header(self):
        atlantia_env = os.environ.get("ATLANTIA_ENV")
        if atlantia_env and atlantia_env.lower() == "ccs-dev":
            return self.atlantia_authentication_header
        # token would be static in dev sandbox cluster
        if self.static_token:
            self.token = self.static_token
        elif (self.token is None) or (self.check_token_status(self.token_generate_time) == "Expired"):
            self.token = set_token(self.oauth2_server, self.user.api_client_id, self.user.api_client_secret)
            self.token_generate_time = datetime.now()
        self._authentication_header = {
            "content-type": "application/json",
            "X-Auth-Token": self.token,
            "Authorization": f"Bearer {self.token}",
        }
        return self.set_trace_id(self._authentication_header)

    def set_trace_id(self, headers):
        headers["X-B3-TraceId"] = uuid.uuid4().hex
        headers["X-B3-SpanId"] = uuid.uuid4().hex[:16]
        return headers

    @property
    def atlantia_authentication_header(self):
        # hardcoded token fetched from atlantia_token.json
        # used in functional tests
        return {
            "content-type": "application/json",
            "Authorization": set_atlantia_token(),
        }

    @authentication_header.setter
    def authentication_header(self, value):
        self._authentication_header = value

    def regenerate_header(self):
        """Regenerate header with new token.
        This will be used when token expires (usually in test cases running more than 2 hours)
        """
        self.token = set_token(self.oauth2_server, self.user.api_client_id, self.user.api_client_secret)
        header_with_new_token = {
            "content-type": "application/json",
            "X-Auth-Token": self.token,
            "Authorization": f"Bearer {self.token}",
        }
        return header_with_new_token

    def check_token_status(self, token_time):
        """
        This method checks whether token generated expired or not.
        if token generated more than 2 hours then it returns "Expired" else "Not Expired".
        """
        current_time = datetime.now()
        delta = current_time - token_time
        return "Expired" if (delta.total_seconds() // 3600) >= 2.0 else "Not Expired"


class User(ApiHeader):
    def __init__(
        self, user_tag, oauth2_server: str = "https://sso.common.cloud.hpe.com/as/token.oauth2", static_token=None
    ):
        config = ConfigManager.get_config()
        api_client_cred = APIClientCredential(**config[user_tag])
        super().__init__(api_client_cred, oauth2_server, static_token)
