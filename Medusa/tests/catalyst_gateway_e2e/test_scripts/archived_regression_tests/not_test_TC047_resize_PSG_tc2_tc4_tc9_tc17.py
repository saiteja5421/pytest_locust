"""
TestRail ID - C56958355
    Validate the scale up storage capacity of a PSG with a protection workflow

TestRail ID - C56958176:
    Validate the scale up storage capacity of a PSG with some backups in the local store.

TestRail ID - C56958174:
    Validate the maximum scale up storage capacity supported by PSG (Deploy PSG with 62TB)

TestRail ID - C56958181:
    Validate the scale up storage capacity of a PSG with the datastores already in use
"""

import logging
from pytest import fixture, mark

from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    psgw_storage_resize,
)
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
)
from tests.steps.vm_protection.backup_steps import (
    run_backup,
    restore_virtual_machine,
)
from lib.common.enums.aws_regions import AWSRegions
from lib.common.enums.restore_type import RestoreType
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@mark.resize
@mark.order(2300)
@mark.dependency()
def test_validate_psgw_storage_capacity_resize_with_protection_workflow(context, vm_deploy):
    # Deploy PSGW with Max storage capacity i.e 62TB
    context.psgw_local_store_capacity = 62.0
    vc_name = context.vcenter_name.split(".")
    additional_ds_name = f"{vc_name[0]}-PSG-DS-62TB-1"
    datastore_name = f"{vc_name[0]}-PSG-DS-62TB"
    context.datastore_id = context.hypervisor_manager.get_datastore_id(datastore_name, context.vcenter_name)
    context.update_psg_size = 32.0
    logger.warning(
        f"We need to create datastores to accomodate {context.update_psg_size} and datastore name must contains: {additional_ds_name}, otherwise test expected to fail"
    )
    create_protection_store_gateway_vm(context, add_data_interface=True, psgw_local_store_capacity_required=True)
    validate_protection_store_gateway_vm(context)
    psgw_storage_resize(context, additional_ds_name=additional_ds_name, additional_ds_required=True)
    create_protection_template(context, cloud_region=AWSRegions.AWS_US_EAST_1)
    assign_protection_template_to_vm(context)
    run_backup(context, backup_type=BackupTypeScheduleIDs.cloud)
    restore_virtual_machine(context, RestoreType.new, "local")
    restore_virtual_machine(context, RestoreType.existing, "cloud", quite_time=120)


@mark.resize
@mark.order(2310)
@mark.dependency(depends=["test_validate_psgw_storage_capacity_resize_with_protection_workflow"])
def test_validate_psgw_storage_capacity_resize_with_backups_in_local_store(context):
    context.update_psg_size = 20.0
    run_backup(context)
    psgw_storage_resize(context, additional_ds_required=False)


@mark.resize
@mark.order(2320)
@mark.dependency(depends=["test_validate_psgw_storage_capacity_resize_with_backups_in_local_store"])
def test_validate_max_psgw_storage_capacity_with_max_local_store_capacity(context):
    vc_name = context.vcenter_name.split(".")
    additional_ds_name = f"{vc_name[0]}-PSG-DS"
    context.update_psg_size = 386.0
    logger.warning(
        f"We need to create datastores to accomodate {context.update_psg_size} and datastore name must contains: {additional_ds_name}, otherwise test expected to fail"
    )
    psgw_storage_resize(context, additional_ds_name=additional_ds_name, additional_ds_required=True)
