import logging
import uuid
from pytest import fixture, mark
from tests.steps.vm_protection.storeonces_steps import (
    get_storeonce_id,
    validate_register_storeonces,
    validate_unregister_storeonces,
    get_storeonce_health_status,
    validate_register_storeonces_with_invalid_parameters,
    reset_dsccAdmin_user_pwd,
    validate_patch_registered_storeonce,
    validate_storeonce_details,
    validate_refresh_registered_storeonce,
    validate_register_storeonces_with_incorrect_format_parameters,
    validate_get_storeonce_invalid_id,
    validate_patch_storeonce_invalid_id,
    validate_delete_storeonce_invalid_id,
    validate_refresh_storeonce_invalid_id,
)
from tests.steps.vm_protection.common_steps import perform_storeonce_cleanup
from tests.catalyst_gateway_e2e.test_context import Context

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


@mark.order(3100)
def test_register_storeonces_valid_ip_and_base_encryption_license(context):
    """
    TestRail ID - C57582229
    Register and unregister storeonce with a valid IP and valid base and encrytion license.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)
    # Register storeonce
    validate_register_storeonces(context)

    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "OK")

    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3105)
def test_register_storeonces_valid_fqdn_and_base_encryption_license(context):
    """
    TestRail ID - C57582230
    Register and unregister storeonce with a valid FQDN and valid base and encrytion license.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # Register storeonce
    validate_register_storeonces(context, network_address=context.storeonces_fqdn)

    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "OK")

    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3110)
def test_register_storeonces_valid_description(context):
    """
    TestRail ID - C57589889
    Register and unregister storeonce adding description value.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # Register storeonce
    validate_register_storeonces(context, description="Storeonce registered via DSCC app")

    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "OK")

    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3115)
def not_test_register_storeonces_valid_hostname_and_base_encryption_license(context):
    """
    TestRail ID - C57582267
    Register and unregister storeonce with a valid hostname and valid base and encrytion license.
    Args:
        context : fixture context
    """

    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # Register storeonce
    validate_register_storeonces(context, network_address=context.storeonces_fqdn.split(".")[0])

    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "OK")

    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3120)
def test_re_register_storeonces_after_unregister(context):
    """
    TestRail ID - C57582279/C57582280
    Register and unregister storeOnce, then perform re-register. Validate UUID of storeOnce.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # Register storeonce
    validate_register_storeonces(context)

    # Checking health state and status of storeonce in DSCC
    registered_storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, registered_storeonce_id, "OK")

    # Unregister storeonce
    validate_unregister_storeonces(context, registered_storeonce_id)

    # Resetting DSCCAdmin user credentials
    reset_dsccAdmin_user_pwd(context)

    # Re-Register storeonce again
    validate_register_storeonces(context)

    # Checking health state and status of storeonce in DSCC
    re_registered_storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, re_registered_storeonce_id, "OK")

    # Checking if UUID of storeOnce is same after re-register
    assert registered_storeonce_id == re_registered_storeonce_id, "UUID of storeonce changed after re-register"

    # Unregister storeonce
    validate_unregister_storeonces(context, re_registered_storeonce_id)


@mark.order(3125)
def test_patch_registered_storeonce_with_description(context):
    """
    TestRail ID - C57582285
    Update the description field of a register storeOnce and refresh.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # Register storeonce
    validate_register_storeonces(context)

    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "OK")

    # Patch registered storeonce by adding a value to the description field.
    validate_patch_registered_storeonce(
        context,
        storeonce_id,
        description="Registered StoreOnce for local and cloud backup",
    )

    # Refesh the storeonce after patch
    validate_refresh_registered_storeonce(context, storeonce_id)

    # Check updated description value
    validate_storeonce_details(
        context,
        storeonce_id,
        description="Registered StoreOnce for local and cloud backup",
    )

    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3130)
def test_patch_registered_storeonce_with_fqdn(context):
    """
    TestRail ID - C57589894
    Update the network_address field of a register storeOnce and refresh.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # Register storeonce
    validate_register_storeonces(context)

    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "OK")

    # Patch registered storeonce by updating the ip address value with fqdn.
    validate_patch_registered_storeonce(context, storeonce_id, network_address=context.storeonces_fqdn)

    # Refesh the storeonce after patch
    validate_refresh_registered_storeonce(context, storeonce_id)

    # Check updated hostname value
    validate_storeonce_details(context, storeonce_id, network_address=context.storeonces_fqdn)

    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3135)
def test_patch_registered_storeonce_with_fqdn_and_description(context):
    """
    TestRail ID - C57589890
    Update the description and network address field of a register storeOnce and refresh.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # Register storeonce
    validate_register_storeonces(context)

    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "OK")

    # Patch registered storeonce by adding a value to the description field and updating the network address
    # IP address value with fqdn.
    validate_patch_registered_storeonce(
        context,
        storeonce_id,
        network_address=context.storeonces_fqdn,
        description="Registered StoreOnce for local and cloud backup",
    )

    # Refesh the storeonce after patch
    validate_refresh_registered_storeonce(context, storeonce_id)

    # Check updated description and network address value
    validate_storeonce_details(
        context,
        storeonce_id,
        network_address=context.storeonces_fqdn,
        description="Registered StoreOnce for local and cloud backup",
    )

    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3140)
def test_re_register_storeonces_with_wrong_password(context):
    """
    TestRail ID - C57582244
    Re-regiter storeOnce with wrong password.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # Register storeonce
    validate_register_storeonces(context)

    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "OK")

    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id)

    # Resetting DSCCAdmin user credentials
    reset_dsccAdmin_user_pwd(context)

    # re-register storeonce with wrong password
    validate_register_storeonces_with_invalid_parameters(context, password="invalid_password")

    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "ERROR")

    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3145)
def test_get_storeonces_details_with_invalid_UUID(context):
    """
    TestRail ID - C57589866
    get storeonce details with invalid UUID.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # validate get storeonce details call with an invalid UUID
    storeonce_id = uuid.uuid4()
    validate_get_storeonce_invalid_id(context, storeonce_id)


@mark.order(3150)
def test_patch_storeonces_details_with_invalid_UUID(context):
    """
    TestRail ID - C57589891
    Try Re-register storeonce details with invalid UUID.
    get storeonce details with invalid UUID.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # validate get storeonce details call with an invalid UUID
    storeonce_id = uuid.uuid4()
    validate_patch_storeonce_invalid_id(
        context,
        storeonce_id,
        network_address=context.storeonces_fqdn,
        description="Registered StoreOnce for local and cloud backup",
    )


@mark.order(3155)
def test_delete_storeonces_details_with_invalid_UUID(context):
    """
    TestRail ID - C57589892
    Delete storeonce details with invalid UUID.
    get storeonce details with invalid UUID.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # validate get storeonce details call with an invalid UUID
    storeonce_id = uuid.uuid4()
    validate_delete_storeonce_invalid_id(context, storeonce_id, force=False)


@mark.order(3160)
def test_refresh_storeonces_details_with_invalid_UUID(context):
    """
    TestRail ID - C57589893
    Refresh storeonce details with invalid UUID.
    get storeonce details with invalid UUID.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # validate get storeonce details call with an invalid UUID
    storeonce_id = uuid.uuid4()
    validate_refresh_storeonce_invalid_id(context, storeonce_id)


@mark.order(3165)
def test_unregister_storeonce_with_force_true(context):
    """
    TestRail ID - C57582262
    Register storeonce with a valid IP,base and encrytion license. Unregister with force set to true.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # Register storeonce
    validate_register_storeonces(context)

    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "OK")

    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id, force=True)


@mark.order(3170)
def test_register_storeonces_invalid_fqdn(context):
    """
    TestRail ID - C57582236
    Register storeonce with invalid fqdn.
    Args:
        context : fixture context
    """

    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # Register storeonce
    validate_register_storeonces_with_invalid_parameters(context, network_address="invalid.lab.nimblestorage.com")

    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "ERROR")

    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3175)
def test_register_storeonces_invalid_ip_address(context):
    """
    TestRail ID - C57582234
    Register storeonce with invalid ip address.
    Args:
        context : fixture context
    """

    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # Register storeonce
    validate_register_storeonces_with_invalid_parameters(context, network_address="1.2.3.4")

    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "ERROR")

    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3180)
def test_register_storeonces_wrong_credentials(context):
    """
    TestRail ID - C57582237
    Register storeonce with invalid DSCCAdmin user credentials.
    Args:
        context : fixture context
    """
    # Resetting context network_address values if previous testcase failed before resetting it will reset here.
    context.storeonces_network_address = context.storeonces_config["ip_address"]

    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # Register storeonce
    validate_register_storeonces_with_invalid_parameters(context, password="invalid_password")

    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "ERROR")

    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3185)
def test_register_storeonces_incorrect_serial_no(context):
    """
    TestRail ID - C57582238
    Register storeonce with incorrect serial number.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    invaild_serial_no = "N0TASERIALN0FOS0"
    # Register storeonce
    validate_register_storeonces_with_invalid_parameters(context, serial_no=invaild_serial_no)

    # Checking health state and status of storeonce in DSCC
    storeonce_id = get_storeonce_id(context)
    get_storeonce_health_status(context, storeonce_id, "ERROR")

    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3190)
def test_register_storeonces_with_no_encryption_license(context):
    """
    TestRail ID - C57582232
    Register storeonce without an encryption license.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    # Register storeonce
    validate_register_storeonces_with_invalid_parameters(context, encryption_license="False")

    # Checking health state and status of storeonce in DSCC
    storeonces_name = context.storeonces_config["no_encryption_name"]
    storeonce_id = get_storeonce_id(context, storeonces_name=storeonces_name)
    get_storeonce_health_status(context, storeonce_id, "ERROR")

    # Unregister storeonce
    validate_unregister_storeonces(context, storeonce_id)


@mark.order(3195)
def test_register_storeonces_incorrect_username(context):
    """
    TestRail ID - C57589888
    Register storeonce with incorrect username.
    Args:
        context : fixture context
    """
    # Reset DSCC user credentials
    reset_dsccAdmin_user_pwd(context)

    invaild_username = "NotDSCCAdminUser"

    # Register storeonce
    validate_register_storeonces_with_incorrect_format_parameters(context, username=invaild_username)
