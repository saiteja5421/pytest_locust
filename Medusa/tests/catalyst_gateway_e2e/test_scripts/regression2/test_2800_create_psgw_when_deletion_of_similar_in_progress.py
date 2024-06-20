"""
TestRail ID - C57581974
    Delete local store and create a new one with same name of store and VM while deletion is in progress on the same vcenter
TestRail ID: C57581989
    Modify Network services settings of Catalyst Gateway & check the Catalyst gateway status & network settings
TestRail ID: C57581990
    Modify Network interface settings of Catalyst Gateway & check the Catalyst gateway status & network settings
TestRail ID: C57581991
    Modify Proxy Server settings of Catalyst Gateway & check the Catalyst gateway status & network settings
TestRail ID: C57581992
    Modify NTP server settings of Catalyst Gateway & check the Catalyst gateway status & network settings
"""

import logging
from lib.common.enums.backup_type_param import BackupTypeParam
from tests.steps.vm_protection.backup_steps import delete_all_backups

from pytest import fixture, mark
from lib.common.enums.aws_regions import AwsStorageLocation

from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    create_psgw_with_same_name_when_delete_psgw_in_progress,
    select_or_create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    validate_psg_networking_settings,
)
from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
)
from tests.steps.vm_protection.backup_steps import run_backup

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context(skip_inventory_exception=True)
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@mark.order(2800)
@mark.deploy
@mark.dependency()
def test_modify_network_and_create_psg_during_deletion(context, vm_deploy, shutdown_all_psgw):
    """TestRail ID: C57581989
        Modify Network services settings of Catalyst Gateway & check the Catalyst gateway status & network settings
    TestRail ID: C57581990
        Modify Network interface settings of Catalyst Gateway & check the Catalyst gateway status & network settings
    TestRail ID: C57581991
        Modify Proxy Server settings of Catalyst Gateway & check the Catalyst gateway status & network settings
    TestRail ID: C57581992
        Modify NTP server settings of Catalyst Gateway & check the Catalyst gateway status & network settings
    """

    # Format PSGW name to have seconday IP in its name
    _psgw_name = context.psgw_name.split("#")
    context.psgw_name = f"{_psgw_name[0]}#{context.secondary_psgw_ip}"

    # Protect a VM
    create_protection_store_gateway_vm(
        context,
        add_data_interface=False,
    )
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_EU_NORTH_1)
    assign_protection_template_to_vm(context)
    run_backup(context)

    # Verify DNS, NTP, Proxy and Primary network interface(IE. 'Network 1')
    validate_psg_networking_settings(context)

    # Post modification of PSG network config verify backup works as expected
    run_backup(context)

    # Delete backups otherwise PSG will not be deleted in the following testcase #2805
    delete_all_backups(BackupTypeParam.backups, context)
    delete_all_backups(BackupTypeParam.snapshots, context)


@mark.order(2805)
@mark.dependency(depends=["test_modify_network_and_create_psg_during_deletion"])
def test_create_psg_when_delete_psg_in_progress(context):
    """
    TestRail ID - C57581974
    Delete local store and create a new one with same name of store and VM while deletion is in progress on the same vcenter
    """
    select_or_create_protection_store_gateway_vm(
        context,
        add_data_interface=False,
    )
    create_psgw_with_same_name_when_delete_psgw_in_progress(context)
