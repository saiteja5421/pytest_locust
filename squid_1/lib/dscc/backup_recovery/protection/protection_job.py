import json
import requests
import logging
from common import helpers
from common.helpers import squid_is_retry_needed
from tests.aws.config import Paths
from tenacity import retry, stop_after_attempt, wait_fixed
from common import common
from common.enums.asset_info_types import AssetType
from common.enums.backup_consistency import BackupConsistency

logger = logging.getLogger(__name__)
headers = helpers.gen_token()


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def create_protection_job(
    asset_id: str,
    protection_policy_id: str,
    protections_id_one: str,
    protections_id_two: str = None,
    cloud_and_backup_schedules: bool = False,
    asset_type: AssetType = AssetType.CSP_MACHINE_INSTANCE,
):
    """Creates protection job to assign policy for the job"""
    consistency: str = BackupConsistency.APPLICATION.value
    if asset_type != AssetType.CSP_MACHINE_INSTANCE:
        consistency = None
    if consistency:
        if not cloud_and_backup_schedules:
            protections = [
                {"id": protections_id_one, "schedules": [{"scheduleId": 1, "consistency": consistency}]},
            ]
        else:
            protections = [
                {"id": protections_id_one, "schedules": [{"scheduleId": 1, "consistency": consistency}]},
                {"id": protections_id_two, "schedules": [{"scheduleId": 2, "consistency": consistency}]},
            ]
    else:
        if not cloud_and_backup_schedules:
            protections = [
                {"id": protections_id_one, "schedules": [{"scheduleId": 1}]},
            ]
        else:
            protections = [
                {"id": protections_id_one, "schedules": [{"scheduleId": 1}]},
                {"id": protections_id_two, "schedules": [{"scheduleId": 2}]},
            ]

    payload = {
        "assetInfo": {"id": asset_id, "type": asset_type.value},
        "overrides": {"protections": protections},
        "protectionPolicyId": protection_policy_id,
    }
    try:
        url = f"{helpers.get_locust_host()}{Paths.PROTECTION_JOBS}"
        response = requests.request("POST", url, headers=headers.authentication_header, data=json.dumps(payload))
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response

        if response.status_code == requests.codes.accepted:
            task_uri = helpers.get_task_uri_from_header(response)
            task_status = helpers.wait_for_task(task_uri=task_uri)
            if task_status == helpers.TaskStatus.success:
                logger.info("Protection job completed successfully")
            elif task_status == helpers.TaskStatus.timeout:
                logger.error("Protection job failed with timeout error. But it will work for now")
                # raise Exception("Protection job failed with status'Timeout' error")
            elif task_status == helpers.TaskStatus.failure:
                raise Exception("Protection job failed with status'FAILED' error")
            else:
                raise Exception("Protection job failed with unknown error")
            return response
        else:
            err_msg = (
                f"Failed to create protection job so protection policy will not be applied. Response is {response.text}"
            )
            logger.error(err_msg)
            raise Exception(err_msg)
    except requests.exceptions.ProxyError:
        raise e

    except Exception as e:
        raise Exception(f"Error while creating protection job:: {e}")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def get_all_protection_job_total():
    """Return count of protection jobs"""

    url = f"{helpers.get_locust_host()}{Paths.PROTECTION_JOBS}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    if response.status_code == requests.codes.ok:
        response_data = response.json()
        logger.info(f"Response data::{response_data}")
        return response_data["total"]
    else:
        logger.info(response.text)


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def get_protection_job_by_asset_id(asset_id):
    url = f"{helpers.get_locust_host()}{Paths.PROTECTION_JOBS}?filter=assetInfo/id eq {asset_id}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    if response.status_code == requests.codes.ok:
        response_data = response.json()
        logger.info(f"Response data::{response_data}")
        return response_data
    else:
        logger.info(response.text)


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def get_protection_job_id(csp_machine_id):
    protection_job_data = get_protection_job_by_asset_id(csp_machine_id)
    if protection_job_data["total"] == 0:
        logger.warning(f"Protection policy is not assigned to the asset: {csp_machine_id}")
        raise Exception(f"No protection job found for Ec2 {csp_machine_id}")
    protection_job_id = protection_job_data["items"][0]["id"]
    logger.info(f"Protection job of asset {csp_machine_id} is {protection_job_id}")
    return protection_job_id


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def get_all_protection_jobs():
    """Return all protection jobs"""

    limit = get_all_protection_job_total()
    url = f"{helpers.get_locust_host()}{Paths.PROTECTION_JOBS}?limit={limit}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    if response.status_code == requests.codes.ok:
        response_data = response.json()
        logger.info(f"Response data::{response_data}")
        return response_data
    else:
        logger.info(response.text)


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def find_protection_job_id(protection_policy_name, instance_id):
    """Return protection job ID from the list of protection jobs by providing policy name and instance id"""

    data = get_all_protection_jobs()
    protection_job_id = None
    if data != None:
        for item in data["items"]:
            logger.info(f"Protection job details {item}")
            # NOTE: Sometimes there can be issues with Protection Policy/Jobs . . . having no 'protectionPolicyInfo' which will fail logger below
            logger.info(f"Protection job policy details {item['protectionPolicyInfo']}")
            if (item["protectionPolicyInfo"]["name"] == protection_policy_name) and (
                item["assetInfo"]["id"] == instance_id
            ):
                protection_job_id = item["id"]
                if protection_job_id != None:
                    return protection_job_id
                else:
                    raise Exception("No protection Job ID ")
    else:
        raise Exception("No protection Job ID ")

    if protection_job_id == None:
        raise Exception(
            f"Protection job id is not found for protection policy {protection_policy_name}.Instance id is {instance_id}"
        )


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def get_protection_job_by_id(protection_job_id):
    """Return all information about specific job"""

    url = f"{helpers.get_locust_host()}{Paths.PROTECTION_JOBS}/{protection_job_id}"

    response = requests.request("GET", url, headers=headers.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response

    if response.status_code == requests.codes.ok:
        response_data = response.json()
        logger.info(f"Response data::{response_data}")
        return response_data
    else:
        logger.info(response.text)


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def run_protection_job(protection_job_id: str, scheduleIds: list[int] = [1]):
    """Backup will be create for the instance by running the protection job"""
    try:
        url = f"{helpers.get_locust_host()}{Paths.PROTECTION_JOBS}/{protection_job_id}/run"
        payload = {"scheduleIds": scheduleIds}
        response = requests.request("POST", url, headers=headers.authentication_header, data=json.dumps(payload))
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response
        if response.status_code == requests.codes.accepted:
            logger.info(f"Backup created. response is {response.text}. Now verify task status of backup")
            return response
        else:
            raise Exception(f"Failed to take backup {response.text}")
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        logger.error(f"Error while running the protection job:: {e}")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def unprotect_job(protection_job_id: str) -> dict:
    """Delete the protection job

    Args:
        protection_job_id (str): protection job id

    Raises:
        Exception: Unprotect job Task timeout error
        Exception: Unprotect job Task status "FAILED" error
        Exception: Unprotect job unknown error

    Returns:
        dict: delete protection job response json
    """
    try:
        url = f"{helpers.get_locust_host()}{Paths.PROTECTION_JOBS}/{protection_job_id}"

        response = requests.request("DELETE", url, headers=headers.authentication_header)

        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response

        if response.status_code == requests.codes.accepted:
            task_uri = helpers.get_task_uri_from_header(response)
            task_status = helpers.wait_for_task(task_uri=task_uri)
            if task_status == helpers.TaskStatus.success:
                logger.info("Unprotect job completed successfully")
            elif task_status == helpers.TaskStatus.timeout:
                raise Exception("Unprotect job failed with timeout error")
            elif task_status == helpers.TaskStatus.failure:
                raise Exception("Unprotect job failed with status'FAILED' error")
            else:
                raise Exception("Unprotect job failed with unknown error")
            return response.text
        else:
            logger.info(response.text)

    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        raise Exception(f"Error while unprotecting the job {protection_job_id}:: {e}")


def unprotect_all():
    protection_jobs = get_all_protection_jobs()
    for protection_job in protection_jobs["items"]:
        print(protection_job["id"])
        unprotect_job(protection_job["id"])
