import logging
import re
from requests import codes
from waiting import wait, TimeoutExpired
import string
import random
from datetime import date, timedelta, datetime
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.api.catalyst_gateway import CatalystGateway
from lib.common.error_messages import ERROR_MESSAGE_PROTECTION_NAME_EXISTS
from lib.dscc.backup_recovery.protection_policies.api.protection_templates import ProtectionTemplate
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.copy_pool_types import CopyPoolTypes
from lib.dscc.tasks.api.tasks import TaskManager
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.backup_steps import wait_for_backup_task, wait_for_backup_task_with_retry
from tests.steps.tasks import tasks
from utils.timeout_manager import TimeoutManager

logger = logging.getLogger()


def create_protection_template(
    context: Context,
    cloud_region=AwsStorageLocation.any,
    onprem_expire_value=1,
    cloud_expire_value=1,
    check_error_msg=False,
):
    """
    This step creates protection template with all three types of backup types and also it creates protection stores
    if they are not available.

    Args:
        context (Context): context object
        cloud_region (_type_, optional): cloud region in which user wants create the template. Defaults to AwsStorageLocation.any.
        create_cloud_pool (bool, optional): if user does not want to create protection store then he can pass False. Defaults to True.
    """
    template = ProtectionTemplate(context.user)
    atlas = CatalystGateway(context.user)
    item = template.get_protection_template_by_name(context.local_template)
    if item:
        if item["name"] == context.local_template:
            logger.info("Protection template already exists, lets continue...")
            return

    # Create cloud protection store
    create_protection_store(context, type=CopyPoolTypes.cloud, cloud_region=cloud_region)

    # This aws region parameter is needed to filter backups based on region.
    context.aws_region = cloud_region.value
    logger.info(f"Creating protection policy with name: {context.local_template}")
    onprem_protection_store_id_list = []
    cloud_protection_store_id_list = []
    onprem_protection_store_id_list, cloud_protection_store_id_list = atlas.get_on_premises_and_cloud_protection_store(
        context
    )
    assert all([onprem_protection_store_id_list, cloud_protection_store_id_list]), "Failed to get protection stores."
    # verifying the DO id is present on the protection store.
    verify_status_and_data_orchestrator_info_on_protection_store(context, onprem_protection_store_id_list)
    verify_status_and_data_orchestrator_info_on_protection_store(context, cloud_protection_store_id_list)
    response = template.create_protection_template(
        context.local_template,
        "YEARS",
        onprem_expire_value,
        cloud_expire_value,
        "WEEKLY",
        1,
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    )
    if check_error_msg is False:
        assert response.status_code == codes.ok, f"create protection policy failed with status : {response.status_code}"
        assert (
            ERROR_MESSAGE_PROTECTION_NAME_EXISTS not in response.text
        ), f"We got wrong message '{ERROR_MESSAGE_PROTECTION_NAME_EXISTS}' in response: {response.text}"
        content = response.json()
        local_template_id = content["id"]
        assert isinstance(local_template_id, str), f"Invalid template id found: {local_template_id}"
        context.local_template_id = local_template_id
        logger.info(
            f"Successfully created protection policy with name: {context.local_template} and ID: {context.local_template_id}"
        )
    else:
        assert (
            response.status_code == codes.bad_request
        ), f"Failed, Expected status code: {codes.bad_request} but received {response.status_code}"
        expected_error = response.json()["message"]
        return expected_error


def verify_status_and_data_orchestrator_info_on_protection_store(context, protection_store_ids):
    """
    Args:
        context: test_context
        protection_store_ids : accepts any number of protection store ids and check it has DO info.
    """
    atlas = CatalystGateway(context.user)
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
        timeout = 600
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


def create_protection_template_with_multiple_cloud_regions(
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
        create_policy_with_existing_store (bool, optional): Directly jumps to create protection policy. Defaults to False.
    """
    logger.info("Started Creation of protection policy with multiple cloud schedules..")
    template = ProtectionTemplate(context.user)
    atlas = CatalystGateway(context.user)
    # Creating new cloud protection stores
    if create_policy_with_existing_store is False:
        for region in cloud_regions:
            logger.info(f"Creating cloud protection store with region as {region}")
            create_protection_store(context, type=CopyPoolTypes.cloud, cloud_region=region)

    onprem_protection_store_id_list, cloud_protection_store_id_list = atlas.get_on_premises_and_cloud_protection_store(
        context
    )
    assert all([cloud_protection_store_id_list]), "Failed to get cloud protection stores."

    response = template.create_protection_template_with_multiple_cloud_regions(
        context.local_template + str("policy"),
        "YEARS",
        onprem_expire_value,
        cloud_expire_value,
        "WEEKLY",
        1,
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    )
    assert response.status_code == codes.ok, f"create protection policy failed with status : {response.status_code}"
    logger.info(f"Response for creating policy with multiple region{response.content}")
    context.local_template = context.local_template + str("policy")

    content = response.json()
    local_template_id = content["id"]
    assert isinstance(local_template_id, str), f"Invalid template id found: {local_template_id}"
    context.local_template_id = local_template_id
    logger.info(
        f"Successfully created protection policy with multiple stores, name: {context.local_template} and ID: {context.local_template_id}"
    )

    template_id_multiple_cloud_region = cloud_protection_store_id_list[1]
    logger.info(f"protection store id for another cloud region {template_id_multiple_cloud_region}")
    return template_id_multiple_cloud_region


def assign_protection_template_to_vm(
    context: Context, backup_granularity_type: str = "VMWARE_CBT", check_error=False, return_task_id=False
):
    """
    This method assigns protection template to a vm which is availble under the provided vcenter.

    Args:
        context (Context): context object
        backup_granularity_type (str, optional): Defaults to "VMWARE_CBT".
    """
    is_vm_protected = get_vm_protection_status(context)
    if is_vm_protected:
        logger.info(f"{context.vm_name} already in protected state, Lets continue...")
        return
    backup_name = "Run snapshot schedule"
    task = TaskManager(context.user)
    hypervisior = context.hypervisor_manager
    virtual_machines_path = f"{hypervisior.atlas_api['virtual_machines']}"
    virtual_machines = f"{hypervisior.hybrid_cloud}/{hypervisior.dscc['beta-version']}/{virtual_machines_path}"
    filter = f"?offset=0&limit=10&sort=createdAt+desc&filter='backup-and-recovery' in services and sourceResourceUri in ('/{virtual_machines}/{context.vm_id}')"
    response = task.get_task_by_filter(filter).json()
    search_for_correct_task = [response for response in response["items"] if backup_name in response["name"]]
    if len(search_for_correct_task) > 0:
        task_id = search_for_correct_task[0]["id"]
        context.last_snapshot_task_id = task_id
    logger.info(f"Assigning protection policy: {context.local_template} to the VM: {context.vm_name}")
    local_backup_id: str = ""
    snapshot_id: str = ""
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
    # snapshot_id, local_backup_id, cloud_backup_id = [protection['id']
    # for protection in protection_template['protections']]
    for protection in protection_template["protections"]:
        pid = protection["schedules"][0]["scheduleId"]
        if pid == 1:
            snapshot_id = protection["id"]
        elif pid == 2:
            local_backup_id = protection["id"]
        elif pid == 3:
            cloud_backup_id = protection["id"]
    response = template.post_protect_vm(
        asset_name=asset_name,
        asset_type=asset_type,
        asset_id=asset_id,
        template_id=template_id,
        snapshot_id=snapshot_id,
        local_backup_id=local_backup_id,
        cloud_backup_id=cloud_backup_id,
        backup_granularity_type=backup_granularity_type,
    )
    assert response.status_code == codes.accepted, f"{response.content}"
    task_id = tasks.get_task_id_from_header(response)
    if return_task_id:
        return task_id
    status = tasks.wait_for_task(task_id, context.user, timeout)
    assert status == "succeeded", f"Assign protection policy failed {task_id} : {status}"
    logger.info(f"Successfully assigned protection policy: {context.local_template} to the VM: {context.vm_name}")
    wait_for_backup_task_with_retry(context, backup_name, check_error=check_error)


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


def unassign_protecion_policy(context: Context, job_id, template, ignore_assert: bool = False):
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
        if ignore_assert:
            if status == "succeeded":
                logger.info(f"Successfully unprotect vm task id: {task_id} : {status}")
            else:
                logger.info(f"Failed to unprotect vm task id: {task_id}")
        else:
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


def delete_unassinged_protection_policy_list(context, template_list):
    for template in template_list:
        context.local_template = template
        delete_unassinged_protection_policy(context)


def get_vm_protection_status(context):
    if not context.vm_id:
        raise Exception("Failed to find VM ID in context file.")
    vm_response = context.hypervisor_manager.get_vm_info(context.vm_id)
    assert vm_response.status_code == codes.ok, f"Failed to get {context.vm_name} info {vm_response.content}"
    vm_info = vm_response.json()
    logger.info(f"{context.vm_name} response is: {vm_info}")
    if (
        vm_info["name"] == context.vm_name
        and vm_info["protectionStatus"] == "PROTECTED"
        or vm_info["protectionStatus"] == "PARTIAL"
    ):
        logger.info(f"{context.vm_name} is in protected state")
        return True
    else:
        logger.info(f"{context.vm_name} is not in protected state")
        return False


def create_protection_store(context, type, cloud_region=AwsStorageLocation.AWS_US_WEST_1, return_task_id=False):
    """This will create either (cloud/on premises) of the protection store based on type.
    Args:
        context (_type_): provide context object which is common accross the test.
        cloud_region (_type_, optional): regions where you want to create schedules. Defaults to AwsStorageLocation.AWS_US_WEST_1.
        type (str, optional): type of protection store.
    """
    atlas = CatalystGateway(context.user)
    psgw_id = atlas.get_catalyst_gateway_id(context)
    display_name_suffix = "".join(random.choice(string.ascii_letters) for _ in range(3))
    display_name = f"{context.psgw_name.split('#')[0]}_{display_name_suffix}"
    if type == CopyPoolTypes.cloud:
        protection_store_payload = {
            "displayName": f"CLOUD_{display_name}",
            "protectionStoreType": "CLOUD",
            "storageLocationId": cloud_region.value,
            "storageSystemId": psgw_id,
        }
    elif type == CopyPoolTypes.local:
        protection_store_payload = {
            "displayName": f"ON_PREMISES_{display_name}",
            "protectionStoreType": "ON_PREMISES",
            "storageSystemId": psgw_id,
        }
    logger.info(f"Protection store creation payload: {protection_store_payload}")
    response = atlas.create_protection_store(protection_store_payload)
    assert (
        response.status_code == codes.accepted
    ), f"Failed to create {display_name} protection store of type {type}. Response: {response.content}"

    task_id = tasks.get_task_id_from_header(response)
    if return_task_id:
        return task_id
    timeout = TimeoutManager.create_psgw_timeout
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout,
        message=f"Create {display_name} protection store {type}  {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert (
        status == "succeeded"
    ), f"We got wrong status: {status} for task: {tasks.get_task_object(user=context.user, task_id=task_id)}"
    logger.info(f"Create {display_name} protection store succeeded of type {type}.")


def verify_cloud_protection_store_error(
    context: Context,
    storage_location_id: str = "",
    response_code: int = codes.bad_request,
    error_message: str = "",
) -> None:
    """verify the error message of while creating the cloud protection store.
    Args:
        storage_location_id (str, optional): eg. AwsStorageLocation.AWS_US_WEST_1.value  Defaults to "".
        response_code : Defaults to codes.bad_request.
        error_message (str, optional): Defaults to "".
    """
    atlas = context.catalyst_gateway
    psgw_id = atlas.get_catalyst_gateway_id(context)
    protection_store_payload = {
        "displayName": "CLOUD_storage_loc_test",
        "protectionStoreType": "CLOUD",
        "storageLocationId": storage_location_id,
        "storageSystemId": psgw_id,
    }
    response = atlas.create_protection_store(protection_store_payload)
    assert (
        response.status_code == response_code
    ), f"Expected response status :{response_code}, Received Response: {response.content}"
    assert re.search(error_message, response.text), f"Failed to validate {error_message} in {response.text}"


def delete_protection_stores_for_cleanup(
    context: Context, protection_store_id: str, protection_store_display_name: str
):
    """
       Delete unused protection store in dscc.
    Args:
        context (Context): context object
        protection_store_id: It will delete protection store with force true
        protection_store_display_name: It will display name for the protection store name.
    """
    atlas = context.catalyst_gateway
    response = atlas.delete_protection_store(protection_store_id, force=True)
    if response.status_code == codes.accepted:
        task_id = tasks.get_task_id_from_header(response)
        logger.info(f"Delete protection store, Task ID: {task_id}")
        status = tasks.wait_for_task(
            task_id,
            context.user,
            timeout=TimeoutManager.health_status_timeout,
            interval=30,
            message="Delete protection store time exceed 5 minutes - TIMEOUT",
        )
        if status == "succeeded":
            logger.info(f"Successfully delete protection store {protection_store_display_name}:{protection_store_id}")
        else:
            logger.info(
                f"Failed to delete protection store {protection_store_display_name}:{protection_store_id} and task id {task_id}"
            )
    else:
        error_message = response.json()["message"]
        logger.info(
            f"Failed to delete protection store {protection_store_display_name}:{protection_store_id} and error message is {error_message}"
        )


def unprotect_vm_delete_policy_for_cleanup_stores(context: Context, protections_stores_deleted_list: list):
    """
    Get the protection list and check whether protection store is protected state if it is
    protected,uprotect vm and delete policy for that vm.
    Args:
        context (Context): context object
        protections_stores_deleted_list (list):It will list protection stores neeed to be deleted
    """
    template = context.protection_template
    policy_response = template.get_protection_templates().json()
    for item in policy_response["items"]:
        policy_id = item["id"]
        policy_name = item["name"]
        for protection in item["protections"]:
            if "protectionStoreInfo" in protection:
                store_id_from_policy = protection["protectionStoreInfo"]["id"]
                if store_id_from_policy in protections_stores_deleted_list:
                    if item["assigned"] == True:
                        protection_job_id = item["protectionJobsInfo"][0]["id"]
                        unassign_protecion_policy(context, protection_job_id, template, ignore_assert=True)
                        delete_policy_for_protection_stores_cleanup(context, policy_id)
                    else:
                        delete_policy_for_protection_stores_cleanup(context, policy_id)
                        logger.info(f"Successfully delete the protection policy {policy_name}")
            else:
                logger.info(f"ProtectionStoreInfo key is not present,as its very old stale policy {policy_name}")


def get_two_days_older_protection_stores_info(context: Context) -> tuple[list, str]:
    """
    Getting two days older protection stores that should not start with dnd and sanity.
    Args:
        context (Context): context object
    Returns:
    protections_stores_deleted_list(list): It will return the protection stores list to be deleted
    protection_store_display_name(str): It will return the display name for protection stores
    """
    atlas = context.catalyst_gateway
    protection_stores_response = atlas.get_protection_stores().json()
    logger.info(f"Protection store response : {protection_stores_response}")
    two_days_old_date = date.today() - timedelta(days=2)
    protections_stores_deleted_list = []
    protection_store_display_name = None
    for ps_response in protection_stores_response["items"]:
        protection_store_display_name = ps_response["displayName"]
        protection_store_createdat = ps_response["createdAt"]
        protection_store_createdat_date = datetime.strptime(protection_store_createdat, "%Y-%m-%dT%H:%M:%S.%fZ").date()
        if (
            (protection_store_createdat_date < two_days_old_date)
            and not (protection_store_display_name.startswith("dnd"))
            and not ("sanity" in protection_store_display_name)
        ):
            protection_store_id = ps_response["id"]
            protections_stores_deleted_list.append(protection_store_id)
    return protections_stores_deleted_list, protection_store_display_name


def delete_policy_for_protection_stores_cleanup(context: Context, policy_id: str):
    """
    Delete protection policy for unprotect vm

    Args:
        context (Context): context object
        policy_id(str)-It will delete the unused policy
    """
    template = context.protection_template
    response = template.delete_policy(policy_id)
    if response.status_code != codes.no_content:
        logger.info(f"Error deleting the protection policy: {response.content}")
