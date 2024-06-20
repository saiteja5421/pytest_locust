"""
This module contains functions related to retrieving and validating Audit Events
"""

import logging
from datetime import datetime, timezone, timedelta
from time import sleep

from lib.common.users.user import User
from lib.dscc.audit.api.audit_events import AuditEvents
from lib.dscc.audit.models.audit_events import AuditEvent, AuditEventList

logger = logging.getLogger()


def get_user_audit_events(context_user: User, minutes_ago: int) -> list[AuditEvent]:
    """Get all Audit Events from "minutes_ago" until "now"

    Args:
        context_user (User): The Context User object
        minutes_ago (int): The number of minutes ago from which to request Audit Events

    Returns:
        list[AuditEvent]: The list of Audit Events returned from the API call
    """
    audit_events: AuditEvents = AuditEvents(context_user)

    # time to search from:  "loggedAt gt 2022-04-12T10:00:00Z" -> "time" == "now - minutes_ago"
    time_delta = timedelta(minutes=minutes_ago)
    # UTC timestamp
    now_utc = datetime.now().astimezone(timezone.utc)

    from_time = now_utc - time_delta
    # from_time is in format:  2022-04-19 17:38:09.498878+00:00
    # need to parse to:        2022-04-12T10:00:00Z
    time_filter: str = from_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    audit_event_list = audit_events.get_audit_events(filter=f"loggedAt gt {time_filter}").items

    return audit_event_list


def find_audit_events_by_permission(audit_events: list[AuditEvent], permission: str) -> list[AuditEvent]:
    """With the provided "audit_events" list, return a list containing only Audit Events with the provided "permission"

    Args:
        audit_events (list[AuditEvent]): The list of Audit Events to filter by permission
        permission (str): The permission to filter on the provided Audit Events list

    Returns:
        list[AuditEvent]: A list of Audit Events of the requested permission
    """
    return_list: list[AuditEvent] = []

    for event in audit_events:
        if event.permission == permission:
            return_list.append(event)

    return return_list


def validate_audit_events_for_user_permission(
    context_user: User,
    minutes_ago: int,
    permission: str,
    expected_state: str,
    min_num_events: int = 1,
    code: str = "",
    name: str = "",
) -> None:
    """Validate expected Audit Events for user permission.

    Args:
        context_user (User): The Context User object
        minutes_ago (int): The number of minutes ago from which to request Audit Events
        permission (str): The Permission to filter on the Audit Events
        expected_state (str): The expected State of the Audit Events
        min_num_events (int, optional): The minimum number of Audit Events expected in the validation call. Defaults to 1.
        code (str, optional): The Audit Event Code to further filter on the Audit Events list. Defaults to "".
        name (str, optional): The name of the asset to further filter on the Audit Events list. Defaults to "".
    """
    filtered_events = []
    len_filtered_events: int = 0
    for _ in range(5):
        audit_event_list = get_user_audit_events(context_user, minutes_ago)
        audit_event_list = [item for item in audit_event_list if item.userEmail == context_user.user.username]
        audit_event_list = [item for item in audit_event_list if item.state == expected_state]

        if code:
            audit_event_list = [item for item in audit_event_list if item.code == code]
        if name:
            audit_event_list = [item for item in audit_event_list if name in item.associatedResource.name]

        filtered_events = find_audit_events_by_permission(audit_event_list, permission)
        len_filtered_events: int = len(filtered_events)

        if len_filtered_events >= min_num_events:
            logger.info([event.state == expected_state for event in filtered_events])
            break
        else:
            sleep(30)

    assert (
        len_filtered_events >= min_num_events
    ), f"Insufficient Audit Events found for '{permission}', {len_filtered_events} vs {min_num_events}"


def verify_protection_policy_create_audit_event(context_user: User, policy_name: str):
    """Verify that a PROTECTION_POLICY_CREATE Audit Event exists for the provided "policy_name"

    Args:
        context_user (User): The Context User object
        policy_name (str): The Protection Policy name
    """
    audit_events: AuditEvents = AuditEvents(context_user)
    filter: str = f"code eq PROTECTION_POLICY_CREATE and associatedResource.name eq {policy_name}"
    audit_event_list: AuditEventList = audit_events.get_audit_events(limit=1, filter=filter)

    assert len(audit_event_list.items) == 1, f"PROTECTION_POLICY_CREATE event not found. Response: {audit_event_list}"
    logger.debug("Verified Audit log has expected event code PROTECTION_POLICY_CREATE")

    assert (
        audit_event_list.items[0].state == "Success"
    ), "Unexpected policy create event state {audit_event_list.items[0].state}"
    logger.debug("Verified Audit log has Success state policy create event")
