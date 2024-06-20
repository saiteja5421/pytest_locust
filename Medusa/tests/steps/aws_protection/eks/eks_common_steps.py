from datetime import datetime, timedelta
import logging
import os
import re
import subprocess
import time
import requests

from tenacity import retry, stop_after_delay, wait_fixed, stop_after_attempt
import random

import yaml
from lib.common.enums.account_validation_status import ValidationStatus
from lib.common.enums.aws_region_zone import AWSRegionZone
from lib.common.enums.eks_cluster_versions import EksClusterVersions
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import CSPAccountModel
from lib.dscc.backup_recovery.aws_protection.eks.domain_models.csp_k8s_model import CSPK8sApplicationModel

from tests.e2e.aws_protection.context import Context
from utils.common_helpers import list_file_tree_structure
from utils.eksctl.eks_cluster import run_eks_cluster_command
from lib.platform.aws_boto3.aws_factory import AWS
from lib.common.enums.asset_info_types import AssetType
import tests.steps.aws_protection.assets.standard_asset_creation_steps as SA
import tests.steps.aws_protection.policy_manager_steps as PolicyManagerSteps
import lib.platform.kubernetes.kubernetes_client as K8SClient
import tests.steps.aws_protection.eks.csp_eks_backup_steps as EKSBackupSteps
import tests.steps.aws_protection.cloud_account_manager_steps as CAMSteps
import tests.steps.aws_protection.eks.csp_eks_inventory_steps as EKSInvSteps
import tests.steps.aws_protection.common_steps as CommonSteps
from lib.common.enums.csp_backup_type import CSPBackupType
from waiting import wait, TimeoutExpired
from botocore import exceptions

logger = logging.getLogger()


def generate_subprocess_cmd_format(eksctl_command: str):
    """It will generate provided command into a subprocess formatted command
    e.g" command = [
    "eksctl",
    "create",
    "iamidentitymapping",
    "--cluster",
    "eks-cluster1",
    "--region=us-east-1",
    "--arn",
    "arn:aws:iam::773592459549:role/hpe-cam-csp-k8s-inventory-manager",
    "--group",
    "system:masters,system:nodes"
    ]

    Args:
        eksctl_command (str): eksctl command which will be returned form the register/unregister eks cluster APIs

    Return:
        list of subprocess formatted commands
    """
    eksctl_commands = eksctl_command.split(";")
    logger.info(f"eksctl command list: {eksctl_commands}")
    formatted_commands = []
    for eksctl_command in eksctl_commands:
        eksctl_command = eksctl_command.lstrip()
        command = eksctl_command.split(" ")
        logger.info(f"eksctl command: {command}")
        formatted_commands.append(command)
    return formatted_commands


def run_iam_role_mapping_cmd_for_eks_cls(
    commands, is_invalid: bool = False, capture_output=True, text=True, timeout=300
):
    """Run eksctl commands for create/delete iamidentitymapping roles for EKS cluster

    Args:
        commands (list[str]): commands to run for register eks cluster iamidentitymapping roles
        is_invalid (bool): Checks whether the method is getting called for positive or negative scenario.
        capture_output (bool, optional): Output of the child process . Defaults to True.
        text (bool, optional): Return the output in the form of string, if set to True. Defaults to True.
        timeout (int, optional): Wait time to run the child process. Defaults to 300.

    Returns:
        bool: return True, if success. else False
    """
    logger.info("Running eksctl command to create/delete iamidentitymapping roles on aws account")
    for command in commands:
        result = run_eks_cluster_command(command, capture_output=capture_output, text=text, timeout=timeout)
        if result:
            logger.info(result)
            logger.info(f"Command result: {result.returncode}")
        if not result:
            if is_invalid:
                logger.info(f"Failed to run eksctl command: {command}, due to an exception")
                return True
            else:
                logger.error(f"Failed to run eksctl command: {command}, due to an exception")
                return False
        if result.returncode:
            if is_invalid:
                logger.info(f"Failed to run eksctl command: {command}, due to setup error: {result.stderr}")
                return True
            else:
                logger.error(f"Failed to run eksctl command: {command}, due to setup error: {result.stderr}")
                return False
        logger.info(f"Successfully executed eksctl command: {command} output: {result.stdout}")
    return True


def run_ctl_command(command, timeout=300, kubectl_command=False):
    """Runs provided ctl command either eksctl or kubectl

    Args:
        command (str): eksctl/kubectl command to be executed
        timeout (int, optional): wait time to execute the command, defaults to 300
        kubectl_command (bool, optional): if kubectl command result need then set to True, defaults to False

    Returns:
        bool: returns boolean based on the test execution status. if kubectl_command is true then returns stdout from result
    """
    result = run_eks_cluster_command(command, timeout=timeout)
    logger.info(f"ctl command execution result: {result}")
    if not result:
        logger.error(f"Failed to run ctl command: {command}, due to an exception")
        return False
    if result.returncode:
        logger.error(f"Failed to run ctl command: {command}, due to setup error: {result.stderr}")
        return False
    logger.info(f"Successfully executed ctl command: {command} output: {result.stdout}")
    if kubectl_command:
        return result.stdout
    return True


@retry(stop=stop_after_attempt(3), reraise=True)
def setup_eks_cluster(
    context: Context,
    cluster_name,
    cluster_region,
    aws_account_id,
    aws_session,
    cluster_config_yaml,
    app_config_yamls=[],
    cluster_timeout=1800,
    app_timeout=300,
    cleanup_before=False,
    driver_name="aws-ebs-csi-driver",
):
    """setup eks cluster

    Args:
        context (Context): Test Context Object
        cluster_name (String): provide name for cluster creation
        cluster_region (String): provide cluster region in which cluster going to create
        aws_account_id (Number): 12 digit Account ID for creating ebs role
        aws_session (AWS): AWS session object
        cluster_config_yaml (str): Cluster configuration yaml path
        app_config_yamls (arr, optional): namespaced applications configuration yaml paths, Defaults to []
        cluster_timeout (int, optional): wait time to execute the command. Defaults to 1800.
        app_timeout (int, optional): wait time to execute the command. Defaults to 300.
        cleanup_before (bool): specify if you want to cleanup cluster resources before deploying new one
        driver_name (string): CSI driver name, defaults to aws-ebs-csi-driver

    """
    logger.info("Setup EKS cluster...")
    if cleanup_before:
        cleanup_eks_cluster(cluster_name, aws_account_id, aws_session, cluster_config_yaml)
    create_cluster(aws_session, cluster_name, cluster_config_yaml, cluster_timeout)
    verify_and_set_eks_cluster_context(
        cluster_name,
        cluster_region,
        aws_eks_iam_user_name=context.aws_eks_iam_user_name,
    )
    log_kube_configs()
    create_oidc(aws_session, cluster_name, cluster_region)
    if driver_name == "aws-ebs-csi-driver":
        role_name = "AmazonEKS_EBS_CSI_DriverRole" + cluster_name
        create_ebs_role(aws_session, cluster_name, cluster_region, role_name, context)
    elif driver_name == "aws-efs-csi-driver":
        role_name = "AmazonEKS_EFS_CSI_DriverRole" + cluster_name
        create_efs_role(aws_session, cluster_name, cluster_region, role_name, context)
    else:
        assert False, f"Got an unexpected csi driver addon name {driver_name}"

    install_snapshotter()
    create_csi_driver_add_on(
        aws_session,
        aws_account_id,
        cluster_name,
        cluster_region,
        app_timeout,
        role_name,
        driver_name=driver_name,
    )

    # added sleep seconds before execute ebs csi add on
    time.sleep(30)
    if app_config_yamls:
        for app_config_yaml in app_config_yamls:
            deploy_application_on_eks_cluster(context, cluster_name, cluster_region, app_config_yaml, app_timeout)


def get_eks_k8s_cluster_app_by_name(context: Context, eks_cluster_name, cluster_region, app_name):
    """this step gets the app id if user provides cluster id and k8S app name

    Args:
        context (Context): Test Context Object
        eks_cluster_name (str): eks cluster name
        cluster_region (str): eks cluster region
        app_name (str): k8s app name

    Returns:
        ste: it returns app ID if matched with provided app name
    """
    # Get EKS cluster info
    cluster_info = EKSInvSteps.get_csp_k8s_cluster_by_name(context, eks_cluster_name, cluster_region)
    all_apps = context.eks_inventory_manager.get_csp_k8s_applications(
        csp_k8s_instance_id=cluster_info.id,
    )
    app_id = None
    for app in all_apps.items:
        if app.name == app_name:
            app_id = app.id
    assert app_id, f"Failed to fetch app id by name {app_name} in api response: {all_apps}"
    return app_id


def get_eks_k8s_cluster_app_info_by_name(context: Context, k8s_cluster_id, app_name):
    """this step gets the app info if user provides cluster id and k8S app name
    Args:
        context (Context): Test Context Object
        k8s_cluster_id (str): Cluster ID from where user want to fetch app
        app_name (str): k8s app name
    Returns:
        ste: it returns app Info if matched with provided app name in the cluster
    """
    all_apps = context.eks_inventory_manager.get_csp_k8s_applications(
        csp_k8s_instance_id=k8s_cluster_id,
    )
    app_info = None
    for app in all_apps.items:
        if app.name == app_name:
            app_info = app
    assert app_info, f"Failed to fetch app info by name {app_name} in api response: {all_apps}"
    return app_info


def create_protection_policy_for_eks_app(
    context: Context, protection_policy_name=None, cloud_only=False, immutable=False
):
    """this step performs creation of protection policy for EKS.

    Args:
        context (Context): Context Object
        protection_policy_name (str): name of protection policy to be created
        cloud_only (bool): create only cloud backup if True
        immutable (bool): if True taken backups are immutable (cannot be modified/deleted)
    """
    logger.info("create protection policy started...")
    policy_name = protection_policy_name if protection_policy_name else context.eks_protection_policy_name
    protection_policy_id = PolicyManagerSteps.create_protection_policy(
        context=context, name=policy_name, cloud_only=cloud_only, immutable=immutable
    )
    logger.info(f"protection policy ID created: {protection_policy_id} Successfully...")
    return protection_policy_id


def assign_protection_policy_to_eks_app(
    context: Context,
    eks_cluster_name,
    cluster_region,
    app_name,
    protection_policy_id,
):
    """This step perform assign of protection policy to an eks k8 app

    Args:
        context (Context): Context Object
        eks_cluster_name (str): eks cluster name
        cluster_region (str): eks cluster region
        app_name (str): Namespace app name in the cluster
        protection_policy_id (str): protection policy id which is created for protecting K8 app
    """
    # Get EKS cluster info
    cluster_info = EKSInvSteps.get_csp_k8s_cluster_by_name(context, eks_cluster_name, cluster_region)
    logger.info(f"assign protection policy {protection_policy_id} to eks application {app_name} is started..")
    application_id = get_eks_k8s_cluster_app_by_name(
        context,
        context.eks_cluster_name,
        context.eks_cluster_aws_region,
        app_name,
    )
    PolicyManagerSteps.assign_protection_policy(
        context=context,
        asset_id=application_id,
        asset_type=AssetType.CSP_K8S_APPLICATION.value,
        protection_policy_id=protection_policy_id,
    )
    logger.info(f"assign protection policy {protection_policy_id} to eks application {app_name} is successful...")


def cleanup_and_create_protection_policy_for_eks_app(
    context: Context,
    protection_policy_name: str,
    csp_k8s_app_id: str,
    cloud_only: bool = False,
    backup_only: bool = False,
    immutable=False,
):
    """Cleanup protection policies with the same name and create new one.

    Note: it will create default protections. Please check in create_protection_policy() for default values

    Args:
        context (Context): context object
        protection_policy_name (str): protection policy name to create
        csp_k8s_app_id (str): eks k8s application ID
        cloud_only (bool): If True, only a CloudBackup schedule will be created. Defaults to False.
        backup_only (bool): If True, only a Backup schedule will be created. Defaults to False.
    """
    PolicyManagerSteps.unassign_all_protection_policies(context, csp_k8s_app_id)
    logger.info(f"Delete protection policy {protection_policy_name} if already exist")
    PolicyManagerSteps.delete_protection_jobs_and_policy(context=context, protection_policy_name=protection_policy_name)

    # creating protection policy
    logger.info(f"Create protection policy {protection_policy_name} for both cloud and native")
    context.protection_policy_id = PolicyManagerSteps.create_protection_policy(
        context=context,
        name=protection_policy_name,
        cloud_only=cloud_only,
        backup_only=backup_only,
        immutable=immutable,
    )
    logger.info(f"Protection policy created successfully {context.protection_policy_id}")


def cleanup_eks_clusters_in_different_regions(
    aws_session, list_of_cluster_config_yamls, aws_account_id, need_asset_info=True
):
    """clean up eks clusters in different regions
    Note: keeping this step just incase if we want to use separate method for multiple eks deletion

    Args:
        aws_session (AWS): AWS session info
        list_of_cluster_config_yamls (list): Cluster configuration yaml paths
        app_config_yaml (str): namespaced application configuration yaml path.
        app_timeout (int, optional): wait time to execute the command. Defaults to 300.
        need_asset_info (bool, optional): Asset info of EKS cluster, e.g cluster name and node group . Defaults to True.

    """
    for cluster_config_yaml in list_of_cluster_config_yamls:
        cluster_name, cluster_aws_region = read_yaml_get_eks_cluster_info(cluster_config_yaml)
        cleanup_eks_cluster(
            cluster_name,
            aws_account_id,
            aws_session,
            cluster_config_yaml,
            need_asset_info=need_asset_info,
        )


def cleanup_eks_cluster(
    cluster_name,
    aws_account_id,
    aws_session,
    cluster_config_yaml,
    need_asset_info=True,
):
    """Clean up eks cluster in order:
    - node groups
    - EKS cluster AWS resources
    - EBS CSI addon stack
    - EKS stack
    - delete snapshots
    - delete volumes
    Applications deployed on EKS cluster are deleted along with EKS cluster itself.

    Args:
        context: Test Context
        cluster_name (String): provide name for cluster deletion
        aws_account_id (Number): 12 digit Account ID for deleting snapshot and volumes etc.,
        aws_session (AWS): aws session object to use for cleanup
        cluster_config_yaml (str): Cluster configuration yaml path
        need_asset_info (bool, optional): Asset info of EKS cluster, e.g cluster name and node group . Defaults to True.

    """
    logger.info("Cleaning up EKS cluster...")
    # Fetching OIDC issuer details before cluster delete
    cluster_details = (
        aws_session.eks.describe_eks_cluster(cluster_name)
        if cluster_name in aws_session.eks.get_eks_clusters().get("clusters")
        else False
    )
    logger.info(f"cluster details: {cluster_details}")
    oidc_issuer = cluster_details["cluster"]["identity"]["oidc"]["issuer"] if cluster_details else False
    logger.info(f"OIDC issuer: {oidc_issuer}")
    stack_list = get_eks_cluster_stack_info(cluster_config_yaml, need_asset_info=need_asset_info)
    delete_eks_node_groups(aws_session, cluster_config_yaml)
    stack_name = get_eks_cluster_stack_info(cluster_config_yaml, need_asset_info=True)[-1]
    cft_client = aws_session.cloud_formation
    stack_exist = cft_client.get_cf_stack(stack_name)
    if stack_exist:
        logger.info("Getting CFT stack resources...")
        resources = cft_client.get_stack_resources(stack_name)["StackResourceSummaries"]
        logger.info("Getting VPC ID...")
        vpc_id = [resource["PhysicalResourceId"] for resource in resources if resource["LogicalResourceId"] == "VPC"][0]
        delete_all_eks_stack_resources(aws_session, vpc_id, cluster_name, oidc_issuer)
    else:
        logger.info(f"No CFT stack with name {stack_name} found. Skipping AWS resources deletion.")
    ebs_csi_stack_name = f"eksctl-{cluster_name}-addon-iamserviceaccount-kube-system-ebs-csi-controller-sa"
    stack_list.append(ebs_csi_stack_name)
    verify_and_delete_cft_stacks(aws_session, cft_client, stack_list=stack_list)
    aws_session.ec2.delete_all_snapshots_from_account(aws_account_id)
    aws_session.ec2.delete_all_volumes()
    logger.info("Cleanup of EKS cluster and resources completed.")


def delete_all_eks_stack_resources(aws_session, vpc_id, cluster_name, oidc_issuer):
    logger.info("Deleting all resources from EKS cluster CFT stack...")
    aws_session.elb.delete_all_elbs()
    aws_session.nat_gateway.delete_all_nat_gateways_in_vpc(vpc_id)
    all_allocation_addresses = aws_session.ec2.get_all_allocation_address()
    logger.info(f"allocated address are: {all_allocation_addresses}")
    describe_addresses = aws_session.ec2.ec2_client.describe_addresses()["Addresses"]
    for each_address in describe_addresses:
        logger.info(f"describe_address: {describe_addresses}")
        associated_cluster_name = [tag["Value"] for tag in each_address["Tags"] if tag["Key"] == "Name"][0]

        if cluster_name in associated_cluster_name:
            logger.info(f"IP releasing: {each_address} from associated cluster: {associated_cluster_name} ...")
            aws_session.ec2.release_elastic_ip(each_address["AllocationId"])
        else:
            logger.info(f"there are no IP associated with {cluster_name}")

    # Deleting OIDC provider for individual clusters
    oidc_providers_list = aws_session.iam.iam_client.list_open_id_connect_providers()
    logger.info(f"OIDC provider list: {oidc_providers_list}")
    if oidc_providers_list and oidc_issuer:
        for provider in oidc_providers_list["OpenIDConnectProviderList"]:
            oidc_provider_for_arn = aws_session.iam.iam_client.get_open_id_connect_provider(
                OpenIDConnectProviderArn=provider["Arn"]
            )
            if oidc_provider_for_arn["Url"] in oidc_issuer:
                aws_session.iam.iam_client.delete_open_id_connect_provider(OpenIDConnectProviderArn=provider["Arn"])
    aws_session.internet_gateway.detach_and_delete_all_igws_in_vpc(vpc_id)
    # The following resources are attached to EKS control plane and AWS managed. Cannot be deleted directly, only by deleteing EKS cluster itself.
    # Resources: Network interface, subnets, route tables, NACL, security groups, VPC


def delete_eks_node_groups(aws_session, cluster_config_yaml, need_asset_info=True):
    """delete eks cluster nodegroup(s)

    Args:
        aws_session (AWS): AWS session info
        cluster_config_yaml (str): Cluster configuration yaml path
        cluster_timeout (int, optional): wait time to execute the command. Defaults to 300.
        need_asset_info (bool, optional): Asset info of EKS cluster, e.g cluster name and node group . Defaults to True.

    """
    logger.info("Deleting nodegroup(s) from EKS cluster...")
    (node_groups_info, cluster_name) = read_yaml_get_eks_cluster_info(
        cluster_config_yaml, need_asset_info=need_asset_info
    )
    stacks = aws_session.cloud_formation.ec2_client.describe_stacks()["Stacks"]
    node_group_stacks = list(filter(lambda stack: "nodegroup" in stack["StackName"], stacks))
    if node_group_stacks:
        for node_group_stack in node_group_stacks:
            if (cluster_name in node_group_stack["StackName"]) and (
                node_groups_info[0] in node_group_stack["StackName"]
            ):
                aws_session.cloud_formation.delete_cf_stack(node_group_stack["StackName"])
                try:
                    node_groups = aws_session.eks.get_eks_nodegroups(cluster_name)["nodegroups"]
                    assert not any(
                        [nodegroup in node_groups for nodegroup in node_groups_info]
                    ), "Deleting EKS cluster nodegroups failed. Found nodegroups on EKS cluster after deletion."
                except TypeError:
                    logger.info(f"Didn't get cluster nodes from cluster {cluster_name}")

                logger.info(f"Successfully deleted node group stack {node_group_stack['StackName']}")
            else:
                continue
    else:
        logger.info("Node groups CFT stack not found. Skipping deletion.")


def scan_all_regions_for_stack_and_delete(
    stack_name,
    aws_access_key_id,
    aws_secret_access_key,
    account_name,
):
    """Scan all supportd AWS regions for CFT stack, if found deletes the CFT

    Args:
        stack_name (str): CFT Stack Name
        aws_access_key_id (str): AWS account access key ID
        aws_secret_access_key (str): AWS account secret access key
        account_name (str): AWS account name in DSCC
    """
    regions_available = list(SA.ami.keys())
    logger.info(f"Searching for CFT stack: '{stack_name}'.")
    for region in regions_available:
        aws: AWS = AWS(
            region_name=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            account_name=account_name,
        )
        cf_stack = aws.cloud_formation.get_cf_stack(stack_name=stack_name)
        if cf_stack:
            logger.info(f"Deleting CFT stack: '{stack_name}'")
            aws.cloud_formation.delete_cf_stack(stack_name=stack_name)
    logger.info(f"Search for CFT stack: '{stack_name}' finished.")


def read_yaml_get_eks_cluster_info(yaml_file, need_asset_info=False):
    """
    this method reads the yaml file provided and returns cluster name and region from the metadata section.

    Args:
        yaml_file path (string): yaml file from where eks cluster name and region should be reading.

    Returns:
        string: EKS cluster name and cluster region or node groups info and cluster name based on need asset info flag
    """
    logger.info(f"Reading config data from {yaml_file} file started...")
    cluster_name = None
    cluster_aws_region = None
    try:
        with open(yaml_file, "r") as file:
            data = yaml.load(file, Loader=yaml.FullLoader)
            cluster_name = data["metadata"]["name"]
            cluster_aws_region = data["metadata"]["region"]
            node_groups_info = [node_group["name"] for node_group in data.get("managedNodeGroups", [])]
            logger.info(f"cluster name read from yaml file: {cluster_name}")
            logger.info(f"cluster aws region read from yaml file: {cluster_aws_region}")
        logger.info(f"Reading config data from {yaml_file} file is completed...")
    except FileNotFoundError as e:
        current_path = os.getcwd()
        logger.debug(f"Error: {e}. File tree: \n {list_file_tree_structure(current_path)}")
        raise
    if need_asset_info:
        logger.info(f"EKS node groups info: {node_groups_info}")
        return node_groups_info, cluster_name
    return cluster_name, cluster_aws_region


def read_yaml_get_cluster_version(yaml_file_path) -> str:
    """This method reads yaml file and returns cluster version

    Args:
        yaml_file_path (str): Path to the yaml file where ClusterConfig is included

    Returns:
        str: Cluster version
    """
    try:
        with open(yaml_file_path, "r") as file:
            # Read the YAML content from the file
            yaml_content = file.read()
    except FileNotFoundError as e:
        current_path = os.getcwd()
        logger.debug(f"Error: {e}. File tree: \n {list_file_tree_structure(current_path)}")
        raise

    # Parse the YAML data
    parsed_yaml = yaml.safe_load_all(yaml_content)

    # Iterate over the YAML documents
    for document in parsed_yaml:
        # Extract the nodegroup name value
        if document["kind"] == "ClusterConfig":
            metadata = document["metadata"]
            cluster_version = metadata["version"]
    return cluster_version


def read_yaml_get_namespace(yaml_file_path):
    """
    this method reads the yaml file provided and returns list of all namespaces in the yaml.

    Args:
        yaml_file path (string): path of the yaml file

    Returns:
        list of namespaces
    """
    try:
        with open(yaml_file_path, "r") as file:
            # Read the YAML content from the file
            yaml_content = file.read()
    except FileNotFoundError as e:
        current_path = os.getcwd()
        logger.debug(f"Error: {e}. File tree: \n {list_file_tree_structure(current_path)}")
        raise

    # Parse the YAML data
    parsed_yaml = yaml.safe_load_all(yaml_content)

    # Iterate over the YAML documents
    for document in parsed_yaml:
        # Extract the Namespace value
        if document["kind"] == "Namespace":
            metadata = document["metadata"]
            namespace = metadata["name"]
    return namespace


def read_yaml_get_nodegroup_name(yaml_file_path):
    try:
        with open(yaml_file_path, "r") as file:
            # Read the YAML content from the file
            yaml_content = file.read()
    except FileNotFoundError as e:
        current_path = os.getcwd()
        logger.debug(f"Error: {e}. File tree: \n {list_file_tree_structure(current_path)}")
        raise

    # Parse the YAML data
    parsed_yaml = yaml.safe_load_all(yaml_content)

    # Iterate over the YAML documents
    for document in parsed_yaml:
        # Extract the nodegroup name value
        if document["kind"] == "ClusterConfig":
            nodegroup_info = document["managedNodeGroups"][0]
            nodegroup_name = nodegroup_info["name"]
    return nodegroup_name


def read_yaml_get_metadata_name(yaml_file_path, kind_value: str):
    """
    this method reads the yaml file provided and returns list of all metadata name for kind value in the yaml.

    Args:
        yaml_file path (string): path of the yaml file
        kind_value (string): Value specified for kind in the yaml

    Returns:
        list of name(s) from metadata section of yaml
    """
    try:
        with open(yaml_file_path, "r") as file:
            # Read the YAML content from the file
            yaml_content = file.read()
    except FileNotFoundError as e:
        current_path = os.getcwd()
        logger.debug(f"Error: {e}. File tree: \n {list_file_tree_structure(current_path)}")
        raise

    # Parse the YAML data
    parsed_yaml = yaml.safe_load_all(yaml_content)
    metadata_name_list = []

    # Iterate over the YAML documents
    for document in parsed_yaml:
        # Extract the Namespace value
        if document["kind"] == kind_value:
            metadata = document["metadata"]
            metadata_name = metadata["name"]
            metadata_name_list.append(metadata_name)
    return metadata_name_list


def read_yaml_get_pvc(yaml_file_path):
    """
    this method reads the yaml file provided and returns list of all pvc in the yaml.

    Args:
        yaml_file path (string): path of the yaml file

    Returns:
        list of pvc
    """
    try:
        with open(yaml_file_path, "r") as file:
            # Read the YAML content from the file
            yaml_content = file.read()
    except FileNotFoundError as e:
        current_path = os.getcwd()
        logger.debug(f"Error: {e}. File tree: \n {list_file_tree_structure(current_path)}")
        raise

    # Parse the YAML data
    parsed_yaml = yaml.safe_load_all(yaml_content)
    pvcname_list = []

    # Iterate over the YAML documents
    for document in parsed_yaml:
        # Extract the Namespace value
        if document["kind"] == "PersistentVolumeClaim":
            metadata = document["metadata"]
            pvcname = metadata["name"]
            pvcname_list.append(pvcname)
    return pvcname_list


def read_yaml_get_storage_class(yaml_file_path):
    """
    this method reads the yaml file provided and returns list of all storage class in the yaml.

    Args:
        yaml_file path (string): path of the yaml file

    Returns:
        list: list of stroage class name
    """
    try:
        with open(yaml_file_path, "r") as file:
            # Read the YAML content from the file
            yaml_content = file.read()
    except FileNotFoundError as e:
        current_path = os.getcwd()
        logger.debug(f"Error: {e}. File tree: \n {list_file_tree_structure(current_path)}")
        raise

    # Parse the YAML data
    parsed_yaml = yaml.safe_load_all(yaml_content)
    scname_list = []

    # Iterate over the YAML documents
    for document in parsed_yaml:
        # Extract the Namespace value
        if document["kind"] == "StorageClass":
            metadata = document["metadata"]
            scname = metadata["name"]
            scname_list.append(scname)
    return scname_list


def read_yaml_get_deployment_name(yaml_file_path):
    """
    this method reads the yaml file provided and returns list of all deployment in the yaml.

    Args:
        yaml_file path (string): path of the yaml file

    Returns:
        list: list of stroage class name
    """
    try:
        with open(yaml_file_path, "r") as file:
            # Read the YAML content from the file
            yaml_content = file.read()
    except FileNotFoundError as e:
        current_path = os.getcwd()
        logger.debug(f"Error: {e}. File tree: \n {list_file_tree_structure(current_path)}")
        raise

    # Parse the YAML data
    parsed_yaml = yaml.safe_load_all(yaml_content)
    deployment_list = []

    # Iterate over the YAML documents
    for document in parsed_yaml:
        # Extract the Namespace value
        if document["kind"] == "Deployment":
            metadata = document["metadata"]
            deployment_name = metadata["name"]
            deployment_list.append(deployment_name)
    return deployment_list


def read_yaml_get_service_name(yaml_file_path):
    """
    this method reads the yaml file provided and returns list of all services in the yaml.

    Args:
        yaml_file path (string): path of the yaml file

    Returns:
        list: list of service name
    """
    try:
        with open(yaml_file_path, "r") as file:
            # Read the YAML content from the file
            yaml_content = file.read()
    except FileNotFoundError as e:
        current_path = os.getcwd()
        logger.debug(f"Error: {e}. File tree: \n {list_file_tree_structure(current_path)}")
        raise

    # Parse the YAML data
    parsed_yaml = yaml.safe_load_all(yaml_content)
    service_list = []

    # Iterate over the YAML documents
    for document in parsed_yaml:
        # Extract the Namespace value
        if document["kind"] == "Service":
            metadata = document["metadata"]
            service_name = metadata["name"]
            service_list.append(service_name)
    return service_list


def get_list_specific_cls_filter(csp_account_id: str, csp_cluster_name: str, aws_region: str):
    """Get a filter to list specific cluster based on the provided account id and cluster name and region

    Args:
        csp_account_id (str): csp AWS account id
        csp_cluster_name (str): csp EKS cluster name
        aws_region (str): EKS cluster region

    Returns:
        string: Returns filter string
    """
    filter_str = (
        f"accountId eq '{csp_account_id}' and name eq '{csp_cluster_name}' and cspInfo.region eq '{aws_region}'"
    )
    filter_string = []
    filter_string.append(filter_str)
    return filter_string


def verify_and_delete_cft_stacks(aws_session, cft_client, stack_list: list = []):
    """Verify cloud formation stack, if available deletes the stack from AWS

    Args:
        aws_session (AWS): AWS session object
        stack_list (list, optional): list of stack names to delete from AWS account. Defaults to [].
    """
    assert len(stack_list), f"Empty stack list: {stack_list}"
    logger.info(f"Stack list: {stack_list}")
    for stack_name in stack_list:
        cf_stack = aws_session.cloud_formation.get_cf_stack(stack_name=stack_name)
        if cf_stack:
            cluster_stack_pattern = re.compile(r"eksctl-eks-cluster\d*-cluster")
            if re.fullmatch(cluster_stack_pattern, stack_name):
                resources = cft_client.get_stack_resources(stack_name)["StackResourceSummaries"]
                vpc_id = [
                    resource["PhysicalResourceId"] for resource in resources if resource["LogicalResourceId"] == "VPC"
                ][0]
                delete_eks_cluster_cft_stack(stack_name, aws_session, vpc_id)
            else:
                logger.info(f"Deleting EKS cluster CF stack: '{stack_name}'")
                aws_session.cloud_formation.delete_cf_stack(stack_name=stack_name)
                logger.info(f"Successfully deleted EKS cluster CF stack: '{stack_name}'")
            if "nodegroup" in cf_stack["StackName"]:
                wait_for_cft = 300
                logger.info(f"Waiting {wait_for_cft} seconds after CFT stack deletion (node groups).")
                time.sleep(wait_for_cft)
            cf_stack_after_deletion = cf_stack = aws_session.cloud_formation.get_cf_stack(stack_name=stack_name)
            assert not cf_stack_after_deletion, "EKS cluster CF stack still exists after deletion."


def delete_eks_cluster_cft_stack(stack_name: str, aws_session, vpc_id):
    try:
        aws_session.cloud_formation.delete_cf_stack(stack_name=stack_name)
        logger.info(f"Successfully deleted EKS cluster CF stack: '{stack_name}'")
    except exceptions.WaiterError as error:
        if f"DELETE_FAILED in {str(error)}":
            aws_session.security_group.delete_all_sgs_in_vpc(vpc_id)
            aws_session.vpc.delete_vpc(vpc_id)
            aws_session.cloud_formation.delete_cf_stack(stack_name=stack_name)
            logger.info(f"Successfully deleted EKS cluster CF stack: '{stack_name}'")
        else:
            raise error


def get_eks_cluster_stack_info(cluster_config_yaml, need_asset_info=True):
    """get EKS cluster cloud formation stack information

    Args:
        cluster_config_yaml (str): EKS cluster config yaml file
        need_asset_info (bool, optional): Asset info of EKS cluster, e.g cluster name and node group . Defaults to True.

    Returns:
        stack list: list of stack name
    """
    (node_groups_info, cluster_name) = read_yaml_get_eks_cluster_info(
        cluster_config_yaml, need_asset_info=need_asset_info
    )
    stack_list = []
    for node_group in node_groups_info:
        stack_list.append(f"eksctl-{cluster_name}-nodegroup-{node_group}")
    stack_list.append(f"eksctl-{cluster_name}-cluster")
    logger.info(f"EKS cluster stack list: {stack_list}")
    return stack_list


def get_eks_k8s_cluster_app_details(context: Context, k8s_cluster_id, app_name) -> CSPK8sApplicationModel:
    """This step gets the k8s app details

    Args:
        context (Context): Test Context Object
        k8s_cluster_id (_type_): Cluster ID from where user want to fetch app
        app_name (_type_): k8s app name

    Returns:
        CSPK8sApplicationModel: Details of a specified K8s application
    """
    app_id = get_eks_k8s_cluster_app_by_name(
        context,
        context.eks_cluster_name,
        context.eks_cluster_aws_region,
        app_name,
    )
    logger.debug("Getting k8s application details... ")
    app_details: CSPK8sApplicationModel = context.eks_inventory_manager.get_k8s_app_by_id(k8s_cluster_id, app_id)
    return app_details


def install_snapshotter():
    """This function to install snapshotter if it does not exist in current directory

    Args:
        none

    Returns:
        none
    """
    logging.info("Installing snapshotter...")
    if not os.path.isdir("external-snapshotter"):
        clone_repo_command = [
            "git",
            "clone",
            "https://github.com/kubernetes-csi/external-snapshotter",
        ]
        run_ctl_command(clone_repo_command)
        os.chdir("external-snapshotter")
        checkout_branch_command = [
            "git",
            "checkout",
            "tags/v6.2.1",
            "-b",
            "release-6.0",
        ]
    else:
        os.chdir("external-snapshotter")
        checkout_branch_command = ["git", "checkout", "release-6.0"]
    run_ctl_command(checkout_branch_command)
    try:
        ps = subprocess.Popen(("kubectl", "kustomize", "client/config/crd"), stdout=subprocess.PIPE)
        subprocess.check_output(("kubectl", "create", "-f-"), stdin=ps.stdout, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as error:
        if "already exists" in str(error.output):
            logger.warning("Client config already configured...")
        else:
            raise error
    try:
        ps = subprocess.Popen(
            (
                "kubectl",
                "-n",
                "kube-system",
                "kustomize",
                "deploy/kubernetes/snapshot-controller",
            ),
            stdout=subprocess.PIPE,
        )
        subprocess.check_output(("kubectl", "create", "-f-"), stdin=ps.stdout)
    except subprocess.CalledProcessError as error:
        if "already exists" in str(error.output):
            logger.warning("Snapshot-controller already configured...")
        else:
            raise error
    os.chdir("..")


def create_cluster(aws_session, cluster_name, cluster_config_yaml, cluster_timeout):
    """This function to create cluster and validate upon creation

    Args:
        aws_session (AWS): AWS session object
        cluster_name (string): Cluster name to be created
        cluster_config_yaml: yaml filepath which has cluster configuration
        cluster_timeout (int): timeout for the cluster creation

    Returns:

    """
    create_cluster_command = ["eksctl", "create", "cluster", "-f", cluster_config_yaml]
    logger.info(f"Creating EKS cluster based on the config file: {cluster_config_yaml}")
    is_cluster_command_executed = run_ctl_command(create_cluster_command, timeout=cluster_timeout)
    if is_cluster_command_executed:
        logger.info("Cluster creation command execution is successful")
        available_cluster_list = aws_session.eks.get_eks_clusters()
        assert (
            cluster_name in available_cluster_list["clusters"]
        ), f"Cluster {cluster_name} creation is un-successful available in the list: {available_cluster_list['clusters']}"
        logger.info(f"Successfully created cluster: {cluster_name}")
    else:
        assert is_cluster_command_executed, "EKS cluster creation failed..."


def log_kube_configs():
    initial_path = os.getcwd()
    path = "/root/.kube"
    os.chdir(path)
    config_files = ["eks.crt", "config"]
    dir_content = os.listdir()
    logger.debug(f"Directory '{path}' content: {dir_content}")
    for item in dir_content:
        if item in config_files:
            item_path = os.path.join(path, item)
            with open(item_path, "r") as file:
                logger.debug(f"File '{item}' content: {file.read()}")
    os.chdir(initial_path)


def deploy_storage_class(storage_class_yaml):
    deploy_storage_class_command = ["kubectl", "apply", "-f", storage_class_yaml]
    logger.info("Deploying storage class...")
    deploy_sc = run_ctl_command(deploy_storage_class_command)
    assert deploy_sc, "Failed to deploy storage class"
    logger.info("Successfully created storage class")


@retry(reraise=True, stop=stop_after_attempt(3), wait=wait_fixed(5))
def create_oidc(aws_session, cluster_name, cluster_region):
    """This function to create OIDC and validate upon creation

    Args:
        aws_session (AWS): AWS session object
        cluster_name (string): Cluster name to be created
        cluster_region: Region where cluster to be created

    Returns:

    """
    logging.info("Associating OIDC provider")
    create_oidc_cmd = [
        "eksctl",
        "utils",
        "associate-iam-oidc-provider",
        "--cluster",
        cluster_name,
        "--approve",
        "--region",
        cluster_region,
    ]
    is_create_oidc_command_executed = run_ctl_command(create_oidc_cmd)
    result = False
    if is_create_oidc_command_executed:
        logger.info("Create oidc command execution is successful")
        oidc_arns_list = aws_session.iam.get_oidc_list()
        arns_with_cluster_region = any(cluster_region in arn for arn in oidc_arns_list)
        if arns_with_cluster_region:
            for arn in oidc_arns_list:
                arn_tags = aws_session.iam.get_oidc_tags_by_arn(arn)
                for arn_tag in arn_tags:
                    if arn_tag.Value == cluster_name:
                        result = True
            assert result, f"OIDC creation for cluster name {cluster_name} is NOT successful"
            logger.info(f"Successfully created oidc: {cluster_name}")
        else:
            assert arns_with_cluster_region, f"OIDC does not exist for region {cluster_region}"
    else:
        assert is_create_oidc_command_executed, "Create OIDC command execution failed..."


def create_ebs_role(
    aws_session,
    cluster_name: str,
    cluster_region: str,
    role_name: str,
    context: Context,
):
    """This function to create EBS role and validate upon creation

    Args:
        aws_session (AWS): AWS session object
        cluster_name (string): Cluster name to be created
        cluster_region (string): Region where cluster to be created
        role_name (string): EBS role name to be created
    Returns:

    """
    ebs_policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy"
    ebs_roles_list = aws_session.iam.get_roles()
    ebs_role_exists = any(role_name == role for role in ebs_roles_list)
    if ebs_role_exists:
        logging.info("Deleting EBS role...")
        aws_session.iam.detach_policy_from_role(role_name, ebs_policy_arn)
        aws_session.iam.delete_iam_role(role_name)
    logging.info("Creating EBS role...")
    ebs_csi_iam_role_cmd = [
        "eksctl",
        "create",
        "iamserviceaccount",
        "--name",
        "ebs-csi-controller-sa",
        "--namespace",
        "kube-system",
        "--cluster",
        cluster_name,
        "--role-name",
        role_name,
        "--role-only",
        "--attach-policy-arn",
        "arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy",
        "--approve",
        "--region",
        cluster_region,
    ]
    is_ebs_role_command_executed = run_ctl_command(ebs_csi_iam_role_cmd)
    if is_ebs_role_command_executed:
        ebs_roles_list = aws_session.iam.get_roles()
        ebs_role_exists = any(role_name in role for role in ebs_roles_list)
        assert ebs_role_exists, f"EBS role {role_name} does not exist which is not as expected"
        logger.info(f"Successfully created EBS service account with role name {role_name}")
    else:
        assert is_ebs_role_command_executed, "Create EBS IAM role command execution failed..."


def create_efs_role(
    aws_session,
    cluster_name: str,
    cluster_region: str,
    role_name,
    context: Context,
):
    """This function to create EFS role and validate upon creation

    Args:
        aws_session (AWS): AWS session object
        cluster_name (string): Cluster name to be created
        cluster_region (string): Region where cluster to be created
        role_name (string): EFS role name to be created
    Returns:

    """
    # Deleting IAM role and iamserviceaccount
    # Adding this step as create role command is failing if kube-system/efs-csi-controller-sa sa already exists.
    del_iamserviceacc_cmd = [
        "eksctl",
        "delete",
        "iamserviceaccount",
        "--name",
        "efs-csi-controller-sa",
        "--namespace",
        "kube-system",
        "--cluster",
        cluster_name,
        "--region",
        cluster_region,
    ]
    is_del_iamserviceacc_cmd_executed = run_ctl_command(del_iamserviceacc_cmd)
    assert is_del_iamserviceacc_cmd_executed, f"deletion of IAM role or serviceaccount failed"

    efs_policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy"
    efs_roles_list = aws_session.iam.get_roles()
    efs_role_exists = any(role_name == role for role in efs_roles_list)
    if efs_role_exists:
        logging.info("Deleting EFS role...")
        aws_session.iam.detach_policy_from_role(role_name, efs_policy_arn)
        aws_session.iam.delete_iam_role(role_name)

    logging.info("Creating EFS role...")
    efs_csi_iam_role_cmd = [
        "eksctl",
        "create",
        "iamserviceaccount",
        "--name",
        "efs-csi-controller-sa",
        "--namespace",
        "kube-system",
        "--cluster",
        cluster_name,
        "--role-name",
        role_name,
        "--role-only",
        "--attach-policy-arn",
        "arn:aws:iam::aws:policy/service-role/AmazonEFSCSIDriverPolicy",
        "--approve",
        "--region",
        cluster_region,
    ]
    is_efs_role_command_executed = run_ctl_command(efs_csi_iam_role_cmd, kubectl_command=True)

    if is_efs_role_command_executed:
        efs_roles_list = aws_session.iam.get_roles()
        efs_role_exists = any(role_name in role for role in efs_roles_list)
        assert efs_role_exists, f"EFS role {role_name} does not exist which is not as expected"
        logger.info(f"Successfully created EFS service account with role name {role_name}")
    else:
        assert is_efs_role_command_executed, "Create EFS IAM role command execution failed..."


def deploy_application_on_eks_cluster(
    context: Context,
    cluster_name,
    cluster_region,
    app_config_yaml,
    app_timeout,
):
    """This function to deploy the application given in yaml configuration and
     validate namespace,PVC,Storage class, services and deployment upon creation

    Args:
        context (Context): Test Context Object
        cluster_name (string): Name of the EKS cluster
        cluster_region (string): AWS region name
        app_config_yaml (str): yaml file path to create eks application
        app_timeout : Time to ececute the command
    Returns:

    """
    verify_and_set_eks_cluster_context(
        cluster_name,
        cluster_region,
        aws_eks_iam_user_name=context.aws_eks_iam_user_name,
    )
    kubectl_command = ["kubectl", "apply", "-f", app_config_yaml]
    logger.info(f"Deploying application based on the config file: {app_config_yaml}")
    is_app_deployed_command_executed = run_ctl_command(kubectl_command, timeout=app_timeout)
    if is_app_deployed_command_executed:
        k8s_client = K8SClient.KubernetesClient()

        # Retrieve data from yaml
        ns_name = read_yaml_get_metadata_name(app_config_yaml, kind_value="Namespace")
        pvc_name = read_yaml_get_metadata_name(app_config_yaml, kind_value="PersistentVolumeClaim")
        sc_name = read_yaml_get_metadata_name(app_config_yaml, kind_value="StorageClass")
        dplmt_name = read_yaml_get_metadata_name(app_config_yaml, kind_value="Deployment")
        service_name = read_yaml_get_metadata_name(app_config_yaml, kind_value="Service")
        config_map_name = read_yaml_get_metadata_name(app_config_yaml, kind_value="ConfigMap")
        cluster_role_name = read_yaml_get_metadata_name(app_config_yaml, kind_value="ClusterRole")
        crb_name = read_yaml_get_metadata_name(app_config_yaml, kind_value="ClusterRoleBinding")

        # Validate name space deployed
        if ns_name:
            expected_ns_name = ns_name[0]
            ns_list = k8s_client.get_namespaces()
            ns_list_items = ns_list.items
            ns_name_list = [
                ns_list_value.metadata.labels
                for ns_list_value in ns_list_items
                if expected_ns_name in ns_list_value.metadata.labels.values()
            ]
            assert len(ns_name_list) > 0, f"Name space {expected_ns_name} does not exist "
            logger.info(f"Successfully name space {expected_ns_name} validated {expected_ns_name}")

        # Validate PVC
        if pvc_name:
            expected_pvc_name = pvc_name[0]
            pvc_list = k8s_client.get_persistent_volume_claim_for_all_namespace()
            pvc_list_items = pvc_list.items
            pvc_name_list = [
                pvc_name_items.metadata.name
                for pvc_name_items in pvc_list_items
                if pvc_name_items.metadata.name == expected_pvc_name
            ]
            assert len(pvc_name_list) > 0, f"Persistent volume claim {expected_pvc_name} does not exist "
            logger.info(f"Successfully PVC {expected_pvc_name} validated with the namespace {expected_ns_name}")

        # Validate storage class
        if sc_name:
            expected_sc_name = sc_name[0]
            storage_class_list = k8s_client.get_eks_storage_class(expected_ns_name)
            sc_list_items = storage_class_list.items
            sc_name_list = [
                sc_name_items.metadata.name
                for sc_name_items in sc_list_items
                if sc_name_items.metadata.name == expected_sc_name
            ]
            assert len(sc_name_list) > 0, f"Storage class {expected_sc_name} does not exist "
            logger.info(
                f"Successfully Storage class {expected_sc_name} validated with the namespace {expected_sc_name}"
            )

        # Validate deployment
        if dplmt_name:
            expected_dplmt_name = dplmt_name[0]
            deployments_list = k8s_client.get_eks_deployments_namespace(expected_ns_name)
            dplmt_list_items = deployments_list.items
            dplmt_name_list = [
                dplmt_name_items.metadata.name
                for dplmt_name_items in dplmt_list_items
                if dplmt_name_items.metadata.name == expected_dplmt_name
            ]
            assert len(dplmt_name_list) > 0, f"Deployment name {expected_dplmt_name} does not exist "
            logger.info(
                f"Successfully deployment name {expected_dplmt_name} validated with the namespace {expected_dplmt_name}"
            )

        # Validate service
        if service_name:
            expected_service_name = service_name[0]
            service_list = k8s_client.get_eks_service_namespace(expected_ns_name)
            service_list_items = service_list.items
            service_name_list = [
                service_name_items.metadata.name
                for service_name_items in service_list_items
                if service_name_items.metadata.name == expected_service_name
            ]
            assert len(service_name_list) > 0, f"EKS service name {expected_service_name} does not exist "
            logger.info(
                f"Successfully services {expected_service_name} are validated for the namespace {expected_ns_name}"
            )

        # Validate configMap
        if config_map_name:
            expected_config_map_name = config_map_name[0]
            config_map_list = k8s_client.get_eks_namespaced_config_map(expected_ns_name)
            config_map_list_items = config_map_list.items
            config_map_name_list = [
                config_map_name_items.metadata.name
                for config_map_name_items in config_map_list_items
                if config_map_name_items.metadata.name == expected_config_map_name
            ]
            assert len(config_map_name_list) > 0, f"EKS configMap name {expected_config_map_name} does not exist "
            logger.info(f"ConfigMap {expected_config_map_name} are validated for the namespace {expected_ns_name}")

        # Validate clusterRole
        if cluster_role_name:
            expected_cluster_role_name = cluster_role_name[0]
            cluster_role_list = k8s_client.get_eks_cluster_role()
            cluster_role_list_items = cluster_role_list.items
            cluster_role_name_list = [
                cluster_role_name_items.metadata.name
                for cluster_role_name_items in cluster_role_list_items
                if cluster_role_name_items.metadata.name == expected_cluster_role_name
            ]
            assert len(cluster_role_name_list) > 0, f"EKS clusterRole name {expected_cluster_role_name} does not exist "
            logger.info(f"ClusterRole {expected_cluster_role_name} is validated.")

        # Validate clusterRoleBinding
        if crb_name:
            expected_crb_name = crb_name[0]
            crb_list = k8s_client.get_eks_cluster_role_binding()
            crb_items = crb_list.items
            crb_name_list = [
                crb_name_items.metadata.name
                for crb_name_items in crb_items
                if crb_name_items.metadata.name == expected_crb_name
            ]
            assert len(crb_name_list) > 0, f"EKS cluster role binding name {expected_crb_name} does not exist "
            logger.info(f"cluster role binding  {expected_crb_name} is validated.")

    else:
        assert is_app_deployed_command_executed, "Deploy application command execution failed..."


def validate_eks_namespace(
    kubernetes_client: K8SClient,
    expected_namespace_name: str = None,
) -> bool:
    """
    This function retrieve the eks workload resources namespace. Return true or false if expected resource exist

    Args:
        kubernetes_client: Instance of the kubernetes client
        expected_namespace_name (string): Mandatory to get all the resources for the given namespace

    Returns:
    true or false (bool): return true if expected eks workload source is available
    """
    ns_list = kubernetes_client.get_namespaces()
    ns_list_items = ns_list.items
    ns_name_list = [
        ns_list_value.metadata.name
        for ns_list_value in ns_list_items
        if ns_list_value.metadata.name == expected_namespace_name
    ]
    if len(ns_name_list) > 0:
        logger.info(f"Successfully validated eks namespace workload name {expected_namespace_name}")
        return True
    return False


def validate_eks_deployment_in_ns(
    namespace_name: str,
    expected_dplmt_name: str,
    kubernetes_client: K8SClient,
) -> bool:
    """
    This function retrieve the eks workload resource deployment in given namespace.
    Return true or false if expected resource exist

    Args:
        namespace_name (string): Deployed namespace name
        expected_dplmt_name (string): Expected deployment name for the given namespace
        kubernetes_client: Kubernetes client instance
    Returns:
    true or false (bool): return true if expected eks workload source is available
    """
    deployments_list = kubernetes_client.get_eks_deployments_namespace(namespace_name)
    dplmt_list_items = deployments_list.items
    dplmt_name_list = [
        dplmt_name_items.metadata.name
        for dplmt_name_items in dplmt_list_items
        if dplmt_name_items.metadata.name == expected_dplmt_name
    ]
    if len(dplmt_name_list) > 0:
        logger.info(f"Successfully validated deployment {dplmt_name_list[0]} for the namespace {namespace_name}")
        return True
    return False


def validate_eks_services_in_ns(
    namespace_name: str,
    expected_service_name: str,
    kubernetes_client: K8SClient,
) -> bool:
    """
    This function retrieve the eks workload resource Services in given namespace.
    Return true or false if expected resource exist

    Args:
        namespace_name (string): Deployed namespace name
        expected_service_name (string): Expected service name for the given namespace
        kubernetes_client: Kubernetes client instance
    Returns:
    true or false (bool): return true if expected eks workload source is available
    """
    service_list = kubernetes_client.get_eks_service_namespace(namespace_name)
    service_list_items = service_list.items
    service_name_list = [
        service_name_items.metadata.name
        for service_name_items in service_list_items
        if service_name_items.metadata.name == expected_service_name
    ]
    if len(service_name_list) > 0:
        logger.info(f"Successfully services {service_name_list[0]} are validated for the namespace {namespace_name}")
        return True
    return False


def validate_eks_pod_in_ns(
    namespace_name: str,
    kubernetes_client: K8SClient,
) -> bool:
    """
    This function retrieve the eks workload resource pods in given namespace and pod in Running status
    Return true or false if expected resource exist

    Args:
        namespace_name (string): Deployed namespace name
        kubernetes_client: Kubernetes client instance
    Returns:
    true or false (bool): return true if expected eks workload source is available
    """
    pods_list = kubernetes_client.get_k8s_list_pods_namespace(namespace_name)
    pod_list_items = pods_list.items
    pod_name_list = [
        pod_name_items.metadata.name
        for pod_name_items in pod_list_items
        if pod_name_items.metadata.namespace == namespace_name and pod_name_items.status.phase == "Running"
    ]
    if len(pod_name_list) > 0:
        logger.info(
            f"Successfully pod name {pod_name_list[0]} and running status and validated for the namespace {namespace_name}"
        )
        return True
    return False


def validate_eks_replicaset_in_ns(
    namespace_name: str,
    kubernetes_client: K8SClient,
) -> bool:
    """
    This function retrieve the eks workload resource replicaset in given namespace
    Return true or false if expected resource exist

    Args:
        namespace_name (string): Deployed namespace name
        kubernetes_client: Kubernetes client instance
    Returns:
    true or false (bool): return true if expected eks workload source is available
    """
    replica_list = kubernetes_client.get_k8s_list_replicaset_namespace(namespace_name)
    replica_list_items = replica_list.items
    replica_name_list = [
        replica_name_items.metadata.name
        for replica_name_items in replica_list_items
        if replica_name_items.metadata.namespace == namespace_name
    ]
    if len(replica_name_list) > 0:
        logger.info(
            f"Successfully replica set name {replica_name_list[0]} validated for the namespace {namespace_name}"
        )
        return True
    return False


def delete_eks_services_in_ns(
    namespace_name: str,
    expected_service_name: str,
    kubernetes_client: K8SClient,
) -> bool:
    """
    This function delete the eks workload resource services in given namespace.
    Return true or false if expected resource exist

    Args:
        namespace_name (string): Deployed namespace name
        expected_service_name (string): Expected service name for the given namespace
        kubernetes_client: Kubernetes client instance
    Returns:
    true or false (bool): return true if expected eks workload source is available
    """

    service_exists = validate_eks_services_in_ns(namespace_name, expected_service_name, kubernetes_client)
    assert service_exists, f"Service name {expected_service_name} does not exist "
    logger.info(f"Successfully validated service {expected_service_name} for the namespace {namespace_name}")

    if service_exists:
        kubernetes_client.delete_k8s_service_namespace(namespace_name)
        return True
    return False


def create_csi_driver_add_on(
    aws_session, account_id, cluster_name, cluster_region, app_timeout, role_name, driver_name
):
    """This function creates the specified CSI driver addon and validates upon creation

    Args:
        aws_session (AWS): AWS session object
        account_id (string): AWS account ID
        cluster_name (string): Cluster name to be created
        cluster_region (string): Region where cluster to be created
        app_timeout : Time to execute the command
        role_name (string): CSI driver role name to be created
        driver_name (string): CSI driver name
    Returns:

    """
    eksctl_command = [
        "eksctl",
        "create",
        "addon",
        "--name",
        driver_name,
        "--cluster",
        cluster_name,
        "--service-account-role-arn",
        f"arn:aws:iam::{account_id}:role/{role_name}",
        "--force",
        "--region",
        cluster_region,
    ]
    logger.info(f"Creating {driver_name} CSI driver...")
    is_driver_deploy_command_executed = run_ctl_command(eksctl_command, app_timeout)
    if is_driver_deploy_command_executed:
        csi_addon_list = aws_session.eks.get_eks_addons(eks_cluster_name=cluster_name)
        assert csi_addon_list["addons"][0] == driver_name, f"Driver add on {driver_name} does not exist "
    else:
        assert is_driver_deploy_command_executed, f"Failed to deploy CSI driver {driver_name}"
        logger.info("CSI driver deployed")


def delete_app(cluster_name, cluster_region, aws_eks_iam_user_name, app_config_yaml, app_timeout):
    """
    This method will delete the EKS application with the provided yaml file
    cluster_name (str): Name of the EKS cluster
    cluster_region (str): EKS cluster region
    aws_iam_username (str): iam username.
    app_config_yaml (string): provide app yaml file
    app_timeout (int): time out value for this action
    """
    verify_and_set_eks_cluster_context(cluster_name, cluster_region, aws_eks_iam_user_name)
    kubectl_command = ["kubectl", "delete", "-f", app_config_yaml]
    logger.info(f"Deleting application based on the config file: {app_config_yaml}")
    app_deleted = run_ctl_command(kubectl_command, timeout=app_timeout)
    assert app_deleted, "Failed to delete the application..."
    app_namespace = read_yaml_get_namespace(app_config_yaml)
    kubernetes_client = K8SClient.KubernetesClient()
    namespaces = kubernetes_client.get_namespaces().items
    assert not any(
        [namespace.metadata.name == app_namespace for namespace in namespaces]
    ), "Failed to delete app namespace after app deletion,"
    logger.info("Successfully deleted the application")


def cleanup_cft_stack_in_aws_account(context: Context, aws_session, stack_name):
    """This step method deletes CFT stack file from the give aws account

    Args:
        context (Context): Context Object
        aws_session (AWS): AWS session in which region this stack file need to be cleanedup.
        stack_name (string): Name of the CFT stack file to cleanup.
    """
    aws_session_for_deletion = aws_session if aws_session else context.aws_eks
    logger.info(f"Getting the CFT file {stack_name}...")
    cf_stack = aws_session_for_deletion.cloud_formation.get_cf_stack(stack_name=stack_name)
    if cf_stack:
        logger.info(f"Cleanup of CFT stack: {stack_name} started...")
        aws_session_for_deletion.cloud_formation.delete_cf_stack(stack_name=stack_name)
        logger.info(f"Cleanup of CFT stack {stack_name} is successful..")
    else:
        logger.info(f"There is no CFT stack available with name: {stack_name} on AWS...")


def perform_eks_test_cleanup(
    context: Context,
    cluster_config_yaml=None,
    eks_cluster_name=None,
    eks_cluster_aws_region=None,
    app_yaml_list: list[str] = [],
    cleanup_application=False,
    app_timeout=300,
    cleanup_aws_account=True,
    account_name=None,
    unregister_cluster=False,
    protection_policy=False,
    cleanup_cft_from_aws=False,
    aws_session: AWS = None,
    stack_name: str = "api-stack",
):
    """This step is to perform cleanup in eks tests
    Args:
        context (Context): Test Context Object
        eks_cluster_name (string): user has to provide eks cluster name to be cleaned up if not it will be picked from context object.
        eks_cluster_aws_region (string): user has to provide the eks cluster aws region if not it will be picked from context object.
        app_yaml_list (list): user has to provide list of app_yaml to read the application name.
        cleanup_application (boolean): if user wants to cleanup the application then provide True if not application will not be deleted.
        app_time_out (int): by default to cleanup the app we are setting a timeout of 300 seconds.
        cleanup_aws_account (boolean): if user wants do not want to unregister the AWS account registered in the DSCC then provide False otherwise by default aws account will be unregistered.
        unregister_cluster (boolean): if user wants to unregister the cluster then user has to provide True otherwise this method will not unregister the cluster.
        protection_policy (boolean): Delete native and cloud backup for all the k8 applications and delete protection policy
    Returns:
        Returns nothing.
    """
    # getting all the required data before going for the cleanup.
    logger.info("Started performing EKS test cleanup...")
    if eks_cluster_name is None:
        eks_cluster_name = context.eks_cluster_name
    if eks_cluster_aws_region is None:
        eks_cluster_aws_region = context.eks_cluster_aws_region

    csp_account: CSPAccountModel = CAMSteps.get_csp_account_by_csp_name(
        context, account_name=context.aws_eks_account_name
    )

    cluster_info = EKSInvSteps.get_csp_k8s_cluster_by_name(context, eks_cluster_name, eks_cluster_aws_region)
    cluster_id = cluster_info.id

    if protection_policy:
        protection_policy_name = ""
        # Get apps from DSCC
        apps_list = context.eks_inventory_manager.get_csp_k8s_applications(cluster_id)
        logger.debug(f"Namespaced apps list: {apps_list}")
        dscc_app_names = [app.name for app in apps_list.items if app.name != "default"]
        logger.info(f"Namespaced apps list from DSCC: {dscc_app_names}")
        for app_name in dscc_app_names:
            app_info = get_eks_k8s_cluster_app_info_by_name(context, cluster_id, app_name)
            if len(app_info.protection_job_info) > 0:
                protection_policy_name = app_info.protection_job_info[0].protection_policy_info.name
            native_backup_count = EKSBackupSteps.get_k8s_app_backup_count(
                context, app_info.id, CSPBackupType.NATIVE_BACKUP
            )
            cloud_backup_count = EKSBackupSteps.get_k8s_app_backup_count(
                context, app_info.id, CSPBackupType.HPE_CLOUD_BACKUP
            )

            logger.info(
                f"Performing cleanup on the cluster with ID: {cluster_id} and app name: {app_name} and app id: {app_info.id}"
            )
            logger.info(f"Number of Native backup found on the cluster: {native_backup_count}")
            logger.info(f"Number of Cloud backup found on the cluster: {cloud_backup_count}")

            # 1. verify backup all if exists delete all.
            if (native_backup_count + cloud_backup_count) > 0:
                EKSBackupSteps.delete_all_k8s_apps_backups(
                    context=context,
                    csp_k8s_application_ids=[app_info.id],
                    csp_account=csp_account,
                    region=eks_cluster_aws_region,
                )
                logger.info(f"Deleted all the k8 app {app_name} backups successfully on the cluster {cluster_id}")
            else:
                logger.info(f"there are no backups on k8 app {app_name} to delete on the cluster {cluster_id}")

            # 2. verify protection job if exists unprotect it.
            # 3. verify policy if exists delete policy.
            if protection_policy_name == "":
                logger.info(
                    f"No protection policy assigned for the eks app {app_name} so skipping unassign protection policy as part of cleanup.."
                )
            else:
                logger.info(
                    f"Starting cleaningup of protection policy {protection_policy_name} for the eks app {app_name}"
                )
                EKSInvSteps.unassign_delete_protection_policy_for_eks_app(
                    context, app_name, protection_policy_name, cluster_id
                )
                logger.info(
                    f"Finished cleaningup of protection policy {protection_policy_name} for the eks app {app_name}"
                )

    # 4. delete application if user wants to delete that particular cluster
    if cleanup_application:
        for app_yaml in app_yaml_list:
            logger.info(f"Started cleanup of application in the AWS based on the yaml {app_yaml}")
            delete_app(
                eks_cluster_name,
                eks_cluster_aws_region,
                context.aws_eks_iam_user_name,
                app_yaml,
                app_timeout,
            )
            logger.info("Successfully deleted the application")

    # 5. unregister the cluster.
    if unregister_cluster:
        logger.info(f"Starting unregister of EKS cluster {cluster_id} and waiting untill the task gets finished")
        EKSInvSteps.perform_csp_k8s_cluster_unregister(
            context,
            eks_cluster_name,
            eks_cluster_aws_region,
            wait_for_task=True,
        )
        logger.info(f"Finished unregister of EKS cluster {cluster_id}")

    # 6. unregister AWS account.
    if cleanup_aws_account:
        logger.info("Started unregister of AWS account from DSCC...")
        if account_name is None:
            EKSInvSteps.unregister_csp_account(context)
        else:
            EKSInvSteps.unregister_csp_account(context=context, csp_account_name=account_name)
        logger.info("Successfully completed the unregister of AWS account from DSCC...")

    if cleanup_cft_from_aws:
        # if the user fail to provide aws_session then we are considering aws_eks as default session.
        cleanup_cft_stack_in_aws_account(context, aws_session, stack_name)
    logger.info("End of performing EKS test cleanup...")


def verify_standard_csp_account_eks_setup(
    context: Context,
    aws: AWS,
    account_id: str = "",
    account_name: str = "",
    reregister_account: bool = False,
    eks_cluster_name: str = "",
    eks_cluster_aws_region: str = "",
) -> str:
    """
    Verify account register in DSCC and existing EKS cluster, application setup

    Args:
        context (Context): Specify the context
        aws (AWS): AWS object
        account_id (str): AWS account name. Defaults to "".
        account_name (str): AWS account ID. Defaults to "".
        reregister_account (bool): Re-register the account. Defaults to False.
        eks_cluster_name (str): Name of the EKS cluster created during setup.
        eks_cluster_aws_region (str): EKS cluster created region.
    Returns:
        cluster ID (str): Registered clustered ID
    """
    if not account_id:
        account_id = context.aws_eks_account_id
    if not account_name:
        account_name = context.aws_eks_account_name

    csp_account_before = CAMSteps.get_csp_account_by_csp_name(context, account_name=account_name, is_found_assert=False)
    logger.info(f"Account already registered: {csp_account_before}")

    eks_discover_register_validate = False

    if reregister_account or not csp_account_before:
        logger.info(f"Test account will be registered: {account_name}, reregister: {reregister_account}")

        CommonSteps.register_and_validate_csp_aws_account(
            context,
            context.aws_eks_account_id,
            context.aws_eks_account_name,
            refresh_timeout=500,
            stack_name=context.aws_eks_account_name,
        )

        eks_discover_register_validate = True
        csp_account = CAMSteps.get_csp_account_by_csp_name(context, account_name, is_found_assert=False)
        logger.info(
            f"Test account successfully registered as does not exist {csp_account_before} or reregistration {reregister_account} is requested"
        )

    if csp_account_before and csp_account_before.validationStatus != ValidationStatus.passed:
        logger.info(f"Test account will be registered: {account_name}, reregister: {reregister_account}")
        csp_account = CommonSteps.register_aws_account_step(context, account_name, account_id)

        CommonSteps.create_stack_with_cloud_formation_template(
            context=context,
            csp_account_id=csp_account.id,
            aws=aws,
            stack_name=context.aws_eks_account_name,
        )
        logger.info(f"Test stack created: {csp_account.id}")
        CommonSteps.validate_aws_account_step(context, csp_account.id)
        logger.info(f"Test account validated: {csp_account.id}")

        eks_discover_register_validate = True

        logger.info(
            f"Test account {csp_account_before} exist and successfully validated validation status is not passed"
        )

    if csp_account_before and csp_account_before.validationStatus == ValidationStatus.passed:
        csp_account = csp_account_before
        cluster_info = EKSInvSteps.get_csp_k8s_cluster_by_name(context, eks_cluster_name, eks_cluster_aws_region)

        if cluster_info.registration_status.value != "REGISTERED":
            # Register EKS cluster in DSCC
            EKSInvSteps.register_csp_k8s_cluster(
                context,
                context.eks_cluster_name,
                context.eks_cluster_aws_region,
            )
            # Validate EKS cluster in DSCC
            EKSInvSteps.validate_csp_k8s_cluster(context, context.eks_cluster_name, context.eks_cluster_aws_region)
            # perform on demand refresh
            EKSInvSteps.perform_eks_inventory_refresh(context, context.aws_eks_account_name)
            # List the applications in DSCC and match with DSCC vs AWS
            EKSInvSteps.list_csp_k8s_applications_and_validate(context, cluster_info.id)

    logger.info(f"Test account {csp_account_before} exist also passed and cluster is successfully registered")

    if eks_discover_register_validate:
        # Discover and validate EKS cluster DSCC and AWS
        EKSInvSteps.cluster_discovery_and_validation(context)

        cluster_info = EKSInvSteps.get_csp_k8s_cluster_by_name(context, eks_cluster_name, eks_cluster_aws_region)

        # Register EKS cluster in DSCC
        EKSInvSteps.register_csp_k8s_cluster(
            context,
            context.eks_cluster_name,
            context.eks_cluster_aws_region,
        )

        # Validate EKS cluster in DSCC
        EKSInvSteps.validate_csp_k8s_cluster(context, context.eks_cluster_name, context.eks_cluster_aws_region)

        # perform on demand refresh
        EKSInvSteps.perform_eks_inventory_refresh(context, context.aws_eks_account_name)

        # List the applications in DSCC and match with DSCC vs AWS
        EKSInvSteps.list_csp_k8s_applications_and_validate(context, cluster_info.id)

        logger.info(f"Cluster {cluster_info.id} successfully registered and validated validated")

    context.csp_account_id_aws_one = csp_account.id
    logger.info(f"Test account: {csp_account.id}")
    return cluster_info.id


def upgrade_cluster_control_plane_version(
    context: Context,
    cluster_name: str,
    cluster_version: str,
    cluster_region: str,
    csp_account_name: str,
    aws_eks_session: str,
):
    """Trigger cluster control plane version upgrade without waiting for finish.

    Args:
        context (Context): context object
        cluster_name (str): name of the cluster the control plane will be upgraded
        cluster_version (str): version the cluster is upgraded to
        cluster_region (str): aws region where upgrading cluster is placed
        csp_account_name (str): csp account name the cluster is associated with
        aws_eks_session (str): aws session the cluster is assoicated with.
    Returns:
        str: update ID needed to track update status
    """

    update_id = aws_eks_session.eks.eks_client.update_cluster_version(name=cluster_name, version=cluster_version)[
        "update"
    ]["id"]
    wait_for_cluster_state(context, csp_account_name, cluster_name, cluster_region, "UPDATING")
    return update_id


@retry(reraise=True, stop=stop_after_delay(100), wait=wait_fixed(30))
def wait_for_cluster_state(
    context: Context,
    csp_account_name: str,
    cluster_name: str,
    cluster_region: str,
    expected_cluster_state: str,
):
    """Wait 2 minutes for specified cluster state with refresh inventory call in between retries.

    Args:
        context (Context): context object
        csp_account_name (str): ID of csp account
        cluster_name (str): name of the cluster the state is being verified
        cluster_region (str): aws region where cluster is placed
        expected_cluster_state (str): state of cluster the method is waiting for
    """
    EKSInvSteps.perform_eks_inventory_refresh(context, csp_account_name)
    cluster_info = EKSInvSteps.get_csp_k8s_cluster_by_name(context, cluster_name, cluster_region)
    assert (
        cluster_info.csp_info.state == expected_cluster_state
    ), f"Cluster state is not expected. Should be {expected_cluster_state} but was {cluster_info.csp_info.state}"


def upgrade_cluster_nodegroup(nodegroup_name: str, cluster_name: str, cluster_version: str, aws_session: AWS):
    """Upgrade cluster nodegroup to provided version.

    Args:
        nodegroup_name (str): Name of the nodegroup which will be upgraded
        cluster_name (str): Name of the cluster where nodegroup belong
        cluster_version (str): Cluster version nodegroups will be upgraded to
        aws_session (AWS): AWS session object
    """

    update_id = aws_session.eks.eks_client.update_nodegroup_version(
        clusterName=cluster_name, nodegroupName=nodegroup_name, version=cluster_version
    )["update"]["id"]
    wait_for_nodegroup_state(aws_session.eks.eks_client, cluster_name, nodegroup_name, "UPDATING")
    return update_id


@retry(reraise=True, stop=stop_after_delay(180), wait=wait_fixed(30))
def wait_for_nodegroup_state(
    eks_client,
    cluster_name: str,
    nodegroup_name: str,
    expected_cluster_state: str,
):
    """Wait 3 minutes for specified cluster state.

    Args:
        eks_client: AWS client
        cluster_name (str): name of the cluster the state is being verified
        nodegroup_name (str): nodegroup_name
        expected_cluster_state (str): state of cluster the method is waiting for
    """
    response = eks_client.describe_nodegroup(clusterName=cluster_name, nodegroupName=nodegroup_name)
    update_status = response["nodegroup"]["status"]
    assert (
        update_status == expected_cluster_state
    ), f"Nodegroup state is not expected. Should be {expected_cluster_state} but was {update_status}"


def verify_nodegroup_and_controlplane_version(context, cluster_name, cluster_region, cluster_nodegroup, aws_session):
    """Verify Cluster upgrade - matching the control plane version and nodegroup verion.

    Args:
        context (Context): context object
        cluster_name (str): Name of the cluster, whose control plane version is upgraded
        cluster_region (str): aws region where cluster is placed
        cluster_nodegroup (str): Name of the upgraded nodegroup
        aws_session (AWS): AWS session object
    """
    cluster_info = EKSInvSteps.get_csp_k8s_cluster_by_name(context, cluster_name, cluster_region)
    dscc_k8s_version = cluster_info.k8s_version
    nodegroup_info = aws_session.eks.describe_eks_nodegroup(cluster_name, cluster_nodegroup)
    nodegroup_version = nodegroup_info["nodegroup"]["version"]
    cluster_version = aws_session.eks.describe_eks_cluster(context.eks_cluster_name)["cluster"]["version"]
    assert (
        nodegroup_version == cluster_version and dscc_k8s_version == cluster_version
    ), f"Nodegroup version didn't match control plane version or DSCC k8s verion. Should be {cluster_version}, but was {nodegroup_info['nodegroup']['version']} or {dscc_k8s_version}"


@retry(reraise=True, stop=stop_after_attempt(4), wait=wait_fixed(20))
def update_cluster_default_addons(cluster_name: str, cluster_region, aws_eks_iam_user_name: str):
    """Updates cluster addons

    Args:
        cluster_name (str): Name of the cluster where updated addons belong
        cluster_region (str): The AWS region where the EKS cluster is located
        aws_eks_iam_user_name (str): The IAM user name associated with the AWS EKS cluster.
    """
    verify_and_set_eks_cluster_context(
        cluster_name,
        cluster_region,
        aws_eks_iam_user_name,
    )

    update_kube_proxy_command = [
        "eksctl",
        "utils",
        "update-kube-proxy",
        f"--cluster={cluster_name}",
        "--approve",
    ]
    update_aws_node_command = [
        "eksctl",
        "utils",
        "update-aws-node",
        f"--cluster={cluster_name}",
        "--approve",
    ]
    update_coredns_command = [
        "eksctl",
        "utils",
        "update-coredns",
        f"--cluster={cluster_name}",
        "--approve",
    ]
    update_kube_proxy = run_ctl_command(update_kube_proxy_command)
    assert update_kube_proxy, "Updating kube-proxy as addons upgrade step failed."
    update_aws_node = run_ctl_command(update_aws_node_command)
    assert update_aws_node, "Updating aws-node as addons upgrade step failed."
    update_coredns = run_ctl_command(update_coredns_command)
    assert update_coredns, "Updating coredns as addons upgrade step failed."


def verify_and_set_eks_cluster_context(cluster_name, cluster_region, aws_eks_iam_user_name="ekscli"):
    """Checks current cluster context if not matches, then set it to the appropriate cluster context

    Args:
        cluster_name (str): Name of the EKS cluster
        cluster_region (str): EKS cluster region
        aws_eks_iam_user_name (str, optional): iam username. Defaults to "ekscli".
    """
    kubernetes_client = K8SClient.KubernetesClient()
    cls_cntxt_name = f"{aws_eks_iam_user_name}@{cluster_name}.{cluster_region}.eksctl.io"
    command = ["kubectl", "config", "use-context", cls_cntxt_name]

    # Get available cluster context list
    contexts = kubernetes_client.get_available_cluster_contexts()
    context_found = 0
    for context in contexts:
        if context == cls_cntxt_name:
            context_found = 1
            # Get current cluster context
            current_context = kubernetes_client.get_current_cluster_context()
            if current_context == cls_cntxt_name:
                logger.info("Current cluster context is appropriate, no action required.")
                return
            else:
                context_found = 1
                logger.info("Current cluster context is not appropriate, need to switch the context.")
                switch_context = run_ctl_command(command, timeout=100)
                assert switch_context, "Failed to run the cluster context command"
                current_context = kubernetes_client.get_current_cluster_context()
                assert (
                    current_context == cls_cntxt_name
                ), f"Failed to switch the cluster context, current context set to: {current_context}"
                logger.info(f"Successfully switched the cluster context, to cluster: {cluster_name}")
                return
    assert context_found, f"Failed to find the associated cluster context for cluster: {cluster_name}"


def get_random_eks_version_and_region(exclude_eks_versions=[1.22], exclude_regions=[]) -> str:
    """Get random eks cluster version and the region

    Args:
        exclude_eks_versions (list, optional): exclude eks version. Defaults to [1.22].
        exclude_regions (list, optional): exclude region. Defaults to [].

    Returns:
        str: returns random eks cluster version and the region
    """
    # Get the eks cluster versions and aws regions from enum
    eks_versions = [version.value for version in list(EksClusterVersions)]
    aws_regions = [region.value for region in list(AWSRegionZone)]

    # Check if there are any eks versions and aws regions to be excluded
    available_eks_versions = [eks_version for eks_version in eks_versions if eks_version not in exclude_eks_versions]
    available_regions = [region for region in aws_regions if region not in exclude_regions]
    random_eks_version = random.choice(available_eks_versions)
    random_region = random.choice(available_regions)
    logger.info(f"Picked up EKS cluster version as: {random_eks_version} and region as {random_region}")

    return random_eks_version, random_region


def update_eks_cluster_config_yaml(file_path, updated_path, new_eks_version, new_region):
    """Update cluster config yaml with eks cluster version and region

    Args:
        file_path (str): cluster config yaml path
        updated_file_path (str): updated cluster config yaml path
        new_eks_version (float): eks version to be updated
        new_region (str): region to be updated
    """
    # Load the existing YAML configuration from the file
    with open(file_path, "r") as config_file:
        eks_config = yaml.safe_load(config_file)

    # Update region and version
    eks_config["metadata"]["version"] = new_eks_version
    eks_config["metadata"]["region"] = new_region

    # Save the updated configuration back to the output file
    with open(updated_path, "w") as updated_file:
        yaml.dump(eks_config, updated_file, default_flow_style=False)

    # print updated yaml file content
    with open(updated_path, "r") as saved_file:
        saved_content = saved_file.read()
    logger.info(f"Updated yaml file content: \n{saved_content}")


@retry(stop=stop_after_attempt(3), wait=wait_fixed(5), reraise=True)
def update_kubectl_version(kubectl_version="1.25"):
    """Update kubectl version in the test machine

    Args:
        kubectl_version (str, optional): kubectl version to update in the system. Defaults to "1.25".
    """
    desired_version = f"v{kubectl_version}.0"
    kubectl_binary_path = "/usr/local/bin/kubectl"

    # Kubectl version, download URL
    kubectl_url = f"https://storage.googleapis.com/kubernetes-release/release/{desired_version}/bin/linux/amd64/kubectl"

    # Download kubectl binary using curl
    download_kubectl = ["curl", "-LO", kubectl_url]

    # Make the binary executable
    update_permissions = ["chmod", "+x", "kubectl"]

    # Move kubectl binary to /usr/local/bin (ensure it's in the PATH)
    move_kbctl_binary = ["mv", "kubectl", kubectl_binary_path]
    commands = [download_kubectl, update_permissions, move_kbctl_binary]
    for command in commands:
        run_command = run_ctl_command(command, timeout=100)
        assert run_command, f"Failed to update kubectl version {desired_version}"
    logger.info(f"Successfully updated kubectl to version {desired_version}")


def get_aws_session_for_cluster_based_on_region(context: Context, cluster_yaml):
    """This step method generates an AWS session for a provided cluster yaml file

    Args:
        context (Context): Context Object
        cluster_yaml (str): Provide yaml file on which user wants to create AWS session.

    Returns:
        AWS object: return AWS object based on the cluster and its region.
    """
    (
        context.eks_cluster_name,
        context.eks_cluster_aws_region,
    ) = read_yaml_get_eks_cluster_info(cluster_yaml)
    aws_session = (
        AWS(
            region_name=context.eks_cluster_aws_region,
            aws_access_key_id=context.eks_account_key,
            aws_secret_access_key=context.eks_account_secret,
            account_name=context.aws_eks_account_name,
        )
        if context.eks_cluster_aws_region != "us-west-2"
        else context.aws_eks
    )
    return aws_session


def validate_eks_app_status(context, cluster_id, app_name, app_state):
    """This method validates the desired status of the k8s application

    Args:
        context (Context): Context Object
        cluster_id (str): id of the cluster where app is installed.
        app_name (str): name is application to be validated
        app_state (str): state of application eg: DELETED, ACTIVE, OK
    """
    # Validate the status of ns.
    apps_list = context.eks_inventory_manager.get_csp_k8s_applications(cluster_id)
    logger.debug(f"Namespaced apps list: {apps_list}")
    dscc_app_name = [app.name for app in apps_list.items if app.name == app_name and app.state == app_state]
    assert app_name in dscc_app_name, f"K8 app {app_name} not in desired state {app_state} in DSCC"
    logger.info(f"EKS app {app_name} in desired state: {app_state}")


def validate_k8s_resources(app_config_yaml: str, app_name: str, kubernetes_client):
    expected_dplmt_name = read_yaml_get_metadata_name(app_config_yaml, kind_value="Deployment")[0]
    deployment_exists = validate_eks_deployment_in_ns(app_name, expected_dplmt_name, kubernetes_client)
    assert deployment_exists, f"Deployment name {expected_dplmt_name} does not exist "
    logger.info(f"Successfully validated deployment {expected_dplmt_name} for the namespace {app_name}")

    EXPECTED_SERVICE_NAME = read_yaml_get_metadata_name(app_config_yaml, kind_value="Service")[0]
    service_exists_one = validate_eks_services_in_ns(app_name, EXPECTED_SERVICE_NAME, kubernetes_client)
    assert service_exists_one, f"Service name {EXPECTED_SERVICE_NAME} does not exist "
    logger.info(f"Successfully validated service {EXPECTED_SERVICE_NAME} for the namespace {app_name}")

    pods_exists = validate_eks_pod_in_ns(app_name, kubernetes_client)
    assert pods_exists, f"EKS namspace {app_name} does not have pods or not on running status"
    logger.info(f"Successfully validated pod is available and running status in the namespace {app_name}")

    replicaset_exists = validate_eks_replicaset_in_ns(app_name, kubernetes_client)
    assert replicaset_exists, f"EKS namspace {app_name} does not have replicaset"
    logger.info(f"Successfully validated replicaset is available in the namespace {app_name}")


def validate_persistent_volume_in_namespace(app_name):
    """Validates if namespace contains any persistent volumes.

    Args:
        app_name (str): k8s app name/namespace
    """
    logger.info(f"Validating persistent volumes in namespace {app_name}")
    pvcs = get_persistent_volume_claim_for_namespace(app_name)
    assert pvcs, f"No persistent volumes found in namespace {app_name}"


def validate_service_account_k8s_resource(
    service_account_name: str,
    namespace: str,
    validate_workflow: str = "read",
    validate_delete_resource: str = False,
):
    """Validates service account k8s resource in the namespace in theree scenarios, 1. Create, 2. Delete and 3. Read
    Args:
        service_account_name (str): ServiceAccount K8s resource name.
        namespace (str): Name of the namespace.
        validate_workflow (str, optional): Validation of create or delete or read . Defaults to 'read'.
        validate_delete_resource  (bool, optional): Validate delete resource workflow if set to True (in case of delete workflow we will get service not found error, this flag addreseses the same), defaults to False.
    """
    k8s_client = K8SClient.KubernetesClient()

    if validate_workflow == "create":
        logger.info(f"Create ServiceAccount k8s resource: '{service_account_name}' on the namespace: '{namespace}'")
        # Validate ServiceAccount
        response = k8s_client.create_eks_service_account(service_account_name=service_account_name, namespace=namespace)
        assert (
            response
        ), f"Failed to deploy ServiceAccount k8s resource: '{service_account_name}' on the namespace: '{namespace}'"
        logger.info(
            f"Sucessfully created and ServiceAccount k8s resource: '{service_account_name}' on the namespace: '{namespace}'"
        )
    if validate_workflow == "delete":
        logger.info(f"Delete ServiceAccount k8s resource: '{service_account_name}' on the namespace: '{namespace}'")
        # Validate ServiceAccount
        response = k8s_client.delete_eks_service_account(service_account_name=service_account_name, namespace=namespace)
        assert (
            response
        ), f"Failed to deploy ServiceAccount k8s resource: '{service_account_name}' on the namespace: '{namespace}'"
        logger.info(
            f"Sucessfully deleted ServiceAccount k8s resource: '{service_account_name}' on the namespace: '{namespace}'"
        )
    if validate_workflow == "read":
        logger.info(f"Verify ServiceAccount k8s resource: '{service_account_name}' on the namespace: '{namespace}'")
        # Validate ServiceAccount
        response = k8s_client.read_eks_service_account(
            service_account_name=service_account_name,
            namespace=namespace,
            validate_delete_resource=validate_delete_resource,
        )
        assert (
            response
        ), f"Failed to check existance of ServiceAccount k8s resource: '{service_account_name}' on the namespace: '{namespace}'"
        logger.info(
            f"Sucessfully verified ServiceAccount k8s resource: '{service_account_name}' on the namespace: '{namespace}'"
        )


def delete_and_validate_k8s_namespace(
    context: Context, eks_cluster_name: str, eks_cluster_aws_region: str, namespace: str, cluster_refresh: bool = True
):
    """Deletes and validate k8s namespace
    Args:
        context (Context): Context object
        eks_cluster_name (str): Name of the EKS cluster
        eks_cluster_aws_region (str): EKS cluster aws region
        namespace (str): Name of the namespace.
    """
    verify_and_set_eks_cluster_context(eks_cluster_name, eks_cluster_aws_region, context.aws_eks_iam_user_name)
    k8s_client = K8SClient.KubernetesClient()

    # Delete application from k8s
    interval = 1.0
    logger.info(f"Delete namespace: '{namespace}'")
    response = k8s_client.delete_namespace(namespace)
    assert response, f"Failed to delete k8s namespace:'{namespace}'"
    logger.info(f"Sucessfully deleted namespace: '{namespace}'")

    try:
        wait(
            lambda: verify_namespace_deleted(namespace),
            timeout_seconds=120,
            sleep_seconds=(interval, 5),
        )
    except TimeoutExpired:
        raise TimeoutError(f"Namespace: {namespace} not deleted")

    if cluster_refresh:
        # Refresh cluster inventory so that deleted namespace will be disappear from DSCC
        EKSInvSteps.perform_eks_cluster_refresh(context, eks_cluster_name, eks_cluster_aws_region)


def verify_namespace_deleted(namespace):
    k8s_client = K8SClient.KubernetesClient()
    ns_list = k8s_client.get_namespaces()
    ns_name_list = [
        ns_list_value.metadata.labels
        for ns_list_value in ns_list.items
        if namespace in ns_list_value.metadata.labels.values()
    ]
    return True if not ns_name_list else False


def get_node_name_of_pod(K8_CLIENT, namespace):
    """Returns the node name where the pod is running
    Args:
        K8_CLIENT: k8s client instance
        namespace (str): Name of the namespace.
    Returns:
        pod_node_name (str): node name where pod is running.
    """
    pod_list = K8_CLIENT.get_k8s_list_pods_namespace(namespace)
    assert pod_list, f"Failed to get running pods in namespce {namespace}"
    pod_node_name = pod_list.items[0].spec.node_name
    return pod_node_name


def copy_dmcore_to_pod(namespace, pod_path):
    """Copies dmcore file to pod in provided namespace

    Args:
        namespace: namespace where the pod is placed
        file_path: filepath in pod where dmcore is copied to
    """
    pod_name = get_k8s_pods_names_in_namespace(namespace)[0]
    path = "lib/platform/resources"
    file_name = "dmcore"
    file_path = f"{path}/{file_name}"
    copy_file_to_pod(file_path, namespace, pod_name, pod_path)


def copy_file_to_pod(
    file_path: str,
    namespace_name: str,
    pod_name: str = "nginx-deployment",
    pod_path: str = "/usr/share/nginx/html/",
):
    """copy file to a specific location in the pod
    Args:
        file_path (str): local file name path
        namespace_name (str): Name of the namespace
        pod_name (str, optional): Name of the pod. Defaults to "nginx-deployment".
        pod_path (str, optional): pod file path. Defaults to "/usr/share/nginx/html/".
    """
    # Create k8s instance
    kubernetes_client = K8SClient.KubernetesClient()
    logger.info(f"Copy file from a local path:{file_path} to pod path: {pod_path}")
    pods_list = kubernetes_client.get_k8s_list_pods_namespace(namespace_name)
    # actual pod name post fixes random generated string
    actual_pod_name = None
    pod_list_items = pods_list.items
    for item in pod_list_items:
        if pod_name in item.metadata.name:
            actual_pod_name = item.metadata.name
            logger.info(f"Actual k8s pod name: {actual_pod_name}")
            break
    # construct copy to pod command
    command = ["kubectl", "cp", file_path, f"{namespace_name}/{actual_pod_name}:{pod_path}"]
    command_result = run_ctl_command(command, timeout=300)
    assert command_result, f"Failed to copy file from a local path:{file_path} to pod path: {pod_path}"
    logger.info(f"Successfully copied file from a local path:{file_path} to pod path: {pod_path}")


def generate_dmcore_file(k8s_client, app_name, dmcore_path, file_name, file_size_in_gb=5):
    """Generates test file with use of dmcore.
    Default dmcore parameters:
    - DMExecSet=Nas
    - DMVerificationMode=MD5
    - WriteI=256k
    Args:
        k8s_client: kubernetes client instance
        app_name (str): name of the app/namespace where file is created
        dmcore_path (str): path in pod where file is created
        file_name (str): name of generated file
        file_size_in_gb (int, optional): size of generated file. Defaults to 5.
    """
    pod_name = get_k8s_pods_names_in_namespace(app_name)[0]
    logger.info("Giving execute permissions for dmcore file...")
    k8s_client.pod_command_exec(pod_name, app_name, f"chmod +x {dmcore_path}/dmcore/dmcore")
    logger.info(f"Generating file ({file_size_in_gb}g) with use of dmcore...")
    k8s_client.pod_command_exec(
        pod_name,
        app_name,
        f"{dmcore_path}/dmcore/dmcore Command=Write 'DMExecSet=Nas' 'DMVerificationMode=MD5' 'ExportFileName={dmcore_path}/{file_name}' 'WriteT={file_size_in_gb}g' 'WriteI=256k'",
    )
    logger.info("Successfully generated file with use of dmcore")


def validate_dmcore_file(k8s_client, namespace: str, file_path: str, file_name: str, file_size_in_gb=5):
    """Validate data integrity of dmcore generated file.

    Args:
        k8s_client: kubernetes client instance
        namespace (str): namespace of generated file to validate
        file_path (str): file path of generated file to validate
        file_name (str): file name of generated file to validate
        file_size_in_gb (int, optional): file sise of generated file to validate. Defaults to 5.
    """
    pod_name = get_k8s_pods_names_in_namespace(namespace)[0]
    logger.info(
        f"Reading and verifying dmcore generated file {file_name} in {file_path}. Pod: {pod_name}, namespace: {namespace}"
    )
    k8s_client.pod_command_exec(
        pod_name,
        namespace,
        f"usr/share/nginx/html/dmcore/dmcore Command=Read 'DMExecSet=Nas' 'DMVerificationMode=MD5' 'ImportFileName={file_path}/{file_name}' 'ReadT={file_size_in_gb}g' 'ReadI=256k' 'Validation=1' 'CompressionRatio=4' 'CompressionMethod=4'",
    )


def generate_checksum_to_file(k8s_client, namespace, filepath, save_to_filepath):
    pod_name = get_k8s_pods_names_in_namespace(namespace)[0]
    generate_sha_command = f"sha256sum {filepath} >> {save_to_filepath}"
    logger.debug(f"Generating checksum for {filepath} and saving to {save_to_filepath}")
    k8s_client.pod_command_exec(pod_name, namespace, generate_sha_command)


def verify_checksum_from_file(k8s_client, namespace, checksum_filepath):
    pod_name = get_k8s_pods_names_in_namespace(namespace)[0]
    verify_sha_command = f"sha256sum --check {checksum_filepath}"
    logger.debug(f"Verifying checksum based on saved checksum file {checksum_filepath}")
    k8s_client.pod_command_exec(pod_name, namespace, verify_sha_command)


def delete_pvc_from_deployment(namespace: str):
    """Deletes PVC from deployment in provided namespace.
    Note: method assumes that there is one deployment per namespace
    Method executes following steps in order to delete PV:
    1. Scale down deployment to 0
    2. Delete PVC and PV
    3. Scale up deployment back to 1

    Args:
        namespace (str): namespace where deployment of interest is placed
    """
    k8s_client = K8SClient.KubernetesClient()
    # Scale down deployments to zero to be able to delete PV/PVC
    deployments = k8s_client.get_eks_deployments_namespace(namespace)
    deployment_name = [item.metadata.name for item in deployments.items if item.metadata.namespace == namespace][0]
    scale_down_result = k8s_client.scale_deployment(replicas=0, deployment_name=deployment_name, namespace=namespace)
    assert scale_down_result, f"Scaling down deployment failed."
    # Delete PVC and PV
    pvc_name = get_persistent_volume_claim_for_namespace(namespace)[0]
    delete_pvc_result = run_ctl_command(["kubectl", "delete", "pvc", f"{pvc_name}", "-n", f"{namespace}"])
    assert delete_pvc_result, f"PVC {pvc_name} in namespace {namespace} deletion failed."
    pv_name = k8s_client.get_persistent_volumes_for_namespace(namespace)[0]
    pv_deletion_result = run_ctl_command(["kubectl", "delete", "pv", f"{pv_name}"])
    assert pv_deletion_result, f"PV {pv_name} deletion failed."
    # Scale deployment to its original replicas.
    scale_up_result = k8s_client.scale_deployment(replicas=1, deployment_name=deployment_name, namespace=namespace)
    assert scale_up_result, f"Scaling up deployment failed."


def get_k8s_pods_names_in_namespace(namespace: str):
    """This method returns all pod names in provided namespace

    Args:
        namespace (str): Namespace we get the names of pods from

    Returns:
        list[str]: List of pod names
    """
    k8s_client = K8SClient.KubernetesClient()
    pods = k8s_client.get_k8s_list_pods_namespace(namespace)
    logger.debug(f"Pod list from namespace {namespace} returned here is -> {pods}")
    return [item.metadata.name for item in pods.items]


def get_persistent_volume_claim_for_namespace(namespace: str):
    """This method returns persistent volume in provided namespace.

    Args:
        namespace (str): namespace to get persistent volume from

    Returns:
        list[str]: list of persistent volumes in namespace
    """
    k8s_client = K8SClient.KubernetesClient()
    pvcs = k8s_client.get_persistent_volume_claim_for_all_namespace()
    pvcs_names = [item.metadata.name for item in pvcs.items if item.metadata.namespace == namespace]
    return pvcs_names


def validate_nginx_pod_running_status_and_content(
    namespace_name: str,
    expected_content: str = "Welcome to EKS Test Automation",
    wait_timeout: int = 180,
):
    """Validate nginx pod running status and its content

    Args:
        namespace_name (str): Name of the namesapce
        expected_content (str, optional): Expected content to be validated. Defaults to "Welcome to EKS Test Automation".
    """
    # K8s intstance
    kubernetes_client = K8SClient.KubernetesClient()

    # Get the load balancer URL
    service_list = kubernetes_client.get_eks_service_namespace(namespace_name)
    service = service_list.items[0]
    load_balancer_url = service.status.load_balancer.ingress[0].hostname
    logger.info(f"Load Balancer URL: {load_balancer_url}")

    # Set maximum wait time
    end_time = datetime.now() + timedelta(seconds=wait_timeout)

    while datetime.now() < end_time:
        # Check nginx pod status
        response = kubernetes_client.is_nginx_running(load_balancer_url)

        if response.status_code == requests.codes.ok:
            # Break out of the loop if the response is okay
            logger.info(f"Nginx pod is running and response content: {response.text}")
            assert expected_content in response.text, "Failed to validate the nginx pod content"
            logger.info("Successfully validated nginx pod running status and its content")
            break

        # If not ok state, sleep for a short interval before retrying
        logger.info(f"Sleeping for '20 seconds' before retrying...")
        time.sleep(20)
    # If we reach here, it means the maximum wait time elapsed without getting an ok response
    assert (
        response.status_code == requests.codes.ok
    ), f"Nginx pod did not return ok status within {wait_timeout} seconds"


def delete_and_validate_storage_class(context: Context, eks_cluster_name: str, eks_cluster_aws_region: str, sc: str):
    """This method deletes the provided storage class.

    Args:
        context (Context): Context object
        eks_cluster_name (str): Name of the EKS cluster
        eks_cluster_aws_region (str): EKS cluster aws region
        sc (str): storage class name to be deleted
    """
    verify_and_set_eks_cluster_context(eks_cluster_name, eks_cluster_aws_region, context.aws_eks_iam_user_name)
    k8s_client = K8SClient.KubernetesClient()
    sc = k8s_client.delete_storage_class(sc)
    assert sc, f"Deletion of storage class failed"


def delete_ebs_csi_add_on(cluster_name, cluster_region, app_timeout):
    """This function to delete EBS CSI add on and validate upon deletion

    Args:
        cluster_name (string): Cluster name
        cluster_region (string): Cluster region
        app_timeout : Time to execute the command

    """
    # Delete ebs csi driver addon
    ebs_driver_name = "aws-ebs-csi-driver"
    eksctl_command = [
        "eksctl",
        "delete",
        "addon",
        "--cluster",
        cluster_name,
        "--name",
        ebs_driver_name,
        "--region",
        cluster_region,
        "--preserve",
    ]
    logger.info(f"Deleting {ebs_driver_name} addon")
    result = run_ctl_command(eksctl_command, app_timeout)
    assert result, f"Failed to delete ebs csi driver {ebs_driver_name}"
    logger.info(f"Waiting for two minutes before validating if {ebs_driver_name} addon is deleted")
    time.sleep(120)

    # Validate ebs csi driver addon is deleted.
    eksctl_command = [
        "eksctl",
        "get",
        "addon",
        "--cluster",
        cluster_name,
        "--region",
        cluster_region,
    ]

    logger.info("Get addons list post delete")
    result = run_ctl_command(eksctl_command, app_timeout, kubectl_command=True)
    assert ebs_driver_name not in result, f"Failed to delete ebs csi driver {ebs_driver_name}"


def get_count_of_all_k8s_applications(context: Context):
    """Get count of all K8s apps from all clusters in inventory

    Returns:
        int: Number of applications from all clusters in inventory
    """
    clusters = context.eks_inventory_manager.get_csp_k8s_clusters()
    dscc_apps_count = 0
    for cluster in clusters.items:
        dscc_apps_count += cluster.application_count
    return dscc_apps_count
