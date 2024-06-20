import logging
import json
import time
from requests import codes
import re
from waiting import wait, TimeoutExpired

from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.tasks import tasks
from lib.common.enums.storeonce import HealthState, HealthStatus
from lib.platform.storeonce.storeonce import StoreOnce
from lib.dscc.backup_recovery.vmware_protection.storeonce.api.storeonce import (
    StoreonceManager,
)
from lib.common.error_messages import (
    ERROR_MESSAGE_DELETE_PROTECTION_STORE_WITH_BACKUP_WITHOUT_USING_FORCE,
    ERROR_MESSAGE_INCORRECT_FORMAT_FOR_STOREONCE_USERNAME,
    ERROR_MESSAGE_STOREONCE_HAS_NO_VALID_LICENSE,
    ERROR_MESSAGE_STOREONCE_WITH_INVALID_SERIAL_NUMBER,
    ERROR_MESSAGE_STOREONCE_WITH_INVALID_PASSWORD,
    ERROR_MESSAGE_STOREONCE_WITH_INVALID_IPADDRESS_OR_FQDN,
    ERROR_MESSAGE_STOREONCE_WITH_INVALID_UUID,
    ERROR_MESSAGE_UNREGISTRING_STOREONCE_WITH_BACKUP,
    ERROR_MESSAGE_UNREGISTRING_STOREONCE_WITH_DUALAUTH,
)
from tests.steps.vm_protection.storeonce_protection_template_steps import (
    create_protection_store,
)
from lib.common.enums.copy_pool_types import CopyPoolTypes
from utils.timeout_manager import TimeoutManager
from tests.steps.vm_protection.storeonce_protection_template_steps import (
    verify_status_and_data_orchestrator_info_on_protection_store,
)

logger = logging.getLogger()


def validate_register_storeonces(context: Context, multiple_local_protection_store=1, secondary_so=False, **kwargs):
    """
    Performs register of storeonce
    context: object of Context class
    kwargs: keyword arguments for the register post call
    """
    atlas = context.storeonces
    if not kwargs and secondary_so == False:
        response = atlas.register_storeonce(
            network_address=context.storeonces_network_address,
            serial_number=context.storeonces_serial_number,
            name=context.storeonces_name,
            dscc_username=context.storeonces_dscc_admin_username,
            dscc_password=context.storeonces_dscc_admin_password,
        )

    if "network_address" in kwargs:
        context.storeonces_network_address = kwargs["network_address"]
        response = atlas.register_storeonce(
            context.storeonces_network_address,
            context.storeonces_serial_number,
            context.storeonces_name,
            dscc_username=context.storeonces_dscc_admin_username,
            dscc_password=context.storeonces_dscc_admin_password,
        )

    if "description" in kwargs:
        description = kwargs["description"]
        response = atlas.register_storeonce(
            context.storeonces_network_address,
            context.storeonces_serial_number,
            context.storeonces_name,
            description,
            dscc_username=context.storeonces_dscc_admin_username,
            dscc_password=context.storeonces_dscc_admin_password,
        )

    if secondary_so:
        response = atlas.register_storeonce(
            context.secondary_storeonce_ip,
            context.second_so_serialnumber,
            context.second_so_name,
            dscc_username=context.storeonces_dscc_admin_username,
            dscc_password=context.storeonces_dscc_admin_password,
        )
    assert (
        response.status_code == codes.accepted
    ), f"Unexpected response received, expected: {codes.accepted}  \
        received: {response.status_code} content: {response.content}"
    task_id = tasks.get_task_id_from_header(response)
    logger.info(f"Register storeonce, Task ID: {task_id}")
    timeout = 1800
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout,
        interval=30,
        message=f"Register storeonce time exceed {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert (
        status == "succeeded"
    ), f"Failed register storeonce: {context.storeonces_name} \
                                        {tasks.get_task_error(task_id, context.user)}"
    # Getting storeonce id and assert if not None
    storeonce_id = get_storeonce_id(context)
    assert storeonce_id is not None, f"storeonce failed to register as storeonce id not found {context.storeonces_name}"
    # Checking status of sub task 'Create local protection store' post register of storeonce
    # display_name = "Create local protection store"
    # display_name = f"Create On-Premises Protection Store [Local_{context.storeonces_name}]"
    # is_local_store_created = get_local_protection_store_status(context, display_name)
    # assert is_local_store_created
    time.sleep(120)
    for i in range(multiple_local_protection_store):
        create_protection_store(context, type=CopyPoolTypes.local)


def get_storeonce_id(context: Context, **kwargs):
    """
    Get details of the registered storeonce
    context: object of Context class
    """
    if "storeonces_name" in kwargs:
        storeonces_name = kwargs["storeonces_name"]
    else:
        storeonces_name = context.storeonces_name
    atlas = context.storeonces
    response = atlas.get_storeonces()
    assert (
        response.status_code == codes.ok
    ), f"Unexpected response received, expected: {codes.ok}  \
        received: {response.status_code} content: {response.content}"
    try:
        item = next(
            filter(
                lambda item: item["name"] == storeonces_name,
                response.json().get("items"),
            )
        )
        return item["id"]
    except StopIteration:
        logger.error(f"Failed to find id for storeonce: {storeonces_name}")
        return {}


def get_storeonce_health_status(context: Context, storeonce_id, state):
    """
    Checks health and state of the registered storeonce
    storeonce_id: str, UUID of the registered storeonce
    state: str, state of the storeonce, expected values OK, ERROR
    """
    atlas = context.storeonces
    response = atlas.get_storeonce_details(storeonce_id)
    assert (
        response.status_code == codes.ok
    ), f"Unexpected response received, expected: {codes.ok}  \
        received: {response.status_code} content: {response.content}"
    temp = json.loads(response.text)
    if state == "OK" or state == "WARNING":
        assert (
            temp["health"]["state"] == HealthState.OK.value or temp["health"]["state"] == HealthState.WARNING.value
        ) and temp["health"][
            "status"
        ] == HealthStatus.CONNECTED.value, f"Unexpected state or status value received for storeonce. Current state:{temp['health']['state']},\
            status:{temp['health']['status']}"

        # Checking health state and status of storeonce via storeonce api
        storeonce_obj = StoreOnce(
            context.storeonces_network_address,
            context.storeonces_admin_username,
            context.storeonces_admin_password,
        )
        storeonce_obj.verify_health_status_for_storeonce()
    if state == "ERROR":
        assert (
            temp["health"]["state"] == HealthState.ERROR.value
            and temp["health"]["status"] == HealthStatus.DISCONNECTED.value
        ), f"Unexpected state or status value received for storeonce. Current state:{temp['health']['state']}, \
            status:{temp['health']['status']}"


def validate_unregister_storeonces(context: Context, storeonce_id, force=False):
    """
    Performs unregister of storeonce
    context: object of Context class
    storeonce_id: str, UUID of the registered storeonce
    """

    atlas = context.storeonces

    response = atlas.unregister_storeonce(storeonce_id, force)
    assert (
        response.status_code == codes.accepted
    ), f"Unexpected response received, expected: {codes.accepted}  \
        received: {response.status_code} content: {response.content}"
    task_id = tasks.get_task_id_from_header(response)
    logger.info(f"Delete of storeonce, Task ID: {task_id}")
    timeout = 1800
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout,
        interval=30,
        message=f"Deletion of storeonce time exceed {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert (
        status == "succeeded"
    ), f"Failed to unregister storeonce: {context.storeonces_name} \
                                        {tasks.get_task_error(task_id, context.user)}"


def unregister_storeonces_validate_error_msg(context: Context, storeonce_id, force=False):
    """
    Performs unregister of storeonce and verify the error msg
    context: object of Context class
    storeonce_id: str, UUID of the registered storeonce
    """

    atlas = context.storeonces

    response = atlas.unregister_storeonce(storeonce_id, force)
    assert (
        response.status_code == codes.accepted
    ), f"Unexpected response received, expected: {codes.accepted}  \
        received: {response.status_code} content: {response.content}"
    task_id = tasks.get_task_id_from_header(response)
    logger.info(f"Delete of storeonce, Task ID: {task_id}")
    timeout = TimeoutManager.standard_task_timeout
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout,
        interval=30,
        message=f"Deletion of storeonce time exceed {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert status == "failed", f"Task expected to failed {status}"
    error_message = tasks.get_task_error(task_id, context.user)
    assert (
        ERROR_MESSAGE_UNREGISTRING_STOREONCE_WITH_DUALAUTH in error_message
    ), f"Failed to validate error message EXPECTED: {ERROR_MESSAGE_UNREGISTRING_STOREONCE_WITH_DUALAUTH} ACTUAL: {error_message}"
    logger.info(f"Successfully validated error message")


def validate_patch_registered_storeonce(context: Context, storeonce_id, **kwargs):
    """
    Performs patch of registered storeonce parameters
    context: object of Context class
    storeonce_id: str, UUID of the registered storeonce
    kwargs: keyword arguments for the patch call
    """
    atlas = context.storeonces

    if kwargs is not None:
        for key, value in kwargs.items():
            if "description" in kwargs and "network_address" in kwargs:
                description = kwargs["description"]
                context.storeonces_network_address = kwargs["network_address"]
                response = atlas.patch_storeonce(context.storeonces_network_address, description, storeonce_id)
                break
            elif "description" == key:
                description = kwargs.get(key)
                response = atlas.patch_storeonce(context.storeonces_network_address, description, storeonce_id)
                break
            elif "network_address" == key:
                context.storeonces_network_address = kwargs.get(key)
                response = atlas.patch_storeonce(
                    context.storeonces_network_address,
                    description="",
                    storeonce_id=storeonce_id,
                )
                break
    else:
        assert False, "Did not receive any patch parameters"
    assert (
        response.status_code == codes.accepted
    ), f"Unexpected response received, expected: {codes.accepted}  \
        received: {response.status_code} content: {response.content}"
    task_id = tasks.get_task_id_from_header(response)
    logger.info(f"Patch of storeonce, Task ID: {task_id}")
    timeout = 1800
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout,
        interval=30,
        message=f"Time exceeded while performing storeonce patch operation {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert (
        status == "succeeded"
    ), f"Failed to patch storeonce: {context.storeonces_name} \
                                        {tasks.get_task_error(task_id, context.user)}"


def validate_refresh_registered_storeonce(context: Context, storeonce_id):
    """
    Performs refresh of registered storeonce parameters
    context: object of Context class
    storeonce_id: str, UUID of the registered storeonce
    """
    atlas = context.storeonces

    response = atlas.refresh_storeonce(storeonce_id)
    assert (
        response.status_code == codes.accepted
    ), f"Unexpected response received, expected: {codes.accepted}  \
        received: {response.status_code} content: {response.content}"
    task_id = tasks.get_task_id_from_header(response)
    logger.info(f"Patch of storeonce, Task ID: {task_id}")
    timeout = 1800
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout,
        interval=30,
        message=f"Time exceeded while performing storeonce refresh operation {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert (
        status == "succeeded"
    ), f"Failed to patch storeonce: {context.storeonces_name} \
                                        {tasks.get_task_error(task_id, context.user)}"


def reset_dsccAdmin_user_pwd(context: Context, storeonce_network_address=False):
    if storeonce_network_address:
        storeonce_obj = StoreOnce(
            context.secondary_storeonce_ip,
            context.storeonces_admin_username,
            context.storeonces_admin_password,
        )
    else:
        storeonce_obj = StoreOnce(
            context.storeonces_network_address,
            context.storeonces_admin_username,
            context.storeonces_admin_password,
        )

    storeonce_obj.reset_user_password(
        username=context.storeonces_dscc_admin_username, password=context.storeonces_dscc_admin_password
    )


def validate_storeonce_details(context: Context, storeonce_id, **kwargs):
    """
    Performs validate of registered storeonce details
    context: object of Context class
    storeonce_id: str, UUID of the registered storeonce
    kwargs: keyword arguments of the storeonce fields to validate
    """
    atlas = context.storeonces
    response = atlas.get_storeonce_details(storeonce_id)
    assert (
        response.status_code == codes.ok
    ), f"Unexpected response received, expected: {codes.ok}  \
        received: {response.status_code} content: {response.content}"
    storeonce_details = json.loads(response.text)
    if "description" in kwargs:
        assert (
            kwargs["description"] == storeonce_details["description"]
        ), "Validation of storeonce description field value failed"
    if "network_address" in kwargs:
        assert (
            kwargs["network_address"] == storeonce_details["network"]["hostname"]
        ), "Validation of storeonce name field value failed"


def get_local_protection_store_status(context: Context, display_name):
    atlas = context.storeonces
    storeonce_id = get_storeonce_id(context)
    resource_uri = f"/backup-recovery/{atlas.dscc['beta-version']}/{atlas.path}/{storeonce_id}"
    logger.info("Looking for local protection store trigger task")
    # waiting for create local protectio store, "Trigger" task to appear
    try:
        wait(
            lambda: len(
                tasks.get_tasks_by_name_and_resource_uri_with_no_offset(
                    user=context.user, task_name=display_name, resource_uri=resource_uri
                ).items
            )
            > 0,
            timeout_seconds=5 * 60,
            sleep_seconds=10,
        )
    except TimeoutExpired as e:
        logger.error("TimeoutExpired: waiting for 'Trigger' task")
        raise e
    # get the local store task id
    trigger_task_id = (
        tasks.get_tasks_by_name_and_resource_uri_with_no_offset(
            user=context.user, task_name=display_name, resource_uri=resource_uri
        )
        .items[0]
        .id
    )
    logger.info(f"Local protection store triggered task ID: {trigger_task_id}")

    # wait for the trigger task to complete
    trigger_task_state = tasks.wait_for_task(
        task_id=trigger_task_id,
        user=context.user,
        timeout=TimeoutManager.create_local_store_timeout,
        log_result=True,
    )
    if trigger_task_state == "succeeded":
        logger.info(f"Successfully created local protection store, task state: {trigger_task_state}")
        return True
    else:
        logger.error(
            f"Failed to Create On-Premises Protection Store [Local_{context.storeonces_name}], task state: {trigger_task_state}"
        )
        return False


def validate_register_storeonces_with_invalid_parameters(context: Context, **kwargs):
    """
    Validate failure while registering of storeonce with invalid parameters
    context: object of Context class
    kwargs: keyword arguments of invalid register parameters
    """
    atlas = context.storeonces
    if "network_address" in kwargs:
        invaild_storeonces_network_address = kwargs["network_address"]
        response = atlas.register_storeonce(
            network_address=invaild_storeonces_network_address,
            serial_number=context.storeonces_serial_number,
            name=context.storeonces_name,
            dscc_username=context.storeonces_dscc_admin_username,
            dscc_password=context.storeonces_dscc_admin_password,
        )
    if "password" in kwargs:
        password = kwargs["password"]
        response = atlas.register_storeonce(
            network_address=context.storeonces_network_address,
            serial_number=context.storeonces_serial_number,
            name=context.storeonces_name,
            description="",
            dscc_username=context.storeonces_dscc_admin_username,
            dscc_password=password,
        )
    if "serial_no" in kwargs:
        invaild_storeonces_serial_number = kwargs["serial_no"]
        response = atlas.register_storeonce(
            network_address=context.storeonces_network_address,
            serial_number=invaild_storeonces_serial_number,
            name=context.storeonces_name,
            dscc_username=context.storeonces_dscc_admin_username,
            dscc_password=context.storeonces_dscc_admin_password,
        )

    if "encryption_license" in kwargs:
        no_encryption_storeonces_network_address = context.storeonces_config["no_encryption_ip_address"]
        no_encryption_storeonces_serial_number = context.storeonces_config["no_encryption_serial_number"]
        no_encryption_storeonces_name = context.storeonces_config["no_encryption_name"]
        response = atlas.register_storeonce(
            network_address=no_encryption_storeonces_network_address,
            serial_number=no_encryption_storeonces_serial_number,
            name=no_encryption_storeonces_name,
            dscc_username=context.storeonces_dscc_admin_username,
            dscc_password=context.storeonces_dscc_admin_password,
        )

    logger.info(response.text)
    assert (
        response.status_code == codes.accepted
    ), f"Unexpected response received, expected: {codes.accepted}  \
        received: {response.status_code} content: {response.content}"
    task_id = tasks.get_task_id_from_header(response)
    logger.info(f"Register storeonce, Task ID: {task_id}")
    timeout = 1500
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout,
        interval=30,
        message=f"Register storeonce time exceed {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert (
        status == "failed"
    ), f"register storeonce task should have failed: {context.storeonces_name} \
                                        {tasks.get_task_error(task_id, context.user)}"

    # Validation of correct error message shown to user and backend
    if "encryption_license" in kwargs:
        error_message = tasks.get_task_error(task_id, context.user)
        assert (
            ERROR_MESSAGE_STOREONCE_HAS_NO_VALID_LICENSE in error_message
        ), f"Got incorrect error_message while registering storeonce with no encryption license ERROR: {error_message}"

    if "serial_no" in kwargs:
        error_message = tasks.get_task_error(task_id, context.user)
        assert (
            ERROR_MESSAGE_STOREONCE_WITH_INVALID_SERIAL_NUMBER in error_message
        ), f"Got incorrect error_message while registering storeonce with incorrect serial number ERROR: \
        {error_message}"

    if "password" in kwargs:
        error_message = tasks.get_task_error(task_id, context.user)
        assert (
            ERROR_MESSAGE_STOREONCE_WITH_INVALID_PASSWORD in error_message
        ), f"Got incorrect error_message while registering storeonce with incorrect password or FQDN ERROR: \
            {error_message}"

    if "network_address" in kwargs:
        error_message = tasks.get_task_error(task_id, context.user)
        assert (
            ERROR_MESSAGE_STOREONCE_WITH_INVALID_IPADDRESS_OR_FQDN in error_message
        ), f"Got incorrect error_message while registering storeonce with incorrect password or FQDN ERROR: \
            {error_message}"


def validate_register_storeonces_with_incorrect_format_parameters(context: Context, **kwargs):
    """
    Validate failure while registering of storeonce with incorrect format parameters
    context: object of Context class
    kwargs: keyword arguments of incorrect format of register parameters
    """
    atlas = context.storeonces

    if "username" in kwargs:
        username = kwargs["username"]
        response = atlas.register_storeonce(
            network_address=context.storeonces_network_address,
            serial_number=context.storeonces_serial_number,
            name=context.storeonces_name,
            dscc_username=username,
            dscc_password=context.storeonces_dscc_admin_password,
        )
    logger.info(response.text)
    assert (
        response.status_code == codes.bad_request
    ), f"Unexpected response received, expected: {codes.bad_request}  \
        received: {response.status_code} content: {response.content}"
    error_message = response.json().get("message")
    assert (
        error_message == ERROR_MESSAGE_INCORRECT_FORMAT_FOR_STOREONCE_USERNAME
    ), f"Got incorrect register storeonce error_message ERROR: {error_message}"


def validate_get_storeonce_invalid_id(context: Context, storeonce_id):
    """
    validate get details of storeonce with invalid UUID
    context: object of Context class
    """
    atlas = context.storeonces
    response = atlas.get_storeonce_details(storeonce_id)
    assert (
        response.status_code == codes.not_found
    ), f"Unexpected response received, expected: {codes.not_found}  \
        received: {response.status_code} content: {response.content}"
    error_message = response.json().get("message")
    assert (
        ERROR_MESSAGE_STOREONCE_WITH_INVALID_UUID in error_message
    ), f"Got incorrect get storeonce details error_message ERROR: {error_message}"


def validate_patch_storeonce_invalid_id(context: Context, storeonce_id, network_address, description):
    """
    validate patch storeonce with invalid UUID
    context: object of Context class
    """
    atlas = context.storeonces

    response = atlas.patch_storeonce(network_address, description, storeonce_id)
    assert (
        response.status_code == codes.not_found
    ), f"Unexpected response received, expected: {codes.not_found}  \
        received: {response.status_code} content: {response.content}"
    error_message = response.json().get("message")
    assert (
        ERROR_MESSAGE_STOREONCE_WITH_INVALID_UUID in error_message
    ), f"Got incorrect patch storeonce error_message ERROR: {error_message}"


def validate_delete_storeonce_invalid_id(context: Context, storeonce_id, force):
    """
    validate delete storeonce with invalid UUID
    context: object of Context class
    """
    atlas = context.storeonces
    response = atlas.unregister_storeonce(storeonce_id, force)
    assert (
        response.status_code == codes.not_found
    ), f"Unexpected response received, expected: {codes.not_found}  \
        received: {response.status_code} content: {response.content}"
    error_message = response.json().get("message")
    assert (
        ERROR_MESSAGE_STOREONCE_WITH_INVALID_UUID in error_message
    ), f"Got incorrect delete storeonce error_message ERROR: {error_message}"


def validate_refresh_storeonce_invalid_id(context: Context, storeonce_id):
    """
    validate refresh storeonce with invalid UUID
    context: object of Context class
    """
    atlas = context.storeonces
    response = atlas.refresh_storeonce(storeonce_id)
    assert (
        response.status_code == codes.not_found
    ), f"Unexpected response received, expected: {codes.not_found}  \
        received: {response.status_code} content: {response.content}"
    error_message = response.json().get("message")
    assert (
        ERROR_MESSAGE_STOREONCE_WITH_INVALID_UUID in error_message
    ), f"Got incorrect refresh storeonce error_message ERROR: {error_message}"


def verify_stores_storeonce(context: Context):
    atlas = context.storeonces
    storeonce_id = get_storeonce_id(context)
    response = atlas.refresh_storeonce(storeonce_id)
    assert (
        response.status_code == codes.accepted
    ), f"Unexpected response received, expected: {codes.accepted}  \
        received: {response.status_code} content: {response.content}"
    protection_stores_response = atlas.get_copy_pools()
    resp_body = protection_stores_response.json()
    logger.info(resp_body)
    for item in resp_body["items"]:
        if item["protectionStoreType"] == "CLOUD":
            size_disk_bytes = item["sizeOnDiskInBytes"]
            user_data_bytes = item["userDataStoredInBytes"]
        if item["protectionStoreType"] == "ON_PREMISES":
            max_capacity_bytes_local = item["maxCapacityInBytes"]
    storeonce_obj = StoreOnce(
        context.storeonces_network_address,
        context.storeonces_admin_username,
        context.storeonces_admin_password,
    )
    # Checking local and cloud value of storeonce via storeonce api
    storeonce_obj.verify_stores_with_local_cloud_value(
        size_disk_bytes,
        user_data_bytes,
        max_capacity_bytes_local,
    )


def verify_unregister_storeonce_not_allowed_if_backup_exists(context: Context):
    """
    If the storeonce has backup and user tries to unregister then we expect error message and we verify the same in \
    this step
    Args:
        context (Context): Context object
    """
    timeout = 300
    atlas = StoreonceManager(context.user)
    storeOnce = atlas.get_storeonce_by_name(context.storeonces_name)
    assert "id" in storeOnce, "Failed to find Storeonce ID"
    response = atlas.unregister_storeonce(storeOnce["id"], force=False)
    assert response.status_code == codes.accepted, f"{response.content}"
    task_id = tasks.get_task_id_from_header(response)
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout,
        interval=30,
        message=f"Storeonce delete time exceed {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert status == "failed", f"We got wrong state {status} for task {task_id}"
    task_error_msg = tasks.get_task_error(task_id, context.user)
    assert re.search(
        ERROR_MESSAGE_UNREGISTRING_STOREONCE_WITH_BACKUP, task_error_msg
    ), f"Expected error message not found {ERROR_MESSAGE_UNREGISTRING_STOREONCE_WITH_BACKUP} on {task_error_msg}"
    logger.info(f"Successfully verified the error message {task_error_msg}")


def enable_disable_and_approve_the_dual_request(context, enable=False):
    storeonce_obj = StoreOnce(
        context.storeonces_network_address,
        context.storeonces_admin_username,
        context.storeonces_admin_password,
    )
    # Enable the  dual auth in storeonce
    storeonce_obj.enable_disable_dual_auth_in_storeonce(enable=enable)
    if enable:
        logger.info(f"Successfully enabled the dual auth request")
    else:
        logger.info("Successfully disabled the dual auth request")
    # getting dual auth request id for approving
    request_id = storeonce_obj.get_dual_auth_pending_request_id()
    logger.info(f"request id of dual auth request{request_id}")
    storeonce_obj.approve_dual_auth_request(
        context.storeonces_dualauth_username,
        context.storeonces_dualauth_password,
        context.storeonces_admin_username,
        context.storeonces_admin_password,
        request_id,
    )
    logger.info("successfully approved the dual auth request")


def disable_dual_auth_status_when_its_enabled(context):
    storeonce = StoreOnce(
        context.storeonces_network_address,
        context.storeonces_admin_username,
        context.storeonces_admin_password,
    )
    dualauth_status = storeonce.get_dualauth_status()
    if dualauth_status:
        enable_disable_and_approve_the_dual_request(context, enable=False)
        time.sleep(120)
        # Unregister storeonce after disbled the dual request
        storeonce_id = get_storeonce_id(context)
        validate_unregister_storeonces(context, storeonce_id)


def verify_state_and_stateReason_of_protection_store(
    context: Context, exp_state="ONLINE", exp_state_reason="", secondary_so=False
):
    """Verify state and stateReason of protection stores.
    Args:
        context (Context): object of a context class
    """
    atlas = context.storeonces
    (
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    ) = atlas.get_on_premises_and_cloud_protection_store(context, secondary_so=secondary_so)
    assert all([cloud_protection_store_id_list]), "Failed to get cloud protection stores."

    for onprem_ps in onprem_protection_store_id_list:
        state = atlas.get_protection_stores_info_by_id(onprem_ps).get("state")
        state_reason = atlas.get_protection_stores_info_by_id(onprem_ps).get("stateReason")
        assert (
            state == exp_state and state_reason == exp_state_reason
        ), f"Protection store is in unexpected state: {state} and State Reason: {state_reason}. Expected state: {exp_state} and state reason: {exp_state_reason}"
        logger.info(
            f"As expected : Protection store id {onprem_ps} state is {state} and state reason is {state_reason}"
        )
    verify_status_and_data_orchestrator_info_on_protection_store(context, onprem_protection_store_id_list)
    verify_status_and_data_orchestrator_info_on_protection_store(context, cloud_protection_store_id_list)


def reattach_cloud_protection_store_to_new_storeonce(context: Context, secondary_so=True):
    """Deletes the PSGW and reattach its protection store to new PSGW.
    Args:
        context (Context): object of a context class
    """
    atlas = context.storeonces
    (
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    ) = atlas.get_on_premises_and_cloud_protection_store(context)
    assert all([cloud_protection_store_id_list]), "Failed to get cloud protection stores."
    logger.info(f"Cloud protection store id for reattach: {cloud_protection_store_id_list[0]}")

    old_storeonce_id = atlas.get_storeonce_id(context)
    reset_dsccAdmin_user_pwd(context, storeonce_network_address=True)
    validate_register_storeonces(context, multiple_local_protection_store=0, secondary_so=secondary_so)

    secondary_storeonce_id = atlas.get_secondary_storeonce_id(context)

    reattach_protection_store_payload = {
        "storageSystemId": secondary_storeonce_id,
        "storageSystemType": "STOREONCE",
    }
    logger.info(f"Payload for reattach protectore store: {reattach_protection_store_payload}")
    response = atlas.reattach_protection_store(reattach_protection_store_payload, cloud_protection_store_id_list[0])
    assert response.status_code == codes.accepted, f"Reattach protection store failed: {response.content}"
    task_id = tasks.get_task_id_from_header(response)
    logger.info(f"Reattach protection store, Task ID: {task_id}")
    timeout = TimeoutManager.first_time_psgw_creation
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout=timeout,
        interval=30,
        message="Reattach protection store time exceed 60 minutes - TIMEOUT",
    )
    assert (
        status == "succeeded"
    ), f"Failed to reattach protection store to new psg: {context.psgw_name} \
                                        {tasks.get_task_error(task_id, context.user)}"
    logger.info(f"Reattach protection store to new psg {context.psgw_name} succeeded.")
    verify_state_and_stateReason_of_protection_store(context, secondary_so=secondary_so)

    logger.info(f"Verifying detach of protection store: {cloud_protection_store_id_list[0]} from old PSGW.")
    protection_stores_response = atlas.get_protection_stores()
    verify_protection_store_detached_from_old_storeonce(old_storeonce_id, protection_stores_response)
    logger.info(f"Protection store: {cloud_protection_store_id_list[0]} successfully detached from old PSGW.")


def verify_protection_store_detached_from_old_storeonce(storeonce_id, protection_stores_response):
    """Verifies whether protection store is succesfully detached from old psg.

    Args:
        psgw_id (_type_): PSGW id
        protection_stores_response (_type_): Response of get all protection stores.
    """
    assert (
        protection_stores_response.status_code == codes.ok
    ), f"Protection stores not fetched properly: {protection_stores_response.status_code}, {protection_stores_response.text}"
    for protection_store in protection_stores_response.json().get("items"):
        if protection_store["storageSystemInfo"]["id"] == storeonce_id:
            assert f"Protection Store still attached to old PSGW: {storeonce_id}"


def delete_protection_stores(context: Context, force=False, expected_err=False):
    """It deletes the on premises protection store and cloud protection ids.
    Args:
        context (Context): object of a context class
        force(False):force will be either true or false
    """
    (
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    ) = get_protection_store_ids(context)
    protection_store_id_list = onprem_protection_store_id_list + cloud_protection_store_id_list
    if expected_err is True:
        logger.info(f"Deleting cloud protection store id {cloud_protection_store_id_list[0]}")
        delete_protection_store_by_id(
            context,
            cloud_protection_store_id_list[0],
            force=force,
            expected_err=expected_err,
        )
        return
    for protection_store_id in protection_store_id_list:
        logger.info(protection_store_id)
        delete_protection_store_by_id(context, protection_store_id, force=force)


def delete_protection_store_by_id(context: Context, protection_store_id, force=False, expected_err=False):
    atlas = context.storeonces
    response = atlas.delete_protection_store(protection_store_id, force=force)
    if expected_err is True:
        response_err_msg = response.json().get("message")
        logger.info(response_err_msg)
        exp_error_msg = ERROR_MESSAGE_DELETE_PROTECTION_STORE_WITH_BACKUP_WITHOUT_USING_FORCE
        assert (
            response.status_code == codes.precondition_failed or response.status_code == codes.bad_request
        ), f"Failed, Expected status code: {codes.bad_request} but received {response.status_code}"
        assert re.search(
            response_err_msg, exp_error_msg
        ), f"Failed to validate error message EXPECTED: {exp_error_msg} ACTUAL: {response_err_msg}"
        logger.info(f"Successfully validated error message EXPECTED: {exp_error_msg} ACTUAL: {response_err_msg}")
        return
    assert (
        response.status_code == codes.accepted
    ), f"Failed, Expected status code: {codes.accepted} but received {response.status_code}"
    task_id = tasks.get_task_id_from_header(response)
    timeout = TimeoutManager.task_timeout
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout=timeout,
        interval=30,
        message="Delete protection store time exceed 3 minutes - TIMEOUT",
    )
    assert (
        status == "succeeded"
    ), f"Failed to delete protection store: {protection_store_id}, {tasks.get_task_error(task_id, context.user)}"
    logger.info(f"Delete protection store: {protection_store_id} succeeded.")


def get_protection_store_ids(context: Context):
    """It will return the on premises protection store ids and cloud protection store ids.
    Args:
        context (Context): object of a context class
    """
    atlas = context.storeonces
    (
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    ) = atlas.get_on_premises_and_cloud_protection_store(context)
    assert all([onprem_protection_store_id_list, cloud_protection_store_id_list]), "Failed to get protection stores."
    return onprem_protection_store_id_list, cloud_protection_store_id_list
