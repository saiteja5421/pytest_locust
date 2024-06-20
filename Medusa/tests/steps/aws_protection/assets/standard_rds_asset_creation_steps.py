"""
This module contains functions related to the creation and deletion of RDS DB Instances and an accompanying EC2 Bastion
"""

import logging
import random
import uuid
from typing import Union

# Internal libraries
from lib.common.enums.aws_availability_zone import AWSAvailabilityZone
from lib.common.enums.db_engine import DBEngine
from lib.common.enums.db_instance_class import DBInstanceClass
from lib.common.enums.db_port import DBPort
from lib.common.enums.ec2_state import Ec2State
from lib.common.enums.os import OS

from lib.dscc.backup_recovery.aws_protection.common.models.rds_asset_set import RDSAssetSet
from lib.dscc.backup_recovery.aws_protection.common.models.rds_common_objects import (
    RDSDBConnection,
    RDSDBEnginesCountsPorts,
)

from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.aws_boto3.models.instance import Tag

from tests.e2e.aws_protection.context import Context

# Steps
import tests.steps.aws_protection.assets.standard_asset_creation_steps as StdAssetSteps
import tests.steps.aws_protection.rds.aws_rds_steps as AWSRDSSteps
import tests.steps.aws_protection.rds.csp_rds_inventory_manager_steps as RDSInvMgrSteps

logger = logging.getLogger()

RDS_BASTION_KEY: str = "RDS_Standard"
RDS_BASTION_VALUE: str = "EC2_Bastion"

RDS_EC2_BASTION_TAG: Tag = Tag(Key=RDS_BASTION_KEY, Value=RDS_BASTION_VALUE)


def create_ec2_bastion(
    aws: AWS,
) -> tuple[str, str]:
    """Create an EC2 Bastion. Used to access RDS Instances.

    Args:
        aws (AWS): The AWS Account

    Returns:
        tuple[str, str]: The EC2 Instance ID of the EC2 Bastion created, and the Key Pair Name generated for Bastion access
    """
    ec2_key_pair_name: str = f"ec2_rds_bastion-{str(uuid.uuid4())}"

    # Grab the VPC with DNS Support Enabled so that EC2 will have DNS Name/IP supported
    vpc = aws.vpc.get_vpc(public_dns_support=True)

    availability_zone = [
        zone["ZoneName"] for zone in aws.ec2.ec2_client.describe_availability_zones()["AvailabilityZones"]
    ][0]
    subnet = [
        subnet
        for subnet in aws.subnet.get_all_subnets()
        if ((subnet.availability_zone == availability_zone) and (subnet.vpc_id == vpc.id))
    ][0]
    security_group = [
        security_group
        for security_group in aws.security_group.get_all_security_groups()
        if security_group.vpc_id == subnet.vpc_id
    ][-1]

    aws.security_group.update_security_group_ingress_allow_all(security_group)

    StdAssetSteps.generate_key_pair(
        aws,
        ec2_key_pair_name,
    )

    ubuntu_image = StdAssetSteps.get_latest_ami_image_filters(aws, OS.UBUNTU)

    ec2_instances = aws.ec2.create_custom_config_ec2_instances(
        key_name=ec2_key_pair_name,
        image_id=ubuntu_image,
        availability_zone=availability_zone,
        subnet_id=subnet.id,
        security_groups=[security_group.id],
        tags=[
            Tag(
                Key="Name",
                Value=ec2_key_pair_name,
            ),
            RDS_EC2_BASTION_TAG,
        ],
    )

    return (
        ec2_instances[0].id,
        ec2_key_pair_name,
    )


def delete_rds_standard_asset_ec2_bastions(aws: AWS):
    """Delete all EC2 Bastions in AWS region

    Args:
        aws (AWS): The AWS Account
    """
    ec2_instances = aws.ec2.get_instances_by_tag(tag=RDS_EC2_BASTION_TAG)
    for ec2 in ec2_instances:
        key_pair = ec2.key_name
        aws.ec2.terminate_ec2_instance(ec2_instance_id=ec2.id)
        logger.info(f"Bastion deleted: {ec2.id}")
        aws.ec2.delete_key_pair(key_name=key_pair)
        logger.info(f"key_pair deleted: {key_pair}")


def setup_rds_standard_asset_ec2_bastion(
    aws: AWS,
) -> tuple[str, str]:
    """Get or create an EC2 Bastion

    Args:
        aws (AWS): The AWS Account

    Returns:
        tuple[str, str]: The EC2 Instance ID of the EC2 Bastion, and its assigned Key Pair Name
    """
    # Get any bastion EC2 instances by Tag
    ec2_instances = aws.ec2.get_instances_by_tag(tag=RDS_EC2_BASTION_TAG)

    # keep only "running" bastions from returned list
    ec2_instances = [ec2 for ec2 in ec2_instances if ec2.state["Name"] == Ec2State.RUNNING.value]

    # if we have some instances, grab the 1st one
    if len(ec2_instances):
        ec2_bastion_id = ec2_instances[0].id
        ec2_key_pair_name = ec2_instances[0].key_name
        logger.info(f"RDS bastion found: {ec2_bastion_id}")
    else:
        (
            ec2_bastion_id,
            ec2_key_pair_name,
        ) = create_ec2_bastion(aws=aws)
        logger.info(f"created RDS bastion: {ec2_bastion_id}")

    return (
        ec2_bastion_id,
        ec2_key_pair_name,
    )


def create_rds_standard_assets(
    aws: AWS,
    context: Context,
    csp_account_id: str,
    rds_asset_set: RDSAssetSet,
    tags: list[Tag] = [],
    any_db_count: int = None,
    db_engines_counts_ports: list[RDSDBEnginesCountsPorts] = [
        RDSDBEnginesCountsPorts(
            db_engine=DBEngine.POSTGRES,
            db_count=1,
            db_port=DBPort.POSTGRES.value,
        ),
    ],
) -> Union[RDSAssetSet, None]:
    """Get or create RDS Standard Assets

    Args:
        aws (AWS): AWS factory object
        context (Context): Atlantia context object
        csp_account_id (str): The CSP Account ID to use for RDS Inventory Refresh
        rds_asset_set (RDSAssetSet): Context asset set attribute
        tags (list[Tag], optional): Tag key value list. Defaults to [].
        any_db_count (int, optional): Total of DB required (one each) system will create in random choice of
            postgres, mysql, mariadb, sqlserver and oracle. Note: any_db_count should be 5 or less. Defaults to None.
        db_engines_counts_ports (list[RDSDBEnginesCountsPorts], optional): List of db name, db count and db port
            in the format RDSDBEnginesCountsPorts(db_engine=DBEngine.POSTGRES, db_count=1, db_port=DBPort.POSTGRES.value)
            Note: If any_db_count is not none then db_engines_counts_ports should be empty.
            If db_engines_counts_ports is not empty then any_db_count should be none. Defaults to [ RDSDBEnginesCountsPorts( db_engine=DBEngine.POSTGRES, db_count=1, db_port=DBPort.POSTGRES.value, ), ].

    Returns:
        Union[RDSAssetSet, None]: A populated RDSAssetSet is returned if RDS Instance request can be satisfied.  None is returned if "any_db_count" and "db_engines_counts_ports" are both invalid
    """
    # we must have at least 1 Tag.  If none are provided, set default for discovery with "_update_standard_rds_asset_details()"
    if not tags:
        tags = [Tag(Key="Standard", Value="Test")]

    # Check if EC2 Bastion exists
    (
        ec2_bastion_id,
        ec2_key_pair_name,
    ) = setup_rds_standard_asset_ec2_bastion(aws=aws)

    # input list of RDS assets to choose DB randomly
    list_of_db_engines_counts_ports = [
        RDSDBEnginesCountsPorts(
            db_engine=DBEngine.POSTGRES,
            db_count=1,
            db_port=DBPort.POSTGRES.value,
        ),
        RDSDBEnginesCountsPorts(
            db_engine=DBEngine.MARIADB,
            db_count=1,
            db_port=DBPort.MARIADB.value,
        ),
        RDSDBEnginesCountsPorts(
            db_engine=DBEngine.MYSQL,
            db_count=1,
            db_port=DBPort.MYSQL.value,
        ),
        RDSDBEnginesCountsPorts(
            db_engine=DBEngine.ORACLE_EE,
            db_count=1,
            db_port=DBPort.ORACLE.value,
        ),
        RDSDBEnginesCountsPorts(
            db_engine=DBEngine.SQLSERVER_EX,
            db_count=1,
            db_port=DBPort.SQLSERVER.value,
        ),
    ]
    db_name_prefix = "strd" + str(
        random.randrange(
            50,
            100,
            1,
        )
    )
    db_identifier_prefix = "strd" + str(
        random.randrange(
            50,
            100,
            1,
        )
    )
    # check if standard assets exists
    discovered_asset_set = _update_standard_rds_asset_details(
        aws,
        rds_asset_set,
        ec2_bastion_id,
        ec2_key_pair_name,
        tag=tags[0],
    )
    # if we have an asset_set returned, we found our standard asset will adjust the dbname and count if it is less
    discovered_asset_count = len(discovered_asset_set.rds_db_connection_list)
    discovered_asset_list = discovered_asset_set.rds_db_connection_list
    logger.info(f"We found: {discovered_asset_count} standard assets in the availability region {aws.region_name}")

    if any_db_count:
        logger.info(f"Any DB count is : {any_db_count} so comparing count of discovered db vs expected db")
        if discovered_asset_count >= any_db_count:
            logger.info(f"Discovered asset: {discovered_asset_count} greater than required DB as  {any_db_count}")
            return discovered_asset_set
        else:
            logger.info(f"Discovered asset count: {discovered_asset_count} is less than required DB as  {any_db_count}")
            any_db_count = any_db_count - discovered_asset_count
            logger.info(f"We require {any_db_count} more standard assets to be created in the region")
            db_engines_counts_ports = random.sample(
                list_of_db_engines_counts_ports,
                any_db_count,
            )
            logger.info(f"RDS db expected to be created are {db_engines_counts_ports}")
    # This case is for when any db count is None and user requested for specific DB and adjust per assets
    elif db_engines_counts_ports:
        logger.info("comparing the list of db count provided by user with discovered DB")
        logger.info(f"Actual requested dname list details are : {db_engines_counts_ports}")
        db_engines_counts_ports = _updated_dbname_count(
            aws,
            db_engines_counts_ports,
            discovered_asset_list,
        )
        logger.info(f"updated list after excluding discovered DB: {db_engines_counts_ports}")
    else:
        logger.info(
            f"Exiting the test as both inputs db_engine_counts_and_ports {db_engines_counts_ports} and any_db_count are {any_db_count}"
        )
        return None
    rds_asset_set.rds_db_connection_list.extend(discovered_asset_set.rds_db_connection_list)

    # if requested db engine and count are match with discovered DB then will only return rdsasset with discovered
    if db_engines_counts_ports:
        rds_db_connection_list: list[RDSDBConnection] = AWSRDSSteps.create_rds_instances_with_custom_configurations(
            aws=aws,
            db_name=db_name_prefix,
            db_identifier_prefix=db_identifier_prefix,
            allocated_storage=10,
            availability_zone=AWSAvailabilityZone(aws.ec2.get_availability_zone()),
            max_allocated_storage=15,
            db_instance_class=DBInstanceClass.DB_T3_MICRO,
            db_engines_counts_ports=db_engines_counts_ports,
            master_username="AtlantiaTestRDS",
            master_password=AWSRDSSteps.get_rds_password(),
            publicly_accessible=True,
            multi_az=False,
            tags=tags,
            wait_for_creation=True,
            ec2_bastion_id=ec2_bastion_id,
            ec2_key_pair_name=ec2_key_pair_name,
        )
        rds_asset_set.rds_db_connection_list.extend([rds_db_connection for rds_db_connection in rds_db_connection_list])
    logger.info(f"Refreshing account {csp_account_id} inventory")
    RDSInvMgrSteps.perform_rds_inventory_refresh_with_retry(
        context=context,
        csp_account_id=csp_account_id,
    )
    return rds_asset_set


def delete_standard_rds_assets(
    aws: AWS,
    rds_asset_set: RDSAssetSet,
):
    """Deletes the standard assets populated in the RDSAssetSet object, along with any EC2 Bastions

    Args:
        aws (AWS): AWS factory object
        rds_asset_set (RDSAssetSet): RDS asset set attribute
    """
    for rds_db_connection in rds_asset_set.rds_db_connection_list:
        logger.info(f"Deleting DB: {rds_db_connection.rds_instance_identifier}")
        aws.rds.delete_db_instance_by_id(db_instance_identifier=rds_db_connection.rds_instance_identifier)

    # then delete any RDS bastions in the AWS region
    delete_rds_standard_asset_ec2_bastions(aws=aws)


def _update_standard_rds_asset_details(
    aws: AWS,
    rds_asset_set: RDSAssetSet,
    ec2_bastion_id: str,
    ec2_key_pair_name: str,
    tag: Tag = Tag(Key="Standard", Value="Test"),
) -> RDSAssetSet:
    """Function to fetch the details of the existing standard RDS Asset set

    Args:
        aws (AWS): AWS factory object
        rds_asset_set (RDSAssetSet): RDS asset set attribute
        ec2_bastion_id (str): EC2 Bastion ID
        ec2_key_pair_name (str): EC2 Bastion key pair name
        tag (Tag, optional): The Standard Asset Tag to search on. Defaults to Tag(Key="Standard", Value="Test")

    Returns:
        RDSAssetSet: RDSAssetSet object with the asset details populated
    """
    # Get available DB instance by tag
    rds_db_instances = aws.rds.get_available_db_instances_by_tag(tag=tag)
    rds_asset_set.rds_db_connection_list = []

    for rds_db_instance in rds_db_instances:
        # NOTE: "sqlserver" DB type does not have "rds_db_instance["DBName"]" field
        db_name = rds_db_instance["DBName"] if "DBName" in rds_db_instance else ""

        rds_db_connect = RDSDBConnection(
            ec2_bastion_id=ec2_bastion_id,
            ec2_key_pair_name=ec2_key_pair_name,
            rds_instance_identifier=rds_db_instance["DBInstanceIdentifier"],
            engine=DBEngine(rds_db_instance["Engine"]),
            port=rds_db_instance["Endpoint"]["Port"],
            db_host=rds_db_instance["Endpoint"]["Address"],
            user=rds_db_instance["MasterUsername"],
            password=AWSRDSSteps.get_rds_password(),
            db_name=db_name,
        )
        rds_asset_set.rds_db_connection_list.append(rds_db_connect)
    return rds_asset_set


def _updated_dbname_count(
    aws: AWS,
    db_engines_counts_ports: list[RDSDBEnginesCountsPorts],
    discovered_asset_list: list[RDSDBConnection],
) -> list[RDSDBEnginesCountsPorts]:
    """This function updates the RDSDBEnginesCountsPorts list provided by excluding the discovered assets and returning the updated list

    Args:
        aws (AWS): AWS factory object
        db_engines_counts_ports (list[RDSDBEnginesCountsPorts]): A list of requested RDS Instances
        discovered_asset_list (list[RDSDBConnection]): A list of discovered RDS Instances

    Returns:
        list[RDSDBEnginesCountsPorts]: An updated list[RDSDBEnginesCountsPorts, exluding those from the list[RDSDBConnection]
    """
    discovered_dbname_list = []
    for db_connection in discovered_asset_list:
        # Get DB Identifier from RDSDBConnection object
        dbidentifier = db_connection.rds_instance_identifier
        discovered_dbname_list.append((aws.rds.get_db_instance_by_id(dbidentifier))["Engine"])
    logger.info(f"RDS DB available are: {discovered_dbname_list}")

    # convert discovered_dbname_list as dictionary to compare
    dis_db_dict = {}
    for db_identifier in discovered_dbname_list:
        if db_identifier in dis_db_dict.keys():
            dis_db_dict[db_identifier] = dis_db_dict.get(db_identifier) + 1
        else:
            dis_db_dict[db_identifier] = 1

    logger.info(f"RDS DB available and counts are: {dis_db_dict}")

    updated_db_engines_counts_ports = []
    for db_identifier in db_engines_counts_ports:
        if db_identifier.db_engine.value in dis_db_dict.keys():
            if db_identifier.db_count > dis_db_dict.get(db_identifier.db_engine.value):
                db_identifier.db_count = db_identifier.db_count - dis_db_dict.get(db_identifier.db_engine.value)
                updated_db_engines_counts_ports.append(db_identifier)
        # if the requested DB and count are not in discovered
        else:
            updated_db_engines_counts_ports.append(db_identifier)

    return updated_db_engines_counts_ports
