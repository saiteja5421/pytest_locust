import logging
from pytest import fixture, mark
from lib.dscc.backup_recovery.vmware_protection.minio_client.minio_bucket_steps import (
    get_all_minio_bucket,
    create_minio_bucket,
    set_minio_bucket_public_policy,
    delete_minio_bucket,
)
from tests.catalyst_gateway_e2e.test_context import Context


logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context


def test_minio_sample(context):
    minio_bucket_name = context.minio_bucket_name
    get_all_minio_bucket(context)
    create_minio_bucket(context, minio_bucket_name)
    set_minio_bucket_public_policy(context, minio_bucket_name)
    delete_minio_bucket(context, minio_bucket_name)
