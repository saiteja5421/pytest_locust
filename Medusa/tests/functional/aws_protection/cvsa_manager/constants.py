import logging
from functools import cache
from os import getenv
from typing import Tuple, List

import grpc
from storage_proto.cloudobjectstores.v1 import service_pb2_grpc

from lib.common.enums.aws_region_zone import AWSRegionZone
from lib.common.enums.cvsa import AwsRegions
from lib.platform.vault import VaultManager

logger = logging.getLogger()

regions = {
    # US Regions
    "us-east-1": AwsRegions.AWS_US_EAST_1,
    "us-east-2": AwsRegions.AWS_US_EAST_2,
    "us-west-1": AwsRegions.AWS_US_WEST_1,
    "us-west-2": AwsRegions.AWS_US_WEST_2,
    # EU Regions
    "eu-central-1": AwsRegions.AWS_EU_CENTRAL_1,
    "eu-west-1": AwsRegions.AWS_EU_WEST_1,
    "eu-west-2": AwsRegions.AWS_EU_WEST_2,
    "eu-west-3": AwsRegions.AWS_EU_WEST_3,
    "eu-north-1": AwsRegions.AWS_EU_NORTH_1,
    # CA Regions
    "ca-central-1": AwsRegions.AWS_CA_CENTRAL_1,
    # AP Regions
    "ap-northeast-1": AwsRegions.AWS_AP_NORTHEAST_1,
    "ap-northeast-2": AwsRegions.AWS_AP_NORTHEAST_2,
    "ap-northeast-3": AwsRegions.AWS_AP_NORTHEAST_3,
    "ap-southeast-1": AwsRegions.AWS_AP_SOUTHEAST_1,
    "ap-southeast-2": AwsRegions.AWS_AP_SOUTHEAST_2,
    "ap-south-1": AwsRegions.AWS_AP_SOUTH_1,
    # ME Regions
    "me-south-1": AwsRegions.AWS_ME_SOUTH_1,
}

AWS_REGION_1_NAME = getenv("AWS_REGION_ONE", AWSRegionZone.EU_WEST_1.value)
AWS_REGION_1_ENUM = regions.get(AWS_REGION_1_NAME)

logger.info(f"Selected region for AWS_REGION_1: {AWS_REGION_1_NAME} - {AWS_REGION_1_ENUM}")
CVSA_APPLICATION_CUSTOMER_ID = getenv("CVSA_APPLICATION_CUSTOMER_ID", None)
if CVSA_APPLICATION_CUSTOMER_ID:
    CVSA_APPLICATION_CUSTOMER_ID = bytes(CVSA_APPLICATION_CUSTOMER_ID, "utf-8")
    logger.warning(f"Application Customer ID is predefined: {CVSA_APPLICATION_CUSTOMER_ID} - use with caution!")

USER_BYTES_EXPECTED = 696_254_720  # expected for default snapshot backup
CVSA_MANAGER_GRPC_ADDR = getenv("CVSA_MANAGER_GRPC_ADDR", "localhost:5401")
CLOUD_OBJECTSTORE_ADDR = getenv("CLOUD_OBJECTSTORE_ADDR")


@cache
def get_grpc_insecure_channel():
    return grpc.insecure_channel(CVSA_MANAGER_GRPC_ADDR)


@cache
def get_grpc_insecure_channel_cosm():
    assert CLOUD_OBJECTSTORE_ADDR is not None, "Value of env var CLOUD_OBJECTSTORE_ADDR is None"
    return grpc.insecure_channel(CLOUD_OBJECTSTORE_ADDR)


@cache
def get_cvsa_manager_grpc_token() -> str:
    auth_token = getenv("CVSA_MANAGER_GRPC_AUTH_TOKEN", "")
    if auth_token != "":
        return auth_token

    try:
        vm = VaultManager()
        secret = vm.get_secret("/storagecentral/app/atlantia/cvsa-manager")
        assert secret.status_code == 200, secret.json()
        auth_token = secret.json()["data"]["grpcAuthHardcodedToken"]
    except Exception as e:
        logger.warning(f"cVSA Manager gRPC Token could not be fetched from Vault: {e}")
        raise e

    return auth_token


@cache
def get_grpc_cloud_object_store_service_stub():
    return service_pb2_grpc.CloudObjectStoreManagerServiceStub(channel=get_grpc_insecure_channel_cosm())


@cache
def get_cvsa_manager_grpc_metadata() -> List[Tuple[str, str]]:
    auth_token = get_cvsa_manager_grpc_token()
    return [
        ("authorization", auth_token),
    ]


@cache
def get_azure_resource_group_name() -> str:
    cluster_name = getenv("CLUSTER_NAME")
    cluster_region = getenv("CLUSTER_REGION")
    if cluster_region and cluster_name:
        return f"atlantia-cvsa-manager-{cluster_name}-{cluster_region}"
    else:
        return "atlantia-cvsa-manager-devel"


@cache
def get_azure_gallery_name() -> str:
    env = get_azure_resource_group_name().replace("-", "")
    return f"sig{env}"
