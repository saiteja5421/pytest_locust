"""
TestRail ID - C57581950: 
    Parallel Protection Store/Protection Store Gateway VM creation on different vcenter with different users from a single tenant
"""

import multiprocessing

from pytest import fixture, mark
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
)
from tests.steps.vm_protection.protection_template_steps import (
    create_protection_template,
    assign_protection_template_to_vm,
)
from tests.steps.vm_protection.backup_steps import run_backup
from tests.catalyst_gateway_e2e.test_context import Context
from lib.common.enums.provided_users import ProvidedUser
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs


@fixture(scope="module")
def context():
    context_for_user_one = Context(v_center_type="VCENTER1", test_provided_user=ProvidedUser.user_one)
    context_for_user_two = Context(v_center_type="VCENTER2", test_provided_user=ProvidedUser.user_two)
    context_for_user_two.local_template += "2"
    context_for_user_two.psgw_name += f"_{context_for_user_two.secondary_psgw_ip}"
    context_for_user_two.network = context_for_user_two.secondary_psgw_ip
    context_for_user_two.nic_primary_interface["network_address"] = context_for_user_two.nic_primary_interface[
        "additional_network_address1"
    ]
    yield context_for_user_one, context_for_user_two
    perform_cleanup(context_for_user_one)
    perform_cleanup(context_for_user_two)


def user_behaviour(context):
    create_protection_store_gateway_vm(
        context,
        add_data_interface=False,
        max_cld_dly_prtctd_data=2.0,
        max_cld_rtn_days=199,
        max_onprem_dly_prtctd_data=5.0,
        max_onprem_rtn_days=99,
    )
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_EU_WEST_3)
    assign_protection_template_to_vm(context)
    run_backup(context, backup_type=BackupTypeScheduleIDs.local)


@mark.order(600)
@mark.deploy
def test_parallel_deploy_on_diff_vc_multi_user(context, vm_deploy):
    """
    TestRail ID - C57581950:
    Parallel Protection Store/Protection Store Gateway VM creation on different vcenter with different users from a single tenant
    """
    with multiprocessing.Pool(2) as pool:
        pool.map(user_behaviour, context)
