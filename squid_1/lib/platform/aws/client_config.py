import os

from configparser import ConfigParser

from botocore.config import Config

from common.config.config_manager import ConfigManager

# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html

CONFIG = ConfigManager.get_config()

# Let's not add proxy definitions if we're running localstack
LOCAL_STACK: bool = True if os.getenv("LOCALSTACK_URL") else False

# build proxy definitions
PROXY_DEFINITIONS: dict[str, str] = {
    "http": CONFIG["proxy"]["proxy_uri"],
    "https": CONFIG["proxy"]["proxy_uri"],
}

SIGNATURE_VERSION: str = CONFIG["aws_client_config"]["signature-version"]
MAX_RETRIES: int = int(CONFIG["aws_client_config"]["retry-max-attempts"])
RETRY_MODE: str = CONFIG["aws_client_config"]["retry-mode"]


class ClientConfig:
    def __init__(self, region_name: str):
        self.client_config = Config(
            region_name=region_name,
            signature_version=SIGNATURE_VERSION,
            retries={"max_attempts": MAX_RETRIES, "mode": RETRY_MODE},
            proxies=PROXY_DEFINITIONS if not LOCAL_STACK else None,
        )
