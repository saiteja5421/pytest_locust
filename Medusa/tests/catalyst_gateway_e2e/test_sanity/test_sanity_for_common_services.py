"""
This Sanity test is to performs the following workflow and this is for common services team to monitor daily:

    1. Deploy PSG in the provided vCenter
    2. Create on-prem and AWS cloud store
    3. Create protection policy and protect vm
    4. Create AZURE cloud store
    5. Create protection policy and protect vm


following common services are covering as part of this sanity:
> Authz token
> Login
> Software Catalogue
> Tasks
> Audit

"""

import logging

from pytest import fixture, mark
from lib.common.enums.azure_locations import AzureLocations
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
)
from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
    delete_unassinged_protection_policy,
    unassign_protecion_policy_from_vm,
)
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.audit.audit_events_steps import verify_protection_policy_create_audit_event
from tests.catalyst_gateway_e2e.test_context import SanityContext
from lib.common.enums.aws_regions import AwsStorageLocation

global cloud_usage, local_usage

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = SanityContext(set_static_policy=False, deploy=True)
    test_context.backups_taken = 0
    yield test_context
    logger.info(f"\n{'Teardown Start'.center(40, '*')}")
    perform_cleanup(test_context, clean_vm=True)
    logger.info(f"\n{'Teardown Complete'.center(40, '*')}")


@mark.common_service_tests
@mark.order(100)
@mark.dependency(name="test_deploy_psgvm", scope="module")
def test_deploy_psgvm(context, vm_deploy):
    create_protection_store_gateway_vm(context, add_data_interface=True)
    validate_protection_store_gateway_vm(context)


@mark.common_service_tests
@mark.order(200)
@mark.dependency(name="test_create_protection_policy", depends=["test_deploy_psgvm"], scope="module")
def test_create_protection_policy(context):
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_US_WEST_1)


@mark.common_service_tests
@mark.order(300)
@mark.dependency(
    name="test_assign_protection_policy",
    depends=["test_create_protection_policy"],
    scope="module",
)
def test_assign_protection_policy(context):
    assign_protection_template_to_vm(context, backup_granularity_type="VOLUME")


@mark.common_service_tests
@mark.order(400)
@mark.dependency(depends=["test_create_protection_policy"])
def test_verify_protection_policy_create_audit_log(context):
    verify_protection_policy_create_audit_event(context_user=context.user, policy_name=context.local_template)
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)


@mark.common_service_tests
@mark.order(500)
@mark.dependency(
    name="test_create_protection_policy_on_Azure",
    depends=["test_verify_protection_policy_create_audit_log"],
    scope="module",
)
def test_create_protection_policy_on_Azure(context):
    create_protection_template(context, cloud_region=AzureLocations.AZURE_eastus)


@mark.common_service_tests
@mark.order(600)
@mark.dependency(
    name="test_assign_protection_policy_on_Azure",
    depends=["test_create_protection_policy_on_Azure"],
    scope="module",
)
def test_assign_protection_policy_on_Azure(context):
    assign_protection_template_to_vm(context, backup_granularity_type="VOLUME")


@mark.common_service_tests
@mark.order(700)
@mark.dependency(depends=["test_create_protection_policy_on_Azure"])
def test_verify_protection_policy_create_audit_log_on_Azure(context):
    verify_protection_policy_create_audit_event(context_user=context.user, policy_name=context.local_template)
