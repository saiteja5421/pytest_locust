from typing import Callable

import boto3
from lib.platform.aws_boto3.client_config import ClientConfig


class STSManager:
    def __init__(
        self, aws_session: Callable[[], boto3.Session], endpoint_url: str = None, client_config: ClientConfig = None
    ):
        self.get_session = aws_session
        self.endpoint_url = endpoint_url
        self.client_config = client_config

    @property
    def sts_client(self):
        return self.get_session().client("sts", endpoint_url=self.endpoint_url, config=self.client_config)

    def get_caller_identity(self):
        return self.sts_client.get_caller_identity()["Account"]
