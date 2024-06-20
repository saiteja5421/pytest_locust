import json
from minio import Minio
import urllib3
from lib.common.config.config_manager import ConfigManager


class MinioBuckets:
    def __init__(self) -> None:
        self.config = ConfigManager.get_config()
        self.minio = self.config["MINIO"]
        self.minio_server_name = self.minio["minio_server_host_name"]
        self.mino_server_port = self.minio["minio_server_port"]
        self.minio_access_key = self.minio["minio_access_key"]
        self.minio_secret_key = self.minio["minio_secret_key"]

        self.test_data = self.config[f"TEST-DATA-FOR-USER-ONE"]
        self.proxy = self.test_data["proxy"]
        self.proxy_port = self.test_data["port"]

        self.minio_client = Minio(
            f"{self.minio_server_name}:{ self.mino_server_port}",
            access_key=self.minio_access_key,
            secret_key=self.minio_secret_key,
            secure=True,
            http_client=urllib3.ProxyManager(
                f"{self.proxy}:{self.proxy_port}",
                timeout=urllib3.Timeout.DEFAULT_TIMEOUT,
                cert_reqs="CERT_REQUIRED",
                ca_certs="minio_certs.crt",
                retries=urllib3.Retry(
                    total=5,
                    backoff_factor=0.2,
                    status_forcelist=[500, 502, 503, 504],
                ),
            ),
        )

    def list_all_minio_buckets(self) -> list[str]:
        """
        Returns:
            list[str]: list on minio bucket name
        """
        buckets = self.minio_client.list_buckets()
        buckets_list = []
        for bucket in buckets:
            buckets_list.append(bucket.name)
        return buckets_list

    def make_minio_bucket(self, minio_bucket_name: str) -> None:
        """create minio buckets and returns none
        Args:
            minio_bucket_name (str): name of the minio bucket to be created
        """
        self.minio_client.make_bucket(minio_bucket_name)

    def minio_bucket_exists(self, minio_bucket_name: str) -> bool:
        """check minio bucket exists
        Args:
            minio_bucket_name (str): name of the minio bucket to be check
        Returns:
            bool: true if exists otherwise false
        """
        return self.minio_client.bucket_exists(minio_bucket_name)

    def remove_minio_bucket(self, minio_bucket_name: str) -> None:
        """delete minio buckets and returns none
        Args:
            minio_bucket_name (str): name of the minio bucket to be deleted
        """
        self.minio_client.remove_bucket(minio_bucket_name)

    def set_minio_bucket_policy(self, minio_bucket_name: str, policy_payload: json) -> None:
        """get the json policy payload and replace the "test-api-bucket" with given bucket name and set the policy to bucket
        Args:
            minio_bucket_name (str): name of the minio bucket to be set policy
            policy_payload (json): json policy payload.
        """
        str_policy = json.dumps(policy_payload)
        updated_policy_name = str_policy.replace("test-api-bucket", minio_bucket_name)
        json_policy = json.loads(updated_policy_name)
        self.minio_client.set_bucket_policy(minio_bucket_name, json.dumps(json_policy))

    def get_minio_data_size_on_bucket(self, minio_bucket_name: str) -> float:
        """get the size of the data on the minio bucket
        Args:
            minio_bucket_name (str): name of the minio bucket to be get size
        Returns:
            float: total size in kib
        """
        objects = self.minio_client.list_objects(minio_bucket_name, recursive=True)
        total_obj_size = 0
        for obj in objects:
            obj_size = obj.size
            total_obj_size += obj_size
        total_obj_size_in_kib = total_obj_size / 1024
        return total_obj_size_in_kib
