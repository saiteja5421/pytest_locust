import os
import subprocess
import logging
import time
import uuid
from datetime import datetime
from pytest import fixture, mark
from requests import Response

from lib.common.enums.csp_protection_job_type import CSPProtectionJobType
from lib.common.enums.csp_resource_type import CSPResourceType
from lib.common.enums.protection_summary import ProtectionStatus
from lib.common.enums.protection_types import ProtectionType
from tests.steps.aws_protection.inventory_manager.functional_protection_steps import apply_asset_protection_status
from tests.steps.aws_protection.protection_job_steps import KafkaProtectionJob
from tests.steps.tasks import tasks
from utils.timeout_manager import TimeoutManager
from lib.common.config.config_manager import ConfigManager
from lib.common.enums.provided_users import ProvidedUser
from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.aws_boto3.models.instance import Tag
from tests.functional.aws_protection.inventory_manager.localstack.test_account_management import (
    update_account,
)
from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.protection_group_dynamic_filter_type import ProtectionGroupDynamicFilterType

from lib.dscc.backup_recovery.aws_protection.protection_groups.payload.patch_custom_protection_group import (
    PatchCustomProtectionGroup,
)
from lib.dscc.backup_recovery.aws_protection.protection_groups.models.protection_group import (
    DynamicMemberFilter,
)
from lib.dscc.backup_recovery.aws_protection.protection_groups.payload.post_dynamic_protection_group import (
    PostDynamicProtectionGroup,
)
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import CSPTag
from tests.steps.aws_protection.inventory_manager.bootstrap_test_assets import (
    BootstrapTestbed,
)
from tests.steps.aws_protection.inventory_manager_steps import (
    account_inventory_refresh,
    get_csp_instance_by_ec2_instance_id,
)
from tests.e2e.aws_protection.context import Context
import json

logger = logging.getLogger()
config = ConfigManager.get_config()
ABSOLUTE_CWD = str(os.path.abspath(os.getcwd()))
RELATIVE_OUTPUT_DIR = "tests/contract/aws_protection/inventory_manager/localstack/payloads"
ABSOLUTE_OUTPUT_DIR = os.path.join(ABSOLUTE_CWD, RELATIVE_OUTPUT_DIR)
logger.info(f"ABSOLUTE_OUTPUT_DIR = {ABSOLUTE_OUTPUT_DIR}")

EC2_INSTANCES = None
EBS_VOLUMES = None


@fixture(scope="module")
def context():
    return Context(test_provided_user=ProvidedUser.user_one, initialize_minimal=True)


@fixture(scope="module")
def aws():
    return AWS(region_name=config["AWS"]["region-one"])


@fixture(scope="module")
def private_account_id(context: Context, aws: AWS):
    """Fixture to create private test account"""
    account_id = str(uuid.uuid4())
    update_account(context=context, aws=aws, account_id=account_id, status="STATUS_REGISTERED")
    yield account_id
    update_account(context=context, aws=aws, account_id=account_id, status="STATUS_UNREGISTERED")


@fixture(scope="module")
def testbed(aws: AWS, context: Context, private_account_id: str):
    testbed = BootstrapTestbed(aws=aws)
    yield testbed
    logger.info(10 * "=" + "Initiating Teardown" + 10 * "=")
    logger.info(f"ABSOLUTE_OUTPUT_DIR = {ABSOLUTE_OUTPUT_DIR}")
    result = subprocess.run(["ls", "-ll", ABSOLUTE_OUTPUT_DIR], capture_output=True, text=True, check=True)
    directory_listing = result.stdout.strip()
    logger.info(f"Directory Listing = {directory_listing}")
    testbed.destroy()
    logger.info(10 * "=" + "Teardown Complete !!!" + 10 * "=")


@mark.csp_inventory_localstack_post_test
@mark.xfail
def test_account(context: Context, aws: AWS, private_account_id: str, testbed: BootstrapTestbed):
    global EC2_INSTANCES, EBS_VOLUMES
    # Volume tags
    volume_tags: list[Tag] = [Tag(Key="Contract-Automation-Tags", Value="Vol-Tag1")]
    # Create volume on aws account
    EBS_VOLUMES = testbed.create_ebs_instances(volume_count=1, tags=volume_tags)
    assert len(EBS_VOLUMES) == 1

    # Instance tags
    instance_tags: list[Tag] = [Tag(Key="Contract-Automation-Tags", Value="Machine-Instance-Tag1")]
    _, EC2_INSTANCES, _ = testbed.create_ec2_instances(ec2_count=1, attached_volume_count=0, tags=instance_tags)
    assert len(EC2_INSTANCES) == 1

    # Sync assets into IM
    response: Response = context.inventory_manager.get_trigger_account_inventory_sync_response(private_account_id)
    task_id = response.json()["taskUri"].split("/")[-1]
    tasks.wait_for_task(
        task_id=task_id,
        user=context.user,
        timeout=TimeoutManager.standard_task_timeout,
        log_result=True,
    )

    response_json_str = json.dumps(response.json(), indent=4)
    with open(f"{ABSOLUTE_OUTPUT_DIR}/post_csp_inventory_accounts_refresh_response.json", "w") as outfile:
        outfile.write(response_json_str)
    logger.info(f"response json refresh account = {response_json_str}")

    # Get and dump subnets
    response = context.inventory_manager.raw_get_subnets(account_id=private_account_id)
    response_json_str = json.dumps(response.json(), indent=4)
    with open(f"{ABSOLUTE_OUTPUT_DIR}/get_csp_inventory_accounts_subnet_response.json", "w") as outfile:
        outfile.write(response_json_str)
    logger.info(f"response json subnets = {response_json_str}")

    # Get and dump tag keys
    response = context.inventory_manager.raw_get_tag_keys(
        account_id=private_account_id, regions=config["AWS"]["region-one"]
    )
    response_json_str = json.dumps(response.json(), indent=4)
    with open(f"{ABSOLUTE_OUTPUT_DIR}/get_csp_inventory_accounts_tag_keys_response.json", "w") as outfile:
        outfile.write(response_json_str)
    logger.info(f"response json tag_keys = {response_json_str}")

    # Get and dump tags
    response = context.inventory_manager.raw_get_tag_key_values(
        key="Contract-Automation-Tags",
        account_id=private_account_id,
        regions=config["AWS"]["region-one"],
    )
    response_json_str = json.dumps(response.json(), indent=4)
    with open(f"{ABSOLUTE_OUTPUT_DIR}/get_csp_inventory_accounts_tags_response.json", "w") as outfile:
        outfile.write(response_json_str)
    logger.info(f"response json tags = {response_json_str}")

    # Get and dump vpcs
    response = context.inventory_manager.raw_get_vpcs(account_id=private_account_id)
    response_json_str = json.dumps(response.json(), indent=4)
    with open(f"{ABSOLUTE_OUTPUT_DIR}/get_csp_inventory_accounts_vpcs_response.json", "w") as outfile:
        outfile.write(response_json_str)
    logger.info(f"response json vpcs = {response_json_str}")


@mark.csp_inventory_localstack_post_test
@mark.xfail
def test_volume(context: Context, aws: AWS, private_account_id: str, testbed: BootstrapTestbed):
    # Sync assets into IM
    account_inventory_refresh(context=context, account_id=private_account_id)
    testbed._master_asset_tracker

    # Get and dump volume list
    filter = f"cspInfo.id eq '{EBS_VOLUMES[0].id}' and accountId eq '{private_account_id}'"
    response: Response = context.inventory_manager.raw_get_csp_volumes(filter=filter)
    response_json = response.json()
    volume_id = response_json["items"][0]["id"]
    response_json["items"][0]["cspInfo"]["iops"] = 10
    response_json_str = json.dumps(response_json, indent=4, default=str)
    with open(f"{ABSOLUTE_OUTPUT_DIR}/get_csp_inventory_volumes_response.json", "w") as outfile:
        outfile.write(response_json_str)
    logger.info(f"response json get volumes = {response_json_str}")

    # Get and dump volume info by id
    response = context.inventory_manager.raw_get_csp_volume_by_id(volume_id)
    response_json = response.json()
    response_json["cspInfo"]["iops"] = 10
    response_json_str = json.dumps(response_json, indent=4, default=str)
    with open(f"{ABSOLUTE_OUTPUT_DIR}/get_csp_inventory_volume_by_id_response.json", "w") as outfile:
        outfile.write(response_json_str)
    logger.info(f"response json get volume by id = {response_json_str}")

    # Sync volume
    response = context.inventory_manager.raw_trigger_csp_volume_sync(volume_id)
    response_json_str = json.dumps(response.json(), indent=4)
    with open(f"{ABSOLUTE_OUTPUT_DIR}/post_csp_inventory_volume_response.json", "w") as outfile:
        outfile.write(response_json_str)
    logger.info(f"response json post volume = {response_json_str}")


@mark.csp_inventory_localstack_post_test
@mark.xfail
def test_machine_instance(context: Context, aws: AWS, private_account_id: str, testbed: BootstrapTestbed):
    protection_group_name = "DynamicPG-EC2-CT-1-" + str(uuid.uuid4())
    region = aws._aws_session_manager.region_name
    csp_tags: list[CSPTag] = [CSPTag(key="Contract-Automation-Tags", value="Machine-Instance-Tag1")]

    account_inventory_refresh(context=context, account_id=private_account_id)

    dynamic_member_filter: DynamicMemberFilter = DynamicMemberFilter(
        tags=csp_tags, type=ProtectionGroupDynamicFilterType.CSP_TAG.value
    )
    post_dynamic_protection_group = PostDynamicProtectionGroup(
        account_ids=[private_account_id],
        dynamic_member_filter=dynamic_member_filter,
        asset_type=AssetType.CSP_MACHINE_INSTANCE.value,
        description="Dynamic PG EBS Protection Jobs Contract Test",
        name=protection_group_name,
        csp_regions=[region],
    )
    response: Response = context.inventory_manager.raw_create_protection_group(post_dynamic_protection_group)
    task_id = response.json()["taskUri"].split("/")[-1]
    tasks.wait_for_task(task_id, context.user, TimeoutManager.task_timeout)

    customer_id: str = context.get_customer_id()
    csp_machine_instance = get_csp_instance_by_ec2_instance_id(
        context=context, ec2_instance_id=EC2_INSTANCES[0].id, account_id=private_account_id
    )

    apply_asset_protection_status(
        context=context,
        customer_id=customer_id,
        asset_type=AssetType.CSP_MACHINE_INSTANCE,
        asset_id=csp_machine_instance.cspId,
        csp_asset_id=csp_machine_instance.id,
        protection_status=ProtectionStatus.PROTECTED,
        account_id=private_account_id,
    )

    # Get and dump csp machines instances
    filter = f"cspInfo.id eq '{EC2_INSTANCES[0].id}' and accountId eq '{private_account_id}'"
    response: Response = context.inventory_manager.raw_get_csp_machine_instances(filter=filter)
    response_json = response.json()
    machine_instance_id = response.json()["items"][0]["id"]
    response_json["items"][0]["cspInfo"]["cpuCoreCount"] = 10
    response_json["items"][0]["cspInfo"]["accessProfileId"] = ""
    response_json = json.dumps(response_json, indent=4)
    with open(f"{ABSOLUTE_OUTPUT_DIR}/get_csp_inventory_machine_instances_response.json", "w") as outfile:
        outfile.write(response_json)
    logger.info(f"response json get machine instance = {response_json}")

    # Get and dump csp machine by id
    response = context.inventory_manager.raw_get_csp_machine_instance_by_id(machine_instance_id)
    response_json = response.json()
    response_json["cspInfo"]["cpuCoreCount"] = 10
    response_json["cspInfo"]["accessProfileId"] = ""
    response_json_str = json.dumps(response_json, indent=4)
    with open(
        f"{ABSOLUTE_OUTPUT_DIR}/get_csp_inventory_machine_instance_by_id_response.json",
        "w",
    ) as outfile:
        outfile.write(response_json_str)
    logger.info(f"response json get machine instance by id = {response_json_str}")

    # Sync machine instance
    response = context.inventory_manager.get_trigger_csp_machine_instance_sync_response(machine_instance_id)
    response_json_str = json.dumps(response.json(), indent=4, default=str)
    with open(
        f"{ABSOLUTE_OUTPUT_DIR}/post_csp_inventory_machine_instance_refresh_response.json",
        "w",
    ) as outfile:
        outfile.write(response_json_str)
    logger.info(f"response json post machine instance = {response_json_str}")


@mark.csp_inventory_localstack_post_test
@mark.xfail
def test_protection_groups(context: Context, aws: AWS, private_account_id: str, testbed: BootstrapTestbed):
    # create automatic aws dynamic pg
    tags: list[Tag] = [Tag(Key="DynamicPG-EBS-ProtectionJobTest-1-" + str(uuid.uuid4()), Value="Test-1")]
    region = aws._aws_session_manager.region_name
    csp_tags: list[CSPTag] = [CSPTag(key=tag.Key, value=tag.Value) for tag in tags]
    dynamic_member_filter: DynamicMemberFilter = DynamicMemberFilter(
        cspTags=csp_tags, filterType=ProtectionGroupDynamicFilterType.CSP_TAG.value
    )

    # Sync assets into IM
    account_inventory_refresh(context=context, account_id=private_account_id)
    protection_group_name = "DynamicPG-EBS-CT-1-" + str(uuid.uuid4())
    curr_datetime = datetime.now().strftime("%d-%m-%y")
    post_dynamic_protection_group = PostDynamicProtectionGroup(
        account_ids=[private_account_id],
        dynamic_member_filter=dynamic_member_filter,
        asset_type=AssetType.CSP_VOLUME.value,
        description=f"Dynamic PG EBS Protection Jobs Contract Test {curr_datetime}",
        name=protection_group_name,
        csp_regions=[region],
    )
    response: Response = context.inventory_manager.raw_create_protection_group(post_dynamic_protection_group)
    task_id = response.json()["taskUri"].split("/")[-1]
    tasks.wait_for_task(task_id, context.user, TimeoutManager.task_timeout)

    response_json_str = json.dumps(response.json(), indent=4, default=str)
    with open(
        f"{ABSOLUTE_OUTPUT_DIR}/post_csp_inventory_protection_group_create_response.json",
        "w",
    ) as outfile:
        outfile.write(response_json_str)
    logger.info(f"response json post protection group = {response_json_str}")

    # Get and dump protection groups
    protection_group_id = tasks.get_task_source_resource_uuid(
        task_id=task_id,
        user=context.user,
        source_resource_type=CSPResourceType.PROTECTION_GROUP_RESOURCE_TYPE.value,
    )

    protection_job_group = KafkaProtectionJob(
        context=context,
        customer_id=context.get_customer_id(),
        csp_asset_id=protection_group_id,
        asset_type=CSPProtectionJobType.CSP_PROTECTION_GROUP_PROT_JOB,
        protection_type=ProtectionType.BACKUP,
    )
    protection_job_group.create(
        wait_for_complete=True,
        number_of_expected_jobs=1,
    )

    matching_filter = f"name eq '{protection_group_name}'"
    response = context.inventory_manager.raw_get_protection_groups(filter=matching_filter)
    response_json_str = json.dumps(response.json(), indent=4, default=str)
    with open(f"{ABSOLUTE_OUTPUT_DIR}/get_csp_inventory_protection_groups_response.json", "w") as outfile:
        outfile.write(response_json_str)
    logger.info(f"response json get protection groups = {response_json_str}")

    # Get and dump protection group by id
    response = context.inventory_manager.raw_get_protection_group_by_id(protection_group_id)
    response_json_str = json.dumps(response.json(), indent=4, default=str)
    with open(
        f"{ABSOLUTE_OUTPUT_DIR}/get_csp_inventory_specific_protection_group_response.json",
        "w",
    ) as outfile:
        outfile.write(response_json_str)
    logger.info(f"response json specific protection group = {response_json_str}")

    # Update protection group
    name = f"contract_test_update_pg_name_{int(time.time())}"
    description = f"Updated the protection group name to {name}"
    patch_custom_protection_group = PatchCustomProtectionGroup(name=name, description=description)
    response = context.inventory_manager.raw_update_protection_group(
        protection_group_id=protection_group_id,
        patch_custom_protection_group=patch_custom_protection_group,
    )
    response_json_str = json.dumps(response.json(), indent=4, default=str)
    with open(
        f"{ABSOLUTE_OUTPUT_DIR}/update_csp_inventory_protection_group_response.json",
        "w",
    ) as outfile:
        outfile.write(response_json_str)
    logger.info(f"response json update protection group = {response_json_str}")

    # delete protection group
    protection_job_group.delete(wait_for_complete=True)
    response = context.inventory_manager.raw_delete_protection_group(protection_group_id=protection_group_id)
    response_json_str = json.dumps(response.json(), indent=4, default=str)
    with open(
        f"{ABSOLUTE_OUTPUT_DIR}/delete_csp_inventory_protection_group_response.json",
        "w",
    ) as outfile:
        outfile.write(response_json_str)
    logger.info(f"response json delete protection group = {response_json_str}")
