"""
TestRail ID - C57484230
  Workflow - Get CSP Accounts - A workflow that tests different GET csp-accounts REST requests
"""

import itertools
import logging
import random
import uuid

from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from http import HTTPStatus
from pytest import fixture, mark
from pytest_testrail.plugin import pytestrail
from requests import codes, Response
from waiting import wait

import lib.platform.kafka.protobuf.inventory_manager.account_pb2 as account_pb2
import lib.platform.kafka.protobuf.cloud_account_manager.account_pb2 as cam_account_pb2


from lib.common.config.config_manager import ConfigManager
from lib.common.enums.atlantia_kafka_events import AtlantiaKafkaEvents
from lib.common.enums.atlantia_kafka_topics import AtlantiaKafkaTopics
from lib.common.enums.provided_users import ProvidedUser
from lib.dscc.backup_recovery.csp_account.rest.v1beta1.model.csp_account import (
    CSPAccount,
    CSPAccountList,
)
from lib.common.enums.csp_type import CspType
from lib.common.enums.refresh_status import CSPK8sRefreshStatus
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    GLCPErrorResponse,
)
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.e2e.aws_protection.context import Context
from tests.steps.aws_protection.common_steps import send_kafka_message


##############################################################################################################
# MODULE VARIABLES AND TEST SETTINGS
##############################################################################################################

config = ConfigManager.get_config()
logger = logging.getLogger()


##############################################################################################################
# FIXTURES
##############################################################################################################


@fixture(scope="module")
def context():
    context = Context(test_provided_user=ProvidedUser.user_one, initialize_minimal=True)
    return context


@fixture(scope="module")
def csp_accounts(context: Context):
    # Register an AWS account
    start = 100000000000
    stop = 1000000000000
    arn = "arn:aws:iam::" + str(random.randrange(start, stop)) + ":"
    aws_account_name = "AWSAccount-" + str(uuid.uuid4())
    aws_account: CSPAccount = context.cam_client_v1beta1.create_csp_account(
        csp_id=arn, name=aws_account_name, csp_type=CspType.AWS
    )

    # Register an Azure account
    tenant_id = str(uuid.uuid4())
    azure_account_name = "AzureAccount-" + str(uuid.uuid4())
    azure_account: CSPAccount = context.cam_client_v1beta1.create_csp_account(
        csp_id=tenant_id, name=azure_account_name, csp_type=CspType.AZURE
    )

    yield aws_account, azure_account

    logger.info(10 * "=" + "Initiating Teardown" + 10 * "=")

    # Unregister the AWS account
    context.cam_client_v1beta1.delete_csp_account(account_id=aws_account.id)

    # Unregister the Azure account
    context.cam_client_v1beta1.delete_csp_account(account_id=azure_account.id)

    logger.info(10 * "=" + "Teardown Complete!" + 10 * "=")


##############################################################################################################
# FUNCTIONAL TESTS
##############################################################################################################


@mark.cam_localstack_serial
@pytestrail.case("C57484230")
def test_get_csp_accounts(context: Context, csp_accounts: tuple[CSPAccount, CSPAccount]):
    """
        Functional test that tests various requests for the GET CSP Accounts REST endpoint.

    Args:
        context (Context): test execution context
        csp_accounts (tuple[CSPAccount, CSPAccount]): fixture that registers and yields an AWS account and Azure account
    """
    # Step 1 - Fixture takes care of registering the accounts
    aws_account, azure_account = csp_accounts

    # Step 2 - Validate GET CSP Account requests with valid offset queries return expected responses
    empty_csp_account_list: CSPAccountList = CSPAccountList(items=[], count=0, offset=2, total=2)
    single_azure_account_list: CSPAccountList = CSPAccountList(items=[azure_account], count=1, offset=1, total=2)

    offsets_and_expected_responses = [
        {
            "offset": 1,
            "expected_response": single_azure_account_list,
        },
        {
            "offset": 2,
            "expected_response": empty_csp_account_list,
        },
    ]
    for offset_and_expected_response in offsets_and_expected_responses:
        offset = offset_and_expected_response["offset"]
        expected_response = offset_and_expected_response["expected_response"]
        validate_get_csp_accounts(context=context, expected_response=expected_response, offset=offset)

    # Step 3 - Validate GET CSP Account requests with valid limit queries return expected responses
    single_aws_account_list: CSPAccountList = CSPAccountList(items=[aws_account], count=1, offset=0, total=2)
    all_accounts_list: CSPAccountList = CSPAccountList(items=[aws_account, azure_account], count=2, offset=0, total=2)

    limits_and_expected_responses = [
        {
            "limit": 1,
            "expected_response": single_aws_account_list,
        },
        {
            "limit": 2,
            "expected_response": all_accounts_list,
        },
    ]
    for limit_and_expected_response in limits_and_expected_responses:
        limit = limit_and_expected_response["limit"]
        expected_response = limit_and_expected_response["expected_response"]
        validate_get_csp_accounts(context=context, expected_response=expected_response, limit=limit)

    # Step 4 - Validate GET CSP Account requests with valid filters return expected responses
    empty_csp_account_list: CSPAccountList = CSPAccountList(items=[], count=0, offset=0, total=0)
    single_aws_account_list: CSPAccountList = CSPAccountList(items=[aws_account], count=1, offset=0, total=1)
    single_azure_account_list: CSPAccountList = CSPAccountList(items=[azure_account], count=1, offset=0, total=1)
    other_csp_id = str(uuid.uuid4())
    other_id = str(uuid.uuid4())
    filters_and_expected_responses = [
        {
            "filter": f"id eq '{other_id}'",
            "expected_response": empty_csp_account_list,
        },
        {
            "filter": f"cspId eq '{other_csp_id}'",
            "expected_response": empty_csp_account_list,
        },
        {
            "filter": "name eq 'account_name'",
            "expected_response": empty_csp_account_list,
        },
        {
            "filter": "suspended eq true",
            "expected_response": empty_csp_account_list,
        },
        {
            "filter": "validationStatus eq 'PASSED'",
            "expected_response": empty_csp_account_list,
        },
        {
            "filter": "validatedAt eq '1970-01-01T00:00:00.000Z'",
            "expected_response": empty_csp_account_list,
        },
        {
            "filter": f"id eq '{aws_account.id}'",
            "expected_response": single_aws_account_list,
        },
        {
            "filter": f"cspId eq '{aws_account.csp_id}'",
            "expected_response": single_aws_account_list,
        },
        {
            "filter": f"name eq '{aws_account.name}'",
            "expected_response": single_aws_account_list,
        },
        {
            "filter": f"id eq '{aws_account.id}'",
            "expected_response": single_aws_account_list,
        },
        {
            "filter": f"cspId eq '{aws_account.csp_id}'",
            "expected_response": single_aws_account_list,
        },
        {
            "filter": f"name eq '{azure_account.name}'",
            "expected_response": single_azure_account_list,
        },
        {
            "filter": f"id eq '{azure_account.id}'",
            "expected_response": single_azure_account_list,
        },
        {
            "filter": f"cspId eq '{azure_account.csp_id}'",
            "expected_response": single_azure_account_list,
        },
        {
            "filter": "cspType eq 'AWS'",
            "expected_response": single_aws_account_list,
        },
        {
            "filter": "cspType eq 'AZURE'",
            "expected_response": single_azure_account_list,
        },
    ]
    for filter_and_expected_response in filters_and_expected_responses:
        filter = filter_and_expected_response["filter"]
        expected_response = filter_and_expected_response["expected_response"]
        validate_get_csp_accounts(context=context, expected_response=expected_response, filter=filter)

    # Step 5 - Validate GET CSP Account requests with invalid filters return errors
    validation_status_expected_error_prefix = (
        'invalid input(s): filter value "12345677889" is not one of the recognized values for '
        'field "validationStatus": '
    )
    validation_statuses = ["UNVALIDATED", "PASSED", "FAILED"]
    validation_statuses_permutations = list(itertools.permutations(validation_statuses))
    validation_statuses_permutations = [
        "["
        + str(validation_statuses_permutation).replace("(", "").replace(")", "").replace("'", "").replace(",", "")
        + "]"
        for validation_statuses_permutation in validation_statuses_permutations
    ]
    validation_status_expected_errors = [
        GLCPErrorResponse(
            message=validation_status_expected_error_prefix + validation_statuses_permutation,
            errorCode="HPE_GL_ERROR_BAD_REQUEST",
            httpStatusCode=HTTPStatus.BAD_REQUEST.value,
            debugId="",
        )
        for validation_statuses_permutation in validation_statuses_permutations
    ]

    filters_and_expected_errors = [
        {
            "filter": "id eq '12345677889'",
            "expected_errors": [
                GLCPErrorResponse(
                    message='invalid input(s): filter value "12345677889" for field "id" is not a UUID',
                    errorCode="HPE_GL_ERROR_BAD_REQUEST",
                    httpStatusCode=HTTPStatus.BAD_REQUEST.value,
                    debugId="",
                )
            ],
        },
        {
            "filter": "cspType eq 'Test'",
            "expected_errors": [
                GLCPErrorResponse(
                    message=(
                        'invalid input(s): filter value "Test" is not one of the recognized values for field "cspType":'
                        " [AWS AZURE MS365]"
                    ),
                    errorCode="HPE_GL_ERROR_BAD_REQUEST",
                    httpStatusCode=HTTPStatus.BAD_REQUEST.value,
                    debugId="",
                ),
                GLCPErrorResponse(
                    message=(
                        'invalid input(s): filter value "Test" is not one of the recognized values for field "cspType":'
                        " [AWS MS365 AZURE]"
                    ),
                    errorCode="HPE_GL_ERROR_BAD_REQUEST",
                    httpStatusCode=HTTPStatus.BAD_REQUEST.value,
                    debugId="",
                ),
                GLCPErrorResponse(
                    message=(
                        'invalid input(s): filter value "Test" is not one of the recognized values for field "cspType":'
                        " [AZURE AWS MS365]"
                    ),
                    errorCode="HPE_GL_ERROR_BAD_REQUEST",
                    httpStatusCode=HTTPStatus.BAD_REQUEST.value,
                    debugId="",
                ),
                GLCPErrorResponse(
                    message=(
                        'invalid input(s): filter value "Test" is not one of the recognized values for field "cspType":'
                        " [AZURE MS365 AWS]"
                    ),
                    errorCode="HPE_GL_ERROR_BAD_REQUEST",
                    httpStatusCode=HTTPStatus.BAD_REQUEST.value,
                    debugId="",
                ),
                GLCPErrorResponse(
                    message=(
                        'invalid input(s): filter value "Test" is not one of the recognized values for field "cspType":'
                        " [MS365 AWS AZURE]"
                    ),
                    errorCode="HPE_GL_ERROR_BAD_REQUEST",
                    httpStatusCode=HTTPStatus.BAD_REQUEST.value,
                    debugId="",
                ),
                GLCPErrorResponse(
                    message=(
                        'invalid input(s): filter value "Test" is not one of the recognized values for field "cspType":'
                        " [MS365 AZURE AWS]"
                    ),
                    errorCode="HPE_GL_ERROR_BAD_REQUEST",
                    httpStatusCode=HTTPStatus.BAD_REQUEST.value,
                    debugId="",
                ),
            ],
        },
        {
            "filter": "suspended eq 'true1'",
            "expected_errors": [
                GLCPErrorResponse(
                    message="invalid input(s): filter invalid value true1 for field account.suspended",
                    errorCode="HPE_GL_ERROR_BAD_REQUEST",
                    httpStatusCode=HTTPStatus.BAD_REQUEST.value,
                    debugId="",
                )
            ],
        },
        {
            "filter": "validationStatus eq '12345677889'",
            "expected_errors": validation_status_expected_errors,
        },
    ]
    for filter_and_expected_error in filters_and_expected_errors:
        filter = filter_and_expected_error["filter"]
        expected_errors = filter_and_expected_error["expected_errors"]
        validate_get_csp_accounts_error(context, filter, expected_errors)

    # Step 6 - Validate GET CSP Account requests with valid sort queries return expected responses
    all_accounts_list: CSPAccountList = CSPAccountList(items=[aws_account, azure_account], count=2, offset=0, total=2)

    sorts_and_expected_responses = [
        {
            "sort": "cspType",
            "expected_response": all_accounts_list,
        },
    ]
    for sort_and_expected_response in sorts_and_expected_responses:
        sort = sort_and_expected_response["sort"]
        expected_response = sort_and_expected_response["expected_response"]
        validate_get_csp_accounts(context=context, expected_response=expected_response, sort=sort)

    # Step 7 - Validate account refreshStatus is updated after sending account sync info event
    validate_account_sync_info(context, aws_account)

    validate_account_sync_info(context, azure_account)


##############################################################################################################
# FUNCTIONAL TEST SUPPORT ROUTINES
##############################################################################################################


def validate_get_csp_accounts(
    context: Context,
    expected_response: CSPAccountList,
    offset: int = 0,
    limit: int = 1000,
    filter: str = "",
    sort: str = "name",
):
    """
        Validate that GET CSP Accounts returns the expected response.

    Args:
        context (Context): test execution context
        expected_response (CSPAccountList): expected account list returned from the REST request
        offset (str): offset query for the REST request
        filter (str): filter query for the REST request
    """
    # Fetch CSP Accounts
    csp_accounts: CSPAccountList = context.cam_client_v1beta1.get_csp_accounts(
        offset=offset, limit=limit, sort=sort, filter=filter
    )
    assert csp_accounts == expected_response


def validate_get_csp_accounts_error(context: Context, filter: str, expected_errors: list[GLCPErrorResponse]):
    """
        Validate that GET CSP Accounts returns the expected error.

    Args:
        context (Context): test execution context
        filter (str): filter query for the REST request
        expected_errors (list[GLCPErrorResponse]): list of expected errors. Actual error should match one of the expected
        errors
    """
    # Fetch Response
    actual_response: Response = context.cam_client_v1beta1.raw_get_csp_accounts(filter=filter)
    assert actual_response.status_code != codes.ok
    actual_error: GLCPErrorResponse = GLCPErrorResponse(**actual_response.json())
    for expected_error in expected_errors:
        if (
            actual_error.message == expected_error.message
            and actual_error.errorCode == expected_error.errorCode
            and actual_error.httpStatusCode == expected_error.httpStatusCode
        ):
            return
    assert False, f'For filter: "{filter}", actual error: "{actual_error}" does not match any of the expected errors'


def validate_account_sync_info(context: Context, csp_account: CSPAccount):
    """
        Send AccountSyncInfo event to CAM.

    Args:
        context (Context): test execution context
        csp_account (CSPAccount): The CSP Account whose sync info is being modified
    """
    last_synced_at = send_account_sync_info_event(context, csp_account)
    rds_last_synced_at = send_rds_account_sync_info_event(context, csp_account)
    csp_account: CSPAccount = context.cam_client_v1beta1.get_csp_account_by_id(account_id=csp_account.id)
    csp_account.inventory_refresh_info
    assert csp_account.inventory_refresh_info[0].inventory_type == "MACHINE_INSTANCES_AND_VOLUMES"
    assert csp_account.inventory_refresh_info[0].status == CSPK8sRefreshStatus.ok
    _compare_sync_times(csp_account.inventory_refresh_info[0].started_at, last_synced_at)
    if csp_account.csp_type == CspType.AWS:
        assert csp_account.inventory_refresh_info[1].inventory_type == "RDS"
        assert csp_account.inventory_refresh_info[1].status == CSPK8sRefreshStatus.ok
        _compare_sync_times(csp_account.inventory_refresh_info[1].started_at, rds_last_synced_at)


# TODO: Once IM is using CAM's proto definitions, modify helper to accommodate other managers beyond RDS
def send_rds_account_sync_info_event(context: Context, csp_account: CSPAccount):
    """
        Send AccountSyncInfo event to CAM with AssetCategory 'RDS'.

    Args:
        context (Context): test execution context
        csp_account (CSPAccount): The CSP Account whose sync info is being modified
    """
    requested_event = cam_account_pb2.AccountSyncInfo()
    requested_event.account_id = str(csp_account.id)
    timestamp = Timestamp()
    timestamp.GetCurrentTime()
    requested_event.last_synced_at.CopyFrom(timestamp)
    requested_event.last_sync_status = 1
    requested_event.asset_category = cam_account_pb2.AccountSyncInfo().AssetCategory.ASSET_CATEGORY_DATABASE

    logger.info(f"requested_event = {requested_event}")

    kafka_manager = KafkaManager(topic=AtlantiaKafkaTopics.CSP_CAM_COMMANDS.value, host=config["KAFKA"]["host"])
    send_kafka_message(
        kafka_manager=kafka_manager,
        requested_event=requested_event,
        event_type=AtlantiaKafkaEvents.CSP_ACCOUNT_SYNC_INFO_EVENT_TYPE.value,
        customer_id=context.get_customer_id(),
    )

    def _wait_for_message_consume():
        current_offset, _ = kafka_manager.consumer_group_offset("cloud_account_manager", 0)
        return current_offset >= end_offset

    _, end_offset = kafka_manager.consumer_group_offset("cloud_account_manager", 0)

    # wait for Kafka message processing
    wait(_wait_for_message_consume, timeout_seconds=120, sleep_seconds=1)

    return (
        datetime.fromtimestamp(timestamp.seconds + timestamp.nanos / 1e9).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-2] + "Z"
    )


def send_account_sync_info_event(context: Context, csp_account: CSPAccount):
    """
        Send AccountSyncInfo event to CAM.

    Args:
        context (Context): test execution context
        csp_account (CSPAccount): The CSP Account whose sync info is being modified
    """
    requested_event = account_pb2.AccountSyncInfo()
    requested_event.account_id = str(csp_account.id)
    timestamp = Timestamp()
    timestamp.GetCurrentTime()
    requested_event.last_synced_at.CopyFrom(timestamp)
    requested_event.last_sync_status = 1

    logger.info(f"requested_event = {requested_event}")

    kafka_manager = KafkaManager(
        topic=AtlantiaKafkaTopics.CSP_INVENTORY_UPDATES.value,
        host=config["KAFKA"]["host"],
    )
    send_kafka_message(
        kafka_manager=kafka_manager,
        requested_event=requested_event,
        event_type=AtlantiaKafkaEvents.ACCOUNT_SYNC_INFO_EVENT_TYPE.value,
        customer_id=context.get_customer_id(),
    )

    def _wait_for_message_consume():
        current_offset, _ = kafka_manager.consumer_group_offset("cam_client_v1beta1", 0)
        return current_offset >= end_offset

    _, end_offset = kafka_manager.consumer_group_offset("cam_client_v1beta1", 0)

    # wait for Kafka message processing
    wait(_wait_for_message_consume, timeout_seconds=120, sleep_seconds=1)

    return (
        datetime.fromtimestamp(timestamp.seconds + timestamp.nanos / 1e9).strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-2] + "Z"
    )


def _compare_sync_times(time_from_api_response: str, time_in_kafka_message: str):
    """Comparing an account's refreshAt time
    The API response is returning a different length for milliseconds. Eg.:
    2023-04-14T09:48:35.083227Z
    2023-04-14T09:48:35.07535Z

    Args:
        time_from_api_response (str): refreshedAt value for an account
        time_in_kafka_message (str): value of requested_event.last_synced_at for the account's Kafka message
    """
    if len(time_from_api_response.split(".")[-1]) == 6:
        assert time_from_api_response == time_in_kafka_message, f"{time_from_api_response=}, {time_in_kafka_message=}"
    elif len(time_from_api_response.split(".")[-1]) == 7:
        assert (
            time_from_api_response[:-2] + "Z" == time_in_kafka_message
        ), f"time_from_api_response={time_from_api_response[:-2] + 'Z'}, {time_in_kafka_message=}"
