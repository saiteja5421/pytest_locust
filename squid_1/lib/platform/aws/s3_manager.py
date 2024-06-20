import logging
import os
from io import BytesIO
from typing import Callable

import boto3
from botocore.exceptions import ClientError

from lib.platform.aws.models.instance import Tag
from lib.platform.aws.client_config import ClientConfig

logger = logging.getLogger()


class S3Manager:
    def __init__(
        self, aws_session: Callable[[], boto3.Session], endpoint_url: str = None, client_config: ClientConfig = None
    ):
        self.get_session = aws_session
        self.endpoint_url = endpoint_url
        self.client_config = client_config

    @property
    def s3_resource(self):
        return self.get_session().resource("s3", endpoint_url=self.endpoint_url, config=self.client_config)

    @property
    def s3_client(self):
        return self.get_session().client("s3", endpoint_url=self.endpoint_url, config=self.client_config)

    def get_s3_bucket(self, bucket_name: str):
        return self.s3_resource.Bucket(bucket_name)

    def set_s3_tag(self, bucket_name: str, tags_list: list[Tag]):
        tags_dict = [dict(tag) for tag in tags_list]
        bucket_tagging = self.s3_resource.BucketTagging(bucket_name)

        try:
            s3_tags = bucket_tagging.tag_set
            tags_list = set(map(lambda x: (x["Key"]), tags_dict))
            for tag in s3_tags:
                if tag["Key"] not in tags_list:
                    tags_dict.append(tag)
        except ClientError:
            logger.info("S3 bucket tags do not exist")
        bucket_tagging.put(Tagging={"TagSet": tags_dict})

    def get_s3_bucket_size(self, bucket_name: str) -> int:
        """
        Method to obtain s3 bucket size
        :param bucket_name: name of the bucket that we want to check its size
        :return: sum value of all objects size inside bucket in bytes
        """
        return sum([o.size for o in self.s3_resource.Bucket(bucket_name).objects.all()])

    def get_s3_object_keys(self, bucket_name: str) -> list[str]:
        return [o.key for o in self.s3_resource.Bucket(bucket_name).objects.all()]

    def create_s3_presigned_url(
        self,
        bucket_name: str,
        object_key: str,
        client_method: str = "get_object",
        expires_in: int = 3600,
    ) -> str:
        url = self.s3_client.generate_presigned_url(
            ClientMethod=client_method,
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=expires_in,
        )
        return url

    def empty_or_delete_s3_bucket(self, bucket_name, delete_bucket: bool = False):
        bucket = self.get_s3_bucket(bucket_name)
        if not os.getenv("LOCALSTACK_URL"):
            objects_in_bucket = [o for o in bucket.objects.all()]
            for o in objects_in_bucket:
                response = o.delete()
                assert response["ResponseMetadata"]["HTTPStatusCode"] == 204
        if delete_bucket:
            bucket.delete()

    def get_bucket_object(self, bucket_name: str, key: str):
        response = self.s3_client.get_object(
            Bucket=bucket_name,
            Key=key,
        )
        logger.info(response)
        return response

    def read_bucket_object_data(self, bucket_name: str, key: str) -> BytesIO:
        bucket_object_data = self.get_bucket_object(bucket_name=bucket_name, key=key)
        buffered_data = BytesIO(bucket_object_data["Body"].read())
        logger.info(buffered_data)
        return buffered_data

    def download_object(self, bucket_name: str, s3_filename: str, target_filename: str):
        bucket = self.get_s3_bucket(bucket_name)
        bucket.download_file(s3_filename, target_filename)
        logger.info(f"S3 {bucket_name} file {s3_filename} downloaded.")
