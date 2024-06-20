import paramiko
import logging
import os
import re
from requests import codes
from time import sleep
from tenacity import (
    retry,
    stop_after_attempt,
    retry_if_exception_type,
    wait_fixed,
    stop_after_delay,
)
from waiting import wait, TimeoutExpired

from lib.common.enums.vcenter_state import VcenterState
from lib.common.enums.vm_power_option import VmPowerOption
from lib.dscc.backup_recovery.protection_policies.api.protection_templates import ProtectionTemplate
from lib.dscc.tasks.api.tasks import TaskManager
from lib.common.enums.backup_type_param import BackupTypeParam
from lib.common.enums.task_status import TaskStatus
from lib.platform.storage_array.array_api import ArrayApi
from tests.steps.vm_protection import backup_steps
from tests.steps.vm_protection.protection_template_steps import unassign_protecion_policy
from tests.steps.vm_protection.vmware_steps import VMwareSteps
from lib.platform.vmware.vsphere_api import VsphereApi
from lib.platform.vmware.vcenter_details import generate_SmartConnect, get_vm_power_status, power_on_vm
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.tasks import tasks
from lib.dscc.backup_recovery.vmware_protection.common.custom_error_helper import IDNotFoundError, VcenterNotFoundError
from utils.timeout_manager import TimeoutManager

logger = logging.getLogger()


def change_vcenter_password(context, password):
    """This method will change the vcenter user password.

    Args:
        context (Context): context object
        password (String): new password that needs to set to vcenter user
    """
    try:
        logger.info(f"Logging with user {context.vcenter_username}/{context.vcenter_password}:")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            context.vcenter_name,
            port=22,
            username=context.vcenter_username,
            password=context.vcenter_password,
            allow_agent=False,
        )
        logger.info(
            f"Successfully ssh logged into vcenter {context.vcenter_name} through {context.vcenter_username}/{context.vcenter_password}"
        )
        cmd = f"com.vmware.appliance.version1.localaccounts.user.password.update --username test_user --password {password}"
        logger.info(f"Running command to change 'test_user' user password: {cmd}")
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
    except Exception as e:
        logger.error(
            f"Exception while ssh logging through {context.vcenter_username}/{context.vcenter_password}. Error:{e}"
        )
        raise e
    # Checking whether test_user password is updated or not
    try:
        logger.info(f"Checking whether test_user password is changed to {password} or not:")
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            context.vcenter_name,
            port=22,
            username="test_user",
            password=password,
            allow_agent=False,
        )
        logger.info(f"Successfully changed test_user password to {password}")
    except Exception as e:
        logger.error(f"Failed to change test_user password to {password}")
        raise e
    ssh_client.close()


def add_vcenter(context: Context, extended_timeout: bool = False):
    task = TaskManager(context.user)
    logger.info(f"Adding {context.vcenter_name} to DO {context.ope_id}")
    response = context.hypervisor_manager.register_vcenter(
        context.vcenter_name,
        context.vcenter_name,
        context.vcenter_username,
        context.vcenter_password,
        context.ope_id,
    )
    assert response.status_code == codes.accepted, f"{response.content}"
    task_id = task.get_task_id_from_header(response)
    timeout = TimeoutManager.v_center_manipulation_timeout
    if extended_timeout:
        timeout += 180
    status = task.wait_for_task(task_id, timeout)
    if status == "succeeded":
        logger.info(f"Successfully registred vCenter {context.vcenter_name}")
    # assert status == "succeeded", f"We got wrong status: {status} for task: {task.get_task_object(task_id)}"
    else:
        logger.info(f"We got wrong status: {status} for task: {task.get_task_object(task_id)}")
        logger.info(f"Checking availability and state of Vcenter.")
    # Wait for state and status to be in 'Ok' state
    wait_for_vcenter_state(context)

    # sometime we see we are getting 404 vCenter not found as soon as we try to refresh the vCenter when it comes to Ok state..
    sleep(10)

    # Refresh vCenter to ensure all the VM are discovered in the inventory
    logger.info(f"Rebuilding VM inventory {context.vcenter_name}")
    try:
        get_vcenter_refresh_task(context)
    except TypeError:
        logger.warning("vCenter is already present in the Inventory")
        logger.info("Attempting to unregister")
        unregister_vcenter_cascade(context)
        add_vcenter(context)

    logger.info("VM inventory rebuild success")


@retry(
    retry=retry_if_exception_type((VcenterNotFoundError, TimeoutError)),
    stop=stop_after_delay(TimeoutManager.health_status_timeout),
    wait=wait_fixed(5),
    reraise=True,
)
def wait_for_vcenter_state(context, timeout=180, interval=10):
    vcenter = context.hypervisor_manager.get_vcenter_by_name(name=context.vcenter_name)
    vcenter_id = vcenter.get("id")
    try:
        wait(
            lambda: context.hypervisor_manager.get_vcenter_state_by_id(vcenter_id)
            not in [
                VcenterState.INITIALIZING.value,
                VcenterState.CREATING.value,
                VcenterState.REFRESHING.value,
                VcenterState.CONFIGURED.value,
                VcenterState.UPDATING.value,
            ],
            timeout_seconds=timeout,
            sleep_seconds=interval,
        )
    except TimeoutError:
        raise TimeoutError(f"TIME OUT to get valid vCenter state with in {timeout} seconds")
    vcenter_state = context.hypervisor_manager.get_vcenter_state_by_id(vcenter_id)
    assert (
        vcenter_state == VcenterState.OK.value
    ), f"vCenter is not in expected state:{VcenterState.OK.value}, we got: {vcenter_state} for {vcenter.get('name')}"
    logger.info(f"vCenter is in expected state: {vcenter_state}")


def get_vcenter_refresh_task(context):
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
            timeout_seconds=TimeoutManager.standard_task_timeout,
            sleep_seconds=10,
        )
    except TimeoutExpired as e:
        logger.info(f"TimeoutExpired: waiting for 'Trigger' task")
        raise e
    # get the local store task id
    trigger_task_id = (
        tasks.get_tasks_by_name_and_resource_uri_with_no_offset(
            user=context.user, task_name=display_name, resource_uri=resource_uri
        )
        .items[0]
        .id
    )
    logger.info(f"vcenter refresh task ID: {trigger_task_id}")

    # wait for the trigger task to complete
    trigger_task_state = tasks.wait_for_task(
        task_id=trigger_task_id,
        user=context.user,
        timeout=TimeoutManager.create_local_store_timeout,
        log_result=True,
    )
    if trigger_task_state == "succeeded":
        logger.info(f"Successfully refreshed vcenter, task state: {trigger_task_state}")
        return True
    else:
        logger.error(f"Failed to Refresh vCenter [{context.vcenter_name}], task state: {trigger_task_state}")
        return False


def refresh_vcenter_inventory(context, vcenter):
    wait_for_vcenter_state(context)
    response = context.hypervisor_manager.refresh_vcenter(vcenter)
    assert response.status_code == codes.accepted, f"{response.content}"
    get_vcenter_refresh_task(context)
    wait_for_vcenter_state(context)


def unregister_vcenter_cascade(context: Context, force=False):
    template = ProtectionTemplate(context.user)
    vms = context.hypervisor_manager.get_vms().json().get("items")
    _vm_id = None
    if context.vm_id:
        _vm_id = context.vm_id

    for vm in vms:
        if vm["hypervisorManagerInfo"]["name"] == context.vcenter_name:
            context.vm_id = vm["id"]
            backup_steps.delete_all_backups(BackupTypeParam.backups, context)
            backup_steps.delete_all_backups(BackupTypeParam.snapshots, context)
            if "appDataManagementJobInfo" in vm:
                tml_name = vm["appDataManagementJobInfo"]["appDataManagementTemplateInfo"]["name"]
                logger.info(f"Unregistering protection policy {tml_name} from vm: {vm['name']}")
                unassign_protecion_policy(context, vm["appDataManagementJobInfo"]["id"], template)
                logger.info("Protection policy unregistered")

    if _vm_id:
        context.vm_id = _vm_id
    response = context.hypervisor_manager.unregister_vcenter(context.vcenter_id, force)
    assert response.status_code == codes.accepted, "unregister delete call failed"
    task_id = tasks.get_task_id_from_header(response)
    status = tasks.wait_for_task(task_id, context.user, TimeoutManager.v_center_manipulation_timeout)
    assert (
        status.upper() == TaskStatus.success.value
    ), f"Unregister vCenter {context.vcenter_name} task failed, \
                                                unregister manually and try run test again"
    try:
        wait(
            lambda: context.vcenter_name
            not in [vcenter["name"] for vcenter in context.hypervisor_manager.get_vcenters().json().get("items")],
            timeout_seconds=TimeoutManager.v_center_manipulation_timeout,
            sleep_seconds=10,
        )
    except TimeoutExpired:
        raise AssertionError("vCenter unsuccessfully unregistrated - still in db")


def unregister_vcenter(context: Context, force=False):
    task_manager = TaskManager(context.user)
    logger.info(f"Unregister vCenter {context.vcenter_name}")
    response = context.hypervisor_manager.unregister_vcenter(context.vcenter_id, force)
    if response.status_code == codes.accepted:
        status = tasks.wait_for_task(
            task_manager.get_task_id_from_header(response),
            context.user,
            timeout=TimeoutManager.v_center_manipulation_timeout,
            message=f"Unregister vCenter {context.vcenter_name} failed!!!",
        )
        assert (
            status.upper() == TaskStatus.success.value
        ), f"Unregister vCenter {context.vcenter_name} task failed.. please check and report accordingly"
        try:
            wait(
                lambda: context.vcenter_name
                not in [vcenter["name"] for vcenter in context.hypervisor_manager.get_vcenters().json().get("items")],
                timeout_seconds=TimeoutManager.v_center_manipulation_timeout,
                sleep_seconds=10,
            )
            logger.info(f"Unregister vCenter {context.vcenter_name} success")
        except TimeoutExpired:
            raise AssertionError("vCenter unsuccessfully unregistrated - still in db")
        except TypeError:
            logger.info(f"No vCenters availble to fetch so Unregistered {context.vcenter_name} successfully")
    else:
        logger.debug(response.content)
        logger.error(f"Unregister vCenter {context.vcenter_name} failed")


def change_vcenter_credentials(
    context: Context,
    vcenter_username,
    vcenter_user_password,
    expected_status="succeeded",
):
    timeout = TimeoutManager.standard_task_timeout
    response = context.hypervisor_manager.change_user_on_vcenter(
        vcenter_id=context.vcenter_id,
        vcenter_ip=context.vcenter_name,
        new_vcenter_username=vcenter_username,
        new_vcenter_user_password=vcenter_user_password,
    )
    task_id = tasks.get_task_id_from_header(response)
    task_status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout,
        message=f"Unable to change vCenter credentials with given time: {timeout} seconds",
    )
    assert task_status == expected_status, f"Expected task status: {expected_status} but got status as {task_status}"
    return task_id


def add_vcenter_failed(context: Context, vcenter_username, vcenter_user_password):
    logger.info(f"Adding {context.vcenter_name} to DO {context.ope_id}")
    response = context.hypervisor_manager.register_vcenter(
        context.vcenter_name,
        context.vcenter_name,
        vcenter_username,
        vcenter_user_password,
        context.ope_id,
    )
    assert response.status_code == codes.accepted, f"{response.status_code} - {response.content}"
    task_id = tasks.get_task_id_from_header(response)
    tasks.wait_for_task(task_id, context.user, TimeoutManager.v_center_manipulation_timeout)
    return task_id


def create_vm_and_refresh_vcenter_inventory(context, large_vm=False):
    vcenter_control = VMwareSteps(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    if not large_vm:
        vcenter_control.create_vm_from_template(context.vm_template_name, context.vm_name)
    else:
        vcenter_control.create_vm_from_template(context.large_vm_template_name, context.vm_name, power_status=True)

    # Adding retry for inventory sync between DSCC app and the vCenter
    _search_for_vm(context, vcenter_control)

    # Adding retry for inventory sync between DSCC app and the vCenter
    _get_vm_id_and_refresh_inventory(context)


@retry(
    retry=retry_if_exception_type(AssertionError),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _search_for_vm(context, vcenter_control):
    vm_found = vcenter_control.search_vm(context.vm_name)
    logger.info(f"Found vm: {vm_found}")
    if not vm_found:
        raise AssertionError(f"VM '{context.vm_name}' not exists in {context.vcenter_name}")


@retry(
    retry=retry_if_exception_type(IDNotFoundError),
    stop=stop_after_attempt(5),
    wait=wait_fixed(5),
    reraise=True,
)
def _get_vm_id_and_refresh_inventory(context: Context):
    refresh_vcenter_inventory(context, context.vcenter_id)
    # adding this because after refresh immediatly we are trying to fetch vm ids
    sleep(60)
    context.vm_id = context.hypervisor_manager.get_id(context.vm_name, context.hypervisor_manager.get_vms())


def get_vm_datastore_usage(context, vm_vcenter):
    vcenter_control = VMwareSteps(context.vcenter["ip"], context.vcenter["username"], context.vcenter["password"])
    if not vm_vcenter:
        vm_vcenter = context.vcenter_name
    array_api = ArrayApi(
        array_address=context.array,
        username=context.vcenter_username,
        password=context.vcenter_password,
        vcenter_address=vm_vcenter,
    )
    datastore_id = vcenter_control.get_datastore_id(context.vm_name)
    datastore_usage = array_api.get_datastore_usage(datastore_id)
    return datastore_usage


def verify_content_libray_datastore(context):
    vsphere = VsphereApi(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    datastore_obj_from_content_lib = vsphere.get_content_lib_datastore_obj(context.content_library)
    logger.info(f"Datastore from the vcenter content library {datastore_obj_from_content_lib}")
    vcenter_control = VMwareSteps(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    datastore_obj_of_content_lib = vcenter_control.get_datastore_obj_with_name(context.content_library_datastore)
    logger.info(
        f"Datastore obj of the given datastore in variables.ini on content_library_datastore {datastore_obj_of_content_lib}"
    )
    assert (
        datastore_obj_from_content_lib == datastore_obj_of_content_lib
    ), f"Content-library not created on given datastore"
    logger.info("content library verified successfullly")


def register_vcenters_with_given_ope(context: Context, ope_id, vcenter_names):
    vcenters = context.vcenters
    hypervisor = context.hypervisor_manager
    for item in vcenter_names:
        hypervisor.register_vcenter(
            vcenter_name=item,
            network_address=item,
            username=next(vcenter["username"] for vcenter in vcenters if vcenter["ip"] == item),
            password=next(vcenter["password"] for vcenter in vcenters if vcenter["ip"] == item),
            ope_id=ope_id,
        )
    for item in vcenter_names:
        try:
            wait(
                (lambda vcenter: vcenter["name"] == item and vcenter["onPremEngineId"] == ope_id)(
                    hypervisor.get_vcenters().json().get("items")
                ),
                timeout_seconds=300,
                sleep_seconds=5,
            )
        except TimeoutExpired:
            raise AssertionError(f"vCenter {item} unsuccessfully registered")


def verify_vcenters_unregistered_after_deleting_ope(context, vcenter_names):
    for item in vcenter_names:
        try:
            wait(
                lambda: item
                not in [vcenter["name"] for vcenter in context.hypervisor_manager.get_vcenters().json().get("items")],
                timeout_seconds=60,
                sleep_seconds=5,
            )
        except TimeoutExpired:
            raise AssertionError(f"vCenter {item} unsuccessfully unregistrated - still in db")


def check_esxi_host_status(context):
    """This method checks the status of esxi host.

    Args:
        context (Context): Context Object
    """
    vcenter_control = VMwareSteps(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    logger.info("Checking status/state of ESXi host")

    # Check connection status of ESXi host
    _host_list = []
    _host_list = vcenter_control.get_all_hosts(VmPowerOption.unknown)
    for host in _host_list:
        if host.name == context.hypervisor_name:
            vcenter_control.reconnect_host_and_wait(context.hypervisor_name)


def check_esx_and_psg_vm_status(context: Context):
    """
    This method checks the status of both esxi host and psg vm status

    Args:
        context (Context): Context Object
    """
    check_esxi_host_status(context)

    vsphere = VsphereApi(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    vm_network_nic, vm_id, vm_network_state = vsphere.get_vm_network_nic(context.psgw_name)
    logger.info(f"state of psg_vm nic with id {vm_id} and nic {vm_network_nic} is {vm_network_state}")

    # Check recovery of psgw_vm network before cleanup
    if vm_network_state == "DISCONNECTED":
        message = vsphere.reconnect_vm_nic(context.psgw_name)
        assert message == "Reconnect of psg_vm successfull", "Failed to reconnect psgw_vm nic"

    # Check recovery of psgw_vm power state before cleanup
    si = generate_SmartConnect(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    vm_power_status = get_vm_power_status(si, context.psgw_name)
    if vm_power_status == VmPowerOption.off.value:
        status = power_on_vm(si, context.psgw_name)
        assert status == "success", "Failed to power-on psgw_vm after power-off"
    logger.info("Performing cleanup after the test")


def validate_error_message_for_insufficient_previlages(
    context: Context, task_id, expected_error_message, expected_task_log_message
):
    """this step performs validation of error messages for insufficient previlages

    Args:
        context (Context): contest object
        task_id (uuid): taks uuid
        expected_error_message (str): expected error message in task error message
        expected_task_log_message (str): expected error message in task log message
    """
    error_message = tasks.get_task_error(task_id, context.user)
    assert re.search(
        expected_error_message, error_message
    ), f"Expected Error message {expected_error_message} is not present in {error_message}"
    task_logs = tasks.get_task_logs(task_id, context.user)
    assert re.search(
        expected_task_log_message, task_logs[-1]["message"]
    ), f"Expected Error message {expected_task_log_message} is not present in {task_logs[-1]['message']}"
    logger.info("Successfully validated task error messages for insufficient previlages")


def download_DO_from_software_catalogue(context: Context):
    """This step can be used to download DO from software catalogue.

    Args:
        context (Context): Context Object
    """
    latest_software_id, software_file_name = context.software_releases.get_latest_software_id_and_file_name()
    assert (
        latest_software_id is not None and software_file_name is not None
    ), f"Failed to fetch ID and filename from latest \
    software got ID: {latest_software_id}, filename:{software_file_name}"
    logger.info("latest software id: " + str(latest_software_id))
    logger.info("latest software file name: " + str(software_file_name))
    response = context.software_releases.download_latest_software(latest_software_id, software_file_name)
    assert response, f"Failed to download latest software id: {latest_software_id} and file name: {software_file_name}"


def validate_downloaded_DO(context: Context):
    """
    This method validates whether downloaded DO file exists or not and also validates whether size of downloaded DO is
      same as mentioned in software-releases API.
    Args:
        context (Context): Context Object
    """
    response = context.software_releases.get_latest_software_details().json()
    logger.info("response: " + str(response))
    size_of_DO_from_api = response.get("items")[0].get("sizeInBytes")
    filename = response.get("items")[0].get("filename")
    assert os.path.exists(f"{filename}"), f"Download not completed successfully as the file {filename} not exists.."
    size_of_downloaded_DO = os.path.getsize(filename)
    logger.info(f"size of DO from API: {size_of_DO_from_api}")
    logger.info(f"size of DO after downloaded from API: {size_of_downloaded_DO}")
    assert (
        size_of_DO_from_api == size_of_downloaded_DO
    ), f"Both DO sizes are not equal, size of DO mentioned in software-releases API: {size_of_DO_from_api} is not \
        equal to size of DO after downloaded from API: {size_of_downloaded_DO} "


def perform_DO_cleanup(context: Context):
    """
    This step performs cleanup of DO .ova file if it exists.

    Args:
        context (Context): Context Object
    """
    logger.info("Deleting latest DO file..")
    id, filename = context.software_releases.get_latest_software_id_and_file_name()
    if os.path.exists(f"{filename}"):
        logger.debug(f"{filename} file exists so deleting it...")
        os.remove(f"{filename}")
        assert os.path.exists(f"{filename}") is False, "Deletion of file is Failed."
        logger.info(f"File {filename} successfully cleaned up...")
    else:
        logger.info(f"{filename} file is not available to delete...")


def vm_relocate_on_datastore(context):
    """
    https://developer.vmware.com/apis/vsphere-automation/v7.0.0/vcenter/rest/vcenter/vm/vmactionrelocate/post/
    as per document psgvm relocate call https://{api_host}/rest/vcenter/vm/{vm}?action=relocate are using in this method.
    Args:
        context
    """
    vsphere = VsphereApi(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    vcenter_control = VMwareSteps(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    datastore_obj = vcenter_control.get_datastore_obj_with_name(context.datastore_62tb)
    vsphere.relocate_vm_datastore(context.psgw_name, datastore_obj)
    logger.info("successfully relocate the datastore for psgw vm")


def create_tiny_vm_and_get_ip(context):
    vcenter_control = VMwareSteps(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    vcenter_control.create_vm_from_template(context.vm_template_name, context.vm_name, power_status=True)
    logger.info("Waiting for 2 minutes before fetching vm ip.")
    sleep(120)
    vm_ip = vcenter_control.get_vm_ip_by_name(context.vm_name)
    assert vm_ip is not None, f"Failed to fetch VM ip for {context.vm_name}"
    logger.info(f"vm details - name:{context.vm_name} ip:{vm_ip}")
    return vm_ip
