"""
This file contains functions for the restore activities of EKS K8s cluster applications.
"""

import logging
from lib.dscc.backup_recovery.aws_protection.eks.domain_models.csp_k8s_model import (
    CSPK8sClustersModel,
    CSPK8sResourcesListModel,
)
from tests.e2e.aws_protection.context import Context
from lib.dscc.backup_recovery.aws_protection.backup_restore.payload.post_restore_csp_k8s_app import (
    PostRestoreK8sApp,
)
from lib.common.enums.state import State
from tests.steps.aws_protection.eks.csp_eks_backup_steps import get_csp_k8s_app_backup_id
from tests.steps.aws_protection.eks.csp_eks_inventory_steps import (
    get_csp_k8s_cluster_by_name,
    perform_eks_cluster_refresh,
)
from tests.steps.aws_protection.eks.data_integrity_validation import validate_restored_cluster_resources_dscc
from tests.steps.aws_protection.eks.eks_common_steps import (
    get_eks_k8s_cluster_app_by_name,
    get_eks_k8s_cluster_app_details,
    read_yaml_get_namespace,
    delete_and_validate_k8s_namespace,
)
from tests.steps.tasks import tasks
from utils.timeout_manager import TimeoutManager
from lib.common.enums.task_status import TaskStatus
from requests import codes


logger = logging.getLogger()


def restore_k8s_application(
    context: Context,
    csp_k8s_application_id: str,
    backup_id: str,
    cluster_id: str,
    target_namespace: str,
    force_restore: bool = True,
    return_restore_task_id: bool = False,
    negative: bool = False,
    expected_neg_test_response_code: codes = codes.internal_server_error,
) -> bool:
    """Restore provided backup copy for a given k8s application

    Args:
        csp_k8s_application_id (str): csp k8s application id
        backup_id (str): native or cloud snapshot backup id
        cluster_id (str): cluster id to restore the k8s namspaced application
        target_namespace (str): Name of the target namespace
        force_restore (bool, optional): Set to true, will replace the existing namespace, defaults to True
        return_restore_task_id (bool, optional): Returns restore task id immediately, without waiting for restore to complete. Defaults to False
        negative (bool, optional): passed in restore_csp_k8s_application method if negative testcase


    Returns:
        boolean: returns True or False based on the task result
    """
    restore_timeout = TimeoutManager.standard_task_timeout
    payload = PostRestoreK8sApp(
        backup_id,
        cluster_id,
        force_restore,
        target_namespace,
    )
    task_id = context.eks_data_protection_manager.restore_csp_k8s_application(
        csp_k8s_application_id=csp_k8s_application_id,
        restore_payload=payload,
        negative=negative,
        expected_neg_test_response_code=codes.internal_server_error,
    )
    if return_restore_task_id:
        return task_id
    logger.info(f"Wait {restore_timeout} seconds for k8s application restore operation to be successful")
    task_status: str = tasks.wait_for_task(
        task_id=task_id,
        user=context.user,
        timeout=restore_timeout,
    )
    if task_status.lower() != TaskStatus.success.value.lower():
        logger.error(f"k8s application restore task: {task_id} failed with an error: {task_status}")
        return False

    logger.info(f"k8s application restore task is successfully completed: {task_status}")
    return True


def restore_backup_to_different_namespace_and_refresh(
    context: Context,
    app_config_yaml: str,
    target_namespace: str,
    k8s_resources_before_restore: CSPK8sResourcesListModel,
    validate_resources: bool = True,
    backup_id: str = "",
):
    """Restore from backup to different namespace name and validate if ID changed and state is OK.

    Args:
        context (Context): context object
        app_config_yaml (str): path to k8s application configuration yaml file
        target_namespace (str): name of the namespace to which the backup will be restored
        k8s_resources_before_restore (CSPK8sResourcesListModel): k8s resources list before restore operation.
        validate_resources (bool, optional): Validates resources if set to True, defaults to True
        backup_id (str, optional): backup ID, defaults to ''
    """
    cluster_info = get_csp_k8s_cluster_by_name(context, context.eks_cluster_name, context.eks_cluster_aws_region)
    app_name = read_yaml_get_namespace(app_config_yaml)
    app_id = get_eks_k8s_cluster_app_by_name(
        context,
        context.eks_cluster_name,
        context.eks_cluster_aws_region,
        app_name,
    )
    if not backup_id:
        backup_id = get_csp_k8s_app_backup_id(context, app_id)
    logger.info(f"Restore backup ID: {backup_id} to namespace: {target_namespace}")

    # Verify target name is existed, if yes delete it
    delete_and_validate_k8s_namespace(
        context,
        context.eks_cluster_name,
        context.eks_cluster_aws_region,
        target_namespace,
    )
    backup_restore = restore_k8s_application(
        context, app_id, backup_id, cluster_info.id, target_namespace, force_restore=False
    )
    assert backup_restore, "Restore of a k8s namespace to different namespace name failed."
    app_id_after_restore = get_eks_k8s_cluster_app_by_name(
        context,
        context.eks_cluster_name,
        context.eks_cluster_aws_region,
        target_namespace,
    )
    assert (
        app_id_after_restore != app_id
    ), f"ID of restored application to new namespace is the same as before restore. Expected different values. Before restore ID: {app_id}, after restore ID: {app_id_after_restore}."
    app_details = get_eks_k8s_cluster_app_details(context, cluster_info.id, target_namespace)
    assert app_details.state == State.OK, f"K8s app is not in state {State.OK} after restore."
    logger.info(f"Backup ID: {backup_id} restored successfully to namespace: {target_namespace}")
    if not validate_resources:
        return
    validate_restored_cluster_resources_dscc(context, k8s_resources_before_restore)


def restore_eks_backup_to_different_namespace_and_refresh(
    context: Context, app_config_yaml: str, target_namespace_name: str
):
    """Restore from backup to different namespace name and validate if ID changed and state is OK.

    Args:
        context (Context): context object
        app_config_yaml (str): path to k8s application configuration yaml file
        target_namespace_name (str): restore to new namespace name
    """
    cluster_info = get_csp_k8s_cluster_by_name(context, context.eks_cluster_name, context.eks_cluster_aws_region)
    app_name = read_yaml_get_namespace(app_config_yaml)
    app_id = get_eks_k8s_cluster_app_by_name(
        context,
        context.eks_cluster_name,
        context.eks_cluster_aws_region,
        app_name,
    )
    backup_id = get_csp_k8s_app_backup_id(context, app_id)
    backup_restore = restore_k8s_application(
        context, app_id, backup_id, cluster_info.id, target_namespace_name, force_restore=False
    )
    assert backup_restore, "Restore of a k8s namespace to the same namespace name failed."
    perform_eks_cluster_refresh(context, context.eks_cluster_name, context.eks_cluster_aws_region)
    restored_app_details = get_eks_k8s_cluster_app_details(context, cluster_info.id, target_namespace_name)
    assert restored_app_details, f"Could not get the app details from DSCC. App name:{app_name}, ID: {app_id}"
    assert restored_app_details.state == State.OK, f"K8s app is not in state {State.OK} after restore."


def restore_backup_same_namespace_and_refresh(context: Context, app_config_yaml: str, k8s_resources_before_restore):
    """Restore from backup to the same namespace name and validate if ID changed and state is OK.

    Args:
        context (Context): context object
        app_config_yaml (str): path to k8s application configuration yaml file
    """
    cluster_info = get_csp_k8s_cluster_by_name(context, context.eks_cluster_name, context.eks_cluster_aws_region)
    app_name = read_yaml_get_namespace(app_config_yaml)[0]
    app_id = get_eks_k8s_cluster_app_by_name(
        context,
        context.eks_cluster_name,
        context.eks_cluster_aws_region,
        app_name,
    )
    backup_id = get_csp_k8s_app_backup_id(context, app_id)
    backup_restore = restore_k8s_application(context, app_id, backup_id, cluster_info.id, app_name)
    assert backup_restore, "Restore of a k8s namespace to the same namespace name failed."
    perform_eks_cluster_refresh(context, context.eks_cluster_name, context.eks_cluster_aws_region)
    app_details = get_eks_k8s_cluster_app_details(context, cluster_info.id, app_name)
    assert app_details, f"Could not get the app details from DSCC. App name:{app_name}, ID: {app_id}"
    assert app_details.state == State.OK, f"K8s app is not in state {State.OK} after restore."
    validate_restored_cluster_resources_dscc(context, k8s_resources_before_restore)


def verify_restore_task_and_validate_restore(
    context: Context,
    cluster_info: CSPK8sClustersModel,
    app_id: str,
    target_namespace: str,
    task_id: str,
):
    """Restore from backup to different namespace name and validate if ID changed and state is OK.
    Args:
        context (Context): context object
        cluster_info (CSPK8sClustersModel): csp k8s cluster info object
        app_id (str): k8s application id
        target_namespace (str): name of the namespace to which the backup will be restored
        task_id (str): restore task id
    """
    restore_timeout = TimeoutManager.standard_task_timeout
    logger.info(f"Wait {restore_timeout} seconds for k8s application restore operation to be successful")
    task_status: str = tasks.wait_for_task(
        task_id=task_id,
        user=context.user,
        timeout=restore_timeout,
    )
    if task_status.lower() != TaskStatus.success.value.lower():
        logger.error(f"k8s application restore task: {task_id} failed with an error: {task_status}")
    app_id_after_restore = get_eks_k8s_cluster_app_by_name(
        context,
        context.eks_cluster_name,
        context.eks_cluster_aws_region,
        target_namespace,
    )
    logger.info("Validate restored k8s application info")
    assert (
        app_id_after_restore != app_id
    ), f"ID of restored application to new namespace is the same as before restore. Expected different values. Before restore ID: {app_id}, after restore ID: {app_id_after_restore}."
    app_details = get_eks_k8s_cluster_app_details(context, cluster_info.id, target_namespace)
    assert app_details.state == State.OK, f"K8s app is not in state {State.OK} after restore."
    logger.info("Successfully validated restored k8s application info")
