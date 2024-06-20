import time
import traceback
from lib.dscc.backup_recovery.protection import protection_policy, protection_job
from lib.dscc.backup_recovery.aws_protection.ec2 import ec2
import requests
from common import helpers
from common.helpers import squid_is_retry_needed
from tests.aws.config import Paths
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
from common import common

logger = logging.getLogger(__name__)
headers = helpers.gen_token()
proxies = helpers.set_proxy()


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def get_all_csp_machine_instance_backups(csp_machine_id):
    """Returns all csp machine instance backups"""

    url = f"{helpers.get_locust_host()}{Paths.CSP_MACHINE_INSTANCE_BACKUPS}?filter=assetInfo/id eq '{csp_machine_id}'"
    logger.info(url)

    response = requests.request("GET", url, headers=headers.authentication_header)
    logger.info(response)
    if response.status_code == requests.codes.ok:
        response_data = response.json()
        logger.info(f"Response data::{response_data}")
        return response_data
    else:
        logger.error(response.text)


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def get_all_csp_volume_backups(csp_volume_id):
    """Returns all csp volume backups"""
    url = f"{helpers.get_locust_host()}{Paths.CSP_VOLUME_BACKUPS}?filter=assetInfo/id eq '{csp_volume_id}'"
    logger.info(url)

    response = requests.request("GET", url, headers=headers.authentication_header)
    logger.info(response)
    if response.status_code == requests.codes.ok:
        response_data = response.json()
        logger.info(f"Response data::{response_data}")
        return response_data
    else:
        logger.error(response.text)


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def create_csp_machine_instance_backup(ec2_instance_id, timeout_minutes=15, sleep_seconds=10):
    """Creates backup for csp machine instance"""
    try:
        protection_policy_resp_data = protection_policy.create_protection_policy(backup_only=True)
        protection_policy_id, protection_policy_name, protections_id = (
            protection_policy_resp_data["id"],
            protection_policy_resp_data["name"],
            protection_policy_resp_data["protections"][0]["id"],
        )
        csp_machine_id = _get_csp_machine_id(ec2_instance_id)
        protection_job.create_protection_job(
            asset_id=csp_machine_id, protection_policy_id=protection_policy_id, protections_id_one=protections_id
        )
        protection_job_id = _backup_ec2_instance(protection_policy_name, csp_machine_id, timeout_minutes, sleep_seconds)

        return protection_policy_id, protection_job_id
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        logger.error(f"Error while creating backup for ec2 instance {ec2_instance_id}:: {e}")
        logger.error(traceback.format_exc())
        raise Exception(f"Error while creating backup for ec2 instance {ec2_instance_id}:: {e}")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def create_csp_machine_instance_backup_for_given_protection_policy(
    ec2_instance_id, protection_policy_id, protection_policy_name, protections_id, timeout_minutes=15, sleep_seconds=10
):
    """Creates backup for csp machine instance for provided protection policy"""
    try:
        csp_machine_id = _get_csp_machine_id(ec2_instance_id)
        protection_job.create_protection_job(
            asset_id=csp_machine_id, protection_policy_id=protection_policy_id, protections_id_one=protections_id
        )
        protection_job_id = _backup_ec2_instance(protection_policy_name, csp_machine_id, timeout_minutes, sleep_seconds)

        return protection_policy_id, protection_job_id
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        logger.error(f"Error while creating backup for ec2 instance {ec2_instance_id}:: {e}")
        logger.error(traceback.format_exc())
        raise Exception(f"Error while creating backup for ec2 instance {ec2_instance_id}:: {e}")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def _backup_ec2_instance(protection_policy_name, csp_machine_id, timeout_minutes, sleep_seconds):
    protection_job_id = protection_job.get_protection_job_id(csp_machine_id)

    if not protection_job_id:
        raise Exception(
            f"Protection job id is not found. csp machine id is {csp_machine_id} and Protection policy is {protection_policy_name} "
        )

    response = protection_job.run_protection_job(protection_job_id)
    task_uri = response.headers["location"]
    logger.info(f"[_backup_ec2_instance]Task uri while creating ec2 backup:{task_uri}")
    task_status = helpers.wait_for_task(task_uri=task_uri, timeout_minutes=15)
    if task_status == helpers.TaskStatus.success:
        wait_for_backup_creation(csp_machine_id, timeout_minutes, sleep_seconds)
    elif task_status == helpers.TaskStatus.timeout:
        raise Exception("Backup failed with timeout error")
    elif task_status == helpers.TaskStatus.failure:
        raise Exception(f"Backup failed with status'FAILED' error")
    else:
        raise Exception(f"Create backup failed in wait_for_task, taskuri: {task_uri} , taskstatus: {task_status}")
    logger.info(f"Backup tasks status is {task_status}")
    return protection_job_id


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def wait_for_backup_creation(csp_machine_id: str, timeout_minutes: int, sleep_seconds: int) -> dict:
    """Wait for backup to be created. When backup is created state will be OK.
    When it is initiated the state would be 'starting'

    Args:
        csp_machine_id (_type_): CSP Machine id (EC2 machine discovered in atlas)
        timeout_minutes (_type_): Wait time in minutes
        sleep_seconds (_type_): sleep time in seconds

    Raises:
        Exception: If backup not created even after timeout minutes exception will be raised

    Returns:
        dict: backup dict response of recently created
    """
    timeout = (timeout_minutes * 60) / sleep_seconds

    while timeout:
        recent_backup = get_recent_backup(csp_machine_id)
        if recent_backup != None:
            recent_backup_id = recent_backup["id"]
            backup_dict = get_backup_detail(csp_machine_id, recent_backup_id)
            if backup_dict["state"] == "OK":
                logger.info(f"Backup is created successfully")
                return backup_dict
            else:
                time.sleep(sleep_seconds)
        else:
            time.sleep(sleep_seconds)
        timeout = timeout - 1

    raise Exception(f"Backup is not created even after {timeout_minutes} minutes")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def get_backup_detail(csp_machine_id, backup_id) -> dict:
    """for the given csp machine get the backup detail

    Args:
        csp_machine_id (_type_): Id of EC2 machine discovered in Atlas
        backup_id (_type_): Backup Id

    Raises:
        Exception: If get backup REST call fails throw exception

    Returns:
        dict: response.json() dict of backup
    """

    url = f"{helpers.get_locust_host()}{Paths.CSP_MACHINE_INSTANCE_BACKUPS}/{backup_id}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    logger.info(f"Get backups-Response code is {response.status_code}")
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    if response.status_code != requests.codes.ok:
        raise Exception(f"[get_backup_detail] -> Unable to get backup detail for csp id {csp_machine_id} {backup_id}")
    response_data = response.json()
    logger.info(f"backup detail", response_data)
    return response_data


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def get_recent_backup(csp_machine_id) -> dict:
    """Get recent HPE Local backup for given csp machine"""

    logger.info(f"Wait till the backup is created")

    url = f"{helpers.get_locust_host()}{Paths.CSP_MACHINE_INSTANCE_BACKUPS}?filter=assetInfo/id eq '{csp_machine_id}'"
    response = requests.request("GET", url, headers=headers.authentication_header)
    logger.info(f"Recent backup response {response}")
    logger.info(f"Get backups-Response code is {response.status_code}")
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    if response.status_code != requests.codes.ok:
        raise Exception(
            f"[get_recent_backup] -> Unable to get backup list. backup response is {response.text}. Status code is {response.status_code}"
        )

    response_data = response.json()
    logger.debug(f"backup list {response_data}")
    backup_count = len(response_data["items"])
    if backup_count != 0:
        recent_backup = response_data["items"][backup_count - 1]
        logger.info(f"recent backup is  {recent_backup}")
        return recent_backup


def _apply_protection_policy(csp_machine_id, protection_policy_id, protections_id):
    # From EC2 Instance get the csp machine id (CSP Machine idwhich is atlas way of maintaining EC2)
    try:
        # This will apply protection policy to EC2 Instance
        protection_job.create_protection_job(csp_machine_id, protections_id, protection_policy_id)
    except Exception:
        raise Exception("Failed to apply protection policy")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def _get_csp_machine_id(ec2_instance_id):
    csp_machine_dict = ec2.get_csp_machine(ec2_instance_id)
    csp_machine_id = csp_machine_dict["id"]
    return csp_machine_id


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def delete_csp_machine_instance_backup(csp_instance_id: str, backup_id: str, wait_for_task: bool = False) -> dict:
    """Deletes backup of csp machine instance
    Raises:
        Exception: Refresh inventory Task timeout error
        Exception: Refresh inventory Task status "FAILED" error
        Exception: Refresh inventory unknown error

    Returns:
        dict: delete csp machine instance backup response
    """
    try:
        url = f"{helpers.get_locust_host()}{Paths.CSP_MACHINE_INSTANCE_BACKUPS}/{backup_id}"
        response = requests.request("DELETE", url, headers=headers.authentication_header)
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response

        if response.status_code == requests.codes.accepted:
            if wait_for_task:
                task_uri = response.headers["location"]
                task_status = helpers.wait_for_task(task_uri=task_uri, timeout_minutes=30)
                if task_status == helpers.TaskStatus.success:
                    logger.info("CSP volume backup deleted successfully")
                elif task_status == helpers.TaskStatus.timeout:
                    raise Exception("CSP volume backup failed with timeout error")
                elif task_status == helpers.TaskStatus.failure:
                    raise Exception("CSP volume backup failed with status'FAILED' error")
                else:
                    raise Exception("CSP volume backup failed with unknown error")
                return response.text
            else:
                return response.text
        else:
            logger.info(response.text)

    except Exception as e:
        raise Exception(f"Error while deleting backup {backup_id} of {csp_instance_id}:: {e}")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def delete_csp_volume_backup(csp_volume_id, backup_id) -> dict:
    """Deletes backup of csp volume
    Raises:
        Exception: Refresh inventory Task timeout error
        Exception: Refresh inventory Task status "FAILED" error
        Exception: Refresh inventory unknown error

    Returns:
        dict: delete csp volume backup response
    """
    try:
        url = f"{helpers.get_locust_host()}{Paths.CSP_VOLUME_BACKUPS}/{backup_id}"
        response = requests.request("DELETE", url, headers=headers.authentication_header)
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response

        if response.status_code == requests.codes.accepted:
            task_uri = response.headers["location"]
            task_status = helpers.wait_for_task(task_uri=task_uri, timeout_minutes=30)
            if task_status == helpers.TaskStatus.success:
                logger.info("CSP volume backup deleted successfully")
            elif task_status == helpers.TaskStatus.timeout:
                raise Exception("CSP volume backup failed with timeout error")
            elif task_status == helpers.TaskStatus.failure:
                raise Exception("CSP volume backup failed with status'FAILED' error")
            else:
                raise Exception("CSP volume backup failed with unknown error")
            return response.text
        else:
            logger.info(response.text)

    except Exception as e:
        raise Exception(f"Error while deleting backup {backup_id} of {csp_volume_id}:: {e}")
