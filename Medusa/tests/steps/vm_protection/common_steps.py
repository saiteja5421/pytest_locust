import logging
import paramiko
from lib.common.enums.backup_type_param import BackupTypeParam
from tests.steps.vm_protection.backup_steps import delete_all_backups
from tests.steps.vm_protection.protection_template_steps import (
    delete_protection_stores_for_cleanup,
    get_two_days_older_protection_stores_info,
    unassign_protecion_policy_from_vm,
    unassign_protecion_policy_from_all_vms,
    delete_unassinged_protection_policy,
    unprotect_vm_delete_policy_for_cleanup_stores,
)
from tests.steps.vm_protection.psgw_steps import cleanup_all_psgw_vms
from tests.steps.vm_protection.storeonces_steps import (
    enable_disable_and_approve_the_dual_request,
    validate_unregister_storeonces,
)
from tests.steps.vm_protection.vcenter_steps import unregister_vcenter
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.vmware_steps import VMwareSteps
from lib.platform.storeonce.storeonce import StoreOnce
from lib.dscc.backup_recovery.vmware_protection.common.custom_error_helper import (
    IDNotFoundError,
)


__PSGW_ID_NOT_FOUND = "Failed to find PSGW ID"
logger = logging.getLogger()


def perform_cleanup(
    context: Context,
    clean_vm=True,
    clean_psgw=True,
    clean_large_vm=False,
    unregister_vcenter_flag=False,
):
    """This step deletes all the backups from local and cloud and unassigns protection policies and deletes vm.

    Args:
        context (Context): context object
        clean_vm (bool, optional): Parameter to delete vm from vcenter. Defaults to True.
        clean_psgw (bool, optional): parameter to delete vm from DSCC UI. Defaults to True.
        clean_large_vm (bool, optional): parameter to clean large vm. Defaults to False.
        unregister_vcenter_flag (bool, optional): parameter for unregister of vcenter. Defaults to False.
    """
    if clean_large_vm:
        clean_large_vm_with_backup(context)
    delete_all_backups(BackupTypeParam.backups, context)
    delete_all_backups(BackupTypeParam.snapshots, context)
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)
    if clean_vm:
        VMwareSteps(
            context.vcenter["ip"],
            context.vcenter["username"],
            context.vcenter["password"],
        ).delete_vm(context.vm_name)
    if clean_psgw:
        cleanup_all_psgw_vms(context)
    if unregister_vcenter_flag:
        unregister_vcenter(context)


def perform_storeonce_cleanup(
    context: Context,
    unregister_storeonce,
    storeonce_id,
    unregister_secondary_storeonce=False,
    secondary_storeonce_id=None,
    unregister_vcenter_flag=False,
):
    storeonce = StoreOnce(
        context.storeonces_network_address,
        context.storeonces_admin_username,
        context.storeonces_admin_password,
    )
    """This step deletes all the backups from local and cloud and unassigns protection policies"""
    delete_all_backups(BackupTypeParam.backups, context)
    unassign_protecion_policy_from_all_vms(context)
    delete_unassinged_protection_policy(context)
    dualauth_status = storeonce.get_dualauth_status()
    if dualauth_status:
        enable_disable_and_approve_the_dual_request(context, enable=False)
    # Unregister the storeonce
    if unregister_storeonce:
        validate_unregister_storeonces(context, storeonce_id)
    if unregister_secondary_storeonce:
        validate_unregister_storeonces(context, secondary_storeonce_id)

    # Reset the DSCCAdmin user password
    storeonce.reset_user_password(
        username=context.storeonces_dscc_admin_username, password=context.storeonces_dscc_admin_password
    )
    if unregister_vcenter_flag:
        unregister_vcenter(context)


def execute_cmd_in_vm(cmd, vm_ip, username=None, password=None):
    """
    Description: using paramiko logging into vm and executing commands
    cmd: string
    vm_ip: string
    username: string, username of the vm
    password: string, password of the vm
    """
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(vm_ip, port=22, username=username, password=password, allow_agent=False)
        logger.info(f"Running below command on {vm_ip} : \n {cmd}")
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        logger.info(f"stderr ::{stderr.read()}")
        command_output = []
        while True:
            line = stdout.readline()
            if not line:
                break
            command_output.append(str(line).strip())
        ssh_client.close()
        logger.debug(command_output)
        return command_output
    except Exception as e:
        logger.error(f"Exception while Executing command {cmd} in vm {vm_ip} error:{e}")
        raise e


def clean_large_vm_with_backup(context):
    """
    Description: Cleaning up all backups, unassigning the protection policies from large vms, and then deleting all vms

    """
    try:
        vcenter_control = VMwareSteps(context.vcenter_name, context.vcenter_username, context.vcenter_password)
        for vm in context.large_size_data_vm_name_list:
            context.vm_name = vm
            context.vm_id = context.hypervisor_manager.get_id(context.vm_name, context.hypervisor_manager.get_vms())
            delete_all_backups(BackupTypeParam.backups, context)
            delete_all_backups(BackupTypeParam.snapshots, context)
            unassign_protecion_policy_from_vm(context)
            vcenter_control.delete_vm(vm)

        # Deleting unassigned protection policy from dscc,
        delete_unassinged_protection_policy(context)
    except IDNotFoundError:
        pass


def perform_cleanup_old_protection_store(context: Context):
    """
    This Method is used to Protection stores cleanup:
        Deleteing the protection stores steps and conditions:
        we checked protection stores is older than 2 days and name not starts with 'dnd' and name does not contain 'sanity' on it.
        if protection store is assigned to a policy and vm is protected
        unprotect the vm and delete the policy
        otherwise deleteing the protection stores
    Args:context (Context): object of a context class
    """
    protections_stores_deleted_list, protection_store_display_name = get_two_days_older_protection_stores_info(context)
    unprotect_vm_delete_policy_for_cleanup_stores(context, protections_stores_deleted_list)
    try:
        for protection_store_id in protections_stores_deleted_list:
            delete_protection_stores_for_cleanup(context, protection_store_id, protection_store_display_name)

    except Exception as e:
        logger.error(f"Exception while deleting protection store error:{e}")
        raise e
