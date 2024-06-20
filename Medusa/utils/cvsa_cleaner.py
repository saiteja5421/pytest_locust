"""
Script to cleanup resources on AWS for cVSA Manager by sending message to application on csp.cam.updates Kafka topic

usage: python3 -m utils.cvsa_cleaner [-h]
example: python3 -m utils.cvsa_cleaner
"""
import logging
from datetime import datetime, timedelta
from os import getenv
from typing import List

import lib.platform.kafka.protobuf.cloud_account_manager.account_pb2 as cam_pb2
from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.cloud.cloud_dataclasses import CloudInstance
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager, TopicEncoding
from tests.steps.aws_protection.cvsa.cloud_steps import get_creator_environment_name, get_arn_role

logging.getLogger("kafka").setLevel(logging.ERROR)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
stream_formatter = logging.Formatter(
    '{"time":"%(asctime)s","level":"%(levelname)s","path":"cVSA Cleaner","message":"%(message)s"}'
)
stream_handler.setFormatter(stream_formatter)
logger.addHandler(stream_handler)


def instance_is_older_than(instance_launch_time: datetime, age: timedelta) -> bool:
    age_actual = datetime.now() - instance_launch_time.replace(tzinfo=None)
    return age < age_actual


def cvsa_full_cleanup(region: str, environment: str, cloud_vm_mgr: CloudVmManager):
    logger.info(f"Cleaner started for regions: {region}")
    cam_updates_kafka = KafkaManager(topic="csp.cam.updates", topic_encoding=TopicEncoding.PROTOBUF)
    instances: List[CloudInstance] = cloud_vm_mgr.list_instances(location=region)
    for instance in instances:
        instance_id = instance.id
        logging.info(f"unregistering instance {instance_id}")
        instance_tags = instance.tags
        if Tag(Key="cvsa-creator-environment", Value=environment) not in instance_tags:
            logger.debug(
                f"Instance {instance_id}: " + f"cvsa-creator-environment is different than wanted (want={environment})"
            )
            continue
        cvsa_requester = "QA_cvsa.lifecycle.events"
        if Tag(Key="cvsa-requester", Value=cvsa_requester) not in instance_tags:
            logger.debug(
                f"Instance {instance_id}: "
                + f"cvsa-requester tag isn't related to regression tests (want={cvsa_requester})"
            )
            continue
        age_required = timedelta(hours=6)
        if not instance_is_older_than(instance.launch_time, age_required):
            logger.debug(
                f"Instance {instance_id}: " + f"not old enough to cleanup (required age={age_required.seconds}s)"
            )
            continue
        logger.info(f"Instance matches cvsa-creator-environment and cvsa-requester: {instance_id}")
        unregister_event = cam_pb2.CspAccountInfo()
        headers = {
            "ce_type": b"csp.cloudaccountmanager.v1.CspAccountInfo",
        }
        for tag in instance_tags:
            if tag.Key == "cvsa-application-customer-id":
                account_id = bytes(tag.Value, "utf-8")
                headers["ce_id"] = account_id
                headers["ce_partitionkey"] = account_id
                headers["ce_customerid"] = account_id
                cam_updates_kafka.account_id = account_id
            if tag.Key == "cvsa-cloud-account-manager-account-id":
                unregister_event.id = tag.Value
            if tag.Key == "cvsa-cloud-service-provider-account-id":
                unregister_event.service_provider_id = tag.Value
            if tag.Key == "cvsa-id":
                unregister_event.name = f"cVSA_Manager_Tests_Cleanup_{tag.Value}"
        unregister_event.paused = False
        unregister_event.status = cam_pb2._CSPACCOUNTINFO_STATUS.values_by_name["STATUS_UNREGISTERED"].number
        unregister_event.type = cam_pb2._CSPACCOUNTINFO_TYPE.values_by_name["TYPE_AWS"].number
        status = cam_pb2._CSPACCOUNTINFO_VALIDATIONSTATUS.values_by_name["VALIDATION_STATUS_FAILED"].number
        unregister_event.validation_status = status
        cam_updates_kafka.send_message(event=unregister_event, user_headers=headers)
        logger.info(f"Instance id: {instance_id} Unregister event sent")
    logger.info(f"Region {region} cleared")
    logger.info("Cleaner finished")


if __name__ == "__main__":
    region = getenv("AWS_REGION_ONE")
    env = get_creator_environment_name()
    if env and region:
        cloud_mgr = AWS(region_name=region, role_arn=get_arn_role()).ec2
        cvsa_full_cleanup(region, env, cloud_vm_mgr=cloud_mgr)
    else:
        logger.error("CREATOR_ENVIRONMENT_NAME or AWS_REGION_ONE env variable is not set")
        logger.error(f"CREATOR_ENVIRONMENT_NAME: {env}, AWS_REGION_ONE: {region}")
