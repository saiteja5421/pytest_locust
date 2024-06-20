"""
TestRail ID - C57581951:
    Deploy Protection Store/Protection Store Gateway VM with different vcenter users (user with permission)
"""

import logging

from pytest import fixture, mark

from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
)
from tests.catalyst_gateway_e2e.test_context import Context

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context(skip_inventory_exception=True)
    test_context.hypervisor_manager.change_user_on_vcenter(
        test_context.vcenter["username_non_admin_privilege"],
        test_context.vcenter["password"],
        test_context.vcenter["ip"],
        test_context.vcenter_id,
    )
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    test_context.hypervisor_manager.change_user_on_vcenter(
        test_context.vcenter["username"],
        test_context.vcenter["password"],
        test_context.vcenter["ip"],
        test_context.vcenter_id,
    )
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@mark.order(700)
@mark.deploy
def test_deploy_psgw__with_different_user_permission(context, shutdown_all_psgw):
    """
    TestRail ID - C57581951:
        Deploy Protection Store/Protection Store Gateway VM with different vcenter users (user with permission)
    """
    create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=2.0,
        max_cld_rtn_days=199,
        max_onprem_dly_prtctd_data=5.0,
        max_onprem_rtn_days=99,
    )
    validate_protection_store_gateway_vm(context)
