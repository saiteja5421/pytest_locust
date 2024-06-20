from lib.common.config.config_manager import ConfigManager
from lib.common.common import delete, get
from lib.common.users.user import User


class OPE:
    """
    This class contains following functions that can be performed
    from the Atlas UI for App Data Management Engines in Data Services Cloud Console (DSCC)
    """

    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlas_api = config["ATLAS-API"]
        self.dscc = config["CLUSTER"]
        self.backup_recovery = self.atlas_api["backup_recovery"]
        self.url = f"{self.dscc['url']}/{self.backup_recovery}/{self.dscc['beta-version']}"
        self.ope = self.atlas_api["ope"]

    def get_all_ope(self):
        return get(self.url, self.ope, headers=self.user.authentication_header)

    def get_ope(self, ope_id: str):
        return get(self.url, f"{self.ope}/{ope_id}", headers=self.user.authentication_header)

    def delete_ope(self, ope_id: str):
        return delete(self.url, f"{self.ope}/{ope_id}", headers=self.user.authentication_header)
