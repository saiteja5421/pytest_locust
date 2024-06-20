import logging
import time

from pytest import fixture, mark
from lib.platform.storeonce.storeonce import StoreOnce
from tests.steps.vm_protection.common_steps import perform_storeonce_cleanup
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.storeonces_steps import (
    get_storeonce_health_status,
    get_storeonce_id,
    reset_dsccAdmin_user_pwd,
    unregister_storeonces_validate_error_msg,
    enable_disable_and_approve_the_dual_request,
    validate_register_storeonces,
    validate_register_storeonces_with_invalid_parameters,
    validate_unregister_storeonces,
    disable_dual_auth_status_when_its_enabled,
)

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context(set_static_policy=False, deploy=True, storeonce=True)
    yield test_context
    logger.info(f"\n{'Teardown Start'.center(40, '*')}")
    unregister_storeonce = False
    storeonce_id = get_storeonce_id(test_context)
    if storeonce_id:
        unregister_storeonce = True
    perform_storeonce_cleanup(test_context, unregister_storeonce, storeonce_id)
    logger.info(f"\n{'Teardown Complete'.center(40, '*')}")


@mark.order(3200)
def test_unregister_storeonce_when_dual_auth_enabled(context):
    """
    TestRail ID - C57582311
    Unregister storeonce when dual auth enabled in storeonce
    Args:
        context (_type_): context
    """
    enable_disable_and_approve_the_dual_request(context, enable=True)
    reset_dsccAdmin_user_pwd(context)
    #  Register storeonce in dscc
    validate_register_storeonces(context)
    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "OK")
    # unregister the storeonce and verify the error msg
    unregister_storeonces_validate_error_msg(context, storeonce_id)
    # Disable the dual auth in storeonce
    enable_disable_and_approve_the_dual_request(context, enable=False)

    # sleep 3 mins after disableing the  dual request it some taking time to update in dscc
    time.sleep(180)
    # Unregister storeonce after disbled the dual request
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3210)
def test_force_unregister_storeonce_when_dual_auth_enabled(context):
    """
    TestRail ID - C57582312
    Forcefully Unregister storeonce when dual auth is enabled

    Args:
        context (_type_): context
    """
    # Disable dual auth if  it's enabled
    disable_dual_auth_status_when_its_enabled(context)
    time.sleep(120)
    # enable the dual auth request
    enable_disable_and_approve_the_dual_request(context, enable=True)
    reset_dsccAdmin_user_pwd(context)
    #  Register storeonce in dscc
    validate_register_storeonces(context)
    #  Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "OK")
    # unregister the storeonce and verify the error msg
    unregister_storeonces_validate_error_msg(context, storeonce_id, force=True)
    # Disable the dual auth in storeonce
    enable_disable_and_approve_the_dual_request(context, enable=False)
    # sleep 3 mins after disableing the  dual request it's taking time to update in dscc
    time.sleep(180)
    # Unregister storeonce after disbled the dual request
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3220)
def test_register_storeonce_with_wrong_credatials_when_dual_auth_enabled_unregister(context):
    """
    TestRail ID - C57582313
    register storeonce with wrong creadential when dual auth is enabled

    Args:
        context (_type_): context
    """
    # Disabled dual auth if  it's enabled
    disable_dual_auth_status_when_its_enabled(context)
    time.sleep(120)
    # enable the dual auth request
    enable_disable_and_approve_the_dual_request(context, enable=True)
    #  Register storeonce in dscc
    reset_dsccAdmin_user_pwd(context)
    # invalid serial number
    invalid_serial_no = "N0TASERIALN0FOS0"
    validate_register_storeonces_with_invalid_parameters(context, serial_no=invalid_serial_no)
    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "ERROR")
    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id)
    # Disable the dual auth in storeonce
    enable_disable_and_approve_the_dual_request(context, enable=False)
    # sleep 1 mins after disableing the  dual request it's taking time to update in backend
    time.sleep(60)


@mark.order(3230)
def test_register_storeonce_with_wrong_credatials_when_dual_auth_enabled_force_unregister(context):
    """
    TestRail ID - C57582314
    register storeonce with wrong creadential when dual auth is enabled  and unregister storeonce with force
    Args:
        context (_type_): context
    """
    # Disabled dual auth if  it's enabled
    disable_dual_auth_status_when_its_enabled(context)
    time.sleep(120)
    # enable the dual auth request
    enable_disable_and_approve_the_dual_request(context, enable=True)
    #  Register storeonce in dscc
    reset_dsccAdmin_user_pwd(context)
    # Invalid serial no
    invalid_serial_no = "N0TASERIALN0FOS0"
    validate_register_storeonces_with_invalid_parameters(context, serial_no=invalid_serial_no)
    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "ERROR")
    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id, force=True)
    # Disable the dual auth in storeonce
    enable_disable_and_approve_the_dual_request(context, enable=False)
    # sleep 1 mins after disableing the  dual request it's taking time to update in backend
    time.sleep(60)
