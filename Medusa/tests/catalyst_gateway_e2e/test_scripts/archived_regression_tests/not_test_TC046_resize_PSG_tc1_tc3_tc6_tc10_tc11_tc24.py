"""
TestRail ID - C56958175:
    Validate the moderate (i.e random capacity between 1TB - 500TB) scale up storage capacity

TestRail ID - C56963999:
    Validate the error message for scale up storage capacity of a PSG with equal storage capacity of existing PSG store size

TestRail ID - C56958183:
    Validate the scale up storage capacity of a PSG with less storage capacity than the existing PSG store size

TestRail ID - C56958173:
    Validate the maximum scale up storage capacity supported by PSG (Deploy PSG with 1TB)

TestRail ID - C56958182
    Validate the error message for maximum scale up storage capacity of a PSG i.e morethan 500TiB

TestRail ID - C56958178
    Validate the scale up storage capacity of a PSG with bunch of datastores with mixed
"""

import logging
from pytest import fixture, mark

from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    psgw_storage_resize,
    validate_resize_catalyst_gatway_error_message,
)
from tests.catalyst_gateway_e2e.test_context import Context
from lib.common.error_messages import (
    ERROR_MESSAGE_EQUAL_SIZE,
    ERROR_MESSAGE_MAX_PSGW_SIZE,
)

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@mark.resize
@mark.order(2100)
@mark.dependency()
def test_validate_moderate_psgw_storage_capacity_with_min_local_store_capacity(context):
    # Deploy PSG with minimum psgw storage capacity i.e 1TB
    context.psgw_local_store_capacity = 1.0
    vc_name = context.vcenter_name.split(".")
    additional_ds_name = f"{vc_name[0]}-PSG-DS-50TB"
    context.update_psg_size = 31.0
    logger.warning(
        f"We need to create datastores to accomodate {context.update_psg_size} and datastore name must contains: {additional_ds_name}, otherwise test expected to fail"
    )
    create_protection_store_gateway_vm(context, add_data_interface=False, psgw_local_store_capacity_required=True)
    validate_protection_store_gateway_vm(context)
    psgw_storage_resize(context, additional_ds_name=additional_ds_name, additional_ds_required=True)


@mark.resize
@mark.order(2110)
@mark.dependency(depends=["test_validate_moderate_psgw_storage_capacity_with_min_local_store_capacity"])
def test_validate_equal_psgw_store_size_error_message(context):
    context.update_psg_size = 0
    validate_resize_catalyst_gatway_error_message(context, ERROR_MESSAGE_EQUAL_SIZE)


@mark.resize
@mark.order(2120)
@mark.dependency(depends=["test_validate_moderate_psgw_storage_capacity_with_min_local_store_capacity"])
def test_validate_less_psgw_store_size_than_existing_error_message(context):
    context.update_psg_size = -1.0
    validate_resize_catalyst_gatway_error_message(context, ERROR_MESSAGE_EQUAL_SIZE)


@mark.resize
@mark.order(2130)
@mark.dependency(depends=["test_validate_moderate_psgw_storage_capacity_with_min_local_store_capacity"])
def test_validate_max_psgw_storage_capacity_with_min_psgw_local_store_capacity(context):
    context.update_psg_size = 468.0
    vc_name = context.vcenter_name.split(".")
    additional_ds_name = f"{vc_name[0]}-PSG-DS"
    logger.warning(
        f"We need to create datastores to accomodate {context.update_psg_size} and datastore name must contains: {additional_ds_name}, otherwise test expected to fail"
    )
    psgw_storage_resize(context, additional_ds_name=additional_ds_name, additional_ds_required=True)


@mark.resize
@mark.order(2140)
@mark.dependency(depends=["test_validate_max_psgw_storage_capacity_with_min_psgw_local_store_capacity"])
def test_validate_max_storage_allowed_error_message(context):
    context.update_psg_size = 50.0
    validate_resize_catalyst_gatway_error_message(context, ERROR_MESSAGE_MAX_PSGW_SIZE)
