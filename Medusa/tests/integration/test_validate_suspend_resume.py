import logging


from pytest import fixture, mark
from lib.common.enums.account_validation_status import ValidationStatus
from lib.common.enums.csp_type import CspType
from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.aws_boto3.cloud_formation_manager import CloudFormationManager

from tests.e2e.aws_protection.context import SanityContext
from tests.steps.aws_protection.cloud_account_manager_steps import (
    create_csp_account,
    delete_csp_account_with_expectation,
    get_csp_account_by_csp_id,
    get_csp_account_by_csp_name,
    get_csp_account_onboarding_template,
    modify_csp_account,
    validate_csp_account,
)
import tests.steps.aws_protection.policy_manager_steps as PolicyMgrSteps


logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = SanityContext()
    yield test_context

    logger.info(f"\n{'Teardown Start'.center(40, '*')}")

    # Deleting created account
    csp_account = get_csp_account_by_csp_name(
        test_context, account_name=test_context.aws_one_account_name, is_found_assert=False
    )
    if csp_account:
        delete_csp_account_with_expectation(test_context, csp_account_id=csp_account.id)

    logger.info(f"\n{'Teardown Complete'.center(40, '*')}")


@mark.sanity
@mark.order(10)
def test_register_verify_suspend_resume_account(context: SanityContext):
    """
    Integration Test Steps:
        Register Customer Account -> Verify Customer Account -> Suspend Customer Account -> Resume Customer Account
    """
    # Register Customer Account
    # "atlantia_automation" AWS Account ID
    aws_account_id = context.sanity_aws_account_id
    aws_account_name = context.sanity_aws_account_name

    # ensure the Sanity test account is removed
    csp_account = get_csp_account_by_csp_name(context, account_name=aws_account_name, is_found_assert=False)
    if csp_account:
        logger.info("Removing Sanity test account")
        delete_csp_account_with_expectation(context, csp_account_id=csp_account.id)

    # create CSP Account
    csp_account = create_csp_account(context, aws_account_id, aws_account_name, CspType.AWS)
    logger.info("Sanity test account created")

    # Download CloudFormation template and Upload in AWS console
    cloud_formation_template = get_csp_account_onboarding_template(context, csp_account.id)

    # Upload cloud formation template to AWS
    aws = AWS(region_name="us-west-2")
    cloud_formation: CloudFormationManager = aws.cloud_formation
    stack_name: str = "stack-name-TC01-sanity"
    cloud_formation.delete_cf_stack(stack_name)
    response = cloud_formation.create_cf_stack(
        stack_name=stack_name, template_body=cloud_formation_template.onboardingTemplate
    )

    # If status is rollback it means that some of the roles could already exists
    if response == "ROLLBACK_COMPLETE":
        roles_hpe = [
            "hpe-cam-backup-manager",
            "hpe-cam-data-extractor",
            "hpe-cam-restore-manager",
            "hpe-cam-configuration-validator",
            "hpe-cam-data-injector",
            "hpe-cam-inventory-manager",
        ]
        roles_aws = aws.iam.get_roles()
        assert set(roles_hpe).issubset(set(roles_aws))
    else:
        assert response.stack_status == "CREATE_COMPLETE", "Creating the cloud formation failed"

    # Perform Validation from DSCC
    # Verify validation task is successful.
    # Verify account validation status is passed.
    task_id = validate_csp_account(context=context, csp_account_id=csp_account.id)

    # AWS account should be validated in DSCC
    csp_account = get_csp_account_by_csp_id(context=context, csp_account_id=csp_account.id)
    assert (
        csp_account.validationStatus == ValidationStatus.passed
    ), f"Account is registered in DSCC: {csp_account.validationStatus}"

    # Createt Protection Policy
    # the base Sanity Policy name
    policy_base_name = context.sanity_policy_base

    # find and remove any Policies that contain the "policy_base_name"
    policy_list = PolicyMgrSteps.get_protection_policies_containing_name(context=context, name_part=policy_base_name)
    for policy in policy_list:
        logger.warning(f"Removing test policy: {policy.name}")
        context.policy_manager.delete_protection_policy(protection_policy_id=policy.id)

    # new policy name, contains "self.random_suffix"
    policy_name = context.sanity_policy

    protection_policy_id = PolicyMgrSteps.create_protection_policy(context=context, name=policy_name)

    # check that Protection Policy is available
    protection_policy = context.policy_manager.get_protection_policy_by_name(protection_policy_name=policy_name)
    assert protection_policy
    assert (
        protection_policy.id == protection_policy_id
    ), f"Protection Policy ID mismatch: expected {protection_policy_id}, but found {protection_policy.id}"

    # Suspend Customer Account
    task_id = modify_csp_account(context=context, csp_account_id=csp_account.id, name=aws_account_name, suspended=True)

    # AWS account should be Suspended in DSCC
    csp_account = get_csp_account_by_csp_id(context=context, csp_account_id=csp_account.id)
    assert csp_account.suspended == "True", f"Account is Suspended in DSCC: {csp_account.suspended}"

    # Resume Customer Account
    task_id = modify_csp_account(context=context, csp_account_id=csp_account.id, name=aws_account_name, suspended=False)

    # AWS account should be Suspended in DSCC
    csp_account = get_csp_account_by_csp_id(context=context, csp_account_id=csp_account.id)
    assert csp_account.suspended == "False", f"Account is Resumed in DSCC: {csp_account.suspended}"
