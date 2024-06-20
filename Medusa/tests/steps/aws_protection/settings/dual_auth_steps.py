import logging
from lib.common.enums.dual_auth_request import DualAuthRequest
from lib.common.enums.provided_users import ProvidedUser
from lib.dscc.settings.dual_auth.authorization.models.dual_auth_operation import (
    DualAuthOperation,
    DualAuthOperationList,
)
from lib.dscc.settings.dual_auth.authorization.models.dual_auth_settings import DualAuthSettings
from lib.dscc.settings.dual_auth.authorization.payload.patch_request_approve_deny import PatchRequestApproveDeny
from tests.e2e.aws_protection.context import Context
from waiting import wait, TimeoutExpired

logger = logging.getLogger()


def toggle_dual_auth_settings(context: Context, enable: bool = True) -> DualAuthSettings:
    """Toggles DualAuth setting to ON / OFF
    If setting to OFF, another authorized user needs to approve the pending request

    Args:
        enable (bool, optional): Sets DualAuth setting to 'ON' when set to 'True'. Defaults to True.

    Returns:
        DualAuthSettings: DualAuthSettings object
    """
    dual_auth_settings = context.dual_auth_manager.update_dual_auth_settings(enable=enable)
    return dual_auth_settings


def turn_off_dual_auth_setting(context: Context) -> DualAuthOperation:
    """Turns off DualAuth setting
    Initiates the action as user_one and approves as user_two

    Args:
        context (Context): Context object initialized with user_one

    Returns:
        DualAuthOperation: Approved request
    """
    dual_auth_settings = toggle_dual_auth_settings(context=context, enable=False)
    assert (
        dual_auth_settings.next_value == "OFF"
    ), f"Expected next value to be 'OFF' but found {dual_auth_settings.next_value}"

    pending_request = get_pending_request_by_name_and_resource_uri(
        context=context,
        pending_request_name="Change setting - Dual Auth to OFF",
        resource_uri="/api/v1/settings/1",
    )
    logger.info(f"Pending request to turn off dual auth found {pending_request}")

    logger.info("Approving request to turn off dual auth setting")
    dual_auth_context = Context(test_provided_user=ProvidedUser.user_two)
    dual_auth_request = authorize_dual_auth_request(context=dual_auth_context, id=pending_request.id, approve=True)
    return dual_auth_request


def get_dual_auth_operations(
    context: Context,
    request_state: str = "Pending",
    filter: str = "",
) -> DualAuthOperationList:
    """Returns all the pending DualAuth operations

    Args:
        context (Context): Context object
        request_state (str, optional): Request state of the DualAuth operations. Defaults to "Pending".
        filter (str, optional): Parameter to filter results based on name and other applicable fields

    Returns:
        DualAuthOperationList: DualAuthOperationList object
    """
    return context.dual_auth_manager.get_dual_auth_operations(request_state=request_state, filter=filter)


def get_pending_request_by_name_and_resource_uri(
    context: Context,
    pending_request_name: str,
    resource_uri: str,
) -> DualAuthOperation:
    """Returns pending request by its name and resource_uri

    Args:
        context (Context): Context object
        pending_request_name (str): Name of the pending request
        resource_uri (str): resource_uri of the resource for which the authorization is pending

    Raises:
        Exception: "Request not found" exception

    Returns:
        DualAuthOperation: DualAuthOperation object
    """
    filter = f"name eq '{pending_request_name}' and operationResource.resourceUri eq '{resource_uri}'"

    try:
        # Must always be 1 as we are filtering using 'resource_uri' field
        wait(
            lambda: len(get_dual_auth_operations(context=context, filter=filter).items) == 1,
            timeout_seconds=60,
            sleep_seconds=3,
        )
    except TimeoutExpired:
        # changing to logger.error temporarily until the 'operationResource.resourceUri' is fixed
        logger.error(f"Requests filtered by name {pending_request_name} and resource_uri {resource_uri} not found")

    pending_requests = get_dual_auth_operations(context=context, filter=filter)
    if pending_requests.items:
        return pending_requests.items[0]


def authorize_dual_auth_request(context: Context, id: str, approve: bool = True) -> DualAuthOperation:
    """Approves or Rejects a pending request

    Args:
        context (Context): Context object
        id (str): Id of the pending request
        approve (bool, optional): Approve / Reject action to be taken on the request. Defaults to True.

    Returns:
        DualAuthOperation: DualAuthOperation object of the request
    """
    checked_status = DualAuthRequest.APPROVED if approve else DualAuthRequest.CANCELLED
    request_payload = PatchRequestApproveDeny(checked_status=checked_status)

    action = "Approving" if approve else "Denying"
    logger.info(f"{action} request: {id}")
    dual_auth_request = context.dual_auth_manager.patch_request_approve_deny(id=id, request_payload=request_payload)
    return dual_auth_request
