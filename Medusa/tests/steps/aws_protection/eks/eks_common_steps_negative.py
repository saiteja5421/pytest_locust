import logging

import requests
from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.task_status import TaskStatus

from lib.dscc.backup_recovery.aws_protection.backup_restore.payload.post_restore_csp_k8s_app import (
    PostRestoreK8sApp,
)
import tests.steps.aws_protection.policy_manager_steps as PolicyMgrSteps
from tests.e2e.aws_protection.context import Context
from tests.steps.tasks import tasks
from requests import Response


from utils.timeout_manager import TimeoutManager

logger = logging.getLogger()


def eks_protect_asset_with_error(context: Context, asset_id: str, protection_policy_id: str, expected_error: str):
    """Protects asset and asserts appropriate task error is returned for an eks

    Args:
        context (Context): test Context
        asset_id (str): Asset id
        protection_policy_id (str): Protection policy id
        expected_error (str): Expected task error
    """
    task_id = PolicyMgrSteps.create_protection_job_for_asset(
        context=context,
        asset_id=asset_id,
        asset_type=AssetType.CSP_K8S_APPLICATION,
        protection_policy_id=protection_policy_id,
        wait_for_task=False,
    )
    protect_task_status: str = tasks.wait_for_task(task_id, context.user, TimeoutManager.task_timeout)
    protect_task_errors = tasks.get_task_error(task_id, context.user)
    assert protect_task_status.upper() == TaskStatus.failed.value
    logger.info(f"Verify task error {expected_error} for protect asset in: {protect_task_errors}")
    assert expected_error in protect_task_errors, f"Expected error not found {expected_error} in {protect_task_errors}"


def restore_k8s_application_with_error(
    context: Context,
    csp_k8s_application_id: str,
    backup_id: str,
    cluster_id: str,
    target_namespace: str,
    error_expected: str,
    force_restore: bool = True,
):
    """Restore provided backup copy for a given k8s application and validate the error as account suspended

    Args:
        context :Test context
        csp_k8s_application_id (str): csp k8s application id
        backup_id (str): native or cloud snapshot backup id
        cluster_id (str): cluster id to restore the k8s namspaced application
        target_namespace (str): Name of the target namespace
        error_expected (str): expected task failure error message
        force_restore (bool, optional): Set to true, will replace the existing namespace, defaults to True

    """
    payload = PostRestoreK8sApp(
        backup_id,
        cluster_id,
        force_restore,
        target_namespace,
    )
    response = context.eks_data_protection_manager.restore_csp_k8s_application(
        csp_k8s_application_id=csp_k8s_application_id,
        restore_payload=payload,
        return_restore=False,
    )
    assert response.status_code == requests.codes.conflict
    error_message = response.json().get("error", {})
    logger.info(f"task errors for restore(): {error_message}")
    assert error_expected in error_message, f"Expected error {error_expected} not found in {error_message}"
