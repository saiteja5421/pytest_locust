import logging
from typing import Callable

import boto3
import botocore.exceptions as BotoException
from lib.platform.aws.client_config import ClientConfig

logger = logging.getLogger()


class KMSManager:
    def __init__(
        self, aws_session: Callable[[], boto3.Session], endpoint_url: str = None, client_config: ClientConfig = None
    ):
        self.get_session = aws_session
        self.endpoint_url = endpoint_url
        self.client_config = client_config

    @property
    def kms_client(self):
        return self.get_session().client("kms", endpoint_url=self.endpoint_url, config=self.client_config)

    def create_key(
        self,
        key_policy: str = "",
        description: str = "",
        key_usage: str = "ENCRYPT_DECRYPT",
        key_spec: str = "SYMMETRIC_DEFAULT",
        origin: str = "AWS_KMS",
        multi_region: bool = False,
    ) -> dict:
        """Create a KMS Key

        Args:
            key_policy (str, optional): Policy for the KMS key. Determines who can access the key and what permissions are given. Defaults to "".
            description (str, optional): Description of the KMS key. Defaults to "".
            key_usage (str, optional): Cryptographic operations that you can use the key for. Defaults to "ENCRYPT_DECRYPT".
            key_spec (str, optional): Specifies what type of KMS key to create. Can be asymmetric or symmetric. Defaults to "SYMMETRIC_DEFAULT", which creates a KMS key with a 256-bit AES-GCM key
            origin (str, optional): The source of the key material for the KMS key. Cannot change the origin after creating the key. Defaults to "AWS_KMS".
            multi_region (bool, optional): Allows you to replicate the key in different regions. Value cannot be changes after creation. Defaults to False.

        Returns:
            dict: The Response object from AWS
        """
        key_response = self.kms_client.create_key(
            Policy=key_policy,
            Description=description,
            KeyUsage=key_usage,
            KeySpec=key_spec,
            Origin=origin,
            MultiRegion=multi_region,
        )
        logger.info(f"Created key {key_response}")
        return key_response

    def get_key_id_from_key_response(self, key_response: dict) -> str:
        """Get the KeyId value from the AWS KMS Response object

        Args:
            key_response (dict): AWS KMS Response object

        Returns:
            str: The KeyId value from the Response object
        """
        key_id = key_response["KeyMetadata"]["KeyId"]
        return key_id

    def schedule_key_deletion(self, kms_key_id: str) -> dict:
        """Schedule a deletion of the KMS KeyID

        Args:
            kms_key_id (str): The KMS Key ID

        Returns:
            dict: The Response object from AWS, or None if the KMS KeyId is not found
        """
        try:
            # PendingWindowInDays values allowed: 7-30
            response = self.kms_client.schedule_key_deletion(KeyId=kms_key_id, PendingWindowInDays=7)
            logger.info(f"Deletion scheduled: {response}")
            return response
        except BotoException.NotFoundException:
            logger.info(f"KMS Key Not Found: {kms_key_id}")
