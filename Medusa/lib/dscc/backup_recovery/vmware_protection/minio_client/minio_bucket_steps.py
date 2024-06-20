from lib.dscc.backup_recovery.vmware_protection.minio_client.minio_bucket_policy import public_bucket_policy_payload
from tests.catalyst_gateway_e2e.test_context import Context
import logging


logger = logging.getLogger()


def get_all_minio_bucket(context: Context) -> list[str]:
    """
    Args:
        context (Context): test_context
    Returns:
        list[str]: buckets name or None(if empty)
    """
    minio_client = context.minio_client
    bucket_lists = minio_client.list_all_minio_buckets()
    if bucket_lists != []:
        return bucket_lists
    else:
        return None


def create_minio_bucket(context, minio_bucket_name) -> None:
    """
    Args:
        context (Context): test_context
        minio_bucket_name (str): name of the bucket to be created
    """
    minio_client = context.minio_client
    minio_client.make_minio_bucket(minio_bucket_name)
    bucket_exists = minio_client.minio_bucket_exists(minio_bucket_name)
    assert bucket_exists, f"failed to create minio bucket : {minio_bucket_name}"
    logger.info(f"minio bucket : {minio_bucket_name} created successfully")


def delete_minio_bucket(context, minio_bucket_name) -> None:
    """
    Args:
        context (Context): test_context
        minio_bucket_name (str): name of the bucket to be deleted
    """
    minio_client = context.minio_client
    minio_client.remove_minio_bucket(minio_bucket_name)
    bucket_exists = minio_client.minio_bucket_exists(minio_bucket_name)
    assert bucket_exists == False, f"failed to delete minio bucket : {minio_bucket_name}"
    logger.info(f"minio bucket : {minio_bucket_name} deleted successfully")


def set_minio_bucket_public_policy(context, minio_bucket_name) -> None:
    """
    sets the public access policy to the bucket from the json payload
    Args:
        context (Context): test_context
        minio_bucket_name (str): name of the bucket to set policy
    """
    minio_client = context.minio_client
    try:
        minio_client.set_minio_bucket_policy(minio_bucket_name, public_bucket_policy_payload)
    except Exception as e:
        logger.error(f"set minio bucket policy error: {e}")
