"""
This file contains functions for eks inventory validation.
"""

import logging
import copy
from typing import Union
from tenacity import retry, stop_after_attempt
from lib.common.enums.compare_condition import CompareCondition
from lib.common.enums.state import State
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import CSPAccountModel
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ErrorResponse
from lib.dscc.backup_recovery.aws_protection.eks.domain_models.csp_k8s_model import (
    CSPK8sClustersListModel,
    CSPK8sResourcesListModel,
)
from lib.dscc.backup_recovery.aws_protection.dashboard.domain_models.dashboard_and_reporting_model import (
    InventorySummaryModel,
)
from lib.platform.kubernetes.kubernetes_client import KubernetesClient
from lib.platform.aws_boto3.aws_factory import AWS
from tests.e2e.aws_protection.context import Context
from lib.common.enums.csp_k8s_cluster_registration_status import CSPK8sClusterRegistrationStatus
from lib.common.enums.account_validation_status import ValidationStatus
import tests.steps.aws_protection.eks.eks_common_steps as EKSCommonSteps
import tests.steps.aws_protection.policy_manager_steps as PolicyMgrSteps
import tests.steps.aws_protection.eks.csp_eks_backup_steps as EKSBackupSteps
import tests.steps.aws_protection.dashboard_steps as DashboardSteps
from lib.common.enums.task_status import TaskStatus
from tests.steps.tasks import tasks
import tests.steps.aws_protection.cloud_account_manager_steps as CAMSteps
from utils.timeout_manager import TimeoutManager

logger = logging.getLogger()


def perform_eks_inventory_refresh(context: Context, csp_account_name: str, wait_for_task: bool = True) -> str:
    """
    Args:
        context (Context): Context object
        csp_account_id (str): csp account uuid
        wait_for_task (bool, optional): Boolean value to wait of the task. Defaults to True.

    Returns:
        str: The task ID for the EKS inventory request in DSCC
    """
    csp_account = CAMSteps.get_csp_account_by_csp_name(context, csp_account_name)
    csp_account_id = csp_account.id

    task_id = trigger_k8s_inventory_refresh(context, csp_account_id)

    if wait_for_task:
        logger.info(f"Waiting for inventory refresh for {csp_account_id} to complete")
        refresh_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.task_timeout,
        )
        assert (
            refresh_task_status.upper() == TaskStatus.success.value
        ), f"Account {csp_account_id} inventory refresh failure, refresh_task_status={refresh_task_status}"

    return task_id


def trigger_k8s_inventory_refresh(context: Context, csp_account_id: str):
    logger.info(f"Refreshing inventory for EKS account {csp_account_id}")
    task_id = context.eks_inventory_manager.trigger_k8s_inventory_refresh(csp_account_id=csp_account_id)
    return task_id


def perform_eks_resource_refresh(
    context: Context, cluster_name: str, cluster_region: str, app_name: str, wait_for_task: bool = True
) -> str:
    """
    Refresh EKS cluster resource
    Args:
        context (Context): Context object
        cluster_name (str): Name of the EKS cluster
        cluster_region (str): Cluster region
        csp_k8s_resource_id (str): Unique identifier of a Kubernetes resource
        wait_for_task (bool, optional): Boolean value to wait of the task. Defaults to True.

    Returns:
        str: The task ID for the EKS inventory request in DSCC
    """
    cluster_info = get_csp_k8s_cluster_by_name(context, cluster_name, cluster_region)
    app_id = EKSCommonSteps.get_eks_k8s_cluster_app_by_name(context, cluster_name, cluster_region, app_name)
    logger.info(f"Refreshing k8s resources for the application: {app_name}")
    task_id = context.eks_inventory_manager.trigger_k8s_resource_refresh(
        csp_k8s_instance_id=cluster_info.id, csp_k8s_resource_id=app_id
    )

    if wait_for_task:
        logger.info(f"Waiting for eks resource refresh for the application {app_name} to complete")
        refresh_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.task_timeout,
        )
        assert (
            refresh_task_status.upper() == TaskStatus.success.value
        ), f"EKS resource refresh for application {app_name} is failed, refresh_task_status={refresh_task_status}"

    return task_id


def perform_eks_cluster_refresh(
    context: Context,
    cluster_name: str,
    cluster_region: str,
    wait_for_task: bool = True,
) -> str:
    """
    Args:
        context (Context): Context object
        cluster_name (str): Name of the EKS cluster
        cluster_region (str): Cluster region
        wait_for_task (bool, optional): Boolean value to wait of the task. Defaults to True.

    Returns:
        str: The task ID for the cluster request in DSCC
    """
    cluster_info = get_csp_k8s_cluster_by_name(context, cluster_name, cluster_region)
    csp_cluster_id = cluster_info.id
    logger.info(f"Refreshing cluster for EKS account {csp_cluster_id}")
    task_id = context.eks_inventory_manager.trigger_k8s_cluster_refresh(csp_cluster_id=csp_cluster_id)

    if wait_for_task:
        logger.info(f"Waiting for cluster refresh for {csp_cluster_id} to complete")
        refresh_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.task_timeout,
        )
        assert (
            refresh_task_status.upper() == TaskStatus.success.value
        ), f"Cluster {csp_cluster_id} refresh failure, refresh_task_status={refresh_task_status}"

    return task_id


def perform_csp_k8s_cluster_register(context: Context, csp_k8s_cluster_id: str) -> str:
    """
    Args:
        context (Context): Context object
        csp_k8s_cluster_id (str): csp k8s cluster uuid

    Returns:
        str: command to execute.
    """
    command = context.eks_inventory_manager.register_k8s_cluster_with_dscc(csp_k8s_cluster_id)
    assert command, f"Register of csp k8s clutser {csp_k8s_cluster_id} failed."
    return command


def perform_validate_k8s_cluster_accessTo_dscc(
    context: Context,
    csp_k8s_cluster_id: str,
    wait_for_task: bool = True,
) -> str:
    """
    Args:
        context (Context): Context object
        csp_k8s_cluster_id (str): csp k8s cluster uuid
        wait_for_task (bool): decides whether or not we have to wait for the task to complete before proeceeding.

    Returns:
        str: The task ID for the EKS validation request of registered k8s cluster
    """
    task_id = context.eks_inventory_manager.validate_k8s_cluster_accessTo_dscc(csp_k8s_cluster_id)
    if wait_for_task:
        logger.info(f"Waiting for validate task for k8s cluster {csp_k8s_cluster_id} to complete")
        validation_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.task_timeout,
        )
        logger.info(f"Validation Status is {validation_task_status}")
        assert (
            validation_task_status.upper() == TaskStatus.success.value
        ), f"K8s cluster {csp_k8s_cluster_id} validation failed, validation_task_status={validation_task_status}"
    return task_id


def perform_validate_k8s_cluster_access_to_dscc_status_code(context: Context, csp_k8s_instance_id: str):
    """
    Args:
        context (Context): context object
        csp_k8s_instance_id (str): kubernetes cluster dscc id

    Returns:
        int: status code of response
    """
    status_code = context.eks_inventory_manager.validate_k8s_cluster_access_to_dscc_status_code(csp_k8s_instance_id)
    return status_code


def perform_csp_k8s_cluster_unregister_status_code(context: Context, csp_k8s_instance_id: str):
    """
    Args:
        context (Context): Context object
        csp_k8s_instance_id (str): kubernetes cluster dscc id

    Returns:
        int: status code of response
    """
    response_status_code = context.eks_inventory_manager.unregister_k8s_cluster_from_dscc_status_code(
        csp_k8s_instance_id
    )
    return response_status_code


def perform_csp_k8s_cluster_unregister(
    context: Context,
    cluster_name: str,
    cluster_region: str,
    wait_for_task: bool = True,
    skip_verify_and_set_context=False,
) -> str:
    """
    Args:
        context (Context): Context object
        cluster_name (str): Name of the EKS cluster
        cluster_region (str): EKS cluster region
        wait_for_task (bool): decides whether or not we have to wait for the task to complete before proeceeding.

    Returns:
        str: command to execute.
    """
    # Get cluster id
    cluster_info = get_csp_k8s_cluster_by_name(context, cluster_name, cluster_region)
    csp_k8s_cluster_id = cluster_info.id

    # Verify and set appropriate cluster context
    if skip_verify_and_set_context:
        logger.info("Skipping the switch cluster context")
    else:
        EKSCommonSteps.verify_and_set_eks_cluster_context(
            cluster_name,
            cluster_region,
            aws_eks_iam_user_name=context.aws_eks_iam_user_name,
        )
    task_id = context.eks_inventory_manager.unregister_k8s_cluster_from_dscc(csp_k8s_cluster_id)
    if wait_for_task:
        logger.info(f"Waiting for validate task for k8s cluster {csp_k8s_cluster_id} to complete")
        validation_task_status: str = tasks.wait_for_task(
            task_id=task_id,
            user=context.user,
            timeout=TimeoutManager.task_timeout,
        )
        logger.info(f"Validation Status is {validation_task_status}")
        assert (
            validation_task_status.upper() == TaskStatus.success.value
        ), f"Un-registration of K8s cluster {csp_k8s_cluster_id} failed"


def cluster_discovery_and_validation(context: Context, aws_session: AWS = None):
    """list cluster and validate the cluster info by comparing DSCC vs Boto3 APIs
    Args:
        context (Context): Test context
        aws_session (AWS): AWS session object
    """
    # Get cluster info
    cluster_info = get_csp_k8s_cluster_by_name(context, context.eks_cluster_name, context.eks_cluster_aws_region)
    logger.info(f"K8s cluster info from DSCC: {cluster_info}")
    dscc_cluster = cluster_info.name

    # get list of clusters from AWS account
    if not aws_session:
        aws_session = context.aws_eks
    boto3_cls_list = aws_session.eks.get_eks_clusters()
    logger.info(f"K8s cluster info using Boto3 APIs: {boto3_cls_list}")
    assert (
        dscc_cluster in boto3_cls_list["clusters"]
    ), f"Failed to compare Boto3: {boto3_cls_list['clusters']} Vs DSCC: {dscc_cluster} cluster info"
    logger.info(f"Successfully validated Boto3: {boto3_cls_list['clusters']} Vs DSCC: {dscc_cluster} cluster info")


@retry(stop=stop_after_attempt(3), reraise=True)
def register_csp_k8s_cluster(
    context: Context,
    cluster_name,
    cluster_region,
    is_invalid: bool = False,
):
    """Register Csp K8s cluster
    Args:
        context (Context): test context
        cluster_name (str): Name of the EKS cluster
        cluster_region (str): EKS cluster region
        is_invalid (bool): Invalid commad Default to False
    """
    # Register the Kubernetes cluster with DSCC
    cluster_info = get_csp_k8s_cluster_by_name(context, cluster_name, cluster_region)
    cluster_id = cluster_info.id
    logger.info(f"Cluster ID to be registered with DSCC: {cluster_id}")
    EKSCommonSteps.verify_and_set_eks_cluster_context(
        cluster_name, cluster_region, aws_eks_iam_user_name=context.aws_eks_iam_user_name
    )
    cls_register_command = perform_csp_k8s_cluster_register(context, cluster_id)
    formatted_cmd = EKSCommonSteps.generate_subprocess_cmd_format(cls_register_command)
    if is_invalid:
        formatted_invalid_cmd = copy.deepcopy(formatted_cmd)
        for cmd in formatted_invalid_cmd:
            cmd[cmd.index("create")] = "update"
            cmd[cmd.index("--arn")] = "--arm"
        logger.info(formatted_invalid_cmd)
        command_status = EKSCommonSteps.run_iam_role_mapping_cmd_for_eks_cls(formatted_invalid_cmd, is_invalid)
        assert (
            command_status
        ), "Failed to Fail the execution of eksctl commands to map identity roles for the EKS cluster"
        logger.info("Successfully executed invalid commands to ensure invalid results.")
    else:
        command_status = EKSCommonSteps.run_iam_role_mapping_cmd_for_eks_cls(formatted_cmd, is_invalid)
        assert command_status, "Failed to run eksctl commands to map identity roles for the EKS cluster"
        logger.info("Successfully ran eksctl commands to map identity roles for the EKS cluster")


def validate_csp_k8s_cluster_for_negative_scenario(context: Context):
    """Validates k8s cluster for negative scenario.

    Args:
        context (Context): Context set for the test execution.
    """
    logger.info("Validating Clusters for negative Scenario.")
    cluster_info = get_csp_k8s_cluster_by_name(context, context.eks_cluster_name, context.eks_cluster_aws_region)
    cluster_id = cluster_info.id
    assert (
        cluster_info.registration_status.value == "UNREGISTERED"
    ), f"Error - The Cluster with ID:{cluster_id} is registered. Check the register cluster for negative method."
    assert (
        cluster_info.validation_info.status.value == "UNVALIDATED"
    ), f"Error - The cluster with ID:{cluster_id} is validated."


def validate_csp_k8s_cluster(context: Context, cluster_name: str, cluster_region: str):
    """Validate csp k8s cluster
    Args:
        context (Context): test context
        cluster_name (str): EKS cluster name
        cluster_region (str): EKS cluster region
    """
    logger.info("Validating registered csp k8s cluster with DSCC")
    cluster_info = get_csp_k8s_cluster_by_name(context, cluster_name, cluster_region)
    cluster_id = cluster_info.id
    perform_validate_k8s_cluster_accessTo_dscc(context, cluster_id)
    cluster_info = context.eks_inventory_manager.get_csp_k8s_instance_by_id(cluster_id)
    assert (
        cluster_info.registration_status.value == CSPK8sClusterRegistrationStatus.REGISTERED.value
    ), f"failed to register the cluster: {cluster_info}"
    assert (
        cluster_info.validation_info.status.value == ValidationStatus.passed.value
    ), f"Failed to validate eks cluster: {cluster_info}"
    logger.info(f"Successfully validated csp k8s cluster: {cluster_info}")


def list_csp_k8s_applications_and_validate(context: Context, cluster_id: str):
    """List CSP k8s application and validate the apps list with dscc vs k8s

    Args:
        context (Context): Test context
        cluster_id (str): EKS cluster csp ID
    """
    # Get apps from DSCC
    apps_list = context.eks_inventory_manager.get_csp_k8s_applications(cluster_id)
    logger.debug(f"Namespaced apps list: {apps_list}")
    dscc_app_names = [app.name for app in apps_list.items if app.state != State.DELETED]
    logger.info(f"Namespaced apps list from DSCC: {dscc_app_names}")
    # Get apps using kubectl, this will be a workaround until we fix k8 client connection issue
    command = ["kubectl", "get", "ns"]
    command_result = EKSCommonSteps.run_ctl_command(command, kubectl_command=True)
    assert command_result, "kubectl command execution failed..."
    # Split the output into lines
    lines = command_result.strip().split("\n")
    # Extract the names from the lines, excluding the specified names
    excluded_names = ["kube-node-lease", "kube-public", "kube-system"]
    k8s_app_names = [line.split()[0] for line in lines[1:] if line.split()[0] not in excluded_names]
    logger.info(f"Namespaced apps list from kubectl :{k8s_app_names}")
    assert sorted(dscc_app_names) == sorted(
        k8s_app_names
    ), f"Failed to validate applications from the EKS cluster, dscc apps list: {dscc_app_names} k8s apps list: {k8s_app_names}"
    logger.info("Successfully validated the apps list from DSCC vs EKS K8s")


def unregister_csp_account(context: Context, csp_account_name=None):
    """Unregister CSP AWS account

    Args:
        context (Context): _descrTest context
    """
    if csp_account_name is None:
        csp_account_name = context.aws_eks_account_name
    csp_account = CAMSteps.get_csp_account_by_csp_name(context, csp_account_name)

    # Deleting created account
    CAMSteps.delete_csp_account_with_expectation(context, csp_account.id)

    # Validating that the deleted account is no longer present
    csp_account = CAMSteps.get_csp_account_by_csp_name(context, csp_account_name, is_found_assert=False)
    assert csp_account is None, f"CSP account: {csp_account} still exists after unregistration."


def get_csp_k8s_cluster_by_name(context: Context, cluster_name: str, cluster_aws_region: str):
    """Get csp k8s cluster by name

    Args:
        context (Context): Test context
        cluster_name (str): EKS cluster name
        cluster_aws_region (str): EKS cluster region

    Returns:
        CSPK8sCluster: CSP K8s cluster information
    """
    csp_account = CAMSteps.get_csp_account_by_csp_name(context, context.aws_eks_account_name)
    cluster_list: CSPK8sClustersListModel = context.eks_inventory_manager.get_csp_k8s_clusters(
        filter=EKSCommonSteps.get_list_specific_cls_filter(csp_account.id, cluster_name, cluster_aws_region)
    )
    logger.debug(f"cluster info from the response: {cluster_list}")
    assert cluster_list.total == 1, f"Failed to get the cluster info of {cluster_name}"
    return cluster_list.items[0]


def unassign_delete_protection_policy_for_eks_app(
    context: Context, app_name: str, protection_policy_name: str, cluster_id: str
):
    """Unassign protection policy for an eks app
    Args:
        context (Context): test context
        app_name (str): application name deployed into eks cluster
        protection_policy_name (str): protection policy name to unassign and delete
    """
    # Get application id
    logger.info("Get application id which is deployed in csp k8s cluster with DSCC")
    app_id = EKSCommonSteps.get_eks_k8s_cluster_app_by_name(
        context,
        context.eks_cluster_name,
        context.eks_cluster_aws_region,
        app_name,
    )
    logger.info(f"Application id which is deployed in csp k8s cluster with DSCC {cluster_id}")
    # unprotect eks app from protection policy
    PolicyMgrSteps.unassign_all_protection_policies(context, app_id)
    # delete protection policy
    logger.info(f"Delete protection policy {protection_policy_name} if already exist")
    PolicyMgrSteps.delete_protection_jobs_and_policy(context=context, protection_policy_name=protection_policy_name)


def get_all_k8s_namespaces(client: KubernetesClient) -> list:
    """Get list of only name of name spaces in a region using Kubernetes client
    Args:
        client (KubernetesClient): reference to KubernetesClient class
    Returns:
        namespace (list): List only name of namespaces
    """
    ns_list = client.get_namespaces()
    ns_list_items = ns_list.items
    ns_name_label_list = [list(ns_list_value.metadata.labels.values()) for ns_list_value in ns_list_items]
    return [item for sublist in ns_name_label_list for item in sublist]


def verify_and_set_eks_cluster_health_status(context, eks_cluster_name, cluster_region):
    """verifies eks cluster registration status, if it is not in registered state then it will set it to Registered and validated state.

    Args:
        context (obj): context object
        eks_cluster_name (str): eks cluster name
        cluster_region (str): eks cluster region
    """
    # Get EKS cluster info
    cluster_info = get_csp_k8s_cluster_by_name(context, eks_cluster_name, cluster_region)
    logger.info(f"Verifying cluster: {cluster_info.name} and id: {cluster_info.id} health status")
    if (
        cluster_info.registration_status == CSPK8sClusterRegistrationStatus.REGISTERED.value
        and cluster_info.validation_info.status.value == ValidationStatus.passed.value
    ):
        logger.info(
            f"Cluster: {cluster_info.name} and id: {cluster_info.id} is in expected state, lets continue the test"
        )
    if cluster_info.registration_status.value == CSPK8sClusterRegistrationStatus.NOT_REGISTERED.value:
        register_csp_k8s_cluster(context, eks_cluster_name, cluster_region)
        validate_csp_k8s_cluster(context, eks_cluster_name, cluster_region)
    if cluster_info.registration_status.value == CSPK8sClusterRegistrationStatus.UNREGISTERED.value:
        register_csp_k8s_cluster(context, eks_cluster_name, cluster_region)
        validate_csp_k8s_cluster(context, eks_cluster_name, cluster_region)
    if cluster_info.validation_info.status.value == ValidationStatus.failed.value:
        validate_csp_k8s_cluster(context, eks_cluster_name, cluster_region)
    logger.info(f"Successfully verified cluster: {cluster_info.name} and id: {cluster_info.id} health status")


def validate_eks_cluster_state(
    context: Context, eks_cluster_name: str, cluster_region: str, expected_cluster_state: str
):
    """Validate cluster state with expected

    Args:
        context (Context): context object
        eks_cluster_name (str): EKS cluster name
        cluster_region (str): AWS region where cluster is deployed
        expected_cluster_state (str): expected cluster state
    """
    logger.info(f"Validating expected cluster state - {expected_cluster_state}")
    cluster_info = get_csp_k8s_cluster_by_name(context, eks_cluster_name, cluster_region)
    cluster_state = cluster_info.state.value
    assert (
        cluster_state == expected_cluster_state
    ), f"Cluster state is not as expected. Expected: {expected_cluster_state}, but was {cluster_state}."
    logger.info(f"Cluster state is as expected: {cluster_state}")


def validate_application_state(
    context: Context, csp_k8s_instance_id: str, csp_k8s_application_id: str, expected_app_state: str
):
    """Validate K8s app state

    Args:
        context (Context): context object
        csp_k8s_instance_id (str): cluster instance ID
        csp_k8s_application_id (str): app instance ID
        expected_app_state (str): expected app state
    """
    logger.info("Validating application state")
    app_info = context.eks_inventory_manager.get_k8s_app_by_id(csp_k8s_instance_id, csp_k8s_application_id)
    assert (
        app_info.state.name == expected_app_state
    ), f"Expected application state is {expected_app_state}, but was {app_info.state}. App ID: {csp_k8s_application_id}, cluster ID: {csp_k8s_instance_id}"
    logger.info(f"Application state is as expected {app_info.state}")


def verify_and_set_k8s_app_health_status(context: Context, cluster_name, cluster_aws_region, app_yaml):
    # Verify k8s application in DSCC vs EKS cluster
    app_name = validate_csp_k8s_app(context, cluster_name, cluster_aws_region, app_yaml, availability=True)

    if app_name is None:
        # Deploy application again in AWS and confirm the deployment

        EKSCommonSteps.deploy_application_on_eks_cluster(
            context=context,
            cluster_name=context.eks_cluster_name,
            cluster_region=context.eks_cluster_aws_region,
            app_config_yaml=app_yaml,
            app_timeout=300,
        )
        logger.info(f"successfully deployed new application with {app_yaml} yaml file")

        # Perform on-demand refresh
        perform_eks_cluster_refresh(context, context.eks_cluster_name, context.eks_cluster_aws_region)
        logger.info("Successfully refreshed csp k8s inventory")

        # Verify k8s application in DSCC vs EKS cluster
        app_name = validate_csp_k8s_app(
            context, context.eks_cluster_name, context.eks_cluster_aws_region, app_yaml, availability=True
        )
        app_id = EKSCommonSteps.get_eks_k8s_cluster_app_by_name(
            context,
            context.eks_cluster_name,
            context.eks_cluster_aws_region,
            app_name=app_name,
        )
    else:
        # Verify if backup exists, if exists delete the backup
        logger.info(f"Get application ID for the k8 app name {app_name} by using cluster ID")
        app_id = EKSCommonSteps.get_eks_k8s_cluster_app_by_name(
            context,
            context.eks_cluster_name,
            context.eks_cluster_aws_region,
            app_name=app_name,
        )

        # unassign and delete all protection policies.
        protection_job = EKSBackupSteps.get_protection_job(context, app_id)
        if protection_job:
            csp_cluster_info = get_csp_k8s_cluster_by_name(
                context, context.eks_cluster_name, context.eks_cluster_aws_region
            )
            unassign_delete_protection_policy_for_eks_app(
                context=context,
                app_name=app_name,
                protection_policy_name=protection_job.asset_info.name,
                cluster_id=csp_cluster_info.id,
            )

        # delete all backups
        csp_account: CSPAccountModel = CAMSteps.get_csp_account_by_csp_name(context, context.aws_eks_account_name)
        EKSBackupSteps.delete_all_k8s_apps_backups(
            context,
            [app_id],
            csp_account,
            context.eks_cluster_aws_region,
            skip_immutable_backup=True,
        )
    return app_name, app_id


def validate_csp_k8s_app(context: Context, eks_cluster_name, cluster_region, app_yaml, availability=True):
    """Validate CSP k8s app DSCC vs Kubernetes

    Args:
        context (obj): context object
        eks_cluster_name (str): eks cluster name
        cluster_region (str): eks cluster region
        app_yaml (yaml): K8s application yaml file path

    Returns: Returns the discovered k8s app name
    """
    # Get EKS cluster info
    cluster_info = get_csp_k8s_cluster_by_name(context, eks_cluster_name, cluster_region)
    dscc_apps_list = context.eks_inventory_manager.get_csp_k8s_applications(cluster_info.id)
    logger.debug(f"Application list from DSCC: {dscc_apps_list}")
    k8s_app_name = EKSCommonSteps.read_yaml_get_namespace(app_yaml)
    logger.info(f"Application name from yaml: {k8s_app_name}")
    dscc_app_name = None
    for app in dscc_apps_list.items:
        if app.name == k8s_app_name:
            dscc_app_name = app.name
            break
    if availability and (dscc_app_name is not None):
        assert dscc_app_name, f"Deployed K8 app {dscc_app_name} is not available in DSCC which is unexpected"
        logger.info(f"K8s application has been deployed successfully and discovered in DSCC: {dscc_app_name}")
    elif availability and (dscc_app_name is None):
        logger.info("K8s application is not available, need to deploy the application")
    else:
        assert (
            dscc_app_name is None
        ), f"deployed k8s application {k8s_app_name} is available in DSCC which is unexpected"
        logger.info("Verified that the k8s app is successfully deleted")
    return dscc_app_name


def verify_and_prepare_cluster_availability_in_dscc_k8s_inventory(
    context: Context,
    cluster_name,
    cluster_aws_region,
    cluster_available=True,
    account_id=None,
    account_name=None,
    aws_session=None,
    cluster_yaml=None,
    app_config_yaml=[],
):
    """This method verify the availability of your cluster in the DSCC inventory or not based on the parameter available provide by the user and also if user want to create/delete cluster depends on cluster availability he/she can use this method as their testcase environment setup before the acutal testcase. This way we can avoid dependencies on each testcases.

    Args:
        context (Context): Context Object
        cluster_name (string): Cluster name for checking availability
        cluster_aws_region (string): cluster region for checking availability
        cluster_available (bool, optional): If user expecting cluster to not present in DSCC then please provide cluster_available parameter as False. Defaults to True.
        account_id (string, default None): If user have to create/delete cluster then provide aws account id.
        account_name (string, default None): If user have to create/delete cluster then provide aws account name.
        aws_session (AWS object, default None): If user have to create/delete cluster then provide aws session, it is AWS() object.
        cluster_yaml (string, default None): If user have to create/delete cluster then provide cluster yaml path in string.
    """
    # get all the list of clusters in the AWS account
    csp_account = CAMSteps.get_csp_account_by_csp_name(context, context.aws_eks_account_name)
    cluster_list: CSPK8sClustersListModel = context.eks_inventory_manager.get_csp_k8s_clusters(
        filter=EKSCommonSteps.get_list_specific_cls_filter(csp_account.id, cluster_name, cluster_aws_region)
    )
    logger.info(f"cluster info from the response: {cluster_list}")

    # verify cluster availability
    if cluster_available:
        if cluster_list.total == 1:
            logger.info(f"cluster with name: {cluster_name} in region: {cluster_aws_region} is available in DSCC")
        else:
            logger.info(f"cluster with name: {cluster_name} in region: {cluster_aws_region} is not available in DSCC")
            EKSCommonSteps.setup_eks_cluster(
                context,
                cluster_name=cluster_name,
                cluster_region=cluster_aws_region,
                aws_account_id=account_id,
                aws_session=aws_session,
                cluster_config_yaml=cluster_yaml,
                app_config_yamls=app_config_yaml,
                cluster_timeout=1800,
                app_timeout=600,
            )
            logger.info(f"Cluster with name f{cluster_name} is created successfully...")
            perform_eks_inventory_refresh(context=context, csp_account_name=account_name)
            logger.info("Performed account level eks inventory refresh successfully after cluster creation...")

    else:
        if cluster_list.total == 0:
            logger.info(f"cluster with name: {cluster_name} in region: {cluster_aws_region} is not available in DSCC")
        else:
            logger.info(f"cluster with name: {cluster_name} in region: {cluster_aws_region} is available in DSCC")
            EKSCommonSteps.cleanup_eks_cluster(
                cluster_name=cluster_name,
                aws_account_id=account_id,
                aws_session=aws_session,
                cluster_config_yaml=cluster_yaml,
                need_asset_info=True,
            )
            logger.info(f"Cluster with name f{cluster_name} is cleaned successfully...")
            perform_eks_inventory_refresh(context=context, csp_account_name=account_name)
            logger.info("Performed account level eks inventory refresh successfully after cleanup of cluster...")


def verify_created_app_count_in_dashboard(context: Context, inventory_before_deployment: InventorySummaryModel):
    """Verify if count of EKS applications on dashboard increased after app deployment

    Args:
        context (Context): context object
        inventory_before_deployment (Dashboard.InventorySummaryModel): inventory object taken from context dashboard manager
    """
    logger.info("Verifying app count after deployment in dashboard summary...")
    DashboardSteps.wait_dashboard_eks_apps(
        context, inventory_before_deployment.csp_eks_applications.aws, CompareCondition.greater
    )
    inventory_after_deployment = DashboardSteps.get_inventory_summary(context)
    assert (
        inventory_after_deployment.csp_eks_applications.aws == inventory_before_deployment.csp_eks_applications.aws + 1
    ), f"Number of EKS applications in dashboard after deployment is unexpected. Should be {inventory_before_deployment.csp_eks_applications.aws + 1}, but was {inventory_after_deployment.csp_eks_applications.aws}"


def verify_created_volume_count_in_dashboard(context: Context, inventory_before_deployment: InventorySummaryModel):
    """Verify if count of volumes on dashboard increased after volume deployment

    Args:
        context (Context): context object
        inventory_before_deployment (Dashboard.InventorySummaryModel): inventory object taken from context dashboard manager
    """
    logger.info("Verifying volumes count after deployment in dashboard summary...")
    DashboardSteps.wait_dashboard_ebs_volumes(
        context, inventory_before_deployment.csp_volumes.aws, CompareCondition.greater
    )
    inventory_after_deployment = DashboardSteps.get_inventory_summary(context)
    assert (
        inventory_after_deployment.csp_volumes.aws == inventory_before_deployment.csp_volumes.aws + 1
    ), f"Number of EKS PVs in dashboard after deployment is unexpected. Should be {inventory_before_deployment.csp_volumes.aws + 1}, but was {inventory_after_deployment.csp_volumes.aws}"


def verify_deleted_volume_count_in_dashboard(context: Context, inventory_before_deletion: InventorySummaryModel):
    """Verify if count of volumes on dashboard decreased after volume deletion

    Args:
        context (Context): context object
        inventory_before_deletion (Dashboard.InventorySummaryModel): inventory object taken from context dashboard manager
    """
    logger.info("Verifying volumes count after deletion in dashboard summary...")
    DashboardSteps.wait_dashboard_eks_apps(context, inventory_before_deletion.csp_volumes.aws, CompareCondition.less)
    inventory_after_deletion = DashboardSteps.get_inventory_summary(context)
    assert (
        inventory_after_deletion.csp_volumes.aws == inventory_before_deletion.csp_volumes.aws - 1
    ), f"Number of EKS PVs in dashboard after deployment is unexpected. Should be {inventory_before_deletion.csp_volumes.aws - 1}, but was {inventory_after_deletion.csp_volumes.aws}"


def verify_deleted_app_count_in_dashboard(context: Context, inventory_before_delete: InventorySummaryModel):
    """Verify if count of EKS applications on dashboard decreased after app deletion

    Args:
        context (Context): context object
        inventory_before_deletion (Dashboard.InventorySummaryModel): inventory object taken from context dashboard manager
    """
    logger.info("Verifying app count after deletion in dashboard summary...")
    DashboardSteps.wait_dashboard_eks_apps(
        context, inventory_before_delete.csp_eks_applications.aws, CompareCondition.less
    )
    inventory_after_deletion = DashboardSteps.get_inventory_summary(context)
    assert (
        inventory_after_deletion.csp_eks_applications.aws == inventory_before_delete.csp_eks_applications.aws - 1
    ), f"Number of EKS applications in dashboard after deployment is unexpected. Should be {inventory_before_delete.csp_eks_applications.aws - 1}, but was {inventory_after_deletion.csp_eks_applications.aws}"


def verify_all_eks_apps_against_dashboard_summary(context: Context):
    """Verify if dashboard summary of EKS applications equals sum of applications in inventory

    Args:
        context (Context): context object
    """
    logger.info("Verifying count of EKS apps in dashboard and from inventory...")
    dscc_app_count = EKSCommonSteps.get_count_of_all_k8s_applications()
    dashboard_app_count = DashboardSteps.get_inventory_summary(context).csp_eks_applications.aws
    assert (
        dscc_app_count == dashboard_app_count
    ), f"App count in inventory and dashboard doesn't match. In inventory: {dscc_app_count}, in dashboard: {dashboard_app_count}"


def get_csp_k8s_resources(
    context: Context,
    csp_k8s_instance_id: str,
) -> Union[CSPK8sResourcesListModel, ErrorResponse]:
    """Get all resources from kubernetes cluster

    Args:
        context (Context): context object
        csp_k8s_instance_id (str): k8s cluster id in dscc

    Returns:
        Union[CSPK8sResourcesListModel, ErrorResponse]: model of CSPK8sResourcesList or Error
    """
    csp_k8s_resources = context.eks_inventory_manager.get_csp_k8s_resources(csp_k8s_instance_id)
    return csp_k8s_resources
