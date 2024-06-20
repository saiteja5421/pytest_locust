from lib.common.users.user import User
from lib.common.common import get


class Bouncer:
    def __init__(self, user: User):
        self.user = user
        self.endpoint = "bouncer"

    def get_subscription(self, url):
        response = get(url, path=self.endpoint, headers=self.user.authentication_header)
        res_json = response.json()
        return res_json
