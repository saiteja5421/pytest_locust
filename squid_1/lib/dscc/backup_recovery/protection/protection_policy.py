import json
import uuid
import requests
import logging
from common import common
from common.enums.protection_types import ProtectionType
from common import helpers
from tests.aws.config import Paths
from common.helpers import squid_is_retry_needed
from tenacity import retry, stop_after_attempt, wait_fixed
from requests import codes


logger = logging.getLogger(__name__)
headers = helpers.gen_token()

from enum import Enum


class ProtectionType(Enum):
    # Standard across atlantia
    SNAPSHOT = "SNAPSHOT"
    BACKUP = "BACKUP"
    CLOUD_BACKUP = "CLOUD_BACKUP"
    REPLICATED_SNAPSHOT = "REPLICATED_SNAPSHOT"


class ScheduleRecurrence(Enum):
    BY_MINUTES = "BY_MINUTES"
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class ExpireAfter(Enum):
    HOURS = "HOURS"
    DAYS = "DAYS"
    WEEKS = "WEEKS"
    MONTHS = "MONTHS"
    YEARS = "YEARS"


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def create_protection_policy(
    policy_name: str = "PSR_Protection_Policy_" + str(uuid.uuid4()),
    description: str = "Create a new protection policy to restore instance",
    backup_protection_type: ProtectionType = ProtectionType.BACKUP,
    backup_schedule_recurrence: ScheduleRecurrence = ScheduleRecurrence.DAILY,
    backup_schedule_repeat_interval_every: int = 1,
    backup_expire_after_unit: ExpireAfter = ExpireAfter.WEEKS,
    backup_expire_after_value: int = 1,
    backup_start_time: str = "00:00",
    cloud_protection_type: ProtectionType = ProtectionType.CLOUD_BACKUP,
    cloud_schedule_recurrence: ScheduleRecurrence = ScheduleRecurrence.WEEKLY,
    cloud_schedule_repeat_interval_every: int = 1,
    cloud_schedule_repeat_interval_on: list[int] = [4],
    cloud_expire_after_unit: ExpireAfter = ExpireAfter.YEARS,
    cloud_expire_after_value: int = 1,
    cloud_start_time: str = "00:00",
    backup_only: bool = False,
    cloud_only: bool = False,
):
    """Create protection policy
    Args:
        schedule_recurrence (str, optional): schedule frequency such as HOURLY, DAILY, WEEKLY, MONTHLY. Defaults to "WEEKLY".
        protection_type (str, optional): protection type. Defaults to "SNAPSHOT".
    Returns:
        _type_: Response Data of Protection Policy details
    """
    if backup_only and not cloud_only:
        protections = [
            {
                "type": backup_protection_type.value,
                "schedules": [
                    {
                        "scheduleId": 1,
                        "name": "Backup_1",
                        "namePattern": {"format": "Backup_{DateFormat}"},
                        "expireAfter": {"unit": backup_expire_after_unit.value, "value": backup_expire_after_value},
                        "schedule": {
                            "recurrence": backup_schedule_recurrence.value,
                            "repeatInterval": {
                                "every": backup_schedule_repeat_interval_every,
                            },
                            "startTime": backup_start_time,
                        },
                    }
                ],
            }
        ]

    elif cloud_only and not backup_only:
        protections = [
            {
                "type": cloud_protection_type.value,
                "schedules": [
                    {
                        "scheduleId": 1,
                        "name": "Cloud_Backup_1",
                        "namePattern": {"format": "Cloud_Backup_{DateFormat}"},
                        "expireAfter": {"unit": cloud_expire_after_unit.value, "value": cloud_expire_after_value},
                        "schedule": {
                            "recurrence": cloud_schedule_recurrence.value,
                            "repeatInterval": {
                                "every": cloud_schedule_repeat_interval_every,
                                "on": cloud_schedule_repeat_interval_on,
                            },
                            "startTime": cloud_start_time,
                        },
                    }
                ],
            }
        ]
    else:
        protections = [
            {
                "type": backup_protection_type.value,
                "schedules": [
                    {
                        "scheduleId": 1,
                        "name": "Backup_1",
                        "namePattern": {"format": "Backup_{DateFormat}"},
                        "expireAfter": {"unit": backup_expire_after_unit.value, "value": backup_expire_after_value},
                        "schedule": {
                            "recurrence": backup_schedule_recurrence.value,
                            "repeatInterval": {
                                "every": backup_schedule_repeat_interval_every,
                            },
                            "startTime": backup_start_time,
                        },
                    }
                ],
            },
            {
                "type": cloud_protection_type.value,
                "schedules": [
                    {
                        "scheduleId": 2,
                        "name": "Cloud_Backup_2",
                        "namePattern": {"format": "Cloud_Backup_{DateFormat}"},
                        "expireAfter": {"unit": cloud_expire_after_unit.value, "value": cloud_expire_after_value},
                        "schedule": {
                            "recurrence": cloud_schedule_recurrence.value,
                            "repeatInterval": {
                                "every": cloud_schedule_repeat_interval_every,
                                "on": cloud_schedule_repeat_interval_on,
                            },
                            "startTime": cloud_start_time,
                        },
                    }
                ],
            },
        ]

    payload = {"name": policy_name, "description": description, "applicationType": "AWS", "protections": protections}
    try:
        url = f"{helpers.get_locust_host()}{Paths.PROTECTION_POLICIES}"
        data = json.dumps(payload)
        response = requests.request("POST", url, headers=headers.authentication_header, data=data)
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response
        if response.status_code == requests.codes.ok:
            response_data = response.json()
            print("RESPONSE DATA:")
            print(response_data)
            logger.info(f"Create protection policy-Response data::{response.status_code}")
            print(response)
            return response_data
        logger.info(response.text)
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        raise Exception(f"Error while creating protection policy {policy_name}:: {e}")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def delete_protection_policy(protection_policy_id: str) -> str:
    """Delete protection policy

    Args:
        protection_policy_id (str): protection policy id

    Returns:
        str: delete protection policy success message
    """
    try:
        url = f"{helpers.get_locust_host()}{Paths.PROTECTION_POLICIES}/{protection_policy_id}"

        response = requests.request("DELETE", url, headers=headers.authentication_header)
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response

        if response.status_code == requests.codes.no_content:
            return f"Protection policy {protection_policy_id} deleted successfully"
    except requests.exceptions.ProxyError:
        raise e
    except Exception as e:
        raise Exception(f"Error while deleting protection policy {protection_policy_id}:: {e}")


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def get_all_protection_policies():
    url = f"{helpers.get_locust_host()}{Paths.PROTECTION_POLICIES}?limit=1000"
    response = requests.request("GET", url, headers=headers.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    return response.json()


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def get_protection_policy_by_id(policy_id):
    url = f"{helpers.get_locust_host()}{Paths.PROTECTION_POLICIES}/{policy_id}"
    response = requests.request("GET", url, headers=headers.authentication_header)
    if (
        response.status_code == requests.codes.internal_server_error
        or response.status_code == requests.codes.service_unavailable
    ):
        return response
    return response.json()


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(15),
    wait=wait_fixed(10),
    retry_error_callback=common.raise_my_exception,
)
def delete_all_protection_policies():
    protection_policies = get_all_protection_policies()
    for ppolicy in protection_policies["items"]:
        logger.debug(ppolicy["id"])
        url = f"{helpers.get_locust_host()}{Paths.PROTECTION_POLICIES}/{ppolicy['id']}"
        response = requests.request("DELETE", url, headers=headers.authentication_header)
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response
        logger.debug(f"delete response code {response.status_code}")
