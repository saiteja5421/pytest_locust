"""
Test Case:

The following steps iterates across the 5 RDS DBs in db_instance_list - mysql, postgres, mariadb
1. Discovered the existing RDS DB cretaed in the region
2. Adjust the db name and its count to create additional DB as required

"""

# Standard libraries
import logging
from pytest import fixture, mark
from lib.dscc.backup_recovery.aws_protection.common.models.rds_asset_set import RDSAssetSet

# Internal libraries
from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.aws_boto3.aws_factory import AWS
from lib.dscc.backup_recovery.aws_protection.common.models.rds_common_objects import RDSDBEnginesCountsPorts
from lib.common.enums.db_engine import DBEngine
from lib.common.enums.db_port import DBPort

# Steps
from tests.steps.aws_protection.assets.standard_rds_asset_creation_steps import create_rds_standard_assets
from tests.e2e.aws_protection.context import Context
from tests.steps.aws_protection.cloud_account_manager_steps import get_csp_account_by_csp_name

logger = logging.getLogger()


@fixture(scope="module")
def context():
    context = Context()
    yield context

    logger.info(f"\n{'Teardown Start: Context'.center(40, '*')}")

    logger.info(f"\n{'Teardown Complete: Context'.center(40, '*')}")


@mark.order(130)
def test_rds_connect_db_instances(context: Context):
    aws: AWS = context.aws_two
    # NOTE: create_rds_standard_assets() used to call: "get_csp_account_by_csp_name(context, context.aws_one_account_name)".
    # However, this test is using "aws_two" - so we'll get account by name "context.aws_two_account_name"
    aws_account_name = context.aws_two_account_name
    csp_account = get_csp_account_by_csp_name(context, account_name=aws_account_name)

    rds_db_asset_set: RDSAssetSet = create_rds_standard_assets(
        aws=aws,
        context=context,
        csp_account_id=csp_account.id,
        rds_asset_set=context.rds_asset_set_region_one_aws_two,
        tags=[Tag(Key="Standard", Value="Test")],
        any_db_count=0,
        db_engines_counts_ports=[
            RDSDBEnginesCountsPorts(db_engine=DBEngine.POSTGRES, db_count=2, db_port=DBPort.POSTGRES.value),
            RDSDBEnginesCountsPorts(db_engine=DBEngine.MARIADB, db_count=3, db_port=DBPort.MARIADB.value),
            RDSDBEnginesCountsPorts(db_engine=DBEngine.ORACLE_EE, db_count=2, db_port=DBPort.ORACLE.value),
            RDSDBEnginesCountsPorts(db_engine=DBEngine.ORACLE_SE2_CDB, db_count=1, db_port=DBPort.ORACLE.value),
            RDSDBEnginesCountsPorts(db_engine=DBEngine.SQLSERVER_EX, db_count=1, db_port=DBPort.SQLSERVER.value),
        ],
    )
    if rds_db_asset_set.rds_db_connection_list:
        logger.info(f"Count of RDS DBs: {len(rds_db_asset_set.rds_db_connection_list)}")
        for rds_db_connection in rds_db_asset_set.rds_db_connection_list:
            logger.info(f"RDS DB ID: {rds_db_connection.rds_instance_identifier}")
    else:
        logger.info(f" list of RDS DBs are empty {rds_db_asset_set.rds_db_connection_list}")
