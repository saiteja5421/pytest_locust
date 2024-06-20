import requests
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
from tests.aws.config import RDSPaths
from common import helpers
from lib.platform.aws.rds_manager import RDSManager
from common.enums.aws_availability_zone import AWSAvailabilityZone
from common import common
from lib.dscc.backup_recovery.aws_protection.rds.models.csp_rds_instance import (
    CSPRDSInstance,
    CSPRDSInstanceList,
)

logger = logging.getLogger(__name__)
headers = helpers.gen_token()


@retry(
    retry=common.is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def get_csp_rds_instances():
    url = f"{helpers.get_locust_host()}{RDSPaths.CSP_RDS_INSTANCES}"

    response = requests.request("GET", url, headers=headers.authentication_header)
    log_data = f"Get csp rds instance-> response code:: {response.status_code} and response text::{response.text}"

    if response.status_code == requests.codes.ok:
        logger.info(log_data)
        logger.info(f"Response = {response.json()}")
        return CSPRDSInstanceList.from_json(response.text)
    else:
        logger.error(log_data)
        return None


def get_csp_rds_instance_using_db_identifier(
    db_identifier: str,
    region: str,
    state: str = "OK",
) -> CSPRDSInstance:
    """_summary_

    Args:
        db_identifier (str): User defined name for the RDS instance in AWS console
        region (str): Region of the DB Instance
        state (str): State of the backup. Defaults to OK

    Returns:
        CSPRDSInstance: The csp rds instance object for the given db identifier.
    """
    rds_instances: CSPRDSInstanceList = get_csp_rds_instances()

    csp_rds_instances = list(
        filter(
            lambda csp_rds_instance: (
                (csp_rds_instance.csp_info.identifier == db_identifier)
                and (csp_rds_instance.csp_info.csp_region == region)
                and (csp_rds_instance.state == state)
            ),
            rds_instances.items,
        )
    )

    logger.info(f"CSP RDS Instance with identifier {db_identifier} in region {region} is {csp_rds_instances[0]}")
    return csp_rds_instances[0]


def create_rds_instance(db_name, db_identifier):

    config = helpers.read_config()
    rds = RDSManager(aws_config=config["testbed"]["AWS"])
    master_user_name, master_user_password = helpers.get_rds_db_master_username_password()

    db_instance = rds.create_db_instance(
        db_name=db_name,
        db_instance_identifier=db_identifier,
        availability_zone=AWSAvailabilityZone.US_WEST_1A,
        allocated_storage=5,
        tags=[{"Key": "AtlantiaPSRRDSTest", "Value": "PSRTest"}],
        master_username=master_user_name,
        master_user_password=master_user_password,
    )
    return db_instance
