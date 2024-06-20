import json
import logging
from oauthlib.oauth2 import BackendApplicationClient
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session
from tenacity import retry, stop_after_attempt, wait_fixed
from waiting import wait, TimeoutExpired
from lib.common.common import raise_my_exception, is_retry_needed

logger = logging.getLogger()


@retry(
    retry=is_retry_needed,
    stop=stop_after_attempt(3),
    wait=wait_fixed(5),
    retry_error_callback=raise_my_exception,
)
def set_token(oauth2_server, client_id, client_secret):
    def _get_jwt():
        oauth = OAuth2Session(client=BackendApplicationClient(client_id))
        auth = HTTPBasicAuth(client_id, client_secret)
        token = oauth.fetch_token(token_url=oauth2_server, auth=auth)
        if token.get("access_token"):
            return token.get("access_token")

    try:
        return wait(_get_jwt, timeout_seconds=60, sleep_seconds=10)
    except TimeoutExpired:
        raise Exception("Failed to fetch auth token")


def set_atlantia_token() -> str:
    """
    This is a static token given by the DEV team.
    We will update this method once we have the mechanism to generate the token.
    """
    token: str = ""
    with open("tests/atlantia_token.json", "r") as file:
        data = json.load(file)
        token = data["Authorization"]

    return token
