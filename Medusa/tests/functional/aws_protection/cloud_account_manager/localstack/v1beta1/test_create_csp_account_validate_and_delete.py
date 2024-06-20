import logging
import json
import pytest
import random
import uuid
from requests import codes, Response
from lib.common.config.config_manager import ConfigManager
from lib.common.enums.atlantia_kafka_topics import AtlantiaKafkaTopics
from lib.platform.aws_boto3.aws_factory import AWS
from tests.steps.aws_protection.v1beta1.cloud_account_manager_steps import (
    attach_cam_roles_to_policies,
    negative_modify_csp_account,
)
from pytest import fixture, mark
from lib.common.enums.provided_users import ProvidedUser
from lib.dscc.backup_recovery.csp_account.rest.v1beta1.model.csp_account import (
    CSPAccount,
    CSPOnboardingTemplate,
)
from lib.common.enums.csp_type import CspType
from tests.e2e.aws_protection.context import Context
from lib.platform.kafka.kafka_manager import KafkaManager, TopicEncoding
from lib.common.enums.account_validation_status import ValidationStatus
from lib.common.enums.account_onboarding_template import OnboardingTemplateProperties


logger = logging.getLogger()
start = 100000000000
stop = 1000000000000
csp_id = "arn:aws:iam::" + str(random.randrange(start, stop)) + ":"
csp_account_name = "MyAccount-" + str(uuid.uuid4())
updated_csp_account_name: str = "UpdatedAccount-" + str(uuid.uuid4())
aws_stack_name = "CustomerAccount" + str(uuid.uuid4())
config = ConfigManager.get_config()


@fixture(scope="session")
def context():
    return Context(test_provided_user=ProvidedUser.user_one, initialize_minimal=True)


@fixture(scope="session")
def aws():
    return AWS(
        region_name=config["AWS"]["region-two"],
        aws_access_key_id="test",
        aws_secret_access_key="test",
    )


@mark.cam_localstack
def test_create_csp_account_(context: Context):
    # Creating a new CSP Account
    created_csp_account: CSPAccount = context.cam_client_v1beta1.create_csp_account(
        csp_id=csp_id, name=csp_account_name, csp_type=CspType.AWS
    )

    # Fetching created account
    fetched_csp_account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(
        account_id=created_csp_account.id
    )
    assert created_csp_account.name == fetched_csp_account.name

    # Validating Kafka Message sent on CSP_CAM_UPDATES topic
    # __validate_csp_account_on_cam_updates_kafka_topic(csp_account=fetched_csp_account)

    # Validating Kafka Message sent on ATLAS_REPORT_EVENTS topic
    # __validate_csp_account_on_reporting_service_kafka_topic(csp_account=fetched_csp_account)


@mark.cam_localstack
def test_create_duplicate_csp_account(context: Context):
    # Creating a duplicate CSP Account
    response: Response = context.cam_client_v1beta1.raw_create_csp_account(
        csp_id=csp_id, name=csp_account_name, csp_type=CspType.AWS
    )

    # Validating proper error response
    assert response.status_code == codes.bad_request


@mark.cam_localstack
def test_validate_csp_account_without_template(context: Context):
    # Fetching created account
    account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_name(name=csp_account_name)
    assert (
        account.onboarding_template.message == ""
    ), f"Account {account.id} onboarding_template.message = {account.onboarding_template.message}"
    assert (
        not account.onboarding_template.upgrade_needed
    ), f"Account {account.id} onboarding_template.upgrade_needed = {account.onboarding_template.upgrade_needed}"
    assert (
        account.onboarding_template.version_applied == ""
    ), f"Account {account.id} onboarding_template.version_applied = {account.onboarding_template.version_applied}"

    # Validating customer account
    context.cam_client_v1beta1.validate_csp_account(account_id=account.id)

    # Checking account's validation status
    fetched_csp_account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(account_id=account.id)
    validation_status = fetched_csp_account.validation_status
    assert (
        validation_status == ValidationStatus.failed
    ), f"Account {fetched_csp_account.id} status = {validation_status}"

    # Checking account's onboarding template
    assert (
        fetched_csp_account.onboarding_template.message == ""
    ), f"Account {fetched_csp_account.id} onboarding_template.message = {fetched_csp_account.onboarding_template.message}"
    assert not fetched_csp_account.onboarding_template.upgrade_needed, (
        f"Account {fetched_csp_account.id} onboarding_template.upgrade_needed = "
        + fetched_csp_account.onboarding_template.upgrade_needed
    )
    assert fetched_csp_account.onboarding_template.version_applied == "", (
        f"Account {fetched_csp_account.id} onboarding_template.version_applied = "
        + fetched_csp_account.onboarding_template.version_applied
    )

    # Validating Kafka Message sent on ATLAS_REPORT_EVENTS topic
    # __validate_csp_account_on_reporting_service_kafka_topic(csp_account=account)


@mark.cam_localstack
def test_validate_csp_account_before_update(context: Context, aws: AWS):
    # Fetching created account
    account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_name(name=csp_account_name)
    assert (
        account.onboarding_template.message == ""
    ), f"Account {account.id} onboarding_template.message = {account.onboarding_template.message}"
    assert (
        not account.onboarding_template.upgrade_needed
    ), f"Account {account.id} onboarding_template.upgrade_needed = {account.onboarding_template.upgrade_needed}"
    assert (
        account.onboarding_template.version_applied == ""
    ), f"Account {account.id} onboarding_template.version_applied = {account.onboarding_template.version_applied}"

    # Getting Account's CloudFormation Template
    csp_onboarding_template: CSPOnboardingTemplate = context.cam_client_v1beta1.get_csp_account_onboarding_template(
        account_id=account.id
    )
    template_body = csp_onboarding_template.onboardingtemplate

    # Uploading CloudFormation Template from the above written file to customer's AWS account
    aws.cloud_formation.create_cf_stack(stack_name=aws_stack_name, template_body=template_body)

    # Attaching roles to policies as it is not happening on localstack
    attach_cam_roles_to_policies(aws=aws, aws_account_id="000000000000")

    # Validate account ID is a UUID
    try:
        uuid.UUID(str(account.id))
    except ValueError:
        assert False, account.id + " is not a UUID"

    # Validating customer account
    context.cam_client_v1beta1.validate_csp_account(account_id=account.id)

    # Checking account's validation status
    fetched_csp_account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(account_id=account.id)
    validation_status = fetched_csp_account.validation_status
    assert (
        validation_status == ValidationStatus.passed
    ), f"Account {fetched_csp_account.id} status = {validation_status}"

    # Checking account's onboarding template
    assert (
        fetched_csp_account.onboarding_template.message == ""
    ), f"Account {fetched_csp_account.id} onboarding_template.message = {fetched_csp_account.onboarding_template.message}"
    assert not fetched_csp_account.onboarding_template.upgrade_needed, (
        f"Account {fetched_csp_account.id} onboarding_template.upgrade_needed = "
        + fetched_csp_account.onboarding_template.upgrade_needed
    )

    # Validating Kafka Message sent on ATLAS_REPORT_EVENTS topic
    # __validate_csp_account_on_reporting_service_kafka_topic(csp_account=account)


@mark.cam_localstack
def test_suspend_csp_account(context: Context):
    # Fetching created account
    account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_name(name=csp_account_name)

    # Updating Account Name and suspending it
    context.cam_client_v1beta1.modify_csp_account(account_id=account.id, name=updated_csp_account_name, suspended=True)

    # Fetching the updated account
    account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(account_id=account.id)
    assert account.name == updated_csp_account_name
    assert account.suspended is True

    # Validating Kafka Message sent on ATLAS_REPORT_EVENTS topic
    # __validate_csp_account_on_reporting_service_kafka_topic(csp_account=account)


@mark.cam_localstack
def test_validate_csp_account_while_suspended(context: Context):
    # Fetching created account
    account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_name(name=updated_csp_account_name)
    assert (
        account.onboarding_template.message == ""
    ), f"Account {account.id} onboarding_template.message = {account.onboarding_template.message}"
    assert (
        not account.onboarding_template.upgrade_needed
    ), f"Account {account.id} onboarding_template.upgrade_needed = {account.onboarding_template.upgrade_needed}"

    # Validating customer account
    context.cam_client_v1beta1.validate_csp_account(account_id=account.id)

    # Checking account's validation status
    fetched_csp_account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(account_id=account.id)
    validation_status = fetched_csp_account.validation_status
    assert (
        validation_status == ValidationStatus.failed
    ), f"Account {fetched_csp_account.id} status = {validation_status}"

    # Checking account's onboarding template
    assert (
        fetched_csp_account.onboarding_template.message == ""
    ), f"Account {fetched_csp_account.id} onboarding_template.message = {fetched_csp_account.onboarding_template.message}"
    assert not fetched_csp_account.onboarding_template.upgrade_needed, (
        f"Account {fetched_csp_account.id} onboarding_template.upgrade_needed = "
        + fetched_csp_account.onboarding_template.upgrade_needed
    )

    # Validating Kafka Message sent on ATLAS_REPORT_EVENTS topic
    # __validate_csp_account_on_reporting_service_kafka_topic(csp_account=account)


@mark.cam_localstack
def test_resume_csp_account(context: Context):
    # Fetching created account
    account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_name(name=updated_csp_account_name)

    # Resuming Account
    context.cam_client_v1beta1.modify_csp_account(account_id=account.id, name=updated_csp_account_name, suspended=False)

    # Fetching the updated account
    account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(account_id=account.id)
    assert account.suspended is False

    # Validating Kafka Message sent on ATLAS_REPORT_EVENTS topic
    # __validate_csp_account_on_reporting_service_kafka_topic(csp_account=account)


@mark.cam_localstack
def test_validate_csp_account_after_resume(context: Context):
    # Fetching created account
    account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_name(name=updated_csp_account_name)
    assert (
        account.onboarding_template.message == ""
    ), f"Account {account.id} onboarding_template.message = {account.onboarding_template.message}"
    assert (
        not account.onboarding_template.upgrade_needed
    ), f"Account {account.id} onboarding_template.upgrade_needed = {account.onboarding_template.upgrade_needed}"

    # Validating customer account
    context.cam_client_v1beta1.validate_csp_account(account_id=account.id)

    # Checking account's validation status
    fetched_csp_account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(account_id=account.id)
    validation_status = fetched_csp_account.validation_status
    assert (
        validation_status == ValidationStatus.passed
    ), f"Account {fetched_csp_account.id} status = {validation_status}"

    # Checking account's onboarding template
    assert (
        fetched_csp_account.onboarding_template.message == ""
    ), f"Account {fetched_csp_account.id} onboarding_template.message = {fetched_csp_account.onboarding_template.message}"
    assert not fetched_csp_account.onboarding_template.upgrade_needed, (
        f"Account {fetched_csp_account.id} onboarding_template.upgrade_needed = "
        + fetched_csp_account.onboarding_template.upgrade_needed
    )

    # Validating Kafka Message sent on ATLAS_REPORT_EVENTS topic
    # __validate_csp_account_on_reporting_service_kafka_topic(csp_account=account)


@mark.cam_localstack
def test_invalid_update_csp_account(context: Context):
    # Fetching created account
    account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_name(name=updated_csp_account_name)

    # Updating Account Immutable Fields
    updatedCustomerId = account.customer_id + "extra"
    negative_modify_csp_account(
        context=context,
        account_id=account.id,
        payload=json.dumps({"customer_id": f"{updatedCustomerId}"}),
        expected_status_code=codes.bad_request,
    )

    # Fetching the updated account
    account2: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(account_id=account.id)
    assert (
        account2.customer_id == account.customer_id
    ), f"PATCH /csp-accounts/{csp_account_name} allowed customerId update {account.customer_id} to {account2.customer_id}"


rolesAndPolicies = [
    ("hpe-cam-configuration-validator", "hpe-cam-iam-role-and-policy-validation"),
    ("hpe-cam-account-unregistrar", "hpe-cam-iam-role-and-policy-deletion"),
    ("hpe-cam-inventory-manager", "hpe-cam-inventory-manager"),
    ("hpe-cam-backup-manager", "hpe-cam-backup-manager"),
    ("hpe-cam-data-extractor", "hpe-cam-data-extraction"),
    ("hpe-cam-restore-manager", "hpe-cam-restore-manager"),
    ("hpe-cam-data-injector", "hpe-cam-data-injection"),
    ("hpe-cam-csp-rds-inventory-manager", "hpe-cam-csp-rds-inventory-manager"),
    (
        "hpe-cam-csp-rds-data-protection-manager-backup",
        "hpe-cam-csp-rds-data-protection-manager-backup",
    ),
    (
        "hpe-cam-csp-rds-data-protection-manager-restore",
        "hpe-cam-csp-rds-data-protection-manager-restore",
    ),
    ("hpe-hci-ec2-cloud-manager", "hpe-hci-ec2-cloud-manager"),
    ("hpe-cam-csp-k8s-inventory-manager", "hpe-cam-csp-k8s-inventory-manager"),
    (
        "hpe-cam-csp-k8s-data-protection-manager-backup",
        "hpe-cam-csp-k8s-data-protection-manager-backup",
    ),
    (
        "hpe-cam-csp-k8s-data-protection-manager-restore",
        "hpe-cam-csp-k8s-data-protection-manager-restore",
    ),
    ("hpe-cam-gfrs-s3-bucket-manager", "hpe-cam-gfrs-s3-bucket-manager"),
    ("hpe-cam-gfrs-s3-bucket-writer", "hpe-cam-gfrs-s3-bucket-writer"),
    ("hpe-csp-ami-discovery", "hpe-csp-ami-discovery"),
]


@mark.cam_localstack
@pytest.mark.parametrize("role, policy", rolesAndPolicies)
def test_detach_policy_and_validate_account(role: str, policy: str, context: Context, aws: AWS):
    # Detaching one policy from its role
    aws.iam.detach_existing_role_from_policy(aws_account_id="000000000000", role_name=role, policy_name=policy)

    account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_name(name=updated_csp_account_name)
    assert (
        account.onboarding_template.message == ""
    ), f"Account {account.id} onboarding_template.message = {account.onboarding_template.message}"
    assert (
        not account.onboarding_template.upgrade_needed
    ), f"Account {account.id} onboarding_template.upgrade_needed = {account.onboarding_template.upgrade_needed}"

    context.cam_client_v1beta1.validate_csp_account(account_id=account.id)

    # Checking account's validation status
    fetched_csp_account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(account_id=account.id)
    validation_status = fetched_csp_account.validation_status
    assert (
        validation_status == ValidationStatus.failed
    ), f"Account {fetched_csp_account.id} status = {validation_status}"

    # Checking account's onboarding template
    assert (
        fetched_csp_account.onboarding_template.message == ""
    ), f"Account {fetched_csp_account.id} onboarding_template.message = {fetched_csp_account.onboarding_template.message}"
    assert not fetched_csp_account.onboarding_template.upgrade_needed, (
        f"Account {fetched_csp_account.id} onboarding_template.upgrade_needed = "
        + fetched_csp_account.onboarding_template.upgrade_needed
    )

    # Validating Kafka Message sent on ATLAS_REPORT_EVENTS topic
    # __validate_csp_account_on_reporting_service_kafka_topic(csp_account=account)

    # Attach the policy to the role again to set up for next test
    aws.iam.attach_existing_role_to_policy(aws_account_id="000000000000", role_name=role, policy_name=policy)


@mark.cam_localstack
def test_delete_csp_account(context: Context, aws: AWS):
    account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_name(name=updated_csp_account_name)

    # Deleting created account
    context.cam_client_v1beta1.delete_csp_account(account_id=account.id)

    # Validating that the deleted account is no longer present
    deleted_account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_name(name=csp_account_name)
    assert deleted_account is None

    # Validating Kafka Message sent on ATLAS_REPORT_EVENTS topic
    # __validate_csp_account_delete_on_reporting_service_kafka_topic(csp_account=account)

    # Delete the stack
    # aws.cloud_formation.delete_cf_stack(stack_name=aws_stack_name)


def __validate_csp_account_on_cam_updates_kafka_topic(csp_account: CSPAccount):
    kafka_manager = KafkaManager(
        topic=AtlantiaKafkaTopics.CSP_CAM_UPDATES.value,
        host="ccs-kafka:19092",
        topic_encoding=TopicEncoding.PROTOBUF,
    )
    kafka_manager.account_id = "4b793b9610b611ecbda96250d9ed3dec".encode("utf-8")
    consumer = kafka_manager.consumer

    assert any((csp_account.cspId in msg.value.decode("utf-8") for msg in consumer))


def __validate_csp_account_on_reporting_service_kafka_topic(csp_account: CSPAccount):
    flag: bool = False
    kafka_manager = KafkaManager(topic=AtlantiaKafkaTopics.ATLAS_REPORT_EVENTS.value, host="ccs-kafka:19092")
    consumer = kafka_manager.consumer
    for msg in consumer:
        value = msg.value
        logger.info(f"===== value = {value} =====")
        if (
            "cspId" in value.keys()
            and csp_account.cspId == value["cspId"]
            and csp_account.generation == value["generation"]
        ):
            flag = True
            assert csp_account.cspType == value["appType"]
            assert csp_account.name == value["name"]
            assert csp_account.validation_status.value == value["validation_status"]
            assert csp_account.suspended == value["suspended"]
            break

    if not flag:
        assert False


def __validate_csp_account_delete_on_reporting_service_kafka_topic(
    csp_account: CSPAccount,
):
    flag: bool = False
    kafka_manager = KafkaManager(topic=AtlantiaKafkaTopics.ATLAS_REPORT_EVENTS.value, host="ccs-kafka:19092")
    consumer = kafka_manager.consumer
    for msg in consumer:
        value = msg.value
        logger.info(f"===== value = {value} =====")
        if "cspId" in value.keys() and "generation" not in value.keys() and csp_account.cspId == value["cspId"]:
            flag = True
            assert csp_account.cspType == value["appType"]
            break

    if not flag:
        assert False
