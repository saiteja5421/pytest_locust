from requests import codes
import logging
import time
from lib.dscc.backup_recovery.protection_policies.api.protection_templates import (
    ProtectionTemplate,
)
from lib.dscc.backup_recovery.vmware_protection.storeonce.api.storeonce import (
    StoreonceManager,
)
from lib.dscc.tasks.api.tasks import TaskManager
from tests.catalyst_gateway_e2e.test_context import Context
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.error_messages import ERROR_MESSAGE_PROTECTION_NAME_EXISTS
from tests.steps.tasks import tasks
from tests.steps.vm_protection.backup_steps import wait_for_backup_task_with_retry
from utils.timeout_manager import TimeoutManager
from lib.common.enums.copy_pool_types import CopyPoolTypes
import random
import string
from waiting import wait, TimeoutExpired

logger = logging.getLogger()


def create_protection_template(
    context: Context,
    cloud_region=AwsStorageLocation.any,
    onprem_expire_value=1,
    cloud_expire_value=1,
    create_cloud_pool=True,
):
    """Create a protection template for storeonce"""
    logger.info("Create protection policy")
    template = ProtectionTemplate(context.user)
    atlas = StoreonceManager(context.user)
    # Create cloud protection store
    create_protection_store(context, type=CopyPoolTypes.cloud, cloud_region=cloud_region)
    onprem_protection_store_id_list = []
    cloud_protection_store_id_list = []
    (
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    ) = atlas.get_on_premises_and_cloud_protection_store(context)
    assert all([onprem_protection_store_id_list, cloud_protection_store_id_list]), "Failed to get protection stores."
    verify_status_and_data_orchestrator_info_on_protection_store(context, onprem_protection_store_id_list)
    verify_status_and_data_orchestrator_info_on_protection_store(context, cloud_protection_store_id_list)

    response = template.create_protection_template_for_storeonce(
        context.local_template,
        "YEARS",
        onprem_expire_value,
        cloud_expire_value,
        "WEEKLY",
        1,
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    )
    assert (
        ERROR_MESSAGE_PROTECTION_NAME_EXISTS not in response.text
    ), f"We got wrong message '{ERROR_MESSAGE_PROTECTION_NAME_EXISTS}' in response: {response.text}"

    content = response.json()
    local_template_id = content["id"]
    assert type(local_template_id) == str, f"Invalid template id found: {local_template_id}"
    context.local_template_id = local_template_id


def verify_status_and_data_orchestrator_info_on_protection_store(context, protection_store_ids):
    """
    Args:
        context: test_context
        *protection_store_ids : accepts any number of protection store ids and check it has DO info.
    """
    atlas = StoreonceManager(context.user)
    assert protection_store_ids is not None, "Protection store id is None"
    ps_ids = []
    if type(protection_store_ids) is list:
        for ps_id in protection_store_ids:
            ps_ids.append(ps_id)
    else:
        ps_ids.append(protection_store_ids)
    for protection_store in ps_ids:
        connected_state = atlas.get_protection_stores_info_by_id(protection_store).get("connectedState")
        state = atlas.get_protection_stores_info_by_id(protection_store).get("state")
        state_reason = atlas.get_protection_stores_info_by_id(protection_store).get("stateReason")
        assert (
            connected_state == "CONNECTED" and state == "ONLINE"
        ), f"Protection store is in {state} and {connected_state} state. State Reason: {state_reason}"
        do_id_for_ps = None
        timeout = 900
        try:
            wait(
                lambda: atlas.get_protection_stores_info_by_id(protection_store).get("dataOrchestratorInfo") != [],
                timeout_seconds=timeout,
                sleep_seconds=(0.1, 10),
            )
            ps_response_json = atlas.get_protection_stores_info_by_id(protection_store)
            DO_info = ps_response_json["dataOrchestratorInfo"]
            logger.info(f"dataOrchestratorInfo before wait: {DO_info}")
            do_id_for_ps = DO_info[0]["id"]
            logger.info(f"Dataorhestrator id found on protection store: {do_id_for_ps}")
        except TimeoutExpired:
            raise TimeoutError(f"failed to get data orchestrator id within {timeout} seconds")


def assign_protection_template_to_vm(context: Context, backup_granularity_type: str = "VMWARE_CBT"):
    task = TaskManager(context.user)
    # response = task.get_task_by_filter(filter).json()
    logger.info("Assign protection policy to VM resource")
    local_backup_id: str = ""
    cloud_backup_id: str = ""
    asset_name = context.vm_name
    asset_id = context.vm_id
    asset_type = context.asset_type["vm"]
    timeout: int = TimeoutManager.standard_task_timeout
    template = ProtectionTemplate(context.user)
    template_id = context.local_template_id
    response = template.get_protection_template(template_id)
    protection_template = response.json()
    assert response.status_code == codes.ok, f"{response.content}"

    # a candidate to replace for loop below
    # local_backup_id, cloud_backup_id = [protection['id']
    # for protection in protection_template['protections']]
    for protection in protection_template["protections"]:
        pid = protection["schedules"][0]["scheduleId"]
        if pid == 1:
            local_backup_id = protection["id"]
        elif pid == 2:
            cloud_backup_id = protection["id"]
    response = template.post_protect_vm_storeonce(
        asset_name=asset_name,
        asset_type=asset_type,
        asset_id=asset_id,
        template_id=template_id,
        local_backup_id=local_backup_id,
        cloud_backup_id=cloud_backup_id,
        backup_granularity_type=backup_granularity_type,
    )
    assert response.status_code == codes.accepted, f"{response.content}"
    task_id = tasks.get_task_id_from_header(response)
    status = tasks.wait_for_task(task_id, context.user, timeout)
    assert status == "succeeded", f"Assign protection policy failed {task_id} : {status}"
    logger.info("Assign protection policy complete")


def unassign_protecion_policy_from_all_vms(context: Context):
    """Unassign Protection Policy from all VMs in given vCenter"""
    # get all vms from vcenter -> vm_list
    vm_list = context.hypervisor_manager.get_vms().json().get("items")
    # for each vm in vm_list
    for vm in vm_list:
        if vm["hypervisorManagerInfo"]["name"] == context.vcenter_name and vm["protected"]:
            context.vm_name = vm["name"]
            # unassigned Protection Policy from this vm
            unassign_protecion_policy_from_vm(context)


def unassign_protecion_policy_from_vm(context: Context):
    """Remove protection policy from the given VM"""
    app_data_management_job_id: str = ""
    template = ProtectionTemplate(context.user)
    response = template.get_app_data_management_job(context.vm_name)
    if response.status_code == codes.ok:
        app_data_management_job = response.json()
        if app_data_management_job["total"] == 1:
            app_data_management_job_id = app_data_management_job["items"][0]["id"]
            unassign_protecion_policy(context, app_data_management_job_id, template)
        else:
            logger.info("No protection policy is assinged to the virtual machine")
    else:
        logger.info(f"Unprotect VM failed: {response.content}")


def unassign_protecion_policy(context: Context, job_id, template):
    """Remove protection policy job from vm or prtection group"""
    response = template.unprotect_vm(job_id)
    if response.status_code == codes.accepted:
        task_id = tasks.get_task_id_from_header(response)
        status = tasks.wait_for_task(
            task_id,
            context.user,
            timeout=TimeoutManager.standard_task_timeout,
            message=f"Failed to Unassign policy from VM within {TimeoutManager.standard_task_timeout} seconds",
        )
        assert status == "succeeded", f"Unprotect task {task_id} : {status}"
        logger.info(f"Unprotect VM {context.vm_name} success")
    else:
        logger.info(f"Unprotect VM {context.vm_name} failed: {response.content}")


def delete_unassinged_protection_policy(context: Context):
    """Delete unassinged protection policy"""
    template = ProtectionTemplate(context.user)
    _template = template.get_protection_template_by_name(context.local_template)
    if _template:
        logger.info(f"Deleting protection policy: {context.local_template}, id:{_template['id']}")
        response = template.delete_policy(_template["id"])
        if response.status_code != codes.no_content:
            logger.info(f"Error deleting the protection policy: {response.content}")
    else:
        logger.info(f"Failed to find protection template with name: {context.local_template}")


def create_protection_template_with_multiple_cloud_regions_for_storeonce(
    context: Context,
    cloud_regions=[AwsStorageLocation.any],
    create_policy_with_existing_store=False,
    onprem_expire_value=1,
    cloud_expire_value=1,
):
    """User this step user can create a protection policy with multiple cloud schedules in it.
    Args:
        context (Context): provide context object which is common accross the test.
        cloud_regions (list, optional): regions where you want to create schedules. Defaults to AwsStorageLocation.any.
        create_cloud_pool (bool, optional): provide option to create cloud pool or not. Defaults to True.
    """
    logger.info("Started Creation of protection policy with multiple cloud schedules..")
    template = ProtectionTemplate(context.user)
    atlas = StoreonceManager(context.user)
    if create_policy_with_existing_store is False:
        for region in cloud_regions:
            logger.info(f"Creating cloud protection store with region as {region}")
            create_protection_store(context, type=CopyPoolTypes.cloud, cloud_region=region)

    (
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    ) = atlas.get_on_premises_and_cloud_protection_store(context)
    assert all([cloud_protection_store_id_list]), "Failed to get protection stores."

    response = template.create_protection_template_with_multiple_cloud_regions_for_storeonce(
        context.local_template + str("policy"),
        "YEARS",
        onprem_expire_value,
        cloud_expire_value,
        "WEEKLY",
        1,
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    )
    assert (
        ERROR_MESSAGE_PROTECTION_NAME_EXISTS not in response.text
    ), f"We got wrong message '{ERROR_MESSAGE_PROTECTION_NAME_EXISTS}' in response: {response.text}"
    assert response.status_code == codes.ok, f"create protection policy failed with status : {response.status_code}"
    logger.info(f"Response for creating policy with multiple region{response.content}")
    context.local_template = context.local_template + str("policy")

    content = response.json()
    local_template_id = content["id"]
    assert type(local_template_id) == str, f"Invalid template id found: {local_template_id}"
    context.local_template_id = local_template_id
    logger.info("Successfully Created Protection Policy with multiple cloud schedules..")


def create_protection_store(context, type, cloud_region=AwsStorageLocation.AWS_US_WEST_1):
    """This will create either (cloud/on premises) of the protection store based on type.
    Args:
        context (_type_): provide context object which is common accross the test.
        cloud_region (_type_, optional): regions where you want to create schedules. Defaults to AwsStorageLocation.AWS_US_WEST_1.
        type (str, optional): type of protection store.
    """
    atlas = StoreonceManager(context.user)
    storeonce_id = atlas.get_storeonce_id(context)
    display_name_suffix = "".join(random.choice(string.ascii_letters) for _ in range(3))
    display_name = f"{context.storeonces_name.split('#')[0]}_{display_name_suffix}"
    if type == CopyPoolTypes.cloud:
        protection_store_payload = {
            "displayName": f"CLOUD_{display_name}",
            "protectionStoreType": "CLOUD",
            "storageLocationId": cloud_region.value,
            "storageSystemId": storeonce_id,
        }
    elif type == CopyPoolTypes.local:
        protection_store_payload = {
            "displayName": f"ON_PREMISES_{display_name}",
            "protectionStoreType": "ON_PREMISES",
            "storageSystemId": storeonce_id,
        }
    logger.info(f"Protection store creation payload: {protection_store_payload}")
    time.sleep(120)
    response = atlas.create_protection_store(protection_store_payload)
    assert (
        response.status_code == codes.accepted
    ), f"Failed to create {display_name} protection store of type {type}. Response: {response.content}"

    task_id = tasks.get_task_id_from_header(response)
    timeout = TimeoutManager.create_psgw_timeout
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout,
        message=f"Create {display_name} protection store succeeded of type {type}. {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert (
        status == "succeeded"
    ), f"We got wrong status: {status} for task: {tasks.get_task_object(user=context.user, task_id=task_id)}"
    logger.info(f"Create {display_name} protection store succeeded of type {type}.")
