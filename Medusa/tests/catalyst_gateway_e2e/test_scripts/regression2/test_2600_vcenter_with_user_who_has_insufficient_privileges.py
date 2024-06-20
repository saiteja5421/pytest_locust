"""
    TestRail Id - C57581968

    Deploy Protection Store/Protection Store Gateway VM
    when connecting to vcenter with user who has insufficient privileges on vcenter
    
"""

from pytest import fixture, mark
import logging
from tests.steps.vm_protection.vcenter_steps import (
    change_vcenter_credentials,
    unregister_vcenter_cascade,
    add_vcenter,
    add_vcenter_failed,
    validate_error_message_for_insufficient_previlages,
)
from tests.catalyst_gateway_e2e.test_context import Context

from lib.common.error_messages import (
    ERROR_MESSAGE_UNABLE_TO_UPDATE_VCENTER,
    ERROR_MESSAGE_UNABLE_TO_REGISTER_VCENTER,
    ERROR_MESSAGE_FOR_INSUFFICIENT_PREVILEGES_TASK,
)

logger = logging.getLogger()


@fixture()
def context():
    test_context = Context()
    unregister_vcenter_cascade(test_context)
    yield test_context
    add_vcenter(test_context)


@mark.order(2600)
def test_change_credentials_read_only():
    """
    TestRail Id - C57581968

    Deploy Protection Store/Protection Store Gateway VM
    when connecting to vcenter with user who has insufficient privileges on vcenter
    """
    test_context = Context()
    logger.warning(f"{test_context.username_read_only_privilege} should be added in {test_context.vcenter_name}")
    logger.warning("Otherwise TC will get fail with execpected error message not matched")
    task_id = change_vcenter_credentials(
        test_context,
        test_context.username_read_only_privilege,
        test_context.vcenter_password,
        "failed",
    )
    validate_error_message_for_insufficient_previlages(
        test_context, task_id, ERROR_MESSAGE_UNABLE_TO_UPDATE_VCENTER, ERROR_MESSAGE_FOR_INSUFFICIENT_PREVILEGES_TASK
    )


@mark.order(2605)
def test_re_register_vcenter_read_only(context):
    """
    TestRail Id - C57581968

    Deploy Protection Store/Protection Store Gateway VM
    when connecting to vcenter with user who has insufficient privileges on vcenter

    Args:
        context (Context): Context Object
    """
    logger.warning(f"{context.username_read_only_privilege} should be added in {context.vcenter_name}")
    logger.warning("Otherwise TC will get fail with execpected error message not matched")
    task_id = add_vcenter_failed(context, context.username_read_only_privilege, context.vcenter_password)
    validate_error_message_for_insufficient_previlages(
        context, task_id, ERROR_MESSAGE_UNABLE_TO_REGISTER_VCENTER, ERROR_MESSAGE_FOR_INSUFFICIENT_PREVILEGES_TASK
    )
