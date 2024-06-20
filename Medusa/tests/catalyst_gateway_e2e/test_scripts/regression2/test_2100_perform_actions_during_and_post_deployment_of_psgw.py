"""
    Testrail ID: C57582058
    PSGW-Action when PSGW is still in deploying state

    Testrail ID:  C57582142
    Recover a PSG with no cloud stores and perform b&r workflow
    
    TestRail ID - C57582042
    Action- Perform Shutdown

    TestRail ID - C57582157
    Recover a powered OFF PSG

    TestRail ID - C57582041
    Action- Perform Restart

    TestRail ID - C57582056
    Action - Perform Remote Support Enable

    TestRail ID - C57582057
    Action - Perform Remote Support Disable

    TestRail ID - C57582047
    Action-Perform restart when PSGW VM already deleted

    TestRail ID - C57582049
    Action-Perform shutdown when PSGW VM already deleted

    TestRail ID - C57582044
    Action-Perform delete when PSGW VM already deleted

    TestRail ID - C57582064
    PSGW-Perform action after psgw deleted
"""

import logging
import random
import time
from pytest import fixture, mark
from requests import codes
from lib.common.enums.azure_locations import AzureLocations
from lib.common.enums.psg import HealthState, HealthStatus, State
from lib.common.error_messages import ERROR_MESSAGE_RECOVER_OK_CONNECTED_PSG
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
)
from tests.steps.vm_protection.backup_steps import (
    run_backup,
)
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    perform_actions_post_removal_of_psg_from_vcenter,
    perform_actions_while_create_protection_store_gateway,
    validate_protection_store_gateway_vm,
    select_or_create_protection_store_gateway_vm,
    wait_to_get_psgw_to_powered_off,
    wait_for_psgw_to_power_on_and_connected,
    wait_for_psgw_to_restart,
    remote_support_enable_and_disable_on_psgw,
    generate_support_bundle_for_psgw,
)
from lib.common.enums.aws_regions import AwsStorageLocation
from tests.steps.vm_protection.common_steps import perform_cleanup

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


"""
Perform shutdown, restart, power_ON are commented on the first 2 tests due cadence. 
please refer : https://nimblejira.nimblestorage.com/browse/AT-29659
"""

"""    
    Testrail ID: C57582058
    PSGW-Action when PSGW is still in deploying state
"""


@mark.order(2100)
def test_perform_actions_during_deployment_of_psg(context):
    perform_actions_while_create_protection_store_gateway(context)


"""
    TestRail ID - C57582064
    PSGW-Perform action after psgw deleted

    TestRail ID - C57582047
    Action-Perform restart when PSGW VM already deleted

    TestRail ID - C57582049
    Action-Perform shutdown when PSGW VM already deleted
    
    Testrail ID:  C57582142
    Recover a PSG with no cloud stores and perform b&r workflow

    TestRail ID - C57582044
    Action-Perform delete when PSGW VM already deleted
"""


@mark.order(2105)
def test_perform_actions_post_deployment_of_psg(context):
    select_or_create_protection_store_gateway_vm(context)
    perform_actions_post_removal_of_psg_from_vcenter(context)


"""
    TestRail ID - C57582042
    Action- Perform Shutdown
"""


@mark.order(2110)
def test_perform_shutdown_psgw(context, vm_deploy):
    create_protection_store_gateway_vm(context, add_data_interface=False)
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AzureLocations.AZURE_southcentralus)
    assign_protection_template_to_vm(context)
    run_backup(context)
    wait_to_get_psgw_to_powered_off(context)

    # power on the PSG after shutdown operation completed.
    wait_for_psgw_to_power_on_and_connected(context)
    # after power ON sleep for 5 mins to connect the psg and DO to run backup
    logger.info("After the PSG is  powered ON,sleeping for 5 mins to connect the psg and DO to run backup")
    time.sleep(300)
    # Run the backup and make sure, it should pass
    run_backup(context)


"""
    TestRail ID - C57582041
    Action- Perform Restart
"""


@mark.order(2115)
def test_perform_restart_psgw(context):
    select_or_create_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_EU_WEST_2)
    assign_protection_template_to_vm(context)
    wait_for_psgw_to_restart(context)
    run_backup(context)


"""
    TestRail ID - C57582056
    Action - Perform Remote Support Enable
"""


@mark.order(2120)
def test_perform_remote_support_enable(context):
    select_or_create_protection_store_gateway_vm(context, add_data_interface=False)
    remote_support_enable_and_disable_on_psgw(context, remote_support_enable=True)


"""
    TestRail ID - C57582057
    Action - Perform Remote Support Disable
"""


@mark.order(2125)
def test_perform_remote_support_disable(context):
    select_or_create_protection_store_gateway_vm(context, add_data_interface=False)
    remote_support_enable_and_disable_on_psgw(context, remote_support_enable=False)


"""
    TestRail ID - C57582051
    Action - Perform Generate Support Bundle

    TestRail ID - C57582315
    Generate support bundle when generate support bundle is already inprogress
"""


@mark.order(2130)
def test_generate_support_bundle_on_psgw(context):
    select_or_create_protection_store_gateway_vm(context, add_data_interface=False)
    generate_support_bundle_for_psgw(context, support_bundle_slim=True, validate_error_message=True)


"""
    TestRail ID - C57582053
    Action - Perform Generate Support Bundle multiple times back to back from same PSGW
"""


@mark.order(2135)
def test_generate_support_bundle_multiple_times_on_psgw(context):
    select_or_create_protection_store_gateway_vm(context, add_data_interface=False)
    random_num = random.randint(3, 6)
    for num in range(random_num):
        logger.info(f"genereating support bundle for {str(num)} time")
        generate_support_bundle_for_psgw(context, support_bundle_slim=True)
