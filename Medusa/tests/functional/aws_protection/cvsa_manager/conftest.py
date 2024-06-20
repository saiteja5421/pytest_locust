import logging
import re
from typing import Union

import pytest
from reportportal_client import RPLogger, RPLogHandler

from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.azure.azure_factory import Azure
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager, TopicEncoding
from lib.platform.kafka.protobuf.ropcvsamanager.v1alpha1 import cvsamanager_pb2_grpc as ropcvsamanager_pb2_grpc
from tests.functional.aws_protection.cvsa_manager.constants import (
    AWS_REGION_1_NAME,
    get_azure_resource_group_name,
    get_grpc_insecure_channel,
)
from tests.steps.aws_protection.cvsa.cloud_steps import get_arn_role, verify_not_deployed_cvsa
from tests.steps.aws_protection.cvsa.common_steps import cleanup_cvsa_instance
from tests.steps.aws_protection.cvsa.kafka import new_kafka_lifecycle_events
from tests.steps.aws_protection.cvsa.logging_steps import get_logging_formatter

logger_handlers_initialised = {}


def logger_handler_name(kafka: KafkaManager) -> str:
    return f"tc{kafka.tc_id}"


def set_rp_logger(node_config):
    # Create a handler for Report Portal if the service has been
    # configured and started.
    if hasattr(node_config, "py_test_service"):
        # Import Report Portal logger and handler to the test module.
        logging.setLoggerClass(RPLogger)
        rp_handler = RPLogHandler()
        rp_handler.setLevel(logging.INFO)
    else:
        rp_handler = logging.StreamHandler()
    return rp_handler


@pytest.fixture(scope="function", autouse=True)
def logger(request, kafka_mgr: Union[tuple[KafkaManager], KafkaManager]):
    global logger_handlers_initialised
    logger = logging.getLogger()
    logger.propagate = False
    logging.getLogger("kafka").setLevel(logging.ERROR)
    logging.getLogger("reportportal_client").setLevel(logging.NOTSET)
    logging.getLogger("pytest_reportportal").setLevel(logging.NOTSET)
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.ERROR)
    for kafka in kafka_mgr if isinstance(kafka_mgr, tuple) else [kafka_mgr]:
        if logger_handler_name(kafka) in logger_handlers_initialised:
            continue
        logger.setLevel(logging.INFO)
        stream_handler = set_rp_logger(node_config=request.node.config)
        stream_formatter = get_logging_formatter(kafka)
        stream_handler.setFormatter(stream_formatter)
        if logger.hasHandlers():
            logger.handlers.clear()
        logger.addHandler(stream_handler)
        logger_handlers_initialised[logger_handler_name(kafka)] = True


@pytest.fixture(scope="function")
def aws():
    yield AWS(region_name=AWS_REGION_1_NAME, role_arn=get_arn_role()).ec2


@pytest.fixture(scope="function")
def aws_s3():
    yield AWS(region_name=AWS_REGION_1_NAME, role_arn=get_arn_role()).s3


@pytest.fixture(scope="function")
def aws_eu_west():
    yield AWS(
        region_name="eu-west-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    ).ec2


@pytest.fixture(scope="function")
def azure():
    yield Azure(resource_group_name=get_azure_resource_group_name()).az_vm_manager


@pytest.fixture(scope="function")
def kafka_mgr(request) -> KafkaManager:
    if "azure" in request.fixturenames:
        cloud_vm_mgr = request.getfixturevalue("azure")
    elif "aws" in request.fixturenames:
        cloud_vm_mgr = request.getfixturevalue("aws")
    elif "aws_eu_west" in request.fixturenames:
        cloud_vm_mgr = request.getfixturevalue("aws_eu_west")
    elif "cloud_vm_mgr" in request.fixturenames:
        fixture_name = request.getfixturevalue("cloud_vm_mgr")
        cloud_vm_mgr = request.getfixturevalue(fixture_name)
    else:
        raise AttributeError(f"Wrong CloudVmManager fixture provided: {request.fixturenames}")
    test_case_ids = re.findall(r"tc(\d+)", request.node.name, re.IGNORECASE)
    tc_id = test_case_ids[0] if test_case_ids else "99"
    kafka_mgr = new_kafka_lifecycle_events(tc_id=int(tc_id))
    yield kafka_mgr
    logger = logging.getLogger()
    logger.info(10 * "=" + "Initiating Teardown" + 10 * "=")
    cleanup_cvsa_instance(cvsa_kafka=kafka_mgr, cloud_vm_mgr=cloud_vm_mgr)
    logger.info(10 * "=" + "Teardown Complete !!!" + 10 * "=")


@pytest.fixture(scope="function")
def cam_updates_kafka(aws: CloudVmManager):
    yield KafkaManager(topic="csp.cam.updates", topic_encoding=TopicEncoding.PROTOBUF)


@pytest.fixture(scope="function")
def grpc_service_stub():
    yield ropcvsamanager_pb2_grpc.CVSAManagerCrossClusterServiceStub(channel=get_grpc_insecure_channel())


@pytest.fixture(scope="function")
def kafka_mgr_ro_rw(request) -> tuple[KafkaManager, KafkaManager]:
    if "azure" in request.fixturenames:
        cloud_vm_mgr = request.getfixturevalue("azure")
    elif "aws" in request.fixturenames:
        cloud_vm_mgr = request.getfixturevalue("aws")
    else:
        raise AttributeError(f"Wrong CloudVmManager provided: {request.fixturenames}")
    kafka_mgr_rw = new_kafka_lifecycle_events(tc_id=38)
    kafka_mgr_ro = new_kafka_lifecycle_events(tc_id=38, account_id=kafka_mgr_rw.account_id)
    kafka_mgr_ro.cam_account_id = kafka_mgr_rw.cam_account_id
    kafka_mgr_ro.csp_account_id = kafka_mgr_rw.csp_account_id
    verify_not_deployed_cvsa(cloud_vm_mgr=cloud_vm_mgr, account_id=kafka_mgr_rw.account_id)
    yield kafka_mgr_rw, kafka_mgr_ro
    logger = logging.getLogger()
    logger.info(10 * "=" + "Initiating Teardown" + 10 * "=")
    cleanup_cvsa_instance(kafka_mgr_rw, cloud_vm_mgr)
    logger.info(10 * "=" + "Teardown Complete !!!" + 10 * "=")
