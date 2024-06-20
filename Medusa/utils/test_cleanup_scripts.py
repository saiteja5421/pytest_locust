from lib.common.enums.backup_type_param import BackupTypeParam
from tests.catalyst_gateway_e2e.test_context import Context
import logging
from requests import codes
from tests.steps.tasks import tasks
from tests.steps.vm_protection.protection_template_steps import (
    delete_policy_for_protection_stores_cleanup,
    delete_protection_stores_for_cleanup,
    unassign_protecion_policy,
)
from utils.timeout_manager import TimeoutManager

logging.basicConfig(filename="test_run.log", format="%(asctime)s %(message)s", filemode="w")

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def test_dscc_cleanup():
    context = Context()
    get_all_setup_perform_cleanup(context)
    delete_all_policy_for_cleanup(context)
    delete_all_stores_for_cleanup(context)
    delete_all_psg_for_cleanup(context)


def get_all_setup_perform_cleanup(context: Context) -> None:
    """
    Get the all vms delete the backups
       - unprotect the vm
       - delete policy for that vm
       - delete protection stores
       - delete protection store gateway

    Args:
        context (Context): context
    """
    try:
        hypervisor_manager = context.hypervisor_manager
        template = context.protection_template
        response = hypervisor_manager.get_vms()
        vm_list_response = response.json()
        tiny_vm_prefix = f"_{context.vm_template_name}_"
        for item in vm_list_response["items"]:
            vm_name = item["name"]
            if tiny_vm_prefix in vm_name and item["protected"] == True:
                delete_backup_vm_id = item["id"]
                protection_job_id = item["protectionJobInfo"]["id"]
                policy_id = item["protectionJobInfo"]["protectionPolicyInfo"]["id"]
                delete_backups(context, delete_backup_vm_id, backup_type=BackupTypeParam.backups)
                delete_backups(context, delete_backup_vm_id, backup_type=BackupTypeParam.snapshots)
                unassign_protecion_policy(context, protection_job_id, template, ignore_assert=True)
                delete_protection_store_gateway(context, policy_id)
            elif tiny_vm_prefix in vm_name and item["protected"] == False:
                delete_backup_vm_id = item["id"]
                delete_backups(context, delete_backup_vm_id, backup_type=BackupTypeParam.backups)
                delete_backups(context, delete_backup_vm_id, backup_type=BackupTypeParam.snapshots)
    except Exception as e:
        logger.error("Error while set up performing cleanup", e)


def delete_backups(context: Context, uprotect_vm_id: str, backup_type: str) -> None:
    """
    Get the vm id and delete the backup
    Args:
        context (Context): context
        uprotect_vm_id (str): delete the backup for the unprotect vm
        backup_type (BackupTypeParam.value): delete the backup
    """
    hypervisor_manager = context.hypervisor_manager
    asset_id = uprotect_vm_id
    backup_type = backup_type.value
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
        logger.error(f"Failed to get the backup information for {asset_id}: {response.content}")


def delete_protection_policy_and_stores(context: Context, policy_id: str) -> dict:
    """
    Get policy id and delete protection store

    Args:
        context (Context): context
        policy_id (str): get the policy id info

    Returns:
        dict: return protection store info
    """

    try:
        protection_template = context.protection_template
        atlas = context.catalyst_gateway
        resp = protection_template.get_protection_template(policy_id)
        policy_info = resp.json()
        delete_policy_for_protection_stores_cleanup(context, policy_id)
        for protection in policy_info["protections"]:
            protectionsStore_info = protection.get("protectionStoreInfo")
            if protectionsStore_info:
                protection_store_id = protection.get("protectionStoreInfo").get("id")
                protection_store_display_name = protection.get("protectionStoreInfo").get("name")
                protection_store_info = atlas.get_protection_stores_info_by_id(protection_store_id, ignore_assert=False)
                delete_protection_stores_for_cleanup(context, protection_store_id, protection_store_display_name)
        return protection_store_info
    except Exception as e:
        logger.error("Failed during protection policy and protection store cleanup", e)


def delete_protection_store_gateway(context: Context, policy_id: str) -> None:
    """
    Delete protection store gateway

    Args:
        context (Context): context
        policy_id (str): get the policy id info
    """

    try:
        atlas = context.catalyst_gateway
        protection_store_info = delete_protection_policy_and_stores(context, policy_id)
        psgw_id = protection_store_info["storageSystemInfo"]["id"]
        response = atlas.delete_catalyst_gateway_vm(psgw_id)
        task_id = tasks.get_task_id_from_header(response)
        status = tasks.wait_for_task(
            task_id,
            context.user,
            timeout=TimeoutManager.standard_task_timeout,
            message="Failed to remove PSGW within 900 seconds",
        )
        if status == "succeeded":
            logger.info(f"deleted psgw vm successfully.")
        else:
            logger.info(f"Unable delete PSGW VM Task {task_id} : {status}")
    except Exception as e:
        logger.error("Failed during protection store gateway cleanup", e)


def delete_all_policy_for_cleanup(context: Context) -> None:
    """
    Delete the all policy name start with policy_name_prefix

    Args:
        context (Context): context
    """
    try:
        template = context.protection_template
        policy_response = template.get_protection_templates().json()
        policy_name_template = context.local_template
        policy_name_prefix = policy_name_template.split("_")[0]
        for item in policy_response["items"]:
            policy_id = item["id"]
            policy_name = item["name"]
            if policy_name_prefix in policy_name:
                delete_policy_for_protection_stores_cleanup(context, policy_id)
    except Exception as e:
        logger.error("Failed to delete the protection policy ", e)


def delete_all_stores_for_cleanup(context: Context) -> None:
    """
    Delete all protection stores start with apiautorun

    Args:
        context (Context): context
    """
    try:
        atlas = context.catalyst_gateway
        protection_stores_response = atlas.get_protection_stores().json()
        for ps_response in protection_stores_response["items"]:
            protection_store_display_name = ps_response["displayName"]
            protection_store_id = ps_response["id"]
            if "apiautorun" in protection_store_display_name:
                delete_protection_stores_for_cleanup(context, protection_store_id, protection_store_display_name)
    except Exception as e:
        logger.error("Failed to delete the protection stores", e)


def delete_all_psg_for_cleanup(context: Context) -> None:
    """
    Delete all protection store gateway start with apiautorun

    Args:
        context (Context): context
    """
    try:
        atlas = context.catalyst_gateway
        response = atlas.get_catalyst_gateways()
        response_info = response.json()
        psg_name_prefix = context.psgw_name.split("_")[0]
        for item in response_info["items"]:
            psgw_id = item["id"]
            if psg_name_prefix in item["name"]:
                response = atlas.delete_catalyst_gateway_vm(psgw_id)
                task_id = tasks.get_task_id_from_header(response)
                status = tasks.wait_for_task(
                    task_id,
                    context.user,
                    timeout=TimeoutManager.standard_task_timeout,
                    message="Failed to remove PSGW within 900 seconds",
                )
                if status == "succeeded":
                    logger.info(f"deleted psgw vm successfully.")
                else:
                    logger.info(f"Unable delete PSGW VM Task {task_id} : {status}")
    except Exception as e:
        logger.error("Failed to delete the protection store gateway", e)
