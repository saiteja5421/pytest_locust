import json
import requests
import logging
import time
from common import helpers
from tests.vmware.vmware_config import Paths
from requests import codes
from lib.dscc.backup_recovery.vmware_protection.virtual_machines.payload.post_protect_vm import ProtectVM

logger = logging.getLogger(__name__)
headers = helpers.gen_token()
proxies = helpers.set_proxy()


def get_protection_job_id(asset_id):
    """Get protection job id for the given asset

    Args:
        asset_id (str): asset id

    Raises:
        Exception: Raise exception if no protection job found

    Returns:
        str: protection job id
    """
    url = f"{helpers.get_locust_host()}{Paths.protection_jobs}?filter=assetInfo/id eq {asset_id}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    if response.status_code == requests.codes.ok:
        response_data = response.json()

        if response_data["total"] == 0:
            logger.warning(f"Protection policy is not assigned to the asset: {asset_id}")
            raise Exception(f"No protection job found for Ec2 {asset_id}")
        protection_job_id = response_data["items"][0]["id"]
        logger.info(f"Protection job of asset {asset_id} is {protection_job_id}")
    return protection_job_id


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
        url = f"{helpers.get_locust_host()}{Paths.protection_jobs}/{protection_job_id}"

        response = requests.request("DELETE", url, headers=headers.authentication_header)

        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response

        if response.status_code == requests.codes.accepted:
            task_uri = response.headers["location"]
            task_status = helpers.wait_for_task(task_uri=task_uri,timeout_minutes=30)
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


def assign_protection_policy(
    asset_name,
    asset_type,
    asset_id,
    template_id,
    snapshot_id,
    local_backup_id,
    cloud_backup_id,
    backup_granularity_type,
    schedule_id_list,
):
    payload = {
        "assetInfo": {"id": asset_id, "type": asset_type},
        "protectionPolicyId": template_id,
        "overrides": {
            "protections": [
                {
                    "id": snapshot_id,
                    "schedules": [
                        {
                            "scheduleId": schedule_id_list[0],
                            "consistency": "CRASH_CONSISTENT_ON_FAILURE",
                            "backupGranularity": backup_granularity_type,
                        }
                    ],
                },
                {
                    "id": local_backup_id,
                    "schedules": [
                        {
                            "scheduleId": schedule_id_list[1],
                            "consistency": "CRASH_CONSISTENT_ON_FAILURE",
                            "backupGranularity": backup_granularity_type,
                        }
                    ],
                },
                {
                    "id": cloud_backup_id,
                    "schedules": [
                        {
                            "scheduleId": schedule_id_list[2],
                            "consistency": "CRASH_CONSISTENT_ON_FAILURE",
                            "backupGranularity": backup_granularity_type,
                        }
                    ],
                },
            ]
        },
    }
    try:
        url = f"{helpers.get_locust_host()}{Paths.protection_jobs}"
        data = json.dumps(payload)
        logger.info(f"request body {data}")
        response = requests.request("POST", url, headers=headers.authentication_header, data=data)
        assert response.status_code == codes.accepted, f"{response.content}"
        task_uri = response.headers.get("Location")
        task_status = helpers.wait_for_task(task_uri=task_uri,timeout_minutes=30,api_header=headers)
        if task_status == helpers.TaskStatus.success:
            logger.info(f"Protection Policy {template_id} assigned  to {asset_name} successfully.")
        elif task_status == helpers.TaskStatus.timeout:
            logger.error(f"Protect VM for {asset_name}  failed with timeout error.")
        elif task_status == helpers.TaskStatus.failure:
            raise Exception(f"Protect VM for {asset_name}  failed with status'FAILED' error")
        else:
            raise Exception(f"Protect VM for {asset_name}  failed with unknown error")
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        raise Exception(f"Error while protecting vm :: {e}")
    protection_job_id = None
    retry_count = 5
    while protection_job_id is None and retry_count > 0:
        protection_job_id = get_protection_job_id(asset_id)
        if protection_job_id:
            return protection_job_id
        logging.info(
            "Unable to get Protection job id of protection policy is {protection_policy_name} assigned to EC2 {ec2_instance_id}, retrying the operation to obtain protection_job_id"
        )
        retry_count -= 1
        time.sleep(1)
    logging.error(
        "Unable to get Protection job id of protection policy is {protection_policy_name} assigned to EC2 {ec2_instance_id} after 5 retries"
    )
