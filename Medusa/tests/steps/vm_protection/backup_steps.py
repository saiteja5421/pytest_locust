import logging
from datetime import datetime
from time import sleep
from datetime import datetime, timedelta
import requests
from requests import codes
from tenacity import retry, stop_after_delay, wait_fixed, retry_if_exception_type
from waiting import wait, TimeoutExpired
from lib.common.error_messages import ERROR_MESSAGE_BACKUP_ON_PSG_AND_VM_ON_SAME_DATASTORE

from lib.dscc.tasks.api.tasks import TaskManager
from lib.dscc.backup_recovery.vmware_protection.vcenter.api.hypervisor_manager import HypervisorManager
from lib.dscc.backup_recovery.protection_policies.api.protection_templates import ProtectionTemplate
from lib.common.enums.backup_type_param import BackupTypeParam
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from lib.common.enums.restore_type import RestoreType
from lib.common.enums.task_status import TaskStatus
from lib.dscc.backup_recovery.vmware_protection.backup_restore.models.backup_usage_compare import (
    BackupUsageCompare,
    CompareType,
)
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.vmware_steps import VMwareSteps
from tests.steps.tasks import tasks
from lib.dscc.backup_recovery.vmware_protection.common.custom_error_helper import IDNotFoundError
from utils.timeout_manager import TimeoutManager

logger = logging.getLogger()


def change_backup_expiration_time(backup_type, context: Context):
    backups: dict
    backup_count: int
    backup_type = backup_type.value
    hypervisor_manager = context.hypervisor_manager
    if not context.vm_id:
        logger.info("There is no vm id - exit")
        return

    asset_id = context.vm_id
    response = hypervisor_manager.get_backups(asset_id, backup_type)
    if response.status_code == codes.ok:
        backups = response.json()
        backup_count = backups["total"]
        logger.info(f"Total backups available : {backup_count}")
        if backup_count > 0:
            for backup in backups["items"]:
                backup_id = backup["id"]
                backup_name = backup["name"]
                logger.info(f"Backup name : {backup_name}, Backup id : {backup_id}")
                response = hypervisor_manager.change_expiration(asset_id, backup_id, backup_name)
                if response.status_code == codes.accepted:
                    task_id = tasks.get_task_id_from_header(response)
                    try:
                        status = tasks.wait_for_task(
                            task_id,
                            context.user,
                            timeout=TimeoutManager.standard_task_timeout,
                            message=f"Failed to change expiration time of backup : {backup_name}, id: {backup_id}",
                        )
                        logger.info(
                            f"Changing expiration time of Backup {backup_name}, id {backup_id}, status: {status}"
                        )
                    except TimeoutError:
                        assert (
                            status == "succeeded"
                        ), f"Change expiration time of backup task id {task_id} failed for {backup_name}: {backup_id}"
                else:
                    assert (
                        response.status_code == codes.accepted
                    ), f"Error in changing the expiration time for {backup_name}: {backup_id}: {response.content}"
            logger.info(f"Expiration time of all the backups are changed nearer to current time.")
        else:
            assert backup_count > 0, f"No backups availale to change expiration time"
    else:
        assert (
            response.status_code == codes.ok
        ), f"Failed to get the backup information for {context.vm_name}: {response.content}"


def validate_expired_backup_delete(backup_type, context: Context):
    logger.info(f"Validating expired cloud backups.")
    backups: dict
    backup_count: int
    backup_type = backup_type.value
    hypervisor_manager = context.hypervisor_manager
    if not context.vm_id:
        logger.info("There is no vm id - exit")
        return

    asset_id = context.vm_id
    current_time = datetime.now()
    end_time = datetime.now() + timedelta(minutes=45)
    # Keep on fetching backups till 45 minutes at 5 minutes of interval.
    while current_time < end_time:
        logger.info(f"Sleeping again for 5 minutes to wait for the expired backup deletion.")
        sleep(300)
        response = hypervisor_manager.get_backups(asset_id, backup_type)
        if response.status_code == codes.ok:
            backups = response.json()
            backup_count = backups["total"]
            logger.info(f"Backups are : {backups}")
            if backup_count > 0:
                logger.info(f"Updated Backups are not deleted yet. Wait for some more time.")
            else:
                break
        else:
            assert response.status_code == codes.ok, f"Failed to get backups details : {response.text}"
    assert current_time < end_time, f"All expired backups are not deleted."
    logger.info(f"All expired backups are deleted.")


def run_backup(context: Context, backup_type=BackupTypeScheduleIDs.cloud, multiple_stores=False):
    """
    This step performs run backup after successfully create and assigne protection policy to vm

    Args:
        context (Context): context object
        backup_type (optional): on which backup type user want to take the backup. Defaults to BackupTypeScheduleIDs.cloud.
        multiple_stores: It will be true if protection template has multiple on_prem/cloud/snapshot store. By default it is set to false.

    Raises:
        Exception: Raises exception if a protection policy not assigned to a vm.
    """
    app_data_management_job_id: str = ""
    template = ProtectionTemplate(context.user)
    response = template.get_app_data_management_job(context.vm_name)
    assert response.status_code == codes.ok, f"{response.content}"
    content = response.json()
    if content["total"] == 1:
        app_data_management_job_id = content["items"][0]["id"]
    else:
        logger.warning(f"Protection policy is not assigned to the asset {context.vm_name}")
        raise Exception("No protection job found to trigger the backup")

    backups_list = context.hypervisor_manager.get_backups(context.vm_id, "backups")
    assert backups_list.status_code == codes.ok, f"{backups_list.content}"
    backups_list = backups_list.json()
    snapshots_list = context.hypervisor_manager.get_backups(context.vm_id, "snapshots")
    assert snapshots_list.status_code == codes.ok, f"{snapshots_list.content}"
    snapshots_list = snapshots_list.json()

    if multiple_stores:
        schedule_ids = search_schedule_id_of_stores(context, backup_type)
        logger.info(f"Schedule ids to run backup: {schedule_ids}")
        backup_job_result = template.post_backup_run(
            app_data_management_job_id, backup_type, schedule_ids, multiple_stores
        )
    else:
        backup_job_result = template.post_backup_run(app_data_management_job_id, backup_type)
    assert backup_job_result.status_code == codes.accepted, f"{response.content}"
    task_id = tasks.get_task_id_from_header(backup_job_result)
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout=TimeoutManager.create_psgw_timeout,  # increased timeout for taking backup of large vm
        interval=30,
        message=f"Backup job failed to complete within {TimeoutManager.create_psgw_timeout} seconds",
    )
    assert status == "succeeded", f"Run backup task {task_id} : {status}"
    logger.info("Successfully ran the backup job")
    validate_new_backups(context, backups_list, snapshots_list, backup_type)


def search_schedule_id_of_stores(context: Context, backup_type):
    """It will search of schedule ids of protection template and returns ids based on backup type.

    Args:
        context (_type_): context object
        backup_type (_type_): type of backup i.e., cloud or local

    Returns:
        _type_: list of schedule ids
    """
    onprem_schedule_ids = []
    cloud_schedule_ids = []
    snapshot_schedule_ids = []
    template_id = context.local_template_id
    template = ProtectionTemplate(context.user)
    protection_policy_response = template.get_protection_template(template_id)
    assert protection_policy_response.status_code == codes.ok, f"{protection_policy_response.content}"
    protection_policies = protection_policy_response.json()
    for policy in protection_policies["protections"]:
        pid = policy["schedules"][0]["scheduleId"]
        if "Array_Snapshot" in policy["schedules"][0]["name"]:
            snapshot_schedule_ids.append(pid)
        elif "On-Premises" in policy["schedules"][0]["name"]:
            onprem_schedule_ids.append(pid)
        elif "HPE_Cloud" in policy["schedules"][0]["name"]:
            cloud_schedule_ids.append(pid)
    if backup_type == BackupTypeScheduleIDs.cloud:
        return cloud_schedule_ids

    elif backup_type == BackupTypeScheduleIDs.local:
        return onprem_schedule_ids

    elif backup_type == BackupTypeScheduleIDs.snapshot:
        return snapshot_schedule_ids


def run_backup_for_storeonce(context: Context, backup_type=BackupTypeScheduleIDs.storeonce, multiple_stores=False):
    """
        this method the trigger the run for local and cloud.
    Args:
        backup_type (BackupTypeScheduleIDs, optional): BackupTypeScheduleIDs.storeonce.
    """
    app_data_management_job_id: str = ""
    template = ProtectionTemplate(context.user)
    response = template.get_app_data_management_job(context.vm_name)
    assert response.status_code == codes.ok, f"{response.content}"
    content = response.json()
    if content["total"] == 1:
        app_data_management_job_id = content["items"][0]["id"]
    else:
        logger.warning(f"Protection policy is not assigned to the asset {context.vm_name}")
        raise Exception("No protection job found to trigger the backup")

    backups_list = context.hypervisor_manager.get_backups(context.vm_id, "backups")
    assert (
        backups_list.status_code == codes.ok
    ), f"Failed to find virtual machine backup list info {backups_list.content}"
    backups_list = backups_list.json()
    logger.info(backups_list)
    if multiple_stores:
        schedule_ids = search_schedule_id_of_stores_for_storeonce(context, backup_type)
        logger.info(f"Schedule ids to run backup: {schedule_ids}")
        backup_job_result = template.post_backup_run(
            app_data_management_job_id, backup_type, schedule_ids, multiple_stores
        )
    else:
        backup_job_result = template.post_backup_run(app_data_management_job_id, backup_type)
    assert backup_job_result.status_code == codes.accepted, f"Failed to run a backup job {response.content}"
    task_id = tasks.get_task_id_from_header(backup_job_result)
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout=TimeoutManager.create_backup_timeout,
        interval=30,
        message=f"Backup job failed to complete within {TimeoutManager.create_backup_timeout} seconds",
    )
    assert status == "succeeded", f"Run backup task {task_id} : {status}"
    validate_new_backups_for_storeonce(context, backups_list, backup_type)


def search_schedule_id_of_stores_for_storeonce(context: Context, backup_type):
    """It will search of schedule ids of protection template and returns ids based on backup type.

    Args:
        context (_type_): context object
        backup_type (_type_): type of backup i.e., cloud or local

    Returns:
        _type_: list of schedule ids
    """
    onprem_schedule_ids = []
    cloud_schedule_ids = []
    template_id = context.local_template_id
    template = ProtectionTemplate(context.user)
    protection_policy_response = template.get_protection_template(template_id)
    assert protection_policy_response.status_code == codes.ok, f"{protection_policy_response.content}"
    protection_policies = protection_policy_response.json()
    for policy in protection_policies["protections"]:
        pid = policy["schedules"][0]["scheduleId"]
        if "On-Premises" in policy["schedules"][0]["name"]:
            onprem_schedule_ids.append(pid)
        elif "HPE_Cloud" in policy["schedules"][0]["name"]:
            cloud_schedule_ids.append(pid)
    if backup_type == BackupTypeScheduleIDs.cloud:
        return cloud_schedule_ids

    elif backup_type == BackupTypeScheduleIDs.local:
        return onprem_schedule_ids


def run_backup_and_check_usage(context, backup_type=BackupTypeScheduleIDs.cloud, multiple_stores=False):
    backup_usage = BackupUsageCompare(context)
    run_backup(context, backup_type=backup_type, multiple_stores=multiple_stores)
    backup_usage.wait_for_usage_compare(CompareType.greater, backup_type)


def validate_new_backups_for_storeonce(context: Context, backups_list, backup_type: BackupTypeScheduleIDs):
    """
    this method validate  local and cloud backup for storeonce
    """
    if backup_type == BackupTypeScheduleIDs.local:
        _type = "On-Premises"
        _type_search = "backups"
        backup_name = "Run backup schedule"
        logger.info("Waiting local backup validation")
        wait_for_backup_task_with_retry(context, backup_name)
        wait_for_backup(context, backups_list, _type_search, _type)
    if backup_type == BackupTypeScheduleIDs.storeonce:
        _type = "HPE_Cloud"
        _type_search = "backups"
        backup_name = "Run cloud backup schedule"
        logger.info("Waiting cloud backup validation")
        wait_for_backup_task_with_retry(context, backup_name)
        wait_for_backup(context, backups_list, _type_search, _type)


def delete_backup_and_check_usage(context, backups_taken: int = 1, backup_type=BackupTypeScheduleIDs.cloud):
    datastore_usage = 1000
    user_bytes_expected = backups_taken * datastore_usage
    backup_usage = BackupUsageCompare(
        context, user_bytes_local_diff=user_bytes_expected, user_bytes_cloud_diff=user_bytes_expected
    )
    delete_all_backups(BackupTypeParam.backups, context)
    backup_usage.wait_for_usage_compare(CompareType.less, backup_type)


def validate_new_backups(context: Context, backups_list, snapshots_list, backup_type: BackupTypeScheduleIDs):
    _type = "Array_Snapshot"
    _type_search = "snapshots"
    logger.info("Waiting snapshot validation")
    backup_name = "Run snapshot schedule"
    wait_for_backup_task_with_retry(context, backup_name)
    wait_for_backup(context, snapshots_list, _type_search, _type)
    if backup_type == BackupTypeScheduleIDs.local:
        _type = "On-Premises"
        _type_search = "backups"
        backup_name = "Run backup schedule"
        logger.info("Waiting local backup validation")
        wait_for_backup_task_with_retry(context, backup_name)
        wait_for_backup(context, backups_list, _type_search, _type)
    if backup_type == BackupTypeScheduleIDs.cloud:
        _type = "HPE_Cloud"
        _type_search = "backups"
        backup_name = "Run cloud backup schedule"
        logger.info("Waiting cloud backup validation")
        wait_for_backup_task_with_retry(context, backup_name)
        wait_for_backup(context, backups_list, _type_search, _type)


def wait_for_backup_task(context, backup_name, check_error=False):
    task = TaskManager(context.user)
    hypervisior = context.hypervisor_manager
    virtual_machines_path = f"{hypervisior.atlas_api['virtual_machines']}"
    virtual_machines = f"{hypervisior.hybrid_cloud}/{hypervisior.dscc['beta-version']}/{virtual_machines_path}"
    filter = f"?offset=0&limit=10&sort=createdAt+desc&filter='backup-and-recovery' in services and sourceResourceUri in ('/{virtual_machines}/{context.vm_id}')"
    response = task.get_task_by_filter(filter).json()
    search_for_correct_task = [response for response in response["items"] if backup_name in response["name"]]
    logger.info(f"Response is : {response}")
    assert (
        len(search_for_correct_task) != 0
    ), f"Job for: '{backup_name}' has not been found. We got empty list: {search_for_correct_task} in a response {response['items']}"
    task_id = search_for_correct_task[0]["id"]
    assert (
        not context.last_snapshot_task_id or task_id != context.last_snapshot_task_id
    ), "New task hasn't been created."

    # checking for the error message on backup task
    if check_error:
        status = tasks.wait_for_task(
            task_id,
            context.user,
            timeout=120,
            interval=30,
        )
        if status == "failed":
            error_message = tasks.get_task_error(task_id, context.user)
            if ERROR_MESSAGE_BACKUP_ON_PSG_AND_VM_ON_SAME_DATASTORE in error_message:
                logger.info(f"Successfully validated error message")
            else:
                logger.error(
                    f"Failed to validate error message EXPECTED: {ERROR_MESSAGE_BACKUP_ON_PSG_AND_VM_ON_SAME_DATASTORE} ACTUAL: {error_message}"
                )
                assert (
                    False
                ), f"Failed to validate error message EXPECTED: {ERROR_MESSAGE_BACKUP_ON_PSG_AND_VM_ON_SAME_DATASTORE} ACTUAL: {error_message}"
        else:
            logger.error(f"Task expected to failed. but status received: {status}")
            assert False, f"Task expected to failed. but status received: {status}"
    else:
        status = tasks.wait_for_task(
            task_id,
            context.user,
            timeout=TimeoutManager.create_backup_timeout,
            interval=30,
            message=f"Backup job failed to complete within {TimeoutManager.create_backup_timeout} seconds",
        )
        assert status == "succeeded", f"Run backup task {task_id} : {status}"
        context.last_snapshot_task_id = task_id
        logger.info(f"{backup_name} has been created successfully")


@retry(retry=retry_if_exception_type(AssertionError), stop=stop_after_delay(420), wait=wait_fixed(10))
def wait_for_backup_task_with_retry(context, backup_name, check_error=False):
    wait_for_backup_task(context, backup_name, check_error=check_error)


def wait_for_backup(context: Context, backups_list, type_search, _type):
    asset_id = context.vm_id
    hypervisor_manager = context.hypervisor_manager
    backups = {}

    def _return_condition_backup():
        response = hypervisor_manager.get_backups(asset_id, type_search)
        if response.status_code == codes.ok:
            nonlocal backups
            backups = response.json()
            logger.debug(f"All backups that were found: {backups}")
            if backups["total"] == backups_list["total"]:
                return False

            intersection_list = [x for x in backups["items"] if x not in backups_list["items"]]
            for item in intersection_list:
                if _type in item["name"] and item["state"] == "OK" and item["status"] == "OK":
                    logger.info(f"{item['name']} found.")
                    return True
            return False

    create_backup_timeout = TimeoutManager.create_backup_timeout
    try:
        wait(
            _return_condition_backup,
            timeout_seconds=create_backup_timeout,
            sleep_seconds=20,
        )
    except TimeoutExpired:
        raise AssertionError(
            f"New backups were not found in {create_backup_timeout} seconds, we got response {backups['items']}"
        )


def delete_all_backups(backup_type, context: Context):
    """
    Performs cleanup operation after a successful/failed test case excution to keep the setup ready for next run
    backup type can be 'backup' or'snapshot"
    """
    # Get all backups and delete them.
    logger.info("Delete all backups")
    backups: dict
    backup_count: int
    backup_type = backup_type.value
    hypervisor_manager = context.hypervisor_manager
    if not context.vm_id:
        logger.info("There is no vm id - exit")
        return

    asset_id = context.vm_id
    response = hypervisor_manager.get_backups(asset_id, backup_type)
    if response.status_code == codes.ok:
        backups = response.json()
        backup_count = backups["total"]
        if backup_count > 0:
            for backup in backups["items"]:
                backup_id = backup["id"]
                backup_name = backup["name"]
                logger.info(f"Backup {backup_name}, id {backup_id}")
                response = hypervisor_manager.delete_backup(asset_id, backup_id, backup_type)
                if response.status_code == codes.accepted:
                    task_id = tasks.get_task_id_from_header(response)
                    try:
                        status = tasks.wait_for_task(
                            task_id,
                            context.user,
                            timeout=TimeoutManager.standard_task_timeout,
                            message=f"Failed to delete backup: {backup_name}, id: {backup_id}",
                        )
                        logger.info(f"Backup deleted {backup_name}, id {backup_id}, status: {status}")
                    except TimeoutError:
                        logger.exception(f"Delete backup task failed for {backup_name}: {backup_id}")
                else:
                    logger.error(f"Error deleting the resource {backup_name}: {backup_id}: {response.content}")
                # Todo: Add a debug message if backup delete fails.
        else:
            logger.debug("No backups to delete...")
    else:
        logger.error(f"Failed to get the backup information for {context.vm_name}: {response.content}")


def restore_virtual_machine(context, restore_type, backup_type, quite_time=0):
    restore_type = restore_type.value
    response: requests = requests
    success_message: str
    if restore_type == RestoreType.new.value:
        name = f'restored-{context.vm_name}-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
    else:
        name = context.vm_name
    hypervisor_manager = HypervisorManager(context.user)
    vm_id = context.vm_id
    logger.info(f"Searching for {backup_type} backups")
    backup_id = hypervisor_manager.get_backup_id(vm_id, backup_type)
    logger.info(f"Found {backup_id}")
    datastore_id = context.datastore_id
    host_id = context.esxhost_id
    if backup_id:
        if restore_type == RestoreType.new.value:
            logger.info("Initiating restore operation")
            response = hypervisor_manager.restore_vm(
                vm_id,
                backup_id,
                restore_type,
                backup_type,
                name,
                datastore_id,
                host_id,
                power_on=True,
            )
            success_message = f"Task Success: Restored {context.vm_name} VM to {name} in {context.hypervisor_name}"
        elif restore_type == RestoreType.existing.value:
            response = hypervisor_manager.restore_vm(vm_id, backup_id, restore_type, backup_type)
            success_message = f"Task Success: Restored to existing VM {name} in {context.hypervisor_name}"

        # Todo: Temporary debug log to identify root cause of - {"errorCode":"100005","error":"Failed to perform specified operation.
        # Invalid resource state Error. Allowed states are ('Ok',)."}
        try:
            if response.status_code != codes.accepted:
                logger.debug("Logging all backup lists..")
                logger.debug(context.catalyst_gateway.get_catalyst_gateway_by_name(context.psgw_name))
                logger.debug(hypervisor_manager.get_backups(context.vm_id, "backups").json())
                logger.debug(hypervisor_manager.get_backups(context.vm_id, "snapshots").json())
                logger.debug(hypervisor_manager.get_vms().json())
        except Exception as err:
            logger.debug(f"Debug 'errorCode:100005' log attempt experiance some error. Exception: {err}")

        assert (
            response.status_code == codes.accepted
        ), f"POST call to restore vm returned {response.status_code}: \
                                                        {response.content}"
        logger.info("Restore task initiated")
        task_manager = TaskManager(context.user)
        task_id = tasks.get_task_id_from_header(response)
        status = tasks.wait_for_task(
            task_id,
            context.user,
            timeout=TimeoutManager.standard_task_timeout,
            message=f"Failed to restore virtual machine in {TimeoutManager.standard_task_timeout} secs",
            log_result=True,
        )
        logger.info("Task completed, validating task result")
        task_state = task_manager.get_task_state_by_id(task_id)
        assert (
            task_state == TaskStatus.success.value.lower()
        ), f"Task {task_state}: {tasks.get_task_error(task_id, context.user)}"
        logger.info("Restore task success")
        logger.info(success_message)
    else:
        logger.error(f"No {backup_type} backups found for VM {context.vm_name}")
        assert False
    vcenter = VMwareSteps(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    success = f"VM {name} present in the vCenter {context.vcenter_name} after restortion"
    failure = f"VM {name} is not present in the vCenter {context.vcenter_name} after restoration"

    if restore_type == RestoreType.new.value:
        if vcenter.search_vm(name):
            logger.info(success)
            vcenter.delete_vm(name)
            logger.info("VM deleted")
        else:
            assert False, failure
    else:
        if vcenter.search_vm(context.vm_name):
            logger.info(success)
            sleep(quite_time)
            logger.info("Refreshing VM inventory to update restored VM")
            refresh_task = hypervisor_manager.refresh_vcenter(context.vcenter_id)
            assert refresh_task.status_code == codes.accepted, f"{refresh_task.content}"
            # checking for vcenter refresh task.
            atlas = context.catalyst_gateway
            resource_uri = f"/{atlas.hybrid_cloud}/{atlas.v1beta1}/hypervisor-managers/{context.vcenter_id}"
            display_name = f"Refresh vCenter [{context.vcenter_name}]"
            logger.info("Looking for vcenter refresh task to trigger")
            # wait a bit for create local protectio store, "Trigger" task to be appear
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
                logger.info(f"TimeoutExpired: waiting for 'Trigger' task")
                raise e
            # get the local store task id
            task_id = (
                tasks.get_tasks_by_name_and_resource_uri_with_no_offset(
                    user=context.user, task_name=display_name, resource_uri=resource_uri
                )
                .items[0]
                .id
            )
            logger.info(f"vcenter refresh task ID: {task_id}")
            status = tasks.wait_for_task(
                task_id,
                context.user,
                timeout=TimeoutManager.standard_task_timeout,
                interval=30,
                message=f"Refresh task took more than {TimeoutManager.standard_task_timeout}s",
            )
            assert status == "succeeded", f"Run refresh task {task_id} : {status}"
            try:
                context.vm_id = context.hypervisor_manager.get_id(context.vm_name, context.hypervisor_manager.get_vms())
            except IDNotFoundError:
                logger.error(f"Failed to find VM ID of {context.vm_name} after successful restore")
                raise
            logger.debug(f"Restore successful. UUID of '{context.vm_name}' is '{context.vm_id}'")
        else:
            assert False, failure


def wait_for_snapshot(context, snapshot_list):
    if not snapshot_list:
        snapshot_list = context.hypervisor_manager.get_backups(context.vm_id, BackupTypeParam.snapshots.value).json()
    wait_for_backup(context, snapshot_list, BackupTypeParam.snapshots.value, "Snapshot")
