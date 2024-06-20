from dataclasses import dataclass
from lib.common.config.config_manager import ConfigManager
from lib.common.enums.provided_users import ProvidedUser
from lib.common.users.user import User


@dataclass
class CommonContext:
    def __init__(self, test_provided_user=ProvidedUser.user_one):
        self.config = ConfigManager.get_config()
        self.user: User = User(user_tag=test_provided_user.value, oauth2_server=self.config["CLUSTER"]["oauth2_server"])
