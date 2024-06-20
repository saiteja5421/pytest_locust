import os

from configparser import ConfigParser

from botocore.config import Config

from lib.common.config.config_manager import ConfigManager

# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html

CONFIG: ConfigParser = ConfigManager.get_config()

# Let's not add proxy definitions if we're running localstack
LOCAL_STACK: bool = True if os.getenv("LOCALSTACK_URL") else False

# build proxy definitions
PROXY_DEFINITIONS: dict[str, str] = {
    "http": CONFIG["PROXY"]["proxy_uri"],
    "https": CONFIG["PROXY"]["proxy_uri"],
}

SIGNATURE_VERSION: str = CONFIG["AWS-CLIENT-CONFIG"]["signature-version"]
MAX_RETRIES: int = int(CONFIG["AWS-CLIENT-CONFIG"]["retry-max-attempts"])
RETRY_MODE: str = CONFIG["AWS-CLIENT-CONFIG"]["retry-mode"]


class ClientConfig:
    def __init__(self, region_name: str):
        self.client_config = Config(
            region_name=region_name,
            signature_version=SIGNATURE_VERSION,
            retries={"max_attempts": MAX_RETRIES, "mode": RETRY_MODE},
            proxies=PROXY_DEFINITIONS if not LOCAL_STACK else None,
        )
