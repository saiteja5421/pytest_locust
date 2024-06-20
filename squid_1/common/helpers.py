import configparser
import datetime
from email.utils import formatdate
import logging
import os
import time
from urllib.parse import urlparse
from requests import codes, Response
import requests
import yaml
from yaml.loader import SafeLoader
from enum import Enum
from tenacity import retry, stop_after_attempt, wait_fixed
from tests.aws.config import ConfigPaths, Paths
from common import common
from lib.dscc.tasks.payload.task import TaskList
from common.users.user import ApiHeader
from common.users.user_model import APIClientCredential
from utils.dates import parse_to_iso8601
from tests.steps.aws_protection.tasks import tasks
from common.users.user import User


logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    success = "SUCCEEDED"
    failure = "FAILED"
    timeout = "TIMEOUT"


def gen_token(static_token: str = None):
    """Generating token from oauth2 client
    Returns:
        headers : Authorization token
    """

    if static_token:
        api_header = ApiHeader(api_credential=None, oauth2_server="", static_token=static_token)
        return api_header
    else:
        config = read_config()
        api_client_id = os.environ.get("OAUTH_CLIENT_ID")
        api_client_secret = os.environ.get("OAUTH_CLIENT_SECRET")
        user_name = os.environ.get("USER_NAME")
        credential_name = os.environ.get("CREDENTIAL_NAME")
        if not api_client_id and not api_client_secret:
            api_users = config["testbed"]["users"]
            for user in api_users:
                if user[credential_name] == credential_name:
                    api_client_id = os.environ.get("OAUTH_CLIENT_ID")
                    api_client_secret = os.environ.get("OAUTH_CLIENT_SECRET")

        api_client_cred = APIClientCredential(
            api_client_id=api_client_id,
            api_client_secret=api_client_secret,
            credential_name=credential_name,
            username=user_name,
        )
        api_header = ApiHeader(api_credential=api_client_cred, oauth2_server=config["testbed"]["cloud"]["oauth2server"])
        return api_header


def get_config():
    """Returns config dictionary

    Returns:
        config_dict: Return config dictionary
    """
    config = read_config()
    api_client_id = os.environ.get("OAUTH_CLIENT_ID")
    api_client_secret = os.environ.get("OAUTH_CLIENT_SECRET")
    credential_name = os.environ.get("CREDENTIAL_NAME")
    user_name = os.environ.get("USER_NAME")
    config_dict = {
        "api_client_id": api_client_id,
        "api_client_secret": api_client_secret,
        "credential_name": credential_name,
        "username": user_name,
    }
    return config_dict


def get_oauth_url_and_credentials(cloud_config: dict):
    """Oauth token url(oauth2_server_url) and credentials(client id and client secret) will be fetched.
      Client_id and client_secret will be fetched from Environment variable. If not found it will take the hard coded value from config.yml

    Args:
        cloud_config (_type_): testbed.cloud under config.yml

    Returns:
        tuple: oauth2_server,client_id and client_secret will be returned
    """
    oauth2_server = cloud_config["oauth2server"]
    cluster = get_cluster()
    client_id = os.environ.get("OAUTH_CLIENT_ID")
    client_secret = os.environ.get("OAUTH_CLIENT_SECRET")

    if not client_id:
        client_id = cloud_config[cluster]["credentials"]["clientid"]
    if not client_secret:
        client_secret = cloud_config[cluster]["credentials"]["clientsecret"]

    return oauth2_server, client_id, client_secret


def generate_date():
    return datetime.datetime.now().strftime("%m%d%Y%H%M%S%f")


def set_proxy(no_proxy: bool = False):
    proxy = "http://hpeproxy.its.hpecorp.net:443"
    if no_proxy:
        proxies = {
            "http": "",
            "https": "",
        }
    else:
        proxies = {
            "http": proxy,
            "https": proxy,
        }
    return proxies


def read_config():
    path = os.environ.get("CONFIG_FILE_PATH")
    if not path:
        path = ConfigPaths.CONFIG_FILE_PATH
    with open(f"{path}") as f:
        data = yaml.load(f, Loader=SafeLoader)
    return data


def get_cluster() -> str:
    """parse cluster name from locust host url. For ex: from FilePOC cluster fetch the name filepoc.

    Returns:
        str: cluster name
    """
    cloud_url = get_locust_host()
    domain = urlparse(cloud_url).netloc
    cluster = domain.split("-")[0]
    return cluster


def get_locust_host() -> str:
    """Get locust host url from LOCUST_USER environment variable.
       If that is not set then look for locust.conf file.

    Returns:
        str: cloud url of given cluster such as FILEPOC ,SCDEV01
    """
    config = configparser.ConfigParser()
    cloud_url = os.environ.get("LOCUST_HOST")
    if not cloud_url:
        config.read(ConfigPaths.LOCUST_CONF_PATH)
        cloud_url = config["default"]["host"]
    return cloud_url


def get_rds_db_master_username_password() -> str:
    """Get RDS db master username and password from MASTER_USER_NAME and MASTER_USER_PASSWORD environment variable.
       If that is not set then look for config.yml file.

    Returns:
        str:
    """
    master_user_name = os.environ.get("MASTER_USER_NAME")
    master_user_password = os.environ.get("MASTER_USER_PASSWORD")
    if not master_user_name:
        config = read_config()
        master_user_name = config["testInput"]["RDS"]["master_user_name"]
        master_user_password = config["testInput"]["RDS"]["master_user_password"]
    return master_user_name, master_user_password


def squid_is_retry_needed(retry_state):
    needs_retry = False
    result = retry_state.outcome._result

    if isinstance(result, Response) and result.status_code == codes.forbidden:
        # For forbidden response
        needs_retry = True
        logger.debug("Server returned forbidden response. Retrying..")
    elif isinstance(retry_state.outcome._exception, (requests.exceptions.ProxyError, requests.exceptions.ReadTimeout)):
        # For ProxyError OR socket timeouts
        needs_retry = True
        logger.debug("Proxy error occurred. Retrying..")
        logger.debug("Server returned forbidden response. Retrying..")
    elif isinstance(result, Response) and result.status_code == codes.internal_server_error:
        # Workaround till we get fix for SC-8356
        needs_retry = True
        logger.debug("SC-8356(Task service internal error) issue. Retrying..")
    elif isinstance(result, Response) and result.status_code == codes.service_unavailable:
        needs_retry = True
        logger.error("503 Error from tasks service")
    return needs_retry


@retry(
    retry=squid_is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=common.raise_my_exception,
)
def wait_for_task(task_uri, timeout_minutes=10, sleep_seconds=10, api_header: ApiHeader = None):
    """Wait for tasks to reach Success state

    Args:
        task_uri (_type_): Task url fetched from post requests
        max_retry (int, optional): Wait for ten seconds then retry. Max_retry by default is 30 which is 300seconds (5 minutes). Defaults to 30.

    Raises:
        Exception: exception if failed or timeout

    Returns:
        enum: Task status
    """
    if not api_header:
        api_header = gen_token()
    timeout = (timeout_minutes * 60) / sleep_seconds
    url = f"{get_locust_host()}{task_uri}"
    start_perf_counter = time.perf_counter()
    while timeout:
        response = requests.request("GET", url, headers=api_header.authentication_header)
        if (
            response.status_code == requests.codes.internal_server_error
            or response.status_code == requests.codes.service_unavailable
        ):
            return response

        if response.status_code == codes.ok:
            # check whether state is "SUCCEEDED or FAILED"

            task_response = response.json()
            if task_response["state"] == TaskStatus.success.value:
                time_taken = (time.perf_counter() - start_perf_counter) * 1000
                logging.info(f"Wait for task completion time: {time_taken}ms")
                return TaskStatus.success
            elif task_response["state"] == TaskStatus.failure.value:
                logger.info(f"Task Response {task_response}")
                return TaskStatus.failure
            else:
                logging.debug(f"Task status is still in {task_response['state']} state")
                time.sleep(10)
                timeout -= 1
        elif response.status_code == codes.forbidden:
            logging.info("Task state is forbidden due to proxy server issue.Wait for 10 seconds & retry")
            time.sleep(10)
            retry_count += 1
        else:
            logging.info(response.text)
            raise Exception(
                f"Failed to get task status , StatusCode: {str(response.status_code)} , Response is {response.text}"
            )

    logging.error(
        f"Task with id {task_uri}  did not succeeded/failed even after {timeout_minutes} minutes.Task status is{task_response['state']}"
    )
    return TaskStatus.timeout


def get_error_message_from_task_response(task_uri,api_header: ApiHeader = None):
    """Get task response using task uri

    Args:
        task_uri (string): task uri

    Returns:
        err_message (string): error message
    """
    url = f"{get_locust_host()}{task_uri}"
    response = requests.request("GET", url, headers=api_header.authentication_header)
    if response.status_code == codes.ok:
        task_response = response.json()
        if task_response["state"] == TaskStatus.failure.value:
            logger.info(f"Task Response {task_response}")
            err_message = task_response["error"]["error"]
            return err_message
    
        
def wait_for_task_completion_within_time_interval(task_name, customer_id, time_offset_minutes=5, timeout_minutes=10):
    """This function will wait for tasks filtered by given task name and time_offset_minutes within specified time
    Args:
        task_name (str): Task name
        customer_id (str): Customer id
    """
    config = get_config()
    user: User = User(config)
    running_tasks_list = tasks.get_tasks_by_name_and_customer_account(
        user=user, task_name=task_name, customer_id=customer_id, time_offset_minutes=time_offset_minutes
    )
    if running_tasks_list is not None:
        for task in running_tasks_list:
            task_status = wait_for_task(task_uri=task.resource_uri, timeout_minutes=timeout_minutes)
            logger.info(f"{task_name} completed with status {task_status}")


def get_task_uri_from_header(response: Response):
    """Returns task_uri from Location header of response object"""
    logger.info(f"task {response.headers}: {response.headers}")
    task_uri = response.headers.get("Location")
    return task_uri


def get_tasks_by_name_and_resource(task_name: str, resource_uri: str, time_offset_minutes: int = 10) -> TaskList:
    """Return a TaskList matching 'task_name' and 'resource_uri' provided.

    Args:
        task_name (str): The task name to match
        resource_uri (str): The resource uri to match
        time_offset_minutes (int, optional): Number of minutes back from 'now' to search. Defaults to 10.

    Returns:
        TaskList: A TaskList containing any matching Tasks
    """
    url = f"{get_locust_host()}/{Paths.TASK_API}"
    api_header = gen_token()

    # search for tasks 'time_offset_minutes' back from time 'now'
    date_time = formatdate(timeval=None, localtime=False, usegmt=True)
    datetime_formated = parse_to_iso8601(date_time=date_time, time_offset_minutes=time_offset_minutes)

    # NOTE: it seems that the trigger task name format is changed on FILEPOC
    # on SCDEV01: "Trigger Cloud Backup"
    # on FILEPOC: "Trigger Cloud Backup for csp-volume [vol-050603a150e71eae1]"
    # We cannot use the '[' or ']' characters in: "displayName eq '{task_name}'"
    #
    # We'll get all tasks for the 'sourceResource.resourceUri' and then manually look
    # through the 'task.display_name" to match with the 'task_name' provided
    params = f"offset=0&limit=10&sort=createdAt desc&filter=createdAt gt {datetime_formated} and sourceResource.resourceUri eq '{resource_uri}'"
    response = requests.request("GET", f"{url}?{params}", headers=api_header.authentication_header)

    return_list = TaskList(items=[], page_limit=0, page_offset=0, total=0)

    # task.name         = CSPBackupParentWorkflow
    # task.display_name = Trigger Cloud Backup for csp-volume [vol-0ee9a3901a22d8edb]
    task_list: TaskList = TaskList.from_json(response.text)
    for task in task_list.items:
        logger.info(f"Task Name = {task.name}: {task.display_name}")
        if task_name in task.display_name:
            logger.info(f"Adding item: {task}")
            return_list.items.append(task)
            return_list.total += 1

    return return_list


def get_report_portal_info():
    config = read_config()
    report_portal = config["testbed"]["reportportal"]
    report_portal_token = os.environ.get("REPORT_PORTAL_TOKEN")
    if report_portal_token:
        report_portal.update({"token": report_portal_token})
    return report_portal


def custom_locust_response(environment, name, exception, start_time=time.time(), response_time=0, response_result=None):
    request_meta = {
        "request_type": "custom",
        "name": name,
        "start_time": start_time,
        "response_length": 0,
        "exception": None,
        "context": None,
        "response": response_result,
        "url": f"custom:{name}",
    }
    request_meta["exception"] = exception
    request_meta["response_time"] = response_time
    environment.events.request.fire(**request_meta)


def custom_before_sleep(retry_state):
    # Before retrying which logs the message with count of retry
    if retry_state.attempt_number < 1:
        loglevel = logging.INFO
    else:
        loglevel = logging.WARNING
    logger.log(
        loglevel,
        "################Retrying################ %s: attempt %s ended with: %s",
        retry_state.fn,
        retry_state.attempt_number,
        retry_state.outcome,
    )


def raise_retries_exceeded_exception(retry_state):
    # After certain no.of retries which raise the actual exception
    logging.warning("=====Retries exceeded=====")
    result = retry_state.outcome.result()
    return result


def get_v1_beta_api_prefix():
    """Returns API prefix includes api and its version

    Returns:
        string:API prefix string
    """
    config = read_config()
    v1_beta = config["testbed"]["V1BETA"]
    v1_beta_api = v1_beta["backup_recovery"]
    v1_beta_1_api_version = v1_beta["beta_1_version"]
    v1_beta_2_api_version = v1_beta["beta_2_version"]
    return (f"/{v1_beta_api}/{v1_beta_1_api_version}", f"/{v1_beta_api}/{v1_beta_2_api_version}")
