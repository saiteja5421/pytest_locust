"""
TEST CASE USES VCENTER3 FROM VARIABLES.INI

TC110: Delete Data Orchestrator with PSG associated
"""
import logging
import random
import string

from pytest import fixture, mark
from requests import codes
from lib.common.error_messages import UNREGISTER_OPE_FOUND_ASSOCIATED_PSG
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    cleanup_psgw_vm,
)
from tests.steps.vm_protection.vcenter_steps import (
    verify_vcenters_unregistered_after_deleting_ope,
    register_vcenters_with_given_ope,
    add_vcenter,
    unregister_vcenter_cascade,
)
from tests.catalyst_gateway_e2e.test_context import Context

# from utils.deploy_ope_vm import main as deploy_ope


logger = logging.getLogger()

created_ope_id = []


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    _cleanup_after_test(test_context, created_ope_id)
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


def _deploy_and_register_ope(context: Context):
    ope_hostname_generator = "-" + "".join(random.choices(string.digits, k=5))
    context.ope_hostname_prefix + ope_hostname_generator
    # sid = deploy_ope(
    #     ope_url=context.ope_url,
    #     ope_hostname=ope_hostname,
    #     vcenter_hostname=context.vcenter_name,
    #     vcenter_username=context.vcenter_username,
    #     vcenter_password=context.vcenter_password,
    #     datastore=context.datastore_name,
    #     cluster="atlas-api",
    # )
    # response = context.hypervisor_manager.register_ope(sid, ope_hostname)
    # assert (
    #     response.status_code == codes.created
    # ), f"OPE is not registered! Status code: {response.status_code}"
    # return response["id"]


def _delete_data_orchestrator_when_psgw_is_associated(context: Context, ope_id):
    response = context.ope.delete_ope(ope_id)
    assert response.status_code == codes.bad_request
    assert UNREGISTER_OPE_FOUND_ASSOCIATED_PSG in response.text


def _delete_data_orchestrator(context: Context, ope_id):
    response = context.ope.delete_ope(ope_id)
    assert response.status_code == codes.no_content


def _delete_data_orchestrator_cleanup(context: Context, ope_id):
    context.ope.delete_ope(ope_id)


def _verify_that_data_orchestrator_is_deleted(context: Context):
    response = context.ope.get_all_ope()
    assert response.status_code == codes.ok
    content = response.json()
    assert all([item["id"] != context.ope_id_assigned_to_vcenter for item in content["items"]])


def unregister_vcenter(context: Context):
    if context.vcenter_id:
        unregister_vcenter_cascade(context)


def register_vcenter(context: Context):
    if context.vcenter_id:
        add_vcenter(context)


def _cleanup_after_test(context, ope_id):
    cleanup_psgw_vm(context)
    _delete_data_orchestrator_cleanup(context, ope_id)
    register_vcenter(context)


@mark.order(1100)
@mark.deploy
@mark.skip(reason="import doesnt work")
def test_tc110(context: Context, vm_deploy, shutdown_all_psgw):
    created_ope_id.append(_deploy_and_register_ope(context))
    unregister_vcenter(context)
    register_vcenters_with_given_ope(context, created_ope_id[0], [context.vcenter_name])
    create_protection_store_gateway_vm(context)
    validate_protection_store_gateway_vm(context)
    _delete_data_orchestrator_when_psgw_is_associated(context, created_ope_id[0])
    cleanup_psgw_vm(context)
    _delete_data_orchestrator(context, created_ope_id[0])
    verify_vcenters_unregistered_after_deleting_ope(context, [context.vcenter_name])
    _verify_that_data_orchestrator_is_deleted(context)
