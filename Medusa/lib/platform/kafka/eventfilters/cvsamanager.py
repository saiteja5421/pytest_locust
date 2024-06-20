from kafka.protocol.message import Message

from lib.common.enums.cvsa import (
    AwsRegions,
    StopReason,
    TerminateReason,
    MaintenanceOperation,
    MaintenanceAction,
    CspAccountInfoStatus,
)
from .eventfilter import EventFilter
import lib.platform.kafka.protobuf.cloud_account_manager.account_pb2 as cam_pb2


def event_filter_type(event_type: str) -> EventFilter:
    def f(event: Message) -> bool:
        headers = dict(map(lambda x: (x[0], x[1]), event.headers))
        return bytes(event_type, "utf-8") in headers["ce_type"]

    return f


def event_filter_cam_id(cam_account_id: bytes) -> EventFilter:
    def f(event):
        if event.value.get("base"):
            result = True if event.value["base"].get("camAccountId") == cam_account_id.decode("utf-8") else False
            return result
        return True if event.value.get("camAccountId") == cam_account_id.decode("utf-8") else False

    return f


def event_filter_customer_id(customer_id: bytes) -> EventFilter:
    def f(event):
        return True if event.key.decode("utf-8") == customer_id.decode("utf-8") else False

    return f


def event_filter_correlation_id(correlation_id: bytes) -> EventFilter:
    def f(event):
        if event.value.get("base"):
            result = True if event.value["base"].get("correlationId") == correlation_id.decode("utf-8") else False
            return result
        return True if event.value.get("correlationId") == correlation_id.decode("utf-8") else False

    return f


def event_filter_cvsa_id(cvsa_id: str) -> EventFilter:
    def f(event):
        if event.value.get("base"):
            return True if event.value["base"].get("cvsaId") == cvsa_id else False
        return True if event.value.get("cvsaId") == cvsa_id else False

    return f


def event_filter_cloud_region(cloud_region: AwsRegions) -> EventFilter:
    def f(event):
        return True
        # TODO: Fix cloud region based filtering.
        # if event.value.get('base'):
        #     return lambda event: True if event.value['base'].get("cloudRegion") == str(cloud_region) else False
        # return lambda event: True if event.value.get("cloudRegion") == str(cloud_region) else False

    return f


def event_filter_csp_cam_id(csp_cam_id: str) -> EventFilter:
    return lambda event: True if bytes(csp_cam_id) in event.value else False


def event_filter_maintenance_operation_type(
    operation_type: MaintenanceOperation,
) -> EventFilter:
    return lambda event: True if event.value.get("operationType") == str(operation_type) else False


def event_filter_maintenance_action(action: MaintenanceAction) -> EventFilter:
    return lambda event: True if event.value.get("action") == str(action) else False


def event_filter_stop_reason(reason: StopReason) -> EventFilter:
    return lambda event: True if "reason" in event.value and event.value["reason"] == str(reason) else False


def event_filter_terminate_reason(reason: TerminateReason) -> EventFilter:
    return lambda event: True if "reason" in event.value and event.value["reason"] == str(reason) else False


def event_filter_cloud_instance_id(cloud_instance_id: str) -> EventFilter:
    return (
        lambda event: True
        if "cloudInstanceId" in event.value and event.value["cloudInstanceId"] == cloud_instance_id
        else False
    )


def event_filter_trace_id(trace_id) -> EventFilter:
    def f(event: Message) -> bool:
        headers = dict(map(lambda x: (x[0], x[1]), event.headers))
        trace = trace_id.split("-")[0]
        return bytes(trace, "utf-8") in headers["ce_tracestate"]

    return f


def event_filter_catalyst_gateway_id(catalyst_gateway_id: str) -> EventFilter:
    return (
        lambda event: True if event.value and event.value[0].get("catalystGatewayId") == catalyst_gateway_id else False
    )


def event_filter_csp_account_info_status(status: CspAccountInfoStatus) -> EventFilter:
    def f(event: Message) -> bool:
        csp_account_info_event = cam_pb2.CspAccountInfo()
        csp_account_info_event.ParseFromString(event.value)
        return csp_account_info_event.status == status.value

    return f
