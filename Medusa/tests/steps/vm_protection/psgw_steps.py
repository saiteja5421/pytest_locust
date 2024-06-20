import logging
import time
import paramiko
import random
import string
import re
from time import sleep
from requests import codes
from waiting import wait, TimeoutExpired
from tenacity import retry, stop_after_delay, wait_fixed, retry_if_exception_type
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.api.catalyst_gateway import CatalystGateway
from lib.common.error_messages import (
    ERROR_MESSAGE_CLOUD_RETENTION_DAYS,
    ERROR_MESSAGE_DEPLOY_PSG_WITH_DATA_NIC_ONLY,
    ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_CONSOLE_USER,
    ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_POWER_ON,
    ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_RECOVER,
    ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_REMOTE_SUPPORT,
    ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_RESTART,
    ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_SHUTDOWN,
    ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_SUPPORT_BUNDLE,
    ERROR_MESSAGE_FAILED_TO_DELETE_PRIMARY_NIC,
    ERROR_MESSAGE_GENERATE_SUPPORT_BUNDLE_WHEN_ALREADY_INPROGRESS,
    ERROR_MESSAGE_NAME_NOT_UNIQUE,
    ERROR_MESSAGE_CANNOT_CONFIGURE_NIC,
    ERROR_MESSAGE_CANNOT_RESIZE_PSGW_VM,
    ERROR_MESSAGE_DELETING_PSGW_CONTAINS_CLOUD_BACKUP,
    ERROR_MESSAGE_CANNOT_ADD_ANOTHER_NIC,
    ERROR_MESSAGE_DURING_DEPLOYMENT,
    ERROR_MESSAGE_CREATE_PSG_VM_EXISTS,
    ERROR_MESSAGE_MODIFY_NIC_WITH_DUPLICATE_IP,
    ERROR_MESSAGE_DELETE_PROTECTION_STORE_WITHOUT_PROTECTION_POLICY,
    ERROR_MESSAGE_ONPREM_RETENTION_DAYS,
    ERROR_MESSAGE_UPDATE_PROTECTION_STORE_WITH_SAME_NAME,
    ERROR_MESSAGE_DELETE_PROTECTION_STORE_WITH_BACKUP_WITHOUT_USING_FORCE,
    ERROR_MESSAGE_DEPLOY_PSGW_WHEN_UPLOAD_TO_CONTENT_LIBRARY_IS_ALREADY_IN_PROGRESS,
    ERROR_MESSAGE_VALIDATING_PSGW_TOOLING_CONNECTIVITY_TO_INVALID_ADDRESS_TASK_FAILURE,
    ERROR_MESSAGE_VALIDATING_PSGW_TOOLING_CONNECTIVITY_WHEN_PSGW_IS_IN_OFFLINE_STATE,
    ERROR_MESSAGE_VALIDATING_EXPIREAFTER_5_YEARS_WITH_lOCKFOR_VALUE_100_YEARS,
    ERROR_MESSAGE_VALIDATING_EXPIREAFTER_NOT_MORE_THAN_5_YEARS_WITH_lOCKFOR_VALUE_100_YEARS,
)
from lib.dscc.backup_recovery.vmware_protection.common.custom_error_helper import (
    NetworkInterfaceNotFoundError,
)

from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.network_interface_type import NetworkInterfaceType
from lib.common.enums.psg import HealthState, HealthStatus, State
from lib.common.enums.task_status import TaskStatus
from lib.common.enums.vm_power_option import VmPowerOption
from lib.platform.vmware.vcenter_details import (
    generate_SmartConnect,
    get_vms,
    get_vm_power_status,
    power_off_vm,
    power_on_vm,
    destroy_vm,
    reboot_vm,
    wait_until_vm_gets_powered_off,
)
from lib.platform.vmware.vsphere_api import VsphereApi
from lib.common.enums.copy_pool_types import CopyPoolTypes
from lib.common.enums.backup_type_param import BackupTypeParam
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.payload.network_interface import (
    CreateNetworkInterfaceDetails,
    UpdateNetworkInterface,
    CreateNetworkInterface,
    UpdateNetworkInterfaceDetails,
    DeleteNetworkInterface,
    DeleteNetworkInterfaceDetails,
)
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.tasks import tasks
from tests.steps.vm_protection.backup_steps import delete_all_backups
from tests.steps.vm_protection.protection_template_steps import (
    create_protection_template,
    assign_protection_template_to_vm,
    unassign_protecion_policy_from_vm,
    delete_unassinged_protection_policy,
    create_protection_store,
)
from tests.steps.vm_protection.vcenter_steps import (
    verify_content_libray_datastore,
    create_tiny_vm_and_get_ip,
)
from utils.ip_utils import find_unused_ip_from_range, get_unused_ip_for_network_interface, ping
from utils.timeout_manager import TimeoutManager
from lib.common.enums.aws_regions import AwsStorageLocation

__PSGW_ID_NOT_FOUND = "Failed to find PSGW ID"
logger = logging.getLogger()


def create_protection_store_gateway_vm(
    context: Context,
    expected_status: str = "succeeded",
    clear_content_library=False,
    add_data_interface=True,
    max_cld_dly_prtctd_data=1.0,
    max_cld_rtn_days=1,
    max_onprem_dly_prtctd_data=1.0,
    max_onprem_rtn_days=1,
    override_cpu=0,
    override_ram_gib=0,
    override_storage_tib=0,
    return_response=False,
    additional_ds_name=None,
    additional_ds_required=False,
    verify_deploy_state=False,
    same_psgw_name=False,
    check_unused_ip=True,
    datastore_info=None,
    multiple_local_protection_store=1,
    deploy_ova_on_content_lib_ds=False,
    deploy_on_folder=False,
    deploy_with_cluster_id=False,
    deploy_with_resource_pools=False,
):
    """This Step creates a psgw with given parameters.

    Args:
        context (Context): context object
        expected_status (str, optional): expected state of this action. Defaults to "succeeded".
        clear_content_library (bool, optional): if user wants to clean content library then he can set to True. Defaults to False.
        add_data_interface (bool, optional): to add data1 network while creation of PSGW. Defaults to True.
        max_cld_dly_prtctd_data (float, optional): Defaults to 1.0.
        max_cld_rtn_days (int, optional): Defaults to 1.
        max_onprem_dly_prtctd_data (float, optional): Defaults to 1.0.
        max_onprem_rtn_days (int, optional): Defaults to 1.
        override_cpu (int, optional): Defaults to 0.
        override_ram_gib (int, optional): Defaults to 0.
        override_storage_tib (int, optional): Defaults to 0.
        return_response (str, optional): Defaults to False
        additional_ds_name (str, optional): Defaults to None
        additional_ds_required (bool, optional): Defaults to False
        verify_deploy_state (bool, optional): Defaults to False
        same_psgw_name (bool, optional): Defaults to False
        multiple_local_protection_store (int) : defaults to 1, 0 if no local protection stores required
        deploy_ova_on_content_lib_ds (bool, optional): Defaults to False
        deploy_on_folder (bool, optional): Defaults to False
        deploy_with_cluster_id (bool, optional): Defaults to False
        deploy_with_resource_pools (bool, optional): Defaults to False

    Raises:
        AssertionError: It raises an exception when psgw not created with expected state.
    """
    atlas = context.catalyst_gateway
    if clear_content_library or deploy_ova_on_content_lib_ds:
        vsphere = VsphereApi(context.vcenter_name, context.vcenter_username, context.vcenter_password)
        result, message = vsphere.clear_content_library(context.content_library)
        assert result, message
        logger.info(f"content library info :{message}")

    if check_unused_ip == True:
        psg_network_ip = find_unused_ip_from_range(context.network_ip_range)
        assert psg_network_ip is not None, f"Failed to find unused IP from the range {context.network_ip_range}"
        end = context.network_ip_range.split("-")[-1]

        def get_unused_ip_from_DSCC(psg_network_ip):
            context.network = psg_network_ip
            network, start = (".".join(psg_network_ip.split(".")[0:3]), psg_network_ip.split(".")[-1])
            start = int(start) + 1
            next_psg_network_ip = f"{network}.{start}"
            logger.info(f"Checking ping for IP: {psg_network_ip}")
            if ping(psg_network_ip):
                get_unused_ip_from_DSCC(next_psg_network_ip)
            logger.info(f"IP {psg_network_ip} successfully pinging.")
            logger.info(f"Checking whether IP {psg_network_ip} is used by available PSG in DSCC or not.")
            all_psg_ip_list = atlas.get_list_of_all_available_psg_ips()
            logger.info(f"All psgs ip are: {all_psg_ip_list}")
            if psg_network_ip in all_psg_ip_list:
                logger.info(f"IP {psg_network_ip} is used by other PSG.")
                assert int(start) <= int(end), f"No ips available from range: {context.network_ip_range}"
                get_unused_ip_from_DSCC(next_psg_network_ip)

        get_unused_ip_from_DSCC(psg_network_ip)
        logger.info(f"Final Context PSGW IP is : {context.network}")
    standard_psgw_timeout = TimeoutManager.create_psgw_timeout
    long_psgw_timeout = TimeoutManager.first_time_psgw_creation
    timeout = standard_psgw_timeout if not clear_content_library else long_psgw_timeout
    message = lambda place, timeout: f"{place} copy pool creation time exceed {timeout / 60:.1f} minutes"
    if datastore_info is None:
        datastore_info = [context.datastore_id]
    if additional_ds_required:
        datastore_ids = atlas.get_additional_datastores(additional_ds_name)
        datastore_info = datastore_ids

    if not same_psgw_name:
        context.psgw_suffix = "".join(random.choice(string.ascii_letters) for _ in range(10))
        context.psgw_name = f'{context.test_data["psgw_name"]}_{context.psgw_suffix}#{context.network}'
        # creating new protection template if the new psg is created.
        context.local_template = f"{context.test_data['policy_name']}_{context.psgw_suffix}"
    logger.info(f"Create {context.psgw_name} VM on {context.vcenter_name}")
    response = atlas.create_catalyst_gateway_vm(
        context.psgw_name,
        context.vcenter_id,
        datastore_info,
        context.esxhost_id,
        context.hypervisor_cluster_id,
        context.content_lib_datastore_id,
        context.hypervisor_folder_id,
        context.resources_pools_id,
        context.network_name,
        context.network,
        context.netmask,
        context.gateway,
        context.network_type,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
        override_cpu=override_cpu,
        override_ram_gib=override_ram_gib,
        override_storage_tib=override_storage_tib,
        deploy_ova_on_content_lib_ds=deploy_ova_on_content_lib_ds,
        deploy_on_folder=deploy_on_folder,
        deploy_with_cluster_id=deploy_with_cluster_id,
        deploy_with_resource_pools=deploy_with_resource_pools,
    )
    logger.info(f"Creation of protection store gateway VM response: {response.text}")
    if return_response:
        return response
    assert response.status_code == codes.accepted, f"{response.content}"
    if verify_deploy_state:
        state = atlas.get_catalyst_gateway_health_state(context.psgw_name)
        assert state in (
            HealthState.DEPLOYING.value,
            HealthState.REGISTERING.value,
            HealthState.INITIALIZING.value,
        ), f"Failed to get PSGW expected deployment state, received deployment state: {state}"
        logger.info(f"Successfully validated PSGW deployment state: {state}")
        status = atlas.get_catalyst_gateway_health_status(context.psgw_name)
        assert (
            status == HealthStatus.DISCONNECTED.value
        ), f"Failed to get PSGW expected deployment status, received deployment status: {status}"
        logger.info(f"Successfully validated PSGW deployment status: {status}")
    task_id = tasks.get_task_id_from_header(response)
    logger.info(f"Create protection store gateway, Task ID: {task_id}")
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout,
        interval=30,
        message=f"Protection store gateway creation time exceed {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert (
        status == expected_status
    ), f"Failed to deploy protection store gateway: {context.psgw_name} \
                                        {tasks.get_task_error(task_id, context.user)}"
    if expected_status == "failed":
        return task_id
    try:
        wait(
            lambda: atlas.get_catalyst_gateway_health_status(context.psgw_name) == HealthStatus.CONNECTED.value,
            timeout_seconds=TimeoutManager.health_status_timeout,
            sleep_seconds=15,
        )
    except TimeoutExpired:
        raise AssertionError("PSGW VM health status is not the expected")
    if atlas.get_catalyst_gateway_health_state(context.psgw_name) == HealthState.WARNING.value:
        logger.warning("Protection store gateway is in WARNING state after deployment")
    logger.info("Successfully deployed the protection store gateway")

    for i in range(multiple_local_protection_store):
        # Create local protection store
        create_protection_store(context, type=CopyPoolTypes.local)
    if add_data_interface:
        add_additional_network_interface_catalyst_gateway_vm(context, nic_type=NetworkInterfaceType.data1)


def select_or_create_protection_store_gateway_vm(
    context: Context,
    expected_status: str = "succeeded",
    clear_content_library=False,
    add_data_interface=True,
    max_cld_dly_prtctd_data=1.0,
    max_cld_rtn_days=1,
    max_onprem_dly_prtctd_data=1.0,
    max_onprem_rtn_days=1,
    override_cpu=0,
    override_ram_gib=0,
    override_storage_tib=0,
    return_response=False,
):
    """This step makes user to select the existing psg with same name if not it creates one.

    Args:
        context (Context): context object
        expected_status (str, optional): expected state of this action. Defaults to "succeeded".
        clear_content_library (bool, optional): if user wants to clean content library then he can set to True. Defaults to False.
        add_data_interface (bool, optional): to add data1 network while creation of PSGW. Defaults to True.
        max_cld_dly_prtctd_data (float, optional): Defaults to 1.0.
        max_cld_rtn_days (int, optional): Defaults to 1.
        max_onprem_dly_prtctd_data (float, optional): Defaults to 1.0.
        max_onprem_rtn_days (int, optional): Defaults to 1.
        override_cpu (int, optional): Defaults to 0.
        override_ram_gib (int, optional): Defaults to 0.
        override_storage_tib (int, optional): Defaults to 0.
        return_response (str, optional): Defaults to False
    """
    atlas = CatalystGateway(context.user)
    psgw_name, datastore_id, vcenter_name = atlas.get_catalyst_gateway_connected(context)

    if psgw_name and datastore_id and vcenter_name:
        context.psgw_name = psgw_name
        context.datastore_id = datastore_id
        context.vcenter_name = vcenter_name

        state = atlas.get_catalyst_gateway_health_state(context.psgw_name)
        if state not in ("PSG_HEALTH_STATE_OK"):
            logger.info(f"Selected PSGW is: {context.psgw_name} and state: {state}")
            logger.info("Since PSGW state is not OK. That's why deleting existing psgw to avoid stale entries.")
            # Trying to delete stale psg. If delete stale psg failed it won't raise assertion.
            psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
            response = atlas.delete_catalyst_gateway_vm(psgw["id"])
            if response.status_code == codes.accepted:
                task_id = tasks.get_task_id_from_header(response)
                status = tasks.wait_for_task(
                    task_id,
                    context.user,
                    timeout=3600,
                    message="PSGW VM delete failed",
                )
                if status == "succeeded":
                    logger.info(
                        f"Successfully deleted stale psgw vm {context.psgw_name} from vcenter: {context.vcenter_name}"
                    )
                else:
                    logger.info(f"Delete stale PSGW VM Task {task_id} : {status}")
            else:
                logger.info(
                    f"Delete Stale PSG request not accepted status code:  {response.status_code}, psgw vm : {context.psgw_name} from vcenter: {context.vcenter_name}"
                )
            create_protection_store_gateway_vm(context)
    else:
        create_protection_store_gateway_vm(
            context,
            expected_status=expected_status,
            clear_content_library=clear_content_library,
            add_data_interface=add_data_interface,
            max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
            max_cld_rtn_days=max_cld_rtn_days,
            max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
            max_onprem_rtn_days=max_onprem_rtn_days,
            override_cpu=override_cpu,
            override_ram_gib=override_ram_gib,
            override_storage_tib=override_storage_tib,
            return_response=return_response,
        )


def validate_protection_store_gateway_vm(context: Context):
    """
    This step validates whether the psgvm created or not by fetching from vcenter

    Args:
        context (Context): Context object
    """
    logger.info(f"Checking in vCenter: {context.vcenter_name} for the PSGW VM: {context.psgw_name}")
    si = generate_SmartConnect(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    content = si.RetrieveContent()
    vms = get_vms(content)
    assert any([vm.name == context.psgw_name for vm in vms]), "VM not found in vCenter after deployment"
    logger.info(f"Found PSGW VM: {context.psgw_name} in the vCenter: {context.vcenter_name}")
    status = verify_local_protection_store_state(context)
    if status:
        logger.info("Successfully validated the local protection store status")
    else:
        logger.info(f"There is no local protection store created for the PSGW VM : {context.psgw_name}")


def validate_protection_store_gateway_vm_ok_state_and_station_id(context: Context):
    """
    This step validates whether the psgvm is in ok state or not and validate remoteAccessStationId not empty

    Args:
        context (Context): Context object
    """
    atlas = CatalystGateway(context.user)
    wait_for_psg(context, state=State.OK, health_state=HealthState.OK, health_status=HealthStatus.CONNECTED)
    try:
        wait(
            lambda: atlas.get_catalyst_gateway_by_name(context.psgw_name).get("remoteAccessStationId") != "",
            timeout_seconds=TimeoutManager.standard_task_timeout,
            sleep_seconds=5,
        )
    except TimeoutExpired:
        raise AssertionError(f"failed to get remoteaccessstationid after 300sec")

    logging.info("Successfully validated remoteAccessStationId")


def verify_the_PSG_deployment_info_after_successfully_deployment(
    context,
    exp_sizer_fields={},
    deploy_ova_on_content_lib_ds=False,
    deploy_on_folder=False,
    deploy_with_cluster_id=False,
    deploy_with_resource_pools=False,
    verify_size=False,
):
    # Verify the PSG deployment info after successfull deployment
    psg_vm_id_on_hypervisor = context.hypervisor_manager.get_id(context.psgw_name, context.hypervisor_manager.get_vms())
    logger.info(f"vm ID of the PSG from hypervisor manager : {psg_vm_id_on_hypervisor}")
    vm_response = context.hypervisor_manager.get_vm_info(psg_vm_id_on_hypervisor)
    assert vm_response.status_code == codes.ok, f"Failed to get {context.vm_name} info {vm_response.content}"
    vm_info = vm_response.json()
    logger.info(f"{context.psgw_name} response is: {vm_info}")
    vm_resource_pool_id = vm_info["appInfo"]["vmware"]["resourcePoolInfo"]["id"]
    vm_cluster_id = vm_info["clusterInfo"]["id"]
    vm_folder_id = vm_info["folderInfo"]["id"]
    vm_host_id = vm_info["hostInfo"]["id"]
    logger.info(f"vm cluster ID is {vm_cluster_id}")
    if verify_size:
        atlas = context.catalyst_gateway
        psg_size = atlas.psgw_total_disk_size_tib(context.psgw_name)
        actual_sizer_fields = {
            "vCpu": vm_info["computeInfo"]["numCpuCores"],
            "ramInGiB": float(vm_info["computeInfo"]["memorySizeInMib"]) / 1024,
            "storageInTiB": psg_size,
        }
        assert (
            exp_sizer_fields == actual_sizer_fields
        ), f"vCPU, ram and storage not matched for existing PSGW. Actul {actual_sizer_fields}, expected: {exp_sizer_fields}"
        logger.info(f"PSGW {context.psgw_name} successfully running with minimum size. 2 vCPUs and 16Gib ram.")
    if deploy_on_folder:
        assert (
            context.hypervisor_folder_id == vm_folder_id
        ), f"Folder ID not matched, deployed :{context.hypervisor_folder_id} PSG VM : {vm_folder_id}"
        logger.info("folder ID verified successfullly")
    if deploy_ova_on_content_lib_ds:
        verify_content_libray_datastore(context)

    if deploy_with_cluster_id:
        assert (
            context.hypervisor_cluster_id == vm_cluster_id
        ), f"Cluster ID not matched, deployed :{context.hypervisor_cluster_id} PSG VM : {vm_cluster_id}"
        logger.info("cluster ID verified successfullly")
    elif deploy_with_resource_pools:
        assert (
            context.resources_pools_id == vm_resource_pool_id
        ), f"Resources pool ID not matched, deployed :{context.resources_pools_id} PSG VM : {vm_resource_pool_id}"
        logger.info("resource_pool_id verified successfullly")
    else:
        assert (
            context.esxhost_id == vm_host_id
        ), f"Host ID not matched, deployed :{context.esxhost_id} PSG VM : {vm_host_id}"
        logger.info("host_id verified successfullly")


def get_psg_vmid(context: Context):
    """this method helps to get psg vmId

    Args:
        context (Context): Context Object

    Returns:
        uuid: returns PSG vmId
    """
    atlas = CatalystGateway(context.user)
    psgw_id = atlas.get_catalyst_gateway_id(context)
    psgw_info = atlas.get_catalyst_gateway(psgw_id)
    logger.info(f"psgw_info:  {psgw_info}")
    assert psgw_info.status_code == codes.ok, f"Failed to get PSG. Response: {psgw_info.text}"
    psgw_vmId = psgw_info.json().get("vmId", "")
    logger.info(f"psgw_vmId: {psgw_vmId}")
    return psgw_vmId


def validate_psg_vmid_at_given_state(context: Context, state: str, old_psg_vmId=""):
    """This step performs psg vm_Id key validation at different stages.
    PSG vmId will be changed after recovery and assign with new vmId. during recover vmId will be empty string.

    Args:
        context (Context): Context Object
        state (str): state at which user want to verify vmId. valid inputs: "before_recover", "during_recover" or "after_recover"
        old_psg_vmId (str, optional): If user want to verify psg vmId after recover then user has to provide old psg vmId also. Default to "".
    """
    psg_vmId = get_psg_vmid(context)
    logger.debug(f"Current PSG vmId : {psg_vmId}")
    if state == "before_recover":
        assert psg_vmId != "", "PSG vmId is empty before psg recover"
        logger.info(f"Successfully verified that {psg_vmId} is not empty string at {state} state")
    elif state == "during_recover":
        assert psg_vmId == "", "PSG vmId is not empty during psg recover"
        logger.info(f"Successfully verified that {psg_vmId} is empty string at {state} state")
    elif state == "after_recover":
        assert psg_vmId != "", "PSG vmId is empty even after psg recover"
        assert psg_vmId != old_psg_vmId, "New PSG vmId is same as old vmId even after psg recover"
        logger.info(
            f"Successfully verified that {psg_vmId} is not empty string and not a old psg vmId {old_psg_vmId} at {state} state"
        )


def delete_protection_store_gateway_vm_from_vcenter(context: Context, force=False):
    """This method help user to delete psgvm from vcenter

    Args:
        context (Context): Context object
        force (bool, optional): if user want to delete forcifully then provide True. Defaults to False.
    """
    logger.info("Deleting PSGW VM from vCenter")
    si = generate_SmartConnect(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    status = get_vm_power_status(si, context.psgw_name)
    if force and status == VmPowerOption.on.value:
        status = power_off_vm(si, context.psgw_name)
        assert status == "success", "Power OFF VM failed"
    else:
        assert status == VmPowerOption.off.value, f"Unexpected VM status {status}"
    status = destroy_vm(si, context.psgw_name)
    assert status == "success", "Unable to delete vm from vCenter"
    logger.info("Deleted PSGW VM from vCenter")


def power_off_protection_store_gateway_vm_from_vcenter(context: Context):
    """This method helps user to power off the psgvm from vcenter

    Args:
        context (Context): Context Object
    """
    logger.info("Power off PSGW VM from vCenter")
    si = generate_SmartConnect(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    status = get_vm_power_status(si, context.psgw_name)
    if status == VmPowerOption.on.value:
        status = power_off_vm(si, context.psgw_name)
        assert status == "success", "Power OFF VM failed"
    else:
        assert False, f"Unable to power off VM due to unexpected status {status}"
    logger.info("Successfully powered off PSGW VM from vCenter")


def power_on_protection_store_gateway_vm_from_vcenter(context: Context):
    """This method helps user to power on psgvm from vcenter

    Args:
        context (Context): Context Object
    """
    logger.info("Power off PSGW VM from vCenter")
    si = generate_SmartConnect(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    status = get_vm_power_status(si, context.psgw_name)
    if status == VmPowerOption.off.value:
        status = power_on_vm(si, context.psgw_name)
        assert status == "success", "Power ON VM failed"
    else:
        assert False, f"Unable to power on VM due to unexpected status {status}"
    logger.info("Successfully powered on PSGW VM from vCenter")


def reboot_protection_store_gateway_vm_from_vcenter(context: Context):
    """This method helps user to reboot psgvm from vcenter.

    Args:
        context (Context): Context Object
    """
    logger.info("Reboot PSGW VM from vCenter")
    si = generate_SmartConnect(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    status = get_vm_power_status(si, context.psgw_name)
    if status == VmPowerOption.on.value:
        reboot_vm(si, context.psgw_name)
        logger.info("A request to reboot the guest has been sent.")
    else:
        assert False, f"Unable to reboot VM due to unexpected status {status}"


def validate_protection_store_gateway_vm_not_exist(context: Context):
    """This method helps user to validate psgvm is no exists.

    Args:
        context (Context): Context Object
    """
    si = generate_SmartConnect(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    content = si.RetrieveContent()
    vms = get_vms(content)
    assert all([vm.name != context.psgw_name for vm in vms])


def validate_psg_networking_settings(context: Context):
    def _wait_for_psg_state_ok(catalyst_gateway):
        try:
            wait(
                lambda: catalyst_gateway.get_catalyst_gateway_health_state(context.psgw_name) == HealthState.OK.value,
                timeout_seconds=1200,
                sleep_seconds=3,
            )
        except TimeoutExpired:
            raise AssertionError(
                f"Created PSGW health state is not the expected, we got: "
                f"{catalyst_gateway.get_catalyst_gateway_health_state(context.psgw_name)} for {context.psgw_name}"
            )

    logger.info(f"Start validating network setting for {context.psgw_name}")
    timeout = TimeoutManager.v_center_manipulation_timeout
    # Update DNS settings
    catalyst_gateway_id = context.catalyst_gateway.get_catalyst_gateway_id(context)
    catalyst_gateway = context.catalyst_gateway
    _wait_for_psg_state_ok(catalyst_gateway)
    update_dns = catalyst_gateway.update_dns_address(context.dns2, catalyst_gateway_id)
    assert update_dns.status_code == codes.accepted, f"We got wrong code, content: {update_dns.content}"
    tasks.wait_for_task(tasks.get_task_id(update_dns), context.user, timeout)
    _wait_for_psg_state_ok(catalyst_gateway)
    logger.info(f"DNS address successfully updated to {context.dns2}")
    # Update proxy settings
    update_proxy = catalyst_gateway.update_proxy_address(context.proxy, context.port, catalyst_gateway_id)
    assert update_proxy.status_code == codes.accepted, f"We got wrong code, content: {update_proxy.content}"
    tasks.wait_for_task(tasks.get_task_id(update_proxy), context.user, timeout)
    _wait_for_psg_state_ok(catalyst_gateway)
    logger.info(f"Proxy address successfully updated to {context.proxy}")
    # Update NTP settings
    update_ntp = catalyst_gateway.update_ntp_address(context.ntp_server_address, catalyst_gateway_id)
    assert update_ntp.status_code == codes.accepted, f"We got wrong code, content: {update_ntp.content}"
    tasks.wait_for_task(tasks.get_task_id(update_ntp), context.user, timeout)
    _wait_for_psg_state_ok(catalyst_gateway)
    logger.info(f"NTP address successfully updated to {context.ntp_server_address}")
    # Update network address
    nic = context.nic_primary_interface
    update_network_interface_catalyst_gateway_vm(
        context,
        current_address=nic["network_address"],
        network_address=nic["additional_network_address1"],
        network_name=nic["network_name"],
        network_type=nic["network_type"],
        netmask=nic["netmask"],
        gateway=nic["gateway"],
    )
    (
        context.nic_primary_interface["network_address"],
        context.nic_primary_interface["additional_network_address1"],
    ) = (
        context.nic_primary_interface["additional_network_address1"],
        context.nic_primary_interface["network_address"],
    )

    _wait_for_psg_state_ok(catalyst_gateway)
    logger.info(f"Network settings validation success for {context.psgw_name}")


def validate_psg_configured_with_given_nics_count(context: Context, nics_count):
    """This steps performs if current PSG has configured with given number (nic_count) of nics or not.

    Args:
        context (Context): Context Object
        nics_count (int): number of nics that user expecting in the psg.
    """
    atlas = context.catalyst_gateway
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    assert "network" in psgw, f"Failed to find network details for PSG VM: {context.psgw_name} "
    nics_list = psgw.get("network", {}).get("nics", [])
    logger.info(f"Existing PSG VM: {context.psgw_name} with nics list: {nics_list}")
    assert (
        len(nics_list) == nics_count
    ), f"Error in fetching nics lists or {nics_count} nics are not configured as expected."
    logger.info(f"Successfully validated psg is configured with {nics_count} number of nics")


def validate_error_message_after_modifying_network_interface_with_duplicate_ips(context: Context):
    """This function modifies the additional NICs IP with primary IPs and validates the error message.

    Args:
        context (Context): Context object
    """
    atlas = context.catalyst_gateway
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    assert "network" in psgw, f"Failed to find network details for PSG VM: {context.psgw_name}"
    # get list of all NICs available
    nics_list = psgw.get("network", {}).get("nics")
    logger.info(f"Existing PSG VM: {context.psgw_name} with nics list:")
    logger.info(f"{nics_list}")
    # checking if there are atleast two nics present
    assert len(nics_list) > 1, f"Total number of NICs present: {len(nics_list)}"
    # updating nic data1 and data2 ip with primary nic ip
    for nic_index in range(1, len(nics_list)):
        nic_details = UpdateNetworkInterface(
            UpdateNetworkInterfaceDetails(
                nics_list[nic_index]["id"],
                nics_list[0]["networkAddress"],
                nics_list[nic_index]["networkName"],
                nics_list[nic_index]["networkType"],
                nics_list[nic_index]["subnetMask"],
                nics_list[nic_index]["gateway"],
            )
        )
        response = atlas.update_network_interface(psgw["id"], nic_details)
        assert (
            response.status_code == codes.bad_request
        ), f"Failed to receive expected status code: Received: {response.status_code} expected: {codes.bad_request}"
        assert re.search(
            ERROR_MESSAGE_MODIFY_NIC_WITH_DUPLICATE_IP, response.text
        ), f"Failed to validate {ERROR_MESSAGE_MODIFY_NIC_WITH_DUPLICATE_IP} in {response.text}"
        logger.info(
            f"Successfully validated {ERROR_MESSAGE_MODIFY_NIC_WITH_DUPLICATE_IP} in {response.text} for Network Interface Data{nic_index}"
        )


def update_two_network_interface_catalyst_gateway_vm(
    context: Context,
    current_address1,
    network_address1,
    network_name1,
    network_type1,
    netmask1,
    current_address2,
    network_address2,
    network_name2,
    network_type2,
    netmask2,
    gateway="",
):
    atlas = context.catalyst_gateway
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    nic_id1 = atlas.get_network_interface_id_by_network_address(psgw["id"], current_address1)
    nic_id2 = atlas.get_network_interface_id_by_network_address(psgw["id"], current_address2)
    try:
        assert nic_id1 is not None, f"Network interface ID for '{current_address1}' not exists"
    except AssertionError:
        raise NetworkInterfaceNotFoundError()
    try:
        assert nic_id2 is not None, f"Network interface ID for '{current_address2}' not exists"
    except AssertionError:
        raise NetworkInterfaceNotFoundError()
    nic_details1 = UpdateNetworkInterface(
        UpdateNetworkInterfaceDetails(nic_id1, network_address1, network_name1, network_type1, netmask1, gateway)
    )
    nic_details2 = UpdateNetworkInterface(
        UpdateNetworkInterfaceDetails(nic_id2, network_address2, network_name2, network_type2, netmask2, gateway)
    )
    response1 = atlas.update_network_interface(psgw["id"], nic_details1)
    logger.info(
        f"Waiting for PSG to reach ok and connected before updating NIC for Data2. As NIC update won't possible if PSGW is in UPDATE state."
    )
    wait_for_psg(context, state=State.OK, health_state=HealthState.OK, health_status=HealthStatus.CONNECTED)
    response2 = atlas.update_network_interface(psgw["id"], nic_details2)
    assert response1.status_code == codes.accepted, "Failed to update the network interface Data1 for PSGW VM"
    assert response2.status_code == codes.accepted, "Failed to update the network interface Data2 for PSGW VM"
    task_id1 = tasks.get_task_id_from_header(response1)
    task_id2 = tasks.get_task_id_from_header(response2)
    status = tasks.wait_for_task(
        task_id1,
        context.user,
        timeout=TimeoutManager.standard_task_timeout,
        message=f"Failed to update network interface for  in {TimeoutManager.standard_task_timeout} seconds",
    )
    assert status == "succeeded", f"Network interface Data1 update task failed. Task id: {task_id1}"
    logger.info(f"Network config successfully updated for the interface - '{network_name1}'")
    status = tasks.wait_for_task(
        task_id2,
        context.user,
        timeout=TimeoutManager.standard_task_timeout,
        message=f"Failed to update network interface for  in {TimeoutManager.standard_task_timeout} seconds",
    )
    assert status == "succeeded", f"Network interface Data2 update task failed. Task id: {task_id2}"
    logger.info(f"Network config successfully updated for the interface - '{network_name2}'")


def update_network_interface_catalyst_gateway_vm(
    context: Context,
    current_address,
    network_address,
    network_name,
    network_type,
    netmask,
    gateway="",
):
    """
    Updates NIC details of catalyst gateway vm
    """

    atlas = context.catalyst_gateway
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    nic_id = atlas.get_network_interface_id_by_network_address(psgw["id"], current_address)
    try:
        assert nic_id is not None, f"Network interface ID for '{current_address}' not exists"
    except AssertionError:
        raise NetworkInterfaceNotFoundError()
    nic_details = UpdateNetworkInterface(
        UpdateNetworkInterfaceDetails(nic_id, network_address, network_name, network_type, netmask, gateway)
    )

    response = atlas.update_network_interface(psgw["id"], nic_details)
    assert response.status_code == codes.accepted, "Failed to update the network interface for PSGW VM"
    task_id = tasks.get_task_id_from_header(response)
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout=TimeoutManager.standard_task_timeout,
        message=f"Failed to update network interface in {TimeoutManager.standard_task_timeout} seconds",
    )
    assert status == "succeeded", f"Network interface update task failed. Task id: {task_id}"
    logger.info(f"Network config successfully updated for the interface - '{network_name}'")


@retry(
    reraise=True,
    retry=retry_if_exception_type(NetworkInterfaceNotFoundError),
    stop=stop_after_delay(300),
    wait=wait_fixed(10),
)
def update_network_interface_catalyst_gateway_vm_with_retry(
    context: Context,
    current_address,
    network_address,
    network_name,
    network_type,
    netmask,
    gateway="",
):
    update_network_interface_catalyst_gateway_vm(
        context, current_address, network_address, network_name, network_type, netmask, gateway
    )


def delete_network_interface_catalyst_gateway_vm(context: Context, network_address, expect_to_fail=False):
    """
    Delete network interface of catalyst gateway vm
    """
    atlas = context.catalyst_gateway
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    nic_id = atlas.get_network_interface_id_by_network_address(psgw["id"], network_address)
    nic_details = DeleteNetworkInterface(DeleteNetworkInterfaceDetails(nic_id))

    response = atlas.delete_network_interface(psgw["id"], nic_details)
    if expect_to_fail:
        assert response.status_code == codes.bad and ERROR_MESSAGE_FAILED_TO_DELETE_PRIMARY_NIC in response.text, (
            f"It should not be possible to delete the network interface! "
            f"The status code is {response.status_code} and should be {codes.bad}"
            f"The response we got {response.text} and it should be {ERROR_MESSAGE_FAILED_TO_DELETE_PRIMARY_NIC}"
        )
    else:
        assert response.status_code == codes.accepted, (
            f"Failed to delete the network interface for PSGW VM! The "
            f"status code is {response.status_code} and should be {codes.accepted}"
        )
        task_id = tasks.get_task_id_from_header(response)
        status = tasks.wait_for_task(
            task_id,
            context.user,
            timeout=TimeoutManager.standard_task_timeout,
            message=f"Failed to delete network interface in {TimeoutManager.standard_task_timeout}s",
        )
        logger.info(f"Network interface {nic_id} successfully deleted")
        assert status == "succeeded", f"Network interface update task failed. Task id: {task_id}"


def add_additional_network_interface_catalyst_gateway_vm(
    context: Context, nic_type: NetworkInterfaceType, network_interface_ip=None
):
    """
    This adds additional network interface into the PSG
    """

    atlas = context.catalyst_gateway

    nic = None
    if nic_type == NetworkInterfaceType.mgmt_only or nic_type == NetworkInterfaceType.mgmt_and_data:
        nic = context.nic_primary_interface
    elif nic_type == NetworkInterfaceType.data1:
        nic = context.nic_data1
    elif nic_type == NetworkInterfaceType.data2:
        nic = context.nic_data2

    # For additional interface 'gateway' shouldn't be used for now but API allows considering
    # some corner customer senarios also for the future improvement.
    def _add_interface_and_check_status(network_address):
        nic_details = CreateNetworkInterface(
            CreateNetworkInterfaceDetails(
                network_address,
                nic["network_name"],
                nic["network_type"],
                nic["netmask"],
            )
        )
        psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
        response = atlas.create_network_interface(psgw["id"], nic_details)
        assert (
            response.status_code == codes.accepted
        ), f"Failed to add new interface for the PSG. Response: {response.text}"

        task_id_inner = tasks.get_task_id_from_header(response)
        status_inner = tasks.wait_for_task(
            task_id_inner,
            context.user,
            timeout=TimeoutManager.standard_task_timeout,
            message=f"Failed to add new interface for the PSG in {TimeoutManager.standard_task_timeout}s",
        )
        return task_id_inner, status_inner

    available_ip = None
    if network_interface_ip:
        task_id, status = _add_interface_and_check_status(network_interface_ip)
    else:
        available_ip = get_unused_ip_for_network_interface(context, nic["network_address"])
        task_id, status = _add_interface_and_check_status(available_ip)
    assert status == "succeeded", f"Network interface creation task failed. Task id: {task_id}"
    if nic["network_name"] == "Data1":
        context.nic_data1_ip = available_ip
    elif nic["network_name"] == "Data2":
        context.nic_data2_ip = available_ip
    logger.info(f"Network interface {nic['network_name']} successfully created for {context.psgw_name}")


def add_fourth_network_interface_and_verify_error(context):
    """This step performs addition of fourth network interface and user should get error as validating in this step.

    Args:
        context (Context): context object
    """
    atlas = context.catalyst_gateway
    nic_details = CreateNetworkInterface(
        CreateNetworkInterfaceDetails(
            "172.20.232.210",
            "Data3",
            "STATIC",
            "255.255.248.0",
        )
    )
    logger.info("Adding fourth network interface")
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    response = atlas.create_network_interface(psgw["id"], nic_details)
    assert response.status_code == codes.bad, (
        f"Unexpected status code for add fourth network interface. Expected is {codes.bad}"
        f", but it's {response.status_code}. Response: {response.text}"
    )
    assert (
        ERROR_MESSAGE_CANNOT_ADD_ANOTHER_NIC in response.text
    ), f"Unexpected response message. Should contain {ERROR_MESSAGE_CANNOT_ADD_ANOTHER_NIC}, but was: {response.text}"


def delete_protection_store_gateway_vm(context: Context, verify=True):
    """
    Find and remove given PSGW
    If 'verify' flag disabled then post removal validations are skipped

    Args:
        context (Context): context object
        verify (bool, optional): If user want to verify delete psgvm successffuly done or not. Defaults to True.
    """
    atlas = CatalystGateway(context.user)
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    assert "id" in psgw, __PSGW_ID_NOT_FOUND
    response = atlas.delete_catalyst_gateway_vm(psgw["id"])
    assert response.status_code == codes.accepted, f"{response.content}"
    if not verify:
        return response
    task_id = tasks.get_task_id_from_header(response)
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout=TimeoutManager.standard_task_timeout,
        message="Failed to remove PSGW within 900 seconds",
    )
    assert status == "succeeded", f"Delete PSGW VM Task {task_id} : {status}"
    # Verification post removal of PSGW
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    assert psgw == {}, f"Error: PSGW entity '{context.psgw_name}', still listed"
    logger.info(f"deleted {context.psgw_name} successfully..")


def cleanup_all_psgw_vms(context: Context):
    atlas = context.catalyst_gateway
    response = atlas.get_catalyst_gateways()
    assert response.status_code == codes.ok, f"response failed with {response.status_code}, {response.text}"

    items = response.json().get("items")
    logger.info("Get all psgws")
    for item in items:
        if context.psgw_name.split("_")[0] in item["name"]:
            _psgw_name, _, _vcenter_name = atlas.get_catalyst_gateway_details(context.user, item)
            logger.info(f"Get psgw: {_psgw_name}, vcenter: {_vcenter_name}")
            current_vcenter = _vcenter_name == context.vcenter_name
            if current_vcenter:
                context.psgw_name = _psgw_name
                cleanup_psgw_vm(context)
            else:
                logger.info(f"Skipping PSGW cleanup:{_psgw_name}, vcenter: {_vcenter_name}")
        else:
            logger.info(f'Skipping PSGW cleanup: {item["name"]}')


def cleanup_psgw_vm(context: Context):
    delete_all_backups(BackupTypeParam.backups, context)
    delete_all_backups(BackupTypeParam.snapshots, context)
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)
    atlas = context.catalyst_gateway
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    if not psgw:
        logger.info(f"PSGW VM {context.psgw_name} not found in the vCenter: {context.vcenter_name}")
        return
    logger.info(f"Deleting PSGW VM {context.psgw_name} from the vCenter: {context.vcenter_name}")
    response = atlas.delete_catalyst_gateway_vm(psgw["id"])
    if response.status_code == codes.accepted:
        task_id = tasks.get_task_id_from_header(response)
        status = tasks.wait_for_task(
            task_id,
            context.user,
            timeout=3600,
            message="PSGW VM delete failed",
        )
        if status == "succeeded":
            logger.info(f"successfully deleted psgw vm {context.psgw_name} from vcenter: {context.vcenter_name}")
        else:
            logger.info(f"Delete PSGW VM Task {task_id} : {status}")
    else:
        logger.info(
            f"delete PSG request not accepted status code:  {response.status_code}, psgw vm : {context.psgw_name} from vcenter: {context.vcenter_name}"
        )


def update_dns_address_catalyst_gateway_vm(context: Context):
    """Updates DNS address for protection store gateway vm"""
    atlas = CatalystGateway(context.user)
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    assert "id" in psgw, __PSGW_ID_NOT_FOUND
    response = atlas.update_dns_address(context.dns2, psgw["id"])
    assert response.status_code == codes.accepted
    task_id = tasks.get_task_id_from_header(response)
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout=TimeoutManager.v_center_manipulation_timeout,
        message="Failed to update dns address in 60 seconds",
    )
    assert status == "succeeded", f"Update DNS task {task_id} : {status}"


def update_proxy_address_catalyst_gateway_vm(context: Context):
    """Updates proxy address and port for protection store gateway vm"""
    atlas = CatalystGateway(context.user)
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    assert "id" in psgw, __PSGW_ID_NOT_FOUND
    response = atlas.update_proxy_address(context.proxy, context.port, psgw["id"])
    assert response.status_code == codes.accepted
    task_id = tasks.get_task_id_from_header(response)
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout=TimeoutManager.v_center_manipulation_timeout,
        message="Failed to update proxy address in 60 seconds",
    )
    assert status == "succeeded", f"Update proxy task {task_id} : {status}"


def psgw_storage_resize(context, error_case=False, additional_ds_name=None, additional_ds_required=False):
    psgw_resize_timeout = TimeoutManager.resize_psg_timeout
    atlas = CatalystGateway(context.user)
    psgw_id = atlas.get_catalyst_gateway_id(context)
    response = atlas.add_storage(
        context.psgw_name, context.update_psg_size, psgw_id, additional_ds_name, additional_ds_required
    )
    logger.info(f"Resize PSGW storage capacity response: {response.content}")
    if error_case:
        return response
    assert response.status_code == codes.accepted, f"{response.content}"
    task_id = tasks.get_task_id(response)
    logger.info(f"Resize PSGW storage capacity. Task ID: {task_id}")
    status = tasks.wait_for_task(
        task_id,
        context.user,
        psgw_resize_timeout,
        interval=30,
        message=f"PSG Gateway resize time exceed {psgw_resize_timeout / 60:1f} minutes - TIMEOUT",
    )
    assert (
        status == "succeeded"
    ), f"Resize operation failed on PSGW: {context.psgw_name} \
                                        Failed: {tasks.get_task_error(task_id, context.user)}"
    logger.info(f"Successfully resized PSGW: {context.psgw_name} storage capacity!!!")


def validate_resize_catalyst_gatway_error_message(context, expected_error):
    response = psgw_storage_resize(context, error_case=True)
    assert (
        response.status_code == codes.bad_request
    ), f"Failed, Expected status code: {codes.bad_request} but received {response.status_code}"
    assert (
        expected_error in response.json()["message"]
    ), f"Failed to validate error message: {expected_error} in error response: {response.text}"
    logger.info(f"Successfully validated error message: {expected_error} in error response: {response.text}")


def recover_protection_store_gateway_vm(
    context: Context,
    add_data_interface=True,
    recover_psgw_name="recover_psgw",
    max_cld_dly_prtctd_data=25.0,
    max_cld_rtn_days=25,
    max_onprem_dly_prtctd_data=25.0,
    max_onprem_rtn_days=25,
    override_cpu=0,
    override_ram_gib=0,
    override_storage_tib=0,
    verify_vmId=False,
    additional_ds_name=None,
    additional_ds_required=False,
    return_response=False,
    deploy_ova_on_content_lib_ds=False,
    deploy_on_folder=False,
    deploy_with_cluster_id=False,
    deploy_with_resource_pools=False,
):
    atlas = CatalystGateway(context.user)
    logger.info(f"Recovering PSGW: {context.psgw_name}")
    psgw_id = atlas.get_catalyst_gateway_id(context)
    assert psgw_id is not None, f"Failed to find PSGW id for {context.psgw_name}"
    datastore_info = [context.datastore_id]
    if additional_ds_required:
        datastore_ids = atlas.get_additional_datastores(additional_ds_name)
        datastore_info = datastore_ids
    response = atlas.recover_catalyst_gateway_vm(
        psgw_id,
        context.vcenter_id,
        datastore_info,
        context.esxhost_id,
        context.hypervisor_cluster_id,
        context.content_lib_datastore_id,
        context.hypervisor_folder_id,
        context.resources_pools_id,
        context.network_name,
        context.network,
        context.netmask,
        context.gateway,
        context.network_type,
        recover_psgw_name=recover_psgw_name,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
        override_cpu=override_cpu,
        override_ram_gib=override_ram_gib,
        override_storage_tib=override_storage_tib,
        deploy_ova_on_content_lib_ds=deploy_ova_on_content_lib_ds,
        deploy_on_folder=deploy_on_folder,
        deploy_with_cluster_id=deploy_with_cluster_id,
        deploy_with_resource_pools=deploy_with_resource_pools,
    )
    logger.info(response.text)
    if return_response:
        return response
    assert response.status_code == codes.accepted, f"{response.content}"
    if verify_vmId == True:
        context.psgw_name = f"recover_{context.psgw_name}"
        validate_psg_vmid_at_given_state(context, "during_recover")

    status = tasks.wait_for_task(
        tasks.get_task_id(response),
        context.user,
        timeout=TimeoutManager.create_psgw_timeout,
        interval=30,
        message=f"PSG Recover task wait time exceeded {TimeoutManager.create_psgw_timeout / 60:1f} minutes - TIMEOUT",
    )
    assert status.upper() == TaskStatus.success.value, f"Task completed with status '{status}'"

    context.psgw_name = recover_psgw_name
    wait_for_psgw_health_to_reach_ok_or_warning_connected(context)
    health = atlas.get_catalyst_gateway_health_status(recover_psgw_name)
    assert (
        health == HealthStatus.CONNECTED.value
    ), f"Current status - {health} not matched with {HealthStatus.CONNECTED.value}"

    state = atlas.get_catalyst_gateway_health_state(recover_psgw_name)
    assert state in (
        HealthState.OK.value,
        HealthState.WARNING.value,
    ), f"Current state - {state} not matched with {HealthState.OK.value}/{HealthState.WARNING.value}"
    logger.info(f"Successfully recovered the PSGW VM:{recover_psgw_name} with {health} status and {state} state: ")
    if add_data_interface:
        add_additional_network_interface_catalyst_gateway_vm(context, nic_type=NetworkInterfaceType.data1)


def create_cloud_protection_during_recover_protection_store_gateway_vm(
    context: Context,
    add_data_interface=False,
    recover_psgw_name="recover_psgw",
    max_cld_dly_prtctd_data=1.0,
    max_cld_rtn_days=1,
    max_onprem_dly_prtctd_data=1.0,
    max_onprem_rtn_days=1,
    override_cpu=0,
    override_ram_gib=0,
    override_storage_tib=0,
    verify_vmId=False,
    additional_ds_name=None,
    additional_ds_required=False,
    return_response=False,
    deploy_ova_on_content_lib_ds=False,
    deploy_on_folder=False,
    deploy_with_cluster_id=False,
    deploy_with_resource_pools=False,
):
    atlas = context.catalyst_gateway
    logger.info(f"Recovering PSGW: {context.psgw_name}")
    psgw_id = atlas.get_catalyst_gateway_id(context)
    assert psgw_id is not None, f"Failed to find PSGW id for {context.psgw_name}"
    datastore_info = [context.datastore_id]
    if additional_ds_required:
        datastore_ids = atlas.get_additional_datastores(additional_ds_name)
        datastore_info = datastore_ids
    response = atlas.recover_catalyst_gateway_vm(
        psgw_id,
        context.vcenter_id,
        datastore_info,
        context.esxhost_id,
        context.hypervisor_cluster_id,
        context.content_lib_datastore_id,
        context.hypervisor_folder_id,
        context.resources_pools_id,
        context.network_name,
        context.network,
        context.netmask,
        context.gateway,
        context.network_type,
        recover_psgw_name=recover_psgw_name,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
        override_cpu=override_cpu,
        override_ram_gib=override_ram_gib,
        override_storage_tib=override_storage_tib,
        deploy_ova_on_content_lib_ds=deploy_ova_on_content_lib_ds,
        deploy_on_folder=deploy_on_folder,
        deploy_with_cluster_id=deploy_with_cluster_id,
        deploy_with_resource_pools=deploy_with_resource_pools,
    )
    logger.info(f"Response of the recover task: {response.text}")
    if return_response:
        return response
    assert response.status_code == codes.accepted, f"{response.content}"
    if verify_vmId is True:
        context.psgw_name = f"recover_{context.psgw_name}"
        validate_psg_vmid_at_given_state(context, "during_recover")
    context.psgw_name = f"recover_{context.psgw_name}"
    logger.info(f"psgw id :{psgw_id}")

    protection_store_task_id = create_protection_store(
        context, type=CopyPoolTypes.cloud, cloud_region=AwsStorageLocation.AWS_US_EAST_2, return_task_id=True
    )

    status = tasks.wait_for_task(
        tasks.get_task_id(response),
        context.user,
        timeout=TimeoutManager.create_psgw_timeout,
        interval=30,
        message=f"PSG Recover task wait time exceeded {TimeoutManager.create_psgw_timeout / 60:1f} minutes - TIMEOUT",
    )
    assert status.upper() == TaskStatus.success.value, f"Task completed with status '{status}'"

    health = atlas.get_catalyst_gateway_health_status(recover_psgw_name)
    assert (
        health == HealthStatus.CONNECTED.value
    ), f"Current status - {health} not matched with {HealthStatus.CONNECTED.value}"

    state = atlas.get_catalyst_gateway_health_state(recover_psgw_name)
    assert state in (
        HealthState.OK.value,
        HealthState.WARNING.value,
    ), f"Current state - {state} not matched with {HealthState.OK.value}/{HealthState.WARNING.value}"
    logger.info(f"Successfully recovered the PSGW VM:{recover_psgw_name} with {health} status and {state} state: ")
    # context.psgw_name = recover_psgw_name
    if add_data_interface:
        add_additional_network_interface_catalyst_gateway_vm(context, nic_type=NetworkInterfaceType.data1)

    # validate cloud protection store is created
    timeout = TimeoutManager.create_psgw_timeout
    status = tasks.wait_for_task(
        protection_store_task_id,
        context.user,
        timeout,
        message=f"Create protection store {type}  {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert (
        status == "succeeded"
    ), f"We got wrong status: {status} for task: {tasks.get_task_object(user=context.user, task_id=protection_store_task_id)}"
    logger.info(f"Create cloud protection store succeeded")
    onprem_protection_store_id_list, cloud_protection_store_id_list = atlas.get_on_premises_and_cloud_protection_store(
        context
    )
    validate_cloud_protection_store_is_created(context, cloud_protection_store_id_list[1])


def validate_cloud_protection_store_is_created(context: Context, cloud_protection_store_id):
    """
    this function is used to verify cloud store is created with cloud protection store id
    """
    atlas = context.catalyst_gateway
    logger.info(f"cloud protection store id:{cloud_protection_store_id}")
    cloud_protection_store_id_and_ok_state = False
    for i in range(1, 30):
        protection_stores_response = atlas.get_protection_stores()
        resp_body = protection_stores_response.json()
        logger.info(f"protection stores Response:{resp_body}")
        for item in resp_body["items"]:
            if item["id"] == cloud_protection_store_id:
                if item["state"] == "ONLINE":
                    if item["status"] == "OK":
                        cloud_protection_store_id_and_ok_state = True
                        logger.info("Successfully verified cloud protection store after recover the psg")
                        break
                else:
                    sleep(5)
                    logger.info("cloud protection store not yet come to ONLINE state")
        if cloud_protection_store_id_and_ok_state:
            break

    assert (
        cloud_protection_store_id_and_ok_state
    ), f"cloud protection store id not in ok state {cloud_protection_store_id}"


def wait_for_psg(
    context: Context,
    state: State = State.OK,
    health_state: HealthState = HealthState.OK,
    health_status: HealthStatus = HealthStatus.CONNECTED,
    timeout: int = TimeoutManager.standard_task_timeout,
    interval: int = 5,
):
    """
    Waits untill PSG State and its Health State/Status matches with given value.
    Returns AssertionError is given task timed out.
    """
    cgm = context.catalyst_gateway
    psgw = cgm.get_catalyst_gateway_by_name(name=context.psgw_name)
    assert "id" in psgw, f"Failed to find PSGW ID. Response: {psgw}"

    def _check_psg_state_and_status():
        res = cgm.get_catalyst_gateway(catalyst_gateway_id=psgw["id"])
        assert res.status_code == codes.ok, f"Failed to get PSG. Response: {res.text}"
        (v1, v2, v3) = (
            res.json().get("state"),
            res.json().get("health", {}).get("state"),
            res.json().get("health", {}).get("status"),
        )
        logger.debug(f"State: {v1} - Health State: {v2} - Health Status: {v3}")
        return v1 == state.value and v2 == health_state.value and v3 == health_status.value

    try:
        wait(
            _check_psg_state_and_status,
            timeout_seconds=timeout,
            sleep_seconds=interval,
        )
    except TimeoutExpired:
        raise AssertionError(f"PSGW state and status not matched with expected value")


def get_psgw_required_sizer_fields(
    context,
    max_cld_dly_prtctd_data=1.0,
    max_cld_rtn_days=1,
    max_onprem_dly_prtctd_data=1.0,
    max_onprem_rtn_days=1,
):
    atlas = CatalystGateway(context.user)
    psgw_id = atlas.get_catalyst_gateway_id(context)
    response = atlas.psgw_required_sizer_fields_to_resize(
        psgw_id,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    return response


def get_create_psgw_required_sizer_fields(
    context,
    max_cld_dly_prtctd_data=1.0,
    max_cld_rtn_days=1,
    max_onprem_dly_prtctd_data=1.0,
    max_onprem_rtn_days=1,
):
    atlas = CatalystGateway(context.user)
    response = atlas.required_size_fields_to_create_psgw(
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    return response


def validate_psgw_sizer_fields(
    context,
    get_create_psgw_sizer=False,
    max_cld_dly_prtctd_data=1.0,
    max_cld_rtn_days=1,
    max_onprem_dly_prtctd_data=1.0,
    max_onprem_rtn_days=1,
    exp_required_fields={},
):
    response = None
    if get_create_psgw_sizer:
        response = get_create_psgw_required_sizer_fields(
            context,
            max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
            max_cld_rtn_days=max_cld_rtn_days,
            max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
            max_onprem_rtn_days=max_onprem_rtn_days,
        )
    else:
        response = get_psgw_required_sizer_fields(
            context,
            max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
            max_cld_rtn_days=max_cld_rtn_days,
            max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
            max_onprem_rtn_days=max_onprem_rtn_days,
        )
    assert response.status_code == codes.ok, f"{response.content}"
    act_required_fields = response.json()
    assert (
        act_required_fields == exp_required_fields
    ), f"Actual: {act_required_fields} vs Expected: {exp_required_fields} fields are not matched"
    logger.info(f"Actual: {act_required_fields} vs Expected: {exp_required_fields} fields are matched")


def get_existing_psgw_resize_req_response(
    context,
    additional_ds_name=None,
    additional_ds_required=False,
    max_cld_dly_prtctd_data=1.0,
    max_cld_rtn_days=1,
    max_onprem_dly_prtctd_data=1.0,
    max_onprem_rtn_days=1,
    override_cpu=0,
    override_ram_gib=0,
    override_storage_tib=0,
):
    atlas = CatalystGateway(context.user)
    psgw_id = atlas.get_catalyst_gateway_id(context)
    psgw_datastore_info = atlas.get_catalyst_gateway_datastores(context.psgw_name)
    datastore_info = []
    if additional_ds_required:
        additional_datastore_info = atlas.get_additional_datastores(additional_ds_name)
        datastore_ids = additional_datastore_info + psgw_datastore_info
        datastore_info = list(dict.fromkeys(datastore_ids))
    else:
        datastore_info = psgw_datastore_info
    response = atlas.resize_existing_psgw(
        psgw_id,
        datastore_info=datastore_info,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
        override_cpu=override_cpu,
        override_ram_gib=override_ram_gib,
        override_storage_tib=override_storage_tib,
    )
    logger.debug(f"Resize PSGW storage capacity response: {response.content}")
    return response


def get_resize_psg_task_status(context, response):
    psgw_resize_timeout = TimeoutManager.resize_timeout
    assert response.status_code == codes.accepted, f"{response.content}"
    task_id = tasks.get_task_id_from_header(response)
    logger.info(f"Resize PSGW storage capacity. Task ID: {task_id}")
    status = tasks.wait_for_task(
        task_id,
        context.user,
        psgw_resize_timeout,
        interval=30,
        message=f"PSG Gateway resize time exceed {psgw_resize_timeout / 60:1f} minutes - TIMEOUT",
    )
    if status == "succeeded":
        logger.info(f"Successfully resized PSGW: {context.psgw_name}")
        return True
    else:
        logger.error(
            f"Resize operation failed on PSGW: {context.psgw_name} Failed: {tasks.get_task_error(task_id, context.user)}"
        )
        return False


def validate_existing_psgw_resize_functionality(
    context,
    additional_ds_name=None,
    additional_ds_required=False,
    max_cld_dly_prtctd_data=1.0,
    max_cld_rtn_days=1,
    max_onprem_dly_prtctd_data=1.0,
    max_onprem_rtn_days=1,
    override_cpu=0,
    override_ram_gib=0,
    override_storage_tib=0,
):
    logger.info("Validating existing psgw resize functionality")
    response = get_existing_psgw_resize_req_response(
        context,
        additional_ds_name=additional_ds_name,
        additional_ds_required=additional_ds_required,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
        override_cpu=override_cpu,
        override_ram_gib=override_ram_gib,
        override_storage_tib=override_storage_tib,
    )
    resize_status = get_resize_psg_task_status(context, response)
    assert resize_status, "Existing psgw resize validation failed"
    wait_for_psgw_health_to_reach_ok_or_warning_connected(context)
    sleep(300)  # sleep for 300 seconds after resize for protection store to reach online
    verify_local_protection_store_state(context)


def wait_to_get_psgw_to_powered_off(context):
    atlas = CatalystGateway(context.user)
    psgw_id = atlas.get_catalyst_gateway_id(context)

    # Shutdown protection store gateway
    shutdown_timeout = TimeoutManager.psg_shutdown_timeout
    response = atlas.shutdown_catalyst_gateway_vm(psgw_id)
    assert response.status_code == codes.accepted, f"{response.content}"
    logger.debug(f"Shutodown PSGW response: {response.content}")
    task_id = tasks.get_task_id_from_header(response)
    logger.debug(f"Shutdown PSGW Task ID: {task_id}")
    status = tasks.wait_for_task(
        task_id,
        context.user,
        shutdown_timeout,
        interval=30,
        message=f"PSG Gateway shutdown time exceed {shutdown_timeout / 60:1f} minutes - TIMEOUT",
    )
    assert (
        status == "succeeded"
    ), f"Failed to shutdown PSGW: {context.psgw_name} \
                                        Failed: {tasks.get_task_error(task_id, context.user)}"
    logger.info(f"Successfully shutdown PSGW: {context.psgw_name}")

    # Wait until, psgw to powered off state
    service_instance = generate_SmartConnect(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    is_psgw_powered_off = wait_until_vm_gets_powered_off(
        service_instance, context.psgw_name, timeout=TimeoutManager.psg_powered_off_timeout
    )
    assert is_psgw_powered_off, f"Failed to get psgw: {context.psgw_name} {VmPowerOption.off.value} state"


def validate_psgw_resources_post_update(
    context,
    max_cld_dly_prtctd_data=1.0,
    max_cld_rtn_days=1,
    max_onprem_dly_prtctd_data=1.0,
    max_onprem_rtn_days=1,
):
    atlas = CatalystGateway(context.user)
    psg_size = atlas.psgw_total_disk_size_tib(context.psgw_name)
    logger.info(f"Existing PSGW storage capacity: {psg_size}")
    psg_compute_info = atlas.psgw_compute_info(context.user, context.psgw_name)
    logger.info(f"Existing PSGW compute capacity: {psg_compute_info}")
    response = get_psgw_required_sizer_fields(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    assert response.status_code == codes.ok, f"{response.content}"
    act_required_fields = response.json()
    # we don't have an option to fetch iops field, hence Deleting it
    del act_required_fields["iops"]
    # we don't have an option to fetch bandwidthMegabitsPerSecond, hence Deleting it
    del act_required_fields["bandwidthMegabitsPerSecond"]
    exp_required_fields = {
        "vCpu": psg_compute_info["numCpuCores"],
        "ramInGiB": float(psg_compute_info["memorySizeInMib"]) / 1024,
        "storageInTiB": psg_size,
    }
    if act_required_fields == exp_required_fields:
        logger.info(f"Actual: {act_required_fields} vs Expected: {exp_required_fields} fields are matched")
    else:
        assert False, f"Actual: {act_required_fields} vs Expected: {exp_required_fields} fields are not matched"


def validate_psg_health_state_along_with_resize(context, wait_time=180, post_resize_state=False):
    atlas = CatalystGateway(context.user)
    # validate post resize health state
    if post_resize_state:
        state = atlas.get_catalyst_gateway_health_state(context.psgw_name)
        assert (
            HealthState.OK.value in state
        ), f"Current state: {state} not matched with desired state: {HealthState.OK.value}"
        logger.info(f"Current state: {state} matched with desired state: {HealthState.OK.value}")
        return
    timeout = wait_time
    # Validate Updating state
    while wait_time > 0:
        state = atlas.get_catalyst_gateway_health_state(context.psgw_name)
        if HealthState.OK.value in state:
            sleep(30)
            logger.info(f"Current state: {state} sleeping for 30 sec to get {HealthState.UPDATING.value} state")
            wait_time -= 30
        if HealthState.UPDATING.value in state:
            logger.info(f"Current state - {state} matched with desired state {HealthState.UPDATING.value}")
            break
    assert (
        wait_time
    ), f"Times Up!!!, PSG is still in {HealthState.OK.value} state, even after {timeout} sec of resize operation"


def validate_psgw_sizer_fields_error_messages(
    context,
    validate_create_psgw_sizer=False,
    max_cld_dly_prtctd_data=1.0,
    max_cld_rtn_days=1,
    max_onprem_dly_prtctd_data=1.0,
    max_onprem_rtn_days=1,
    exp_error_msg="",
):
    response = None
    if validate_create_psgw_sizer:
        response = get_create_psgw_required_sizer_fields(
            context,
            max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
            max_cld_rtn_days=max_cld_rtn_days,
            max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
            max_onprem_rtn_days=max_onprem_rtn_days,
        )
    else:
        response = get_psgw_required_sizer_fields(
            context,
            max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
            max_cld_rtn_days=max_cld_rtn_days,
            max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
            max_onprem_rtn_days=max_onprem_rtn_days,
        )
    assert (
        response.status_code == codes.bad_request
    ), f"Failed, Expected status code: {codes.bad_request} but received {response.status_code}"
    assert (
        exp_error_msg in response.json()["message"]
    ), f"Failed to validate error message EXPECTED: {exp_error_msg} ACTUAL: {response.text}"
    logger.info(f"Successfully validated error message EXPECTED: {exp_error_msg} ACTUAL: {response.text}")


def get_local_protection_store_status(context):
    atlas = CatalystGateway(context.user)
    psgw_id = atlas.get_catalyst_gateway_id(context)
    resource_uri = f"/api/{atlas.dscc['version']}/{atlas.path}/{psgw_id}"
    # display_name = "Create local protection store"
    display_name = f"Create On-Premises Protection Store [Local_{context.psgw_name}]"
    logger.info("Looking for local protection store trigger task")
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
    trigger_task_id = (
        tasks.get_tasks_by_name_and_resource_uri_with_no_offset(
            user=context.user,
            task_name=display_name,
            resource_uri=resource_uri,
        )
        .items[0]
        .id
    )
    logger.info(f"Local protection store triggered task ID: {trigger_task_id}")

    # wait for the trigger task to complete
    trigger_task_state = tasks.wait_for_task(
        task_id=trigger_task_id, user=context.user, timeout=TimeoutManager.create_local_store_timeout, log_result=True
    )
    if trigger_task_state == "succeeded":
        logger.info(f"Successfully created local protection store, task state: {trigger_task_state}")
        return True
    else:
        logger.error(
            f"Failed to Create On-Premises Protection Store [Local_{context.psgw_name}], task state: {trigger_task_state}"
        )
        return False


def wait_for_psgw_health_to_reach_ok_or_warning_connected(context):
    atlas = CatalystGateway(context.user)
    wait(
        lambda: atlas.get_catalyst_gateway_health_state(context.psgw_name)
        in (HealthState.OK.value, HealthState.WARNING.value)
        and atlas.get_catalyst_gateway_health_status(context.psgw_name) == HealthStatus.CONNECTED.value,
        timeout_seconds=TimeoutManager.psg_powered_off_timeout,
        sleep_seconds=30,
    )
    logger.info("PSGW health state: ok/warning and status: connected")


def wait_for_psgw_to_power_on_and_connected(context):
    atlas = CatalystGateway(context.user)
    psgw_id = atlas.get_catalyst_gateway_id(context)
    res = atlas.poweron_catalyst_gateway_vm(psgw_id)
    assert res.status_code == codes.accepted, f"Failed to power on the psgw vm {res.content}"
    logger.info(f"Successfully power on the PSGW: {context.psgw_name}")
    wait_for_psgw_health_to_reach_ok_or_warning_connected(context)


def wait_for_psgw_to_restart(context):
    atlas = CatalystGateway(context.user)
    psgw_id = atlas.get_catalyst_gateway_id(context)
    # Restart protection store gateway
    restart_timeout = TimeoutManager.psg_shutdown_timeout
    response = atlas.restart_catalyst_gateway_vm(psgw_id)
    assert response.status_code == codes.accepted, f"{response.content}"
    logger.debug(f"Restart PSGW response: {response.content}")
    task_id = tasks.get_task_id(response)
    logger.debug(f"Restart PSGW Task ID: {task_id}")
    status = tasks.wait_for_task(
        task_id,
        context.user,
        restart_timeout,
        interval=30,
        message=f"PSG Gateway Restart time exceed {restart_timeout / 60:1f} minutes - TIMEOUT",
    )
    assert (
        status == "succeeded"
    ), f"Failed to Restart PSGW: {context.psgw_name} \
                                        Failed: {tasks.get_task_error(task_id, context.user)}"
    logger.info(f"Successfully Restart PSGW: {context.psgw_name}")
    # As psgw not coming to unknown state during the restart so we are commenting this part.
    # check for psg status to disconnect after restart
    # wait_for_psg(
    #     context, state=State.UNKNOWN, health_state=HealthState.UNKNOWN, health_status=HealthStatus.DISCONNECTED
    # )
    # wait for 10 mins after restart vm from vcenter
    sleep(600)
    # check for psg to reach healthy state
    wait_for_psgw_health_to_reach_ok_or_warning_connected(context)


def remote_support_enable_and_disable_on_psgw(context, remote_support_enable=False):
    atlas = CatalystGateway(context.user)
    psgw_id = atlas.get_catalyst_gateway_id(context)
    psgw_info = atlas.get_catalyst_gateway(psgw_id)
    psgw_info_json = psgw_info.json()
    if psgw_info_json["remoteAccessEnabled"]:
        logger.info("Enabling Remote support for the PSGW which is already enabled")
    else:
        logger.info("Enabling remote support for psgw")
    response = atlas.set_catalyst_gateway_vm_remote_support(psgw_id, enabled=remote_support_enable)
    if remote_support_enable:
        remote_support = "enable"
    else:
        remote_support = "disable"
    assert (
        response.status_code == codes.accepted
    ), f"Failed to {remote_support} the remote support for psgw {response.content}"
    timeout = TimeoutManager.standard_task_timeout
    task_id = tasks.get_task_id_from_header(response)
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout=timeout,
        message=f"PSGW remote support {remote_support} task exceed {timeout} seconds - TIMEDOUT",
    )
    assert status == "succeeded", f"Failed to {remote_support} remote support on psgw"
    psgw_info = atlas.get_catalyst_gateway(psgw_id)
    psgw_info_json = psgw_info.json()
    if remote_support_enable:
        remote_enabled = (
            psgw_info_json["remoteAccessEnabled"] == True
            and psgw_info_json["adminUserCiphertext"] != ""
            and psgw_info_json["supportUserCiphertext"] != ""
        )
        assert remote_enabled, f"Failed to check remote support {remote_support}"
        logger.info("Remote support for PSGW enabled successfully")
    else:
        remote_disabled = (
            psgw_info_json["remoteAccessEnabled"] == False
            and psgw_info_json["adminUserCiphertext"] == ""
            and psgw_info_json["supportUserCiphertext"] == ""
        )
        assert remote_disabled, f"Failed to check remote support {remote_support}"
        logger.info("Remote support for PSGW disabled successfully")
    station_id = psgw_info_json.get("remoteAccessStationId")
    assert station_id != "", "failed to get stationId for psg when remote support enabled/disabled"


def generate_support_bundle_for_psgw(context, support_bundle_slim=False, validate_error_message=False):
    atlas = CatalystGateway(context.user)
    psgw_id = atlas.get_catalyst_gateway_id(context)
    task_timeout = TimeoutManager.standard_task_timeout
    res = atlas.generate_catalyst_gateway_vm_support_bundle(
        psgw_id, desc="Generated support bundle using api Automation testing", slim=support_bundle_slim
    )
    assert res.status_code == codes.accepted, f"Failed to generate support bundle for psgw"

    if validate_error_message:
        logger.info("validation of generate support bundle error message started")
        error_response = atlas.generate_catalyst_gateway_vm_support_bundle(
            psgw_id,
            desc="Generated support bundle using api Automation testing for error message",
            slim=support_bundle_slim,
        )
        assert error_response.status_code == codes.accepted, f"Failed to generate support bundle for psgw"
        error_task_id = tasks.get_task_id_from_header(error_response)
        error_status = tasks.wait_for_task(
            error_task_id,
            context.user,
            task_timeout,
            interval=30,
        )
        assert (
            error_status == "failed"
        ), "failed to check error message while generating support bundle when already in progress"
        error_message = tasks.get_task_error(error_task_id, context.user)
        assert (
            error_message == ERROR_MESSAGE_GENERATE_SUPPORT_BUNDLE_WHEN_ALREADY_INPROGRESS
        ), f"failed to get expected error message: {ERROR_MESSAGE_GENERATE_SUPPORT_BUNDLE_WHEN_ALREADY_INPROGRESS} , output error message:{error_message}, "
        logger.info(
            "successfully verified the error message for support bundle when generate support bundle task already in progress"
        )

    task_id = tasks.get_task_id_from_header(res)
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout=task_timeout,
        message=f"PSG generate support bundle task exceed {task_timeout} seconds - TIMEDOUT",
    )
    assert status == "succeeded", f"Generate Support Bundle {task_id}: {status}"
    psgw_support_bundle_ticketname = res.json()["ticketName"]
    assert psgw_support_bundle_ticketname != "", f"Fail to check generate support bundle"
    logger.info(f"Support bundle generated successfully for psgw with ticket name : {psgw_support_bundle_ticketname}")


def create_psgvm_nic_interface_when_esx_disconnected(context):
    logger.info(f"Adding nic interface when ESX is disconnected")
    standard_psgw_timeout = TimeoutManager.create_psgw_timeout
    catalyst_gateway = context.catalyst_gateway
    catalyst_gateway_id = catalyst_gateway.get_catalyst_gateway_id(context)
    nic = context.nic_data1
    available_ip = get_unused_ip_for_network_interface(context, nic["network_address"])
    nic_details = CreateNetworkInterface(
        CreateNetworkInterfaceDetails(available_ip, nic["network_name"], nic["network_type"], nic["netmask"])
    )

    response = catalyst_gateway.create_network_interface(catalyst_gateway_id, nic_details)
    task_id = tasks.get_task_id(response)

    status = tasks.wait_for_task(
        task_id,
        context.user,
        standard_psgw_timeout,
        interval=30,
    )
    assert status == "failed", f"Create NIC task should fail, as ESX host is disconnected"
    error_message = tasks.get_task_error(task_id, context.user)
    assert (
        error_message == ERROR_MESSAGE_CANNOT_CONFIGURE_NIC
    ), f"Got incorrect create NIC error_message ERROR: {error_message}"
    logger.info(f"Validated correct error msg while adding nic when ESX is disconnected")


def resize_psgvm_when_esx_disconnected(context):
    logger.info(f"Resize psg_vm when ESX is disconnected")
    standard_psgw_timeout = TimeoutManager.create_psgw_timeout
    response = get_existing_psgw_resize_req_response(
        context,
        max_cld_dly_prtctd_data=1,
        max_cld_rtn_days=1,
        max_onprem_dly_prtctd_data=2,
        max_onprem_rtn_days=1,
    )
    task_id = tasks.get_task_id_from_header(response)

    status = tasks.wait_for_task(
        task_id,
        context.user,
        standard_psgw_timeout,
        interval=30,
    )
    assert status == "failed", f"Resize psgw_vm task should have failed as ESX host is disconnected"
    error_message = tasks.get_task_error(task_id, context.user)
    assert (
        error_message == ERROR_MESSAGE_CANNOT_RESIZE_PSGW_VM
    ), f"Got incorrect resize psgw_vm error_message ERROR: {error_message}"
    logger.info(f"Validated correct error msg while resize of psg_vm when ESX is disconnected")


def reveal_console_password_on_the_recovered_psgw(context):
    atlas = CatalystGateway(context.user)
    psgw_id = atlas.get_catalyst_gateway_id(context)
    res = atlas.post_catalyst_gateway_vm_console_user(psgw_id)
    assert res.status_code == codes.ok, f"Failed to generate a reveal console password"
    reveal_console_password = res.json()["password"]
    logger.info(f"Reveal console password is {reveal_console_password}")
    assert reveal_console_password != "", f"Fail to check generate a reveal console password"
    return reveal_console_password


def validate_ssh_login_through_console_password(context, console_password, console_user="console"):
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            context.network, port=22, username=console_user, password=console_password, allow_agent=False
        )
        logger.info(f"Able to login into through PSGW through reveal console user credentials")
        ssh_client.close()
    except Exception as e:
        logger.error(f"Exception while ssh login through console reveal password in vm {context.network} error:{e}")
        assert e


def enable_remote_support_get_cipher_text(context):
    atlas = context.catalyst_gateway
    psgw_id = atlas.get_catalyst_gateway_id(context)
    psgw_info = atlas.get_catalyst_gateway(psgw_id)
    psgw_info_json = psgw_info.json()
    if psgw_info_json["remoteAccessEnabled"]:
        logger.info("Remote support for the PSGW is already enabled")
    else:
        logger.info("Enabling remote support for psgw")
        response = atlas.set_catalyst_gateway_vm_remote_support(psgw_id, enabled=True)
        assert response.status_code == codes.accepted, f"Failed to enable remote support for psgw {response.content}"
        timeout = TimeoutManager.standard_task_timeout
        task_id = tasks.get_task_id_from_header(response)
        status = tasks.wait_for_task(
            task_id,
            context.user,
            timeout=timeout,
            message=f"PSGW remote support enable task exceed {timeout} seconds - TIMEDOUT",
        )
        assert status == "succeeded", f"Failed to enable remote support on psgw.Task id : {task_id},PSGW id: {psgw_id}"
    psgw_info = atlas.get_catalyst_gateway(psgw_id)
    psgw_info_json = psgw_info.json()
    remote_enabled = (
        psgw_info_json["remoteAccessEnabled"] == True
        and psgw_info_json["adminUserCiphertext"] != ""
        and psgw_info_json["supportUserCiphertext"] != ""
    )
    assert remote_enabled, f"Failed to check remote support enable"
    logger.info("Remote support for PSGW enabled successfully")
    return psgw_info_json["adminUserCiphertext"], psgw_info_json["supportUserCiphertext"]


def check_cipher_text(cipher1, cipher2, type="Admin"):
    logger.info(f"{type} Cipher Text before recovery")
    logger.info(f"{cipher1}")
    logger.info(f"{type} Cipher Text after recovery")
    logger.info(f"{cipher2}")
    assert cipher1 is not cipher2, f"{type} Cipher text before and after recovery are same"
    logger.info(f"{type} Cipher text before and after recovery are different.")


def verify_delete_psgw_not_allowed_if_backup_exists(context: Context):
    """
    If the PSGVM has backup and user tries to delete then we expect error message and we verify the same in this step

    Args:
        context (Context): Context object
    """
    timeout = 300
    atlas = CatalystGateway(context.user)
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    assert "id" in psgw, "Failed to find PSGW ID"
    response = atlas.delete_catalyst_gateway_vm(psgw["id"])
    assert response.status_code == codes.accepted, f"{response.content}"
    task_id = tasks.get_task_id_from_header(response)
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout,
        interval=30,
        message=f"Catalyst Gateway delete time exceed {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert status == "failed", f"We got wrong state {status} for task {task_id}"
    task_error_msg = tasks.get_task_error(task_id, context.user)
    assert re.search(
        ERROR_MESSAGE_DELETING_PSGW_CONTAINS_CLOUD_BACKUP, task_error_msg
    ), f"Expected error message not found {ERROR_MESSAGE_DELETING_PSGW_CONTAINS_CLOUD_BACKUP} on {task_error_msg}"
    logger.info(f"Successfully verified the error message {task_error_msg}")


"""
    validate override functionality with cpu, ram and storage.
    checking values from existing override psgw with the expected value given for override
"""


def validate_the_override_functionality(context, override_cpu, override_ram_gib, override_storage_tib):
    atlas = CatalystGateway(context.user)
    psgw_id = atlas.get_catalyst_gateway_id(context)
    psgw_info = atlas.get_catalyst_gateway(psgw_id)
    act_override_values = psgw_info.json()["override"]
    exp_override_values = {
        "cpu": override_cpu,
        "ramInGiB": override_ram_gib,
        "storageInTiB": override_storage_tib,
    }
    if act_override_values == exp_override_values:
        logger.info(f"Actual: {act_override_values} vs Expected: {exp_override_values} fields are matched")
    else:
        assert False, f"Actual: {act_override_values} vs Expected: {exp_override_values} fields are not matched"


def validate_psgw_error_messages(
    response,
    expected_status_code=codes.bad_request,
    expected_error=ERROR_MESSAGE_NAME_NOT_UNIQUE,
):
    """Validate protection store gateway deployment error messages

    Args:
        response (JSON response): JSON response of create protection store gateway
        expected_status_code (int, optional): expected status code. Defaults to codes.bad_request.
        expected_error (string, optional): expected error string. Defaults to ERROR_MESSAGE_NAME_NOT_UNIQUE.
    """
    assert (
        response.status_code == expected_status_code
    ), f"Failed to receive expected status code: Received: {response.status_code} expected: {expected_status_code}"
    logger.info(f"Received expected status code: Received: {response.status_code} Expected:{expected_status_code} ")
    assert expected_error in response.text, f"Failed to validate {expected_error} in {response.text}"
    logger.info(f"Successfully validated {expected_error} in {response.text}")


def verify_local_protection_store_state(context: Context):
    """Verify local protection store has been created successfully or not

    Args:
        context (Context): object of a context class
    """
    atlas = CatalystGateway(context.user)
    protection_stores = atlas.get_protection_stores()
    psgw_id = atlas.get_catalyst_gateway_id(context)
    assert (
        protection_stores.status_code == codes.ok
    ), f"Status code: {protection_stores.status_code} => {protection_stores.text}"
    logger.debug(f"List of protection stores from the APP: {protection_stores.json()}")
    find_condition = (
        lambda item: item["storageSystemInfo"]["id"] == psgw_id
        and item["protectionStoreType"] == CopyPoolTypes.local.value
        and (item["state"] == "OK" or item["state"] == "CREATED" or item["state"] == "ONLINE")
    )

    try:
        item = next(filter(find_condition, protection_stores.json().get("items")))
        logger.info(f"Found local protection store for the PSGW VM: {context.psgw_name} item: {item} ")
        return True
    except StopIteration:
        logger.info(f"Failed to find a local protection store for the PSGW VM: {context.psgw_name}")
    return False


def validate_psg_at_error_state_and_task_error_message(context: Context, task_id):
    """This step validation for psg is at error state and task id for psg deployment is having proper error message

    Args:
        context (Context): Context Object
        task_id (uuid): task id for psg deployment
    """
    logger.info("Starting of PSG Health State and task error message")
    wait_for_psg(
        context, state=State.DEPLOYED_ERROR, health_state=HealthState.ERROR, health_status=HealthStatus.DISCONNECTED
    )
    logger.info(f"Successfully Verified PSG Health Status as {HealthState.ERROR} & {HealthStatus.DISCONNECTED}")
    error_message = tasks.get_task_error(task_id, context.user)
    assert (
        error_message == ERROR_MESSAGE_DURING_DEPLOYMENT
    ), f"Expected {context.psgw_name} PSG deploy is not failed with Expected Error message: {error_message} and taskId: {task_id}"
    logger.info(f"Successfully Verified Task Error Message: {error_message}")


def perform_given_action_for_nic(context: Context, action):
    vsphere = VsphereApi(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    if action == "disconnect_nic":
        logger.info(f"Performing disconnect of the psg_vm VM Network nic")
        message = vsphere.disconnect_vm_nic(context.psgw_name)
        assert message == "Disconnect of psg_vm successfull", f"disconnect of psg_vm nic failed with {message}"
    if action == "reconnect_nic":
        logger.info(f"Performing reconnect of the psg_vm Network nic")
        message = vsphere.reconnect_vm_nic(context.psgw_name)
        logger.info(message)
        assert message == "Reconnect of psg_vm successfull", f"Reconnect of psg_vm nic failed"


def disconnect_nic_and_validate_psg_creation(context: Context, response):
    assert response.status_code == codes.accepted, f"{response.content}"
    task_id = tasks.get_task_id(response)
    logger.info(f"Create protection store gateway, Task ID: {task_id}")

    # wait for psgw vm to power on from vcenter
    def _wait_for_vm_power_on_status():
        si = generate_SmartConnect(context.vcenter_name, context.vcenter_username, context.vcenter_password)
        status = get_vm_power_status(si, context.psgw_name)
        if status == VmPowerOption.on.value:
            logger.info(f"VM: {context.vcenter_name} is in {VmPowerOption.on.value} state")
            return True

    wait(
        _wait_for_vm_power_on_status,
        timeout_seconds=TimeoutManager.create_psgw_timeout,
        sleep_seconds=15,
    )
    # After VM powered ON from vcenter... Disconnecting the network interface on VM
    perform_given_action_for_nic(context, "disconnect_nic")
    # checking status of the creating PSGW is failing
    status = tasks.wait_for_task(
        task_id,
        context.user,
        TimeoutManager.create_psgw_timeout,
        interval=30,
        message=f"Protection store gateway creation time exceed {TimeoutManager.create_psgw_timeout / 60:1f} minutes - TIMEOUT",
    )
    assert status == "failed", f"PSGW deployment was expected to failed, but its succeeded"
    error_message = tasks.get_task_error(task_id, context.user)
    assert (
        error_message == ERROR_MESSAGE_DURING_DEPLOYMENT
    ), f"Expected error message: {ERROR_MESSAGE_DURING_DEPLOYMENT} doesn't matched with actual error message: {error_message})"
    logger.info(
        f"Expected error message: {ERROR_MESSAGE_DURING_DEPLOYMENT} matched with actual error message: {error_message}"
    )


def validate_psgvm_after_disconnect_nic_and_wait_for_UNKNOWN_state(context):
    perform_given_action_for_nic(context, "disconnect_nic")
    # after disconnecting wait for psgw to reach state:unknown and status: disconnected
    wait_for_psg(
        context, state=State.UNKNOWN, health_state=HealthState.UNKNOWN, health_status=HealthStatus.DISCONNECTED
    )
    logger.info("PSGW is in unknown and disconnected state after disconnecting the device interface")


def validate_psgvm_after_reconnect_nic_and_wait_for_OK_state(context):
    perform_given_action_for_nic(context, "reconnect_nic")
    # after reconnecting wait for psgw to reach state:OK and status: connected
    wait_for_psg(context, state=State.OK, health_state=HealthState.OK, health_status=HealthStatus.CONNECTED)
    logger.info("PSGW is in OK and connected state  after re-connecting the device interface")


def delete_nic_during_deletion_of_psg_and_validate_deletion(context, response):
    # during deletion of psgw disconnecting NIC from vcenter
    perform_given_action_for_nic(context, "disconnect_nic")
    # after disconnecting wait psgw to delete completly
    task_id = tasks.get_task_id_from_header(response)
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout=TimeoutManager.standard_task_timeout,
        message="Failed to remove PSGW within 900 seconds",
    )
    assert status == "succeeded", f"Delete PSGW VM Task {task_id} : {status}"
    logger.info("Deletion of psgw successfull after disconnecting device interface")


def perform_shutdown(context: Context):
    atlas = CatalystGateway(context.user)
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    res = atlas.shutdown_catalyst_gateway_vm(psgw["id"])
    assert res.status_code == codes.bad_request, f'Expected task should fail with bad request. Response" {res.content}'

    # Response expected from the CGM:
    #     Operation 'shutdown protection store gateway' failed because of a bad request. Please retry and contact
    #     HPE support if this error persists.\nError:  validation failed for protection store gateway state: protection
    #     store gateway state is not 'OK'
    assert re.search(ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_SHUTDOWN, res.text), f"Expected error message not matched"
    logger.info(f"Verified expected message '{ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_SHUTDOWN}'")


def perform_power_ON(context: Context):
    atlas = CatalystGateway(context.user)
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    res = atlas.poweron_catalyst_gateway_vm(psgw["id"])
    assert res.status_code == codes.bad_request, f'Expected task should fail with bad request. Response" {res.content}'

    # Response expected from the CGM:
    #     Operation 'power on protection store gateway' failed because of a bad request. Please retry and contact HPE
    #     support if this error persists.\nError:  failed to validate precondition of potection store gateway power on
    #     request: validation failed for protection store gateway state: protection store gateway state is not 'OFF'
    assert re.search(ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_POWER_ON, res.text), f"Expected error message not matched"
    logger.info(f"Verified expected message '{ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_POWER_ON}'")


def perform_restart(context: Context):
    atlas = CatalystGateway(context.user)
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    res = atlas.restart_catalyst_gateway_vm(psgw["id"])
    assert res.status_code == codes.bad_request, f'Expected task should fail with bad request. Response" {res.content}'

    # Response expected from the CGM:
    #     Operation 'restart protection store gateway' failed because it is not yet implemented. Please use another method
    #     if available or contact HPE support.\nError:  feature not ready for implementation
    assert re.search(ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_RESTART, res.text), f"Expected error message not matched"
    logger.info(f"Verified expected message '{ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_RESTART}'")


def perform_remote_support(context: Context):
    atlas = CatalystGateway(context.user)
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    res = atlas.set_catalyst_gateway_vm_remote_support(psgw["id"], enabled=True)
    assert (
        res.status_code == codes.precondition_failed
    ), f'Expected task should fail with bad request. Response" {res.content}'

    # Response expected from the CGM:
    # Operation \'set protection store gateway remote support\' failed because a precondition check failed.
    # Please retry and contact HPE support if this error persists.\\nError:  gateway is not connected
    assert re.search(ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_REMOTE_SUPPORT, res.text), f"Expected error message not matched"
    logger.info(f"Verified expected message '{ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_REMOTE_SUPPORT}'")


def perform_support_bundle(context: Context):
    atlas = CatalystGateway(context.user)
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    res = atlas.generate_catalyst_gateway_vm_support_bundle(psgw["id"])
    assert (
        res.status_code == codes.precondition_failed
    ), f"Expected task should fail with bad request. Response: {res.content}"

    # Response expected from the CGM:
    #     Operation 'generate protection store gateway support bundle' failed because of a bad request. Please retry and contact
    #     HPE support if this error persists.\nError:  validation failed for protection store gateway state: protection store
    #     gateway state is not 'OK' or 'Initialised'
    assert re.search(ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_SUPPORT_BUNDLE, res.text), f"Expected error message not matched"
    logger.info(f"Verified expected message '{ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_SUPPORT_BUNDLE}'")


def perform_reveal_console_user(context: Context):
    atlas = CatalystGateway(context.user)
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    res = atlas.post_catalyst_gateway_vm_console_user(psgw["id"])
    assert (
        res.status_code == codes.internal_server_error
    ), f'Expected task should fail with bad request. Response" {res.content}'

    # Response expected from the CGM:
    #     Opertion 'get protection store gateway console details' failed because of an unexpected internal
    #     server error. Please retry and contact HPE support if this error persists.
    assert re.search(ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_CONSOLE_USER, res.text), f"Expected error message not matched"
    logger.info(f"Verified expected message '{ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_CONSOLE_USER}'")


def perform_delete(context: Context):
    psg_delete_timeout = TimeoutManager.standard_task_timeout
    atlas = CatalystGateway(context.user)
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    response = atlas.delete_catalyst_gateway_vm(psgw["id"])
    assert response.status_code == codes.accepted

    task_id = tasks.get_task_id_from_header(response)
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout=psg_delete_timeout,
        message=f"PSG delete task exceed {psg_delete_timeout} seconds - TIMEDOUT",
    )
    assert status == "succeeded", f"PSG Delete task {task_id}: {status}"

    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    assert psgw == {}, f"PSG VM {psgw['id']} still exists"
    logger.info("PSG successfully removed")


def perform_actions_while_create_protection_store_gateway(context: Context):
    """
    This triggeres PSG deployment and while it is in progress will be performing negative cases below.
        - Perform Shutdown
        - Perform Power ON
        - Perform Restart
        - Perform Remote Support
        - Perform Generate Support Bundle
        - Perform Reveal Console Password
    """
    atlas = CatalystGateway(context.user)
    response = create_protection_store_gateway_vm(
        context,
        return_response=True,
        add_data_interface=False,
    )
    assert response.status_code == codes.accepted, f"{response.content}"
    task_id = tasks.get_task_id_from_header(response)
    logger.info(f"Create protection store gateway. Task ID: {task_id}")

    # Wait for PSG state to become PSG_HEALTH_STATE_DEPLOYING/PSG_HEALTH_STATE_REGISTERING
    expected_state = (HealthState.DEPLOYING.value, HealthState.REGISTERING.value)
    try:
        wait(
            lambda: atlas.get_catalyst_gateway_health_state(context.psgw_name) in expected_state,
            timeout_seconds=TimeoutManager.create_psgw_timeout,
            sleep_seconds=5,
        )
    except TimeoutExpired:
        raise AssertionError(f"Failed to wait for PSG expected state to become {expected_state}")

    perform_remote_support(context)
    perform_support_bundle(context)
    perform_reveal_console_user(context)
    # perform_restart(context)
    # perform_power_ON(context)
    # perform_shutdown(context)
    status = tasks.wait_for_task(
        task_id,
        context.user,
        TimeoutManager.create_psgw_timeout,
        interval=30,
        message=f"PSG creation time exceed {TimeoutManager.create_psgw_timeout}s - TIMEOUT",
    )
    assert status == "succeeded", f"PSG creation task failed - {task_id}"
    wait_for_psg(context, state=State.OK, health_state=HealthState.OK, health_status=HealthStatus.CONNECTED)


def perform_actions_post_removal_of_psg_from_vcenter(context: Context):
    """
    This triggers vCenter SDK call to remove PSG VM from the vCenter(Not via DSCC UI) and then perform below actions
    to validate negative scenarios.
        - Perform Shutdown
        - Perform Power ON
        - Perform Restart
        - Perform Remote Support
        - Perform Generate Support Bundle
        - Perform recover without cloud store
        - Perform Delete
    """
    # Delete PSG directly from the vCenter not via DSCC
    delete_protection_store_gateway_vm_from_vcenter(context, force=True)

    # Wait for PSG state to become PSG_HEALTH_STATE_UNKNOWN
    try:
        atlas = context.catalyst_gateway
        wait(
            lambda: atlas.get_catalyst_gateway_health_state(context.psgw_name) == HealthState.UNKNOWN.value,
            timeout_seconds=TimeoutManager.standard_task_timeout,
            sleep_seconds=5,
        )
    except TimeoutExpired:
        raise AssertionError(f"Failed to wait for PSG expected state to become - PSG_HEALTH_STATE_UNKNOWN")

    perform_remote_support(context)
    perform_support_bundle(context)
    # perform_shutdown(context)
    # perform_power_ON(context)
    # perform_restart(context)

    # Recover PSGW and validate response
    response = recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=f"recover_{context.psgw_name}",
        return_response=True,
    )
    assert (
        response.status_code == codes.bad_request
    ), f"Failed to receive expected status code: Received: {response.status_code} expected: {codes.bad_request}"
    logger.info(f"Received expected status code: Received: {response.status_code} Expected:{codes.bad_request} ")
    assert re.search(
        ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_RECOVER, response.text
    ), f"Failed to validate {ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_RECOVER} in {response.text}"
    logger.info(f"Successfully validated {ERROR_MESSAGE_DEPLOY_PSGW_PERFORM_RECOVER} in {response.text}")
    perform_delete(context)


def create_psgw_with_same_name_when_delete_psgw_in_progress(context):
    """
    Original success criteria:
        Give PSG delete request and immediately start PSG deployment request with same name.

    Success criteria:
        Immediately after delete request giving another call for deployment is not supported for this v1 release.

        - Once after delete request, List PSG and verify entity showing its status as 'Deleting'
        - Verify creation request giving expected error says VM in vCenter exists with the same provided PSG name.
        - Remove VM from vCenter and verify PSG creation should succeed. (This is convered already)
    """

    atlas = CatalystGateway(context.user)
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    assert "id" in psgw, "Failed to find PSGW ID"

    # Initiate delete request for PSG
    logger.debug(f"Deleting PSGW - {context.psgw_name}")
    delete_response = atlas.delete_catalyst_gateway_vm(psgw["id"])
    logger.info(delete_response.text)
    assert delete_response.status_code == codes.accepted, f"{delete_response.content}"

    # Verify PSG state showing as 'Deleting'..
    logger.debug("Verifying PSG state is PSG_HEALTH_STATE_DELETING")
    logger.info("Waiting for PSG state to be deleting.")
    expected_state = HealthState.DELETING.value
    try:
        wait(
            lambda: atlas.get_catalyst_gateway_health_state(context.psgw_name) == expected_state,
            timeout_seconds=120,
            sleep_seconds=1,
            on_poll=lambda: atlas.get_catalyst_gateway_health_state(context.psgw_name),
        )
    except TimeoutError:
        raise TimeoutError("PSG didn't change state to deleting in 1 minute.")
    state = atlas.get_catalyst_gateway_health_state(context.psgw_name)
    assert state == HealthState.DELETING.value, f"Current state: {state}"

    # Redeploy the PSG with same name and assert expected message
    logger.debug("Redeploying PSG with same name")
    create_response = create_protection_store_gateway_vm(
        context,
        return_response=True,
        same_psgw_name=True,
    )
    validate_psgw_error_messages(
        create_response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_CREATE_PSG_VM_EXISTS,
    )


def check_and_register_unregister_expected_data_nics(
    context: Context, expected_network_types: list(NetworkInterfaceType) = []
):
    """
    This method checks all network interfaces present in psgw (data1, data2), and add/delete network interfaces that are expected in psg.
    """
    nics = context.catalyst_gateway.get_psgw_network_interfaces(context.psgw_name)
    registered_nic_addresses = [nic["networkAddress"] for nic in nics]
    context_network_addresses = [context.nic_data1_ip, context.nic_data2_ip]
    network_types = [NetworkInterfaceType.data1, NetworkInterfaceType.data2]
    logger.info(f"Starting network interfaces verification with expected setup -> {expected_network_types}")
    for index, context_nic_adress in enumerate(context_network_addresses):
        network_type = network_types[index]
        if (network_type in expected_network_types) and (context_nic_adress not in registered_nic_addresses):
            if context_nic_adress == None:
                logger.info(f"Adding expected network interface {network_type}")
                add_additional_network_interface_catalyst_gateway_vm(context, network_type)
            else:
                logger.info(
                    f"Adding expected network interface {network_type} with context network ip - {context_nic_adress}"
                )
                add_additional_network_interface_catalyst_gateway_vm(context, network_type, context_nic_adress)
        elif (network_type not in expected_network_types) and (context_nic_adress in registered_nic_addresses):
            logger.info(f"Deleting unexpected network interface {network_type} - {context_nic_adress}")
            delete_network_interface_catalyst_gateway_vm(context, context_nic_adress)


def perform_do_psg_proxy_check(context: Context):
    atlas = CatalystGateway(context.user)
    copy_pools = atlas.get_protection_stores()
    psgw_id = atlas.get_catalyst_gateway_id(context)
    psgw_info = atlas.get_catalyst_gateway(psgw_id)
    psgw_info_json = psgw_info.json()

    local_copy_pool_id = atlas.get_local_copy_pool(context, psgw_id, copy_pools)
    assert local_copy_pool_id is not None, "Local copy pool not found"
    logger.info(f"Local protection store created with id: {local_copy_pool_id}")

    response = context.ope.get_ope(context.ope_id)
    assert (
        response.json()["interfaces"]["network"]["proxy"]["port"] == psgw_info_json["network"]["proxy"]["port"]
        and response.json()["interfaces"]["network"]["proxy"]["networkAddress"]
        == psgw_info_json["network"]["proxy"]["networkAddress"]
    ), f"Error: PSG and DO prxoy configuration not matching."
    logger.info(f"Successfully configured and validated PSG proxy info")

    cloud_copy_pool_id = atlas.get_cloud_copy_pool(
        context,
        context.psgw_name,
        psgw_id,
        copy_pools,
        context.user,
        cloud_region=AwsStorageLocation.any,
        create_cloud_pool=False,
    )
    assert cloud_copy_pool_id is not None, "Cloud copy pool not found"
    logger.info(f"Cloud protection store created with id: {cloud_copy_pool_id}")


def create_and_validate_cloud_store_when_psg_poweredoff(context: Context, cloud_region=AwsStorageLocation.any):
    atlas = CatalystGateway(context.user)
    psgw_id = atlas.get_catalyst_gateway_id(context)

    logger.info("Creating Cloud Protection Store with new location on powered off PSG.")
    display_name_suffix = "".join(random.choice(string.ascii_letters) for _ in range(3))
    display_name = f"{context.psgw_name.split('#')[0]}_{display_name_suffix}"
    protection_store_payload = {
        "displayName": f"CLOUD_{display_name}",
        "protectionStoreType": "CLOUD",
        "storageLocationId": cloud_region.value,
        "storageSystemId": psgw_id,
    }
    response_create_cloud_store = atlas.create_protection_store(protection_store_payload)
    assert response_create_cloud_store.status_code == codes.accepted, f"{response_create_cloud_store.content}"

    task_id = tasks.get_task_id_from_header(response_create_cloud_store)

    # waiting for 5 minutes to check whether task is stucking at initialized state or not
    logger.info("Sleeping for 5 minutes.")
    sleep(300)

    logger.info("Checking after 5 minutes whether task is stuck at initialized state or not.")
    status = tasks.get_task_status(task_id, context.user)
    assert status == "initialized", f"We got wrong status: {status} for task: {tasks.get_task_object(task_id)}"
    logger.info("Creation of New Protection Store stucked at initialized state for more than 5 minutes as expected.")

    # power on the PSG back
    logger.info("PSG powering on so that Creation of New Protection Store gets resume and succeeded.")
    wait_for_psgw_to_power_on_and_connected(context)

    # Wait for PSG state become OK and health state/status become OK/Connected
    wait_for_psg(context, state=State.OK, health_state=HealthState.OK, health_status=HealthStatus.CONNECTED)

    timeout = TimeoutManager.create_psgw_timeout
    status = tasks.wait_for_task(
        task_id,
        context.user,
        timeout,
        message=f"Create cloud protection store with new region after powering on PSG exceed {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert status == "succeeded", f"We got wrong status: {status} for task: {tasks.get_task_object(task_id)}"
    logger.info("Create cloud protection store with new region after powering on PSG succeeded.")


def create_cloud_protection_store_before_recover_and_validate_its_creation_after_recover(context: Context):
    atlas = CatalystGateway(context.user)
    protection_store_task_id = create_protection_store(
        context, type=CopyPoolTypes.cloud, cloud_region=AwsStorageLocation.AWS_US_EAST_2, return_task_id=True
    )
    recover_psgw_name = f"recover_{context.psgw_name}"
    recover_protection_store_gateway_vm(context, recover_psgw_name=recover_psgw_name, add_data_interface=False)
    context.psgw_name = recover_psgw_name
    # Perform asset backup should work well with existing local/cloud stores and also the protection policy
    validate_protection_store_gateway_vm(context)

    # validate cloud protection store is created
    timeout = TimeoutManager.create_psgw_timeout
    status = tasks.wait_for_task(
        protection_store_task_id,
        context.user,
        timeout,
        message=f"Create protection store {type}  {timeout / 60:1f} minutes - TIMEOUT",
    )
    assert (
        status == "succeeded"
    ), f"We got wrong status: {status} for task: {tasks.get_task_object(user=context.user, task_id=protection_store_task_id)}"
    logger.info(f"Create cloud protection store succeeded")
    onprem_protection_store_id_list, cloud_protection_store_id_list = atlas.get_on_premises_and_cloud_protection_store(
        context
    )
    validate_cloud_protection_store_is_created(context, cloud_protection_store_id_list[1])


def validate_error_msg_when_psg_deploy_only_with_data_nic(context: Context):
    atlas = context.catalyst_gateway
    nic = context.nic_data1
    network_address = find_unused_ip_from_range(nic["network_address"])
    datastore_info = [context.datastore_id]

    response = atlas.create_catalyst_gateway_vm(
        context.psgw_name,
        context.vcenter_id,
        datastore_info,
        context.esxhost_id,
        context.hypervisor_cluster_id,
        context.content_lib_datastore_id,
        context.hypervisor_folder_id,
        context.resources_pools_id,
        network_name=nic["network_name"],
        network_address=network_address,
        subnet_mask=nic["netmask"],
        gateway=context.gateway,
        network_type=nic["network_type"],
    )
    assert (
        response.status_code == codes.bad_request
    ), f"Failed to receive expected status code: Received: {response.status_code} expected: {codes.bad_request}"
    assert re.search(
        ERROR_MESSAGE_DEPLOY_PSG_WITH_DATA_NIC_ONLY, response.text
    ), f"Failed to validate {ERROR_MESSAGE_DEPLOY_PSG_WITH_DATA_NIC_ONLY} in {response.text}"
    logger.info(f"Successfully validated {ERROR_MESSAGE_DEPLOY_PSG_WITH_DATA_NIC_ONLY} in {response.text}")


def verify_state_and_stateReason_of_protection_store(context: Context, exp_state="ONLINE", exp_state_reason=""):
    """Verify state and stateReason of protection stores.
    Args:
        context (Context): object of a context class
    """
    atlas = context.catalyst_gateway
    onprem_protection_store_id_list, cloud_protection_store_id_list = atlas.get_on_premises_and_cloud_protection_store(
        context
    )
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

    for cloud_ps in cloud_protection_store_id_list:
        state = atlas.get_protection_stores_info_by_id(cloud_ps).get("state")
        state_reason = atlas.get_protection_stores_info_by_id(cloud_ps).get("stateReason")
        assert (
            state == exp_state and state_reason == exp_state_reason
        ), f"Protection store is in unexpected state: {state} and State Reason: {state_reason}. Expected state: {exp_state} and state reason: {exp_state_reason}"
        logger.info(f"As expected : Protection store id {cloud_ps} state is {state} and state reason is {state_reason}")


def reattach_cloud_protection_store_to_new_psg(context: Context):
    """Deletes the PSGW and reattach its protection store to new PSGW.
    Args:
        context (Context): object of a context class
    """
    atlas = context.catalyst_gateway
    onprem_protection_store_id_list, cloud_protection_store_id_list = atlas.get_on_premises_and_cloud_protection_store(
        context
    )
    assert all([cloud_protection_store_id_list]), "Failed to get cloud protection stores."
    logger.info(f"Cloud protection store id for reattach: {cloud_protection_store_id_list[0]}")

    old_psgw_id = atlas.get_catalyst_gateway_id(context)
    create_protection_store_gateway_vm(context, add_data_interface=False)
    validate_protection_store_gateway_vm(context)

    psgw_id = atlas.get_catalyst_gateway_id(context)

    reattach_protection_store_payload = {
        "storageSystemId": psgw_id,
        "storageSystemType": "PROTECTION_STORE_GATEWAY",
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
    verify_state_and_stateReason_of_protection_store(context)

    logger.info(f"Verifying detach of protection store: {cloud_protection_store_id_list[0]} from old PSGW.")
    protection_stores_response = atlas.get_protection_stores()
    verify_protection_store_detached_from_old_psg(old_psgw_id, protection_stores_response)
    logger.info(f"Protection store: {cloud_protection_store_id_list[0]} successfully detached from old PSGW.")


def verify_protection_store_detached_from_old_psg(psgw_id, protection_stores_response):
    """Verifies whether protection store is succesfully detached from old psg.

    Args:
        psgw_id (_type_): PSGW id
        protection_stores_response (_type_): Response of get all protection stores.
    """
    assert (
        protection_stores_response.status_code == codes.ok
    ), f"Protection stores not fetched properly: {protection_stores_response.status_code}, {protection_stores_response.text}"
    for protection_store in protection_stores_response.json().get("items"):
        if protection_store["storageSystemInfo"]["id"] == psgw_id:
            assert f"Protection Store still attached to old PSGW: {psgw_id}"


def verify_delete_store_without_deleting_protection_policy(context: Context):
    """Verify delete protection store without deleting protection policy.
    Args:
        context (Context): object of a context class
    """
    atlas = context.catalyst_gateway
    onprem_protection_store_id_list, cloud_protection_store_id_list = atlas.get_on_premises_and_cloud_protection_store(
        context
    )
    assert all([cloud_protection_store_id_list]), "Failed to get cloud protection stores."
    logger.info(f"Cloud protection store ids to delete are: {cloud_protection_store_id_list}")

    logger.info(f"Deleting cloud protection store id: {cloud_protection_store_id_list[0]}")
    response = atlas.delete_protection_store(cloud_protection_store_id_list[0])
    assert (
        response.status_code == codes.bad_request
    ), f"Failed, Expected status code: {codes.bad_request} but received {response.status_code}"
    response_err_msg = response.json().get("message")
    exp_error_msg = ERROR_MESSAGE_DELETE_PROTECTION_STORE_WITHOUT_PROTECTION_POLICY
    assert re.search(
        exp_error_msg, response_err_msg
    ), f"Failed to validate error message EXPECTED: {exp_error_msg} ACTUAL: {response_err_msg}"
    logger.info(f"Successfully validated error message EXPECTED: {exp_error_msg} ACTUAL: {response_err_msg}")


def verify_update_store_with_same_name(context: Context):
    """Verify update protection store's display name.
    Args:
        context (Context): object of a context class
    """
    atlas = context.catalyst_gateway
    onprem_protection_store_id_list, cloud_protection_store_id_list = atlas.get_on_premises_and_cloud_protection_store(
        context
    )
    assert all([cloud_protection_store_id_list]), "Failed to get cloud protection stores."
    logger.info(f"Cloud protection store ids for update : {cloud_protection_store_id_list[0]}")

    response = atlas.update_protection_store(cloud_protection_store_id_list[0])
    assert (
        response.status_code == codes.bad_request
    ), f"Failed, Expected status code: {codes.bad_request} but received {response.status_code}"
    response_err_msg = response.json().get("message")
    exp_error_msg = ERROR_MESSAGE_UPDATE_PROTECTION_STORE_WITH_SAME_NAME
    assert re.search(
        exp_error_msg, response_err_msg
    ), f"Failed to validate error message EXPECTED: {exp_error_msg} ACTUAL: {response_err_msg}"
    logger.info(f"Successfully validated error message EXPECTED: {exp_error_msg} ACTUAL: {response_err_msg}")


def delete_onprem_protection_store(context: Context):
    """It deletes the on premises protection store.
    Args:
        context (Context): object of a context class
    """
    atlas = context.catalyst_gateway
    onprem_protection_store_id_list, cloud_protection_store_id_list = atlas.get_on_premises_and_cloud_protection_store(
        context
    )
    assert all([onprem_protection_store_id_list]), "Failed to get on prem protection stores."
    for protection_store in onprem_protection_store_id_list:
        logger.info(f"Deleting protection store: {protection_store}")
        response = atlas.delete_protection_store(protection_store)
        assert response.status_code == codes.accepted, f"Delete protection store failed: {response.content}"
        task_id = tasks.get_task_id_from_header(response)
        logger.info(f"Delete protection store, Task ID: {task_id}")
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
        ), f"Failed to delete protection store: {protection_store}, {tasks.get_task_error(task_id, context.user)}"
        logger.info(f"Delete protection store: {protection_store} succeeded.")


def delete_protection_stores(context: Context, force=False, expected_err=False):
    """It deletes the on premises protection store and cloud protection ids.
    Args:
        context (Context): object of a context class
        force(False):force will be either true or false
    """
    onprem_protection_store_id_list, cloud_protection_store_id_list = get_protection_store_ids(context)
    protection_store_id_list = onprem_protection_store_id_list + cloud_protection_store_id_list
    if expected_err is True:
        logger.info(f"Deleting cloud protection store id {cloud_protection_store_id_list[0]}")
        delete_protection_store_by_id(
            context, cloud_protection_store_id_list[0], force=force, expected_err=expected_err
        )
        return
    for protection_store_id in protection_store_id_list:
        logger.info(protection_store_id)
        delete_protection_store_by_id(context, protection_store_id, force=force)


def delete_protection_store_by_id(context: Context, protection_store_id, force=False, expected_err=False):
    atlas = context.catalyst_gateway
    response = atlas.delete_protection_store(protection_store_id, force=force)
    if expected_err is True:
        response_err_msg = response.json().get("message")
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
    atlas = context.catalyst_gateway
    onprem_protection_store_id_list, cloud_protection_store_id_list = atlas.get_on_premises_and_cloud_protection_store(
        context
    )
    number_of_stores = len(onprem_protection_store_id_list) + len(cloud_protection_store_id_list)
    assert number_of_stores > 0, "Failed to get protection stores."
    return onprem_protection_store_id_list, cloud_protection_store_id_list


def verify_psgw_datastore_info(context: Context, datastore_name):
    """
    This method is used verify datastore id in psgw
    """
    datastore_id = context.hypervisor_manager.get_datastore_id(datastore_name, context.vcenter_name)
    atlas = context.catalyst_gateway
    psgw_id = atlas.get_catalyst_gateway_id(context)
    psgw_info = atlas.get_catalyst_gateway(psgw_id)
    logger.info(f"psgw_info:  {psgw_info}")
    psgw_info_json = psgw_info.json()
    assert (
        psgw_info_json["datastoresInfo"][0]["id"] == datastore_id
    ), f"Datastore {datastore_name} is not matched for psgw {context.psgw_name}"
    logger.info(f"Datastore {datastore_name} successfully matched for psgw {context.psgw_name}")
    # After this point context's datastore id will be updated datastore id.
    context.datastore_id = datastore_id


def validate_deploy_psgw_when_upload_to_content_library_is_already_in_progress(context):
    response = create_protection_store_gateway_vm(
        context,
        clear_content_library=True,
        add_data_interface=False,
        return_response=True,
    )
    assert response.status_code == codes.accepted, f"{response.content}"
    task_id1 = tasks.get_task_id(response)
    logger.info(f"Create protection store gateway, Task ID: {task_id1}")
    timeout = TimeoutManager.first_time_psgw_creation
    logger.info("Waiting for 2 minutes before triggering another request for PSGW deployment.")
    sleep(120)
    response = create_protection_store_gateway_vm(
        context,
        add_data_interface=False,
        return_response=True,
    )
    assert response.status_code == codes.accepted, f"{response.content}"
    task_id2 = tasks.get_task_id(response)
    logger.info("Waiting for 2 minutes before fetching child task id.")
    sleep(120)
    child_task_id = tasks.get_child_task_id(task_id2, context.user)
    error_message = tasks.get_task_error(child_task_id, context.user)
    exp_error_msg = ERROR_MESSAGE_DEPLOY_PSGW_WHEN_UPLOAD_TO_CONTENT_LIBRARY_IS_ALREADY_IN_PROGRESS
    assert re.search(
        exp_error_msg, error_message
    ), f"Failed to validate error message EXPECTED: {exp_error_msg} ACTUAL: {error_message}"
    logger.info(f"Successfully validated error message EXPECTED: {exp_error_msg} ACTUAL: {error_message}")
    logger.info("Waiting for previous PSGW deployment to get complete.")
    status = tasks.wait_for_task(
        task_id1,
        context.user,
        timeout,
        interval=30,
        message=f"Protection store gateway creation time exceed {timeout / 60:1f} minutes - TIMEOUT",
    )
    if status == "succeeded":
        logger.info("1st PSG deployement completed successfully.")
    else:
        logger.info("1st PSG deployement failed to complete.")


def verify_the_error_msg_min_max_onprem_cloud_retention_days(context: Context):
    response = create_protection_store_gateway_vm(
        context,
        return_response=True,
        max_cld_dly_prtctd_data=10.0,
        max_cld_rtn_days=3650,
        max_onprem_dly_prtctd_data=5.0,
        max_onprem_rtn_days=0,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_ONPREM_RETENTION_DAYS,
    )
    logger.info("Successfully vaildated the minimum onprem retaion days")
    response = create_protection_store_gateway_vm(
        context,
        return_response=True,
        max_cld_dly_prtctd_data=10.0,
        max_cld_rtn_days=3650,
        max_onprem_dly_prtctd_data=5.0,
        max_onprem_rtn_days=2556,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_ONPREM_RETENTION_DAYS,
    )
    logger.info("Successfully vaildated the maximum onprem retaion days")
    response = create_protection_store_gateway_vm(
        context,
        return_response=True,
        max_cld_dly_prtctd_data=10.0,
        max_cld_rtn_days=0,
        max_onprem_dly_prtctd_data=5.0,
        max_onprem_rtn_days=2555,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_CLOUD_RETENTION_DAYS,
    )
    logger.info("Successfully vaildated the minimum cloud retaion days")
    response = create_protection_store_gateway_vm(
        context,
        return_response=True,
        max_cld_dly_prtctd_data=10.0,
        max_cld_rtn_days=3651,
        max_onprem_dly_prtctd_data=5.0,
        max_onprem_rtn_days=2555,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_CLOUD_RETENTION_DAYS,
    )
    logger.info("Successfully vaildated the maximum cloud retention days value")


def validate_existing_psgw_resize_functionality_max_min_local_retention_days(
    context,
    additional_ds_name=None,
    additional_ds_required=False,
    max_cld_dly_prtctd_data=1.0,
    max_cld_rtn_days=1,
    max_onprem_dly_prtctd_data=1.0,
    max_onprem_rtn_days=1,
    override_cpu=0,
    override_ram_gib=0,
    override_storage_tib=0,
):
    response = get_existing_psgw_resize_req_response(
        context,
        additional_ds_name=additional_ds_name,
        additional_ds_required=additional_ds_required,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
        override_cpu=override_cpu,
        override_ram_gib=override_ram_gib,
        override_storage_tib=override_storage_tib,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_ONPREM_RETENTION_DAYS,
    )


def validate_existing_psgw_resize_functionality_max_min_cloud_retention_days(
    context,
    additional_ds_name=None,
    additional_ds_required=False,
    max_cld_dly_prtctd_data=1.0,
    max_cld_rtn_days=1,
    max_onprem_dly_prtctd_data=1.0,
    max_onprem_rtn_days=1,
    override_cpu=0,
    override_ram_gib=0,
    override_storage_tib=0,
):
    response = get_existing_psgw_resize_req_response(
        context,
        additional_ds_name=additional_ds_name,
        additional_ds_required=additional_ds_required,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
        override_cpu=override_cpu,
        override_ram_gib=override_ram_gib,
        override_storage_tib=override_storage_tib,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_CLOUD_RETENTION_DAYS,
    )


def validate_psgw_tooling_connectivity(
    context: Context,
    target_address,
    exp_task_err=False,
    exp_res_err="",
    check_ping=True,
    check_traceroute=True,
    exp_err_msg="",
):
    """This method checks the connectivity between PSGW and target address.

    Args:
        context (Context): Context object
        target_address (_type_): Address to which PSG connectivity needs to be check.
        exp_task_err (bool, optional): If task is expected to fail. Defaults to False.
        exp_res_err (string, optional): Expected failed response of ping/traceroute requests. Defaults to "".
        check_ping (bool, optional): If connectivity needs to be checked through ping. Defaults to True.
        check_traceroute (bool, optional): If connectivity needs to be checked through traceroute. Defaults to True.
        exp_err_msg(string, optional):Expected error message of response of ping/traceroute requests. Defaults to "".
    """
    atlas = context.catalyst_gateway
    psgw_id = atlas.get_catalyst_gateway_id(context)

    if target_address == "vm_ip":
        target_address = create_tiny_vm_and_get_ip(context)

    if target_address == "DO_ip":
        DO_ip = context.hypervisor_manager.get_data_orchestrator_ip(hostname_prefix=context.ope_hostname_prefix)
        logger.info(f"Data orchestrator ip is {DO_ip}")
        target_address = DO_ip

    if exp_res_err is not "":
        logger.info(f"Validating PSGW tooling connectivity to {target_address} through ping:")
        response = atlas.validate_psg_connectivity_to_target_address(psgw_id, target_address, type="ping")
        assert (
            response.status_code == exp_res_err
        ), f"Failed, Expected status code: {exp_res_err} but received {response.status_code}"
        res_err_msg = response.json().get("message")
        assert re.search(
            exp_err_msg, res_err_msg
        ), f"Failed to validate error message for ping. EXPECTED: {exp_err_msg} ACTUAL: {res_err_msg}"
        logger.info(f"Successfully validated error message for ping. EXPECTED: {exp_err_msg} ACTUAL: {res_err_msg}")

        logger.info(f"Validating PSGW tooling connectivity to {target_address} through traceroute:")
        response = atlas.validate_psg_connectivity_to_target_address(psgw_id, target_address, type="traceroute")
        assert (
            response.status_code == exp_res_err
        ), f"Failed, Expected status code: {exp_res_err} but received {response.status_code}"
        res_err_msg = response.json().get("message")
        assert re.search(
            exp_err_msg, res_err_msg
        ), f"Failed to validate error message for traceoute. EXPECTED: {exp_err_msg} ACTUAL: {res_err_msg}"
        logger.info(
            f"Successfully validated error message for traceroute. EXPECTED: {exp_err_msg} ACTUAL: {res_err_msg}"
        )
        return

    if check_ping:
        logger.info(f"Validating PSGW tooling connectivity to {target_address} through ping:")
        response = atlas.validate_psg_connectivity_to_target_address(psgw_id, target_address, type="ping")
        assert (
            response.status_code == codes.accepted
        ), f"Failed, Expected status code: {codes.accepted} but received {response.status_code}"
        task_id = tasks.get_task_id(response)
        timeout = 300
        if exp_task_err == True:
            exp_err_msg = ERROR_MESSAGE_VALIDATING_PSGW_TOOLING_CONNECTIVITY_TO_INVALID_ADDRESS_TASK_FAILURE
            task_error = tasks.wait_for_task_error(task_id=task_id, user=context.user, timeout=timeout, interval=30)
            assert exp_err_msg in task_error, f"{task_error} should be {exp_err_msg}"
            logger.info(
                f"Successfully verified error message {exp_err_msg} while pinging PSGW {context.psgw_name} to {target_address}"
            )
        else:
            status = tasks.wait_for_task(
                task_id,
                context.user,
                timeout,
                interval=30,
                message=f"PSGW ping to {target_address} task exceed {timeout / 60:1f} minutes - TIMEOUT",
            )
            assert (
                status == "succeeded"
            ), f"PSGW {context.psgw_name} ping to address {target_address} task failed, {task_id}"
            logger.info(f"PSGW {context.psgw_name} successfully pinging to address {target_address}")

    if check_traceroute:
        logger.info(f"Validating PSGW tooling connectivity to {target_address} through traceroute:")
        response = atlas.validate_psg_connectivity_to_target_address(psgw_id, target_address, type="traceroute")
        assert (
            response.status_code == codes.accepted
        ), f"Failed, Expected status code: {codes.accepted} but received {response.status_code}"
        task_id = tasks.get_task_id(response)
        timeout = 300
        status = tasks.wait_for_task(
            task_id,
            context.user,
            timeout,
            interval=30,
            message=f"PSGW ping to {target_address} task exceed {timeout / 60:1f} minutes - TIMEOUT",
        )
        assert (
            status == "succeeded"
        ), f"PSGW {context.psgw_name} traceroute to address {target_address} task failed, {task_id}"
        logger.info(f"PSGW {context.psgw_name} successfully tracerouting to address {target_address}")


def validate_error_msg_exprireafter_value_100_year_with_lockforvalue_100_years(context):
    protect_vm_task_id = assign_protection_template_to_vm(context, return_task_id=True)
    timeout = 900
    status = tasks.wait_for_task(
        protect_vm_task_id,
        context.user,
        timeout,
        interval=30,
    )
    assert status == "failed", f"Protect task should be failed for more than 5 years"
    res_error_message = tasks.get_task_error(protect_vm_task_id, context.user)
    expected_error_msg = ERROR_MESSAGE_VALIDATING_EXPIREAFTER_NOT_MORE_THAN_5_YEARS_WITH_lOCKFOR_VALUE_100_YEARS
    assert re.search(expected_error_msg, res_error_message), f"Got incorrect  ERROR: {res_error_message}"
    logger.info(f"Successfully validated error message: {res_error_message}")


def validate_error_msg_retention_period_is_5_years_with_lock_for_option_with_100_years(
    context,
    cloud_region,
    onprem_expire_value,
    cloud_expire_value,
    onprem_lockfor_value,
    cloud_lockfor_value,
):
    res_error_msg = create_protection_template(
        context,
        cloud_region=cloud_region,
        onprem_expire_value=onprem_expire_value,
        cloud_expire_value=cloud_expire_value,
        onprem_lockfor_value=onprem_lockfor_value,
        cloud_lockfor_value=cloud_lockfor_value,
        check_error_msg=True,
    )
    expected_error = ERROR_MESSAGE_VALIDATING_EXPIREAFTER_5_YEARS_WITH_lOCKFOR_VALUE_100_YEARS
    assert re.search(expected_error, res_error_msg), f"Failed to validate error message: {expected_error})"
    logger.info(f"Successfully validated error message")
