import logging
import time
from typing import Callable

import boto3
from botocore.errorfactory import ClientError
from botocore.exceptions import WaiterError
from requests import codes
from waiting import wait, TimeoutExpired

from lib.platform.aws_boto3.client_config import ClientConfig
from lib.common.enums.aws_availability_zone import AWSAvailabilityZone
from lib.common.enums.aws_rds_waiters import AWSRDSWaiters
from lib.common.enums.db_engine import DBEngine
from lib.common.enums.db_engine_versions import DBEngineVersion
from lib.common.enums.db_instance_class import DBInstanceClass
from lib.common.enums.rds_snapshot_type import RDSSnapshotType
from lib.dscc.backup_recovery.aws_protection.common.models.rds_common_objects import RDSDBConnection

# Internal libraries
from lib.platform.aws_boto3.models.instance import Tag
from utils.timeout_manager import TimeoutManager
from utils.common_helpers import decode_base64

logger = logging.getLogger()

AWS_DB_APPLY_IMMEDIATELY_DELAY_SECS: int = 60

ERROR_CODE_OPTION_GROUP_NOT_FOUND: str = "OptionGroupNotFoundFault"
OPTION_GROUP_IN_USE: str = "cannot be deleted because it is in use"
OPTION_GROUP_WAIT: int = 30
MASTER_PASSWORD = decode_base64(encoded_string="VGVzdGluZzEyMyE=")


class RDSManager:
    def __init__(
        self, aws_session: Callable[[], boto3.Session], endpoint_url: str = None, client_config: ClientConfig = None
    ):
        self.get_session = aws_session
        self.endpoint_url = endpoint_url
        self.client_config = client_config

    @property
    def rds_client(self):
        return self.get_session().client("rds", endpoint_url=self.endpoint_url, config=self.client_config)

    # region DB Instance
    """
    ***************************************************************************
    DB Instances
    ***************************************************************************
    """

    def _validate_percent_increase(
        self,
        allocated_storage: int,
        max_allocated_storage: int,
        percent_increase: int = 10,
    ):
        """Validate specified 'max_allocated_storage' is 'percent_increase' larger than 'allocated_storage' in GiB

        Args:
            allocated_storage (int): AllocatedStorage for DB Instance
            max_allocated_storage (int): MaxAllocatedStorage for DB Instance
            percent_increase (int, optional): The percent increase to assert. Defaults to 10.
        """
        logger.info(f"{allocated_storage=} {max_allocated_storage=} {percent_increase=}")

        # percent_increase
        increase = allocated_storage * (percent_increase / 100)
        logger.info(f"{increase=}")

        expected_max = allocated_storage + increase
        logger.info(f"{expected_max=}")

        assert (
            max_allocated_storage >= expected_max
        ), f"max_allocated_storage:{max_allocated_storage} must be at least {percent_increase}% greater:{expected_max} than allocated_storage:{allocated_storage}"

    def get_db_engine_default_port(self, db_engine: DBEngine) -> int:
        """Get the default DB Port number for the provided DB Engine

        Args:
            db_engine (DBEngine): The DBEngine

        Returns:
            int: The default DB Port number for the DBEngine provided.
        """
        # Database Engine       Default Port Number
        # PostgreSQL            5432
        # Oracle                1521
        # SQL Server            1433
        # Aurora/MySQL/MariaDB  3306
        if "postgres" in db_engine.value:
            return 5432
        elif "oracle" in db_engine.value:
            return 1521
        elif "sqlserver" in db_engine.value:
            return 1433
        else:  # Aurora/MySQL/MariaDB
            return 3306

    def _validate_db_engine_port(self, db_engine: DBEngine, port: int):
        # MySQL                 1150-65535
        # MariaDB               1150-65535
        # Amazon Aurora         1150-65535
        # PostgreSQL            1150-65535
        # Oracle                1150-65535
        # SQL Server            1150-65535 except 1234, 1434, 3260, 3343, 3389, 47001, and 49152-49156

        # Only "sqlserver" has port values that cannot be used within the range: 1150-65535
        if "sqlserver" in db_engine.value:
            reserved_values = [
                1234,
                1434,
                3260,
                3343,
                3389,
                47001,
                49152,
                49153,
                49154,
                49155,
                49156,
            ]
            assert port not in reserved_values, f"The port value {port} cannot be used for {db_engine.value}"

        # now that we're here, we can check to ensure the "port" is within the overall range: 1150-65535
        assert port >= 1150 and port <= 65535, f"The port value {port} is not within the range: 1150-65535"

    def create_db_instance(
        self,
        db_name: str,
        db_instance_identifier: str,
        allocated_storage: int,
        availability_zone: AWSAvailabilityZone,
        max_allocated_storage: int = 0,
        db_instance_class: DBInstanceClass = DBInstanceClass.DB_T3_MICRO,
        db_engine: DBEngine = DBEngine.POSTGRES,
        port: int = 0,
        master_username: str = "AtlantiaTestRDS",
        master_user_password: str = MASTER_PASSWORD,
        publicly_accessible: bool = True,
        multi_az: bool = False,
        option_group_name: str = "",
        encrypted: bool = False,
        key_id: str = None,
        tags: list[Tag] = [Tag(Key="AtlantiaRDSTest", Value="Test")],
        wait_for_creation: bool = True,
    ):
        """Create an AWS Database Instance

        Args:
            db_name (str): Some DB will not be created in DB Instance if db_name is not provided (dependent on type of Engine used), can NOT use "-" or "_" (only alphanumeric characters).
                           If it is ORACLE DB then db_name should be less than 8 characters
            db_instance_identifier (str): Lowercase str name (can NOT end in a "-")
            allocated_storage (int): Amount of storage in GiB to allocate for DB Instance
            availability_zone:RDS database instance to be created in availability zone of AWS Region
            max_allocated_storage (int, optional): For Autoscaling, max storage in GiB. Must be at least 10% larger than "allocated_storage" (26% recommended).  Defaults to "allocated_storage".
            db_instance_class (DBInstanceClass, optional): Instance compute/memory capacity. Defaults to DBInstanceClass.DB_T3_MICRO.
            db_engine (DBEngine, optional): Type of DB Engine. Defaults to DBEngine.POSTGRES.
            port (int, optional): The DB Port Number to assign to the DB Instance. Defaults to DB Engine default port value.
            master_username (str, optional): Name for the master user. Defaults to "AtlantiaTestRDS".
            master_user_password (str, optional): Password for the master user (can include all characters except: "/", '"', "@").
            publicly_accessible (bool, optional): Indication whether DB Instance is publicly accessible. Defaults to False.
            multi_az (bool, optional): Indication whether DB Instance to be available in multi available zone. Defaults to False.
            option_group_name (str, optional): Create DB instance with custom option group. Defaults to None.
            encrypted (bool, optional): Set this parameter to true or leave it unset. If you set this parameter to false , RDS reports an error.
            key_id (str): key used to encrypt RDS intance. If left unset, AWS will use default key.
            tags (list[Tag], optional): Following Key/Value Pairings; Recommended to make use of specific functions via Tag collections. Defaults to [{"Key": "AtlantiaRDSTest", "Value": "Test"}]
            wait_for_creation (bool, optional): Wait for the creation of the RDS and return to ok state. Defaults to True.
        Returns:
            dict: The AWS Database Instance if successfully created, None otherwise
        """
        logger.info(
            f"Creating DB Instance: {db_name}, {db_instance_identifier}, {allocated_storage}, {db_instance_class.value}, {db_engine.value}, {master_username}, {tags}"
        )

        #####
        # AWS Storage Autoscaling
        #####
        if max_allocated_storage:
            # if max_allocated_storage is supplied, validate it is 10% greater than allocated_storage
            self._validate_percent_increase(
                allocated_storage=allocated_storage,
                max_allocated_storage=max_allocated_storage,
            )
        else:
            # otherwise set max_allocated_storage to allocated_storage value.
            # Must be greater than allocated_storage to enable autoscaling.
            # Setting equal to allocated_storage will disable autoscaling.
            # Less than is error.
            max_allocated_storage = allocated_storage

        logger.info(f"{max_allocated_storage=}")

        #####
        # DB Port Number
        #####
        if port:
            # If "port" is supplied, validate it is acceptable given the DB Engine.
            self._validate_db_engine_port(db_engine=db_engine, port=port)
        else:
            # Otherwise, set "port" to the default port value given the DB Engine.
            port = self.get_db_engine_default_port(db_engine=db_engine)

        tags = [dict(tag) for tag in tags]
        az: str = None
        if availability_zone is not None:
            az = availability_zone.value
        all_params = {
            "DBName": db_name,
            "DBInstanceIdentifier": db_instance_identifier,
            "AllocatedStorage": allocated_storage,
            "MaxAllocatedStorage": max_allocated_storage,
            "AvailabilityZone": az,
            "DBInstanceClass": db_instance_class.value,
            "Engine": db_engine.value,
            "Port": port,
            "MasterUsername": master_username,
            "MasterUserPassword": master_user_password,
            "PubliclyAccessible": publicly_accessible,
            "MultiAZ": multi_az,
            "OptionGroupName": option_group_name,
            "StorageEncrypted": encrypted,
            "KmsKeyId": key_id,
            "Tags": tags,
        }
        params = {k: v for k, v in all_params.items() if v is not None}
        created_db_instance_response = self.rds_client.create_db_instance(**params)
        logger.info(f"Initiated Create DB Instance: {db_instance_identifier} with db engine: {db_engine.value}")

        if wait_for_creation:
            waiter = self.rds_client.get_waiter("db_instance_available")
            waiter.wait(
                DBInstanceIdentifier=db_instance_identifier,
            )
            logger.info(f"Created DB Instance: {created_db_instance_response['DBInstance']['DBInstanceIdentifier']}")

            # Get the latest after waiting, since the DBInstanceStatus should change
            return self.get_db_instance_by_id(db_instance_identifier=db_instance_identifier)

        logger.info(f"Response: {created_db_instance_response}")
        return created_db_instance_response

    def create_db_parameter_group(
        self,
        db_parameter_group_name: str = "PQA-Automation-Postgres",
        db_parameter_group_family: str = "postgres14",
        description: str = "PQA Automation Testing",
    ):
        """Create DB Parameter Group (does not apply to RDS Custom)

        Args:
            db_parameter_group (str): Name of DB Parameter Group, 1-255 letters/numbers/hyphens
            db_parameter_group_family (str): The DB engine and version of the associated DB Instance
            description (str): _description_. Defaults to "PQA Automation Testing".

        Returns:
            response (dict)
        """
        logger.info(f"Creating DB Parameter Group {db_parameter_group_name}, {db_parameter_group_family}")
        response = self.rds_client.create_db_parameter_group(
            DBParameterGroupName=db_parameter_group_name,
            DBParameterGroupFamily=db_parameter_group_family,
            Description=description,
        )
        logger.info(f"Response: {response}")
        return response

    def delete_db_parameter_group(self, db_parameter_group_name: str):
        """Delete DB Parameter Group

        NOTE: must be existing DB Parameter Group, can't delete a default DB Parameter Group, can't be associated with any DB Instances

        Args:
            db_parameter_group_name (str): Name of the DB Parameter Group

        """
        logger.info(f"Deleting DB Parameter Group {db_parameter_group_name}")
        try:
            self.rds_client.delete_db_parameter_group(DBParameterGroupName=db_parameter_group_name)
            logger.info(f"Deleted DB Parameter Group {db_parameter_group_name}")
        except self.rds_client.exceptions.DBParameterGroupNotFoundFault:
            logger.info(f"DB Parameter Group {db_parameter_group_name} not found, ignoring delete request")

    def create_custom_db_instance_with_engine_version_and_parameter_subnet_group(
        self,
        db_name: str,
        db_instance_identifier: str,
        allocated_storage: int,
        availability_zone: AWSAvailabilityZone,
        db_subnet_group: str,
        db_parameter_group: str,
        max_allocated_storage: int = 0,
        db_instance_class: DBInstanceClass = DBInstanceClass.DB_T3_MICRO,
        db_engine: DBEngine = DBEngine.POSTGRES,
        port: int = 0,
        master_username: str = "AtlantiaTestRDS",
        master_user_password: str = MASTER_PASSWORD,
        publicly_accessible: bool = False,
        multi_az: bool = False,
        encrypted: bool = False,
        key_id: str = None,
        engine_version: str = "14.6",
        tags: list[Tag] = [Tag(Key="AtlantiaRDSTest", Value="Test")],
        wait_for_creation: bool = True,
        ec2_bastion_id: str = None,
        ec2_key_pair_name: str = None,
    ) -> RDSDBConnection:
        """Create an AWS Database Instance with custom DB Parameter Group, Subnet Group, and Engine Version

        Args:
            db_name (str): Some DB will not be created in DB Instance if db_name is not provided (dependent on type of Engine used), can NOT use "-" or "_" (only alphanumeric characters).
                           If it is ORACLE DB then db_name should be less than 8 characters
            db_instance_identifier (str): Lowercase str name (can NOT end in a "-")
            allocated_storage (int): Amount of storage in GiB to allocate for DB Instance
            availability_zone:RDS database instance to be created in availability zone of AWS Region
            db_subnet_group (str): DB subnet group to associate with DB instance, must match existing DBSubnetGroup, must not be default
            max_allocated_storage (int, optional): For Autoscaling, max storage in GiB. Must be at least 10% larger than "allocated_storage" (26% recommended).  Defaults to "allocated_storage".
            db_instance_class (DBInstanceClass, optional): Instance compute/memory capacity. Defaults to DBInstanceClass.DB_T3_MICRO.
            db_engine (DBEngine, optional): Type of DB Engine. Defaults to DBEngine.POSTGRES.
            db_parameter_group (str): The name of the DB parameter group to associate with this DB Instance, 1-255 letters/numbers/hyphens, can't end with hyphen or 2 consecutive hyphens
            port (int, optional): The DB Port Number to assign to the DB Instance. Defaults to DB Engine default port value.
            master_username (str, optional): Name for the master user. Defaults to "AtlantiaTestRDS".
            master_user_password (str, optional): Password for the master user (can include all characters except: "/", '"', "@").
            publicly_accessible (bool, optional): Indication whether DB Instance is publicly accessible. Defaults to False.
            multi_az (bool, optional): Indication whether DB Instance to be available in multi available zone. Defaults to False.
            engine_version (str): Version of the DB Engine
            tags (list[Tag], optional): Following Key/Value Pairings; Recommended to make use of specific functions via Tag collections. Defaults to [{"Key": "AtlantiaRDSTest", "Value": "Test"}]
            encrypted (bool, optional): Set this parameter to true or false
            key_id (str): key used to encrypt RDS intance. If left unset, AWS will use default key.
            wait_for_creation (bool, optional): Wait for the creation of the RDS and return to ok state. Defaults to True.
            ec2_bastion_id (str): EC2 bastion ID used for RDS Proxy -> DB connection
            ec2_key_pair_name (str): EC2 key pair name used for RDS Proxy -> DB connection
        Returns:
            rds_db_connection (RDSDBConnection): The RDS DB Connection object
        """
        logger.info(
            f"Creating DB Instance: {db_name}, {db_instance_identifier}, {allocated_storage}, {db_instance_class.value}, {db_engine.value}, {master_username}, {tags}"
        )

        #####
        # AWS Storage Autoscaling
        #####
        if max_allocated_storage:
            # if max_allocated_storage is supplied, validate it is 10% greater than allocated_storage
            self._validate_percent_increase(
                allocated_storage=allocated_storage,
                max_allocated_storage=max_allocated_storage,
            )
        else:
            # otherwise set max_allocated_storage to allocated_storage value.
            # Must be greater than allocated_storage to enable autoscaling.
            # Setting equal to allocated_storage will disable autoscaling.
            # Less than is error.
            max_allocated_storage = allocated_storage

        logger.info(f"{max_allocated_storage=}")

        #####
        # DB Port Number
        #####
        if port:
            # If "port" is supplied, validate it is acceptable given the DB Engine.
            self._validate_db_engine_port(db_engine=db_engine, port=port)
        else:
            # Otherwise, set "port" to the default port value given the DB Engine.
            port = self.get_db_engine_default_port(db_engine=db_engine)

        tags = [dict(tag) for tag in tags]
        created_db_instance_response = self.rds_client.create_db_instance(
            DBName=db_name,
            DBInstanceIdentifier=db_instance_identifier,
            AllocatedStorage=allocated_storage,
            MaxAllocatedStorage=max_allocated_storage,
            AvailabilityZone=availability_zone.value,
            DBSubnetGroupName=db_subnet_group,
            DBInstanceClass=db_instance_class.value,
            Engine=db_engine.value,
            DBParameterGroupName=db_parameter_group,
            Port=port,
            MasterUsername=master_username,
            MasterUserPassword=master_user_password,
            PubliclyAccessible=publicly_accessible,
            MultiAZ=multi_az,
            EngineVersion=engine_version,
            StorageEncrypted=encrypted,
            KmsKeyId=key_id,
            Tags=tags,
        )
        logger.info(f"Initiated Create DB Instance: {db_instance_identifier}")
        rds_db_connection = RDSDBConnection(
            ec2_bastion_id=ec2_bastion_id,
            ec2_key_pair_name=ec2_key_pair_name,
            rds_instance_identifier=db_instance_identifier,
            engine=db_engine,
            port=port,
            user=master_username,
            password=master_user_password,
            db_name=db_name,
        )

        if wait_for_creation:
            waiter = self.rds_client.get_waiter("db_instance_available")
            waiter.wait(
                DBInstanceIdentifier=db_instance_identifier,
            )
            logger.info(f"Created DB Instance: {created_db_instance_response['DBInstance']['DBInstanceIdentifier']}")

            # Get the latest after waiting, since the DBInstanceStatus should change
            rds_db = self.get_db_instance_by_id(db_instance_identifier=db_instance_identifier)
            rds_db_connection.db_host = rds_db["Endpoint"]["Address"]

        logger.info(f"Response: {created_db_instance_response}")
        logger.info(f"RDS DB Connect Object: {rds_db_connection}")
        return rds_db_connection

    def modify_db_instance_port_number(self, db_instance_id: str, port: int, apply_immediately: bool = True):
        """Modify the Port Number to be used by the provided AWS DB Instance ID.

        Args:
            db_instance_id (str): The AWS DB Instance ID
            port (int): The new port number to use. Must pass validation for the type of DB Engine. Set to 0 to use default DB Engine port number.
            apply_immediately (bool, optional): Indicates whether modifications are applied ASAP vs during PreferredMaintenanceWindow.

        Returns:
            dict: The modified AWS Database Instance if the port number was changed, None otherwise
        """
        logger.info(f"{db_instance_id=} {port=}")

        # get db_instance
        db_instance = self.get_db_instance_by_id(db_instance_identifier=db_instance_id)

        if not db_instance:
            logger.info(f"DB Instance not found: {db_instance_id}")
            return None

        # obtain the DBEngine type
        db_engine: DBEngine = DBEngine(db_instance["Engine"])
        logger.info(f"The db_engine is type: {db_engine}")

        # if port = 0, use default DB Engine port number
        if not port:
            port = self.get_db_engine_default_port(db_engine=db_engine)
        else:
            # validate if port number is acceptable given the DB Engine
            self._validate_db_engine_port(db_engine=db_engine, port=port)
            logger.info(f"Port {port} is valid for DBEngine {db_engine.value}")

        # The database restarts regardless of the value of the ApplyImmediately parameter.
        try:
            self.rds_client.modify_db_instance(
                DBInstanceIdentifier=db_instance_id,
                DBPortNumber=port,
                ApplyImmediately=apply_immediately,
            )
            logger.info(f"Initiated Modify DBPortNumber to {port}")

            if apply_immediately:
                logger.info("Wait for DB Instance Available")
                db_instance = self.wait_for_and_return_db_instance(db_instance_id=db_instance_id)
                assert db_instance["Endpoint"]["Port"] == port
                logger.info(f"DB Port = {db_instance['Endpoint']['Port']}")
        except ClientError as error:
            logger.info(f"Error Code: {error.response['Error']['Code']}")
            logger.info(f"Error Message: {error.response['Error']['Message']}")

        return db_instance

    def modify_db_instance_storage_autoscaling(self, db_instance_id: str, new_max_allocated_storage: int):
        """Enable or Disable the Storage Autoscaling of an AWS Database Instance

        Args:
            db_instance_id (str): The Database Identifier
            new_max_allocated_storage (int): Desired MaxAllocatedStorage for the DB Instance.
                To enable, this value should be at least 10% larger than the current AllocatedStorage (26% recommended).
                To disable, this value should be equal to the current AllocatedStorage

        Returns:
            dict: The modified AWS Database Instance if a modification was made, None otherwise
        """

        logger.info(f"{db_instance_id=} {new_max_allocated_storage=}")

        # get db_instance
        db_instance = self.get_db_instance_by_id(db_instance_identifier=db_instance_id)

        if not db_instance:
            logger.info(f"DB Instance not found: {db_instance_id}")
            return None

        allocated_storage = db_instance["AllocatedStorage"]
        max_allocated_storage = db_instance["MaxAllocatedStorage"] if "MaxAllocatedStorage" in db_instance else 0

        logger.info(f"{allocated_storage=} {max_allocated_storage=}")

        # if already disabled and new_max == allocated_storage, nothing to do
        if not max_allocated_storage and new_max_allocated_storage == allocated_storage:
            logger.info(f"DB {db_instance_id} already has Storage Autoscaling disabled")
            return None

        enabling: bool = False

        # if new_max != allocated_storage - validate (enable autoscaling)
        if new_max_allocated_storage != allocated_storage:
            logger.info("validating")
            # validate at least 10% larger
            self._validate_percent_increase(
                allocated_storage=allocated_storage,
                max_allocated_storage=new_max_allocated_storage,
            )
            enabling = True

        # We're here if (a) we passed validation (enable autoscaling) or (b) max_storage == storage (disabling autoscaling)

        # apply setting
        # The change occurs immediately. This setting ignores the apply immediately setting.
        try:
            self.rds_client.modify_db_instance(
                DBInstanceIdentifier=db_instance_id,
                MaxAllocatedStorage=new_max_allocated_storage,
            )
            logger.info(f"Initiated Modify MaxAllocatedStorage to {new_max_allocated_storage}")

            # get modified db_instance
            db_instance = self.get_db_instance_by_id(db_instance_identifier=db_instance_id)

            if enabling:
                assert db_instance["MaxAllocatedStorage"] == new_max_allocated_storage
                logger.info(f"Autoscaling is enabled: MaxAllocatedStorage = {db_instance['MaxAllocatedStorage']}")
            else:
                assert "MaxAllocatedStorage" not in db_instance
                logger.info("Autoscaling is disabled")
        except ClientError as error:
            logger.info(f"Error Code: {error.response['Error']['Code']}")
            logger.info(f"Error Message: {error.response['Error']['Message']}")

        return db_instance

    def get_db_instance_by_id(self, db_instance_identifier: str):
        """Get AWS DB Instance by ID

        Args:
            db_instance_identifier (str): Lowercase str name (can NOT end in a "-") that matches existing DB Instance

        Returns:
            Any | None: AWS DB Instance if found, None otherwise
        """
        logger.info(f"Describing DB Instance: {db_instance_identifier}")

        db_instance_response = None
        db_instance = None

        # if the DB Instance is not found, "DBInstanceNotFound" error is thrown
        try:
            db_instance_response = self.rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
        except ClientError as error:
            logger.info(f"Error Code: {error.response['Error']['Code']}")
            logger.info(f"Error Message: {error.response['Error']['Message']}")

        # describe_db_instances() always returns a list in: {'DBInstances': [...]}
        # Since were getting a single DB Instance via 'db_instance_identifier',
        # we'll return just the single DB Instance object
        if db_instance_response:
            db_instance = db_instance_response["DBInstances"][0]

        logger.info(f"Collected DB Instance: {db_instance}")
        return db_instance

    def get_db_instances_by_filters(self, filters: list = [{"Name": "engine", "Values": ["postgres"]}]) -> list:
        """Get AWS DB Instances by Filters

        Args:
            filters (list, optional): List of notable filters following a 'Name' & 'Values' pairing. Defaults to [{"Name": "engine", "Values": ["postgres"]}].

            There are limited Filters available for DB Instances:
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds.html#RDS.Client.describe_db_instances

            - db-cluster-id
            - db-instance-id
            - dbi-resource-id
            - domain
            - engine

        Returns:
            list: A list of AWS DB Instances matching the provided Filters
        """
        logger.info(f"Describing DB Instance(s) with filters: {filters}")

        # Return only the 'DBInstances' list; no need to return the 'ResponseMetadata'
        db_instances_response = self.rds_client.describe_db_instances(Filters=filters)
        db_instances = [db for db in db_instances_response["DBInstances"]]

        logger.info(f"Collected DB Instance(s): {db_instances}")
        return db_instances

    def get_db_instances_by_tag(self, tag: Tag) -> list:
        """Get AWS DB Instance by Tag

        Args:
            tag (Tag): The Tag to match to DB Instances

        Returns:
            list: A list of AWS DB Instances containing the provided Tag
        """
        db_instances_by_tag: list = []

        logger.info(f"Describing DB Instance(s) with Tag: {tag}")

        # Get all db_instances
        all_db_instances = self.get_all_db_instances()

        for db_instance in all_db_instances:
            for db_instance_tag in db_instance["TagList"]:
                if db_instance_tag["Key"] == tag.Key and db_instance_tag["Value"] == tag.Value:
                    db_instances_by_tag.append(db_instance)
                    # break out to the next DB Instance
                    break

        logger.info(f"Collected DB Instance(s): {db_instances_by_tag}")
        return db_instances_by_tag

    def delete_db_instance_by_id(
        self,
        db_instance_identifier: str,
        skip_final_snapshot: bool = True,
        wait_for_deletion: bool = True,
        delete_automated_backups: bool = True,
    ):
        """Delete AWS DB Instance by ID

        Args:
            db_instance_identifier (str): Lowercase str name (can NOT end in a "-") that matches existing DB Instance
            skip_final_snapshot (bool, optional): Skip the final DB snapshot before deleting instance. Defaults to True.
            wait_for_deletion (bool, optional): Wait for the DB snapshot to get deleted. Defaults to True.
            delete_automated_backups (bool, optional): Wait for the DB automated/system snapshots to get deleted.
                                                        Defaults to True.

        Returns:
            Any | None: Deletes AWS DB Instance if successful, None otherwise
        """
        delete_db_instance_response = None

        logger.info(f"Deleting DB Instance: {db_instance_identifier}")
        try:
            delete_db_instance_response = self.rds_client.delete_db_instance(
                DBInstanceIdentifier=db_instance_identifier,
                SkipFinalSnapshot=skip_final_snapshot,
                DeleteAutomatedBackups=delete_automated_backups,
            )
        except ClientError as error:
            logger.error(f"Error Code: {error.response['Error']['Code']}")
            logger.error(f"Error Message: {error.response['Error']['Message']}")

        if not delete_db_instance_response:
            logger.error(f"Did not delete DB Instance: {db_instance_identifier}")
            return None

        logger.info(f"Initiated Delete DB Instance: {db_instance_identifier}")

        if wait_for_deletion:
            self.waiter_for_rds_operation(
                db_instance_id=db_instance_identifier, waiter=AWSRDSWaiters.DB_INSTANCE_DELETED
            )
            logger.info(f"Deleted DB Instance: {delete_db_instance_response['DBInstance']['DBInstanceIdentifier']}")

        # NOTE: waiters check every 30 seconds for a total of 60 attempts before timing out
        # If there are no automated backups, then this call sits for 30 minutes

        # NOTE: "AWSRDSWaiters.DB_SNAPSHOT_DELETED" waiter does not seem to apply to Automated Backups
        # Automated Backups and Snapshots are 2 separate items in AWS

        # NOTE: It seems that in order for a "delete automated snapshot waiter" to function as expected, the DB must exist.
        # Therefore, waiting for the "delete automated snapshot waiter" step is useless when we're deleting the DB at the same time.
        # I have seen the "DB_INSTANCE_DELETED" waiter complete after the DB is deleted
        # I have not seen the "DB_SNAPSHOT_DELETED" waiter complete (before it times out) either before or after the "DB_INSTANCE_DELETED" waiter completes.

        # if delete_automated_backups:
        #     self.waiter_for_rds_operation(
        #         db_instance_id=db_instance_identifier, waiter=AWSRDSWaiters.DB_SNAPSHOT_DELETED
        #     )
        #     logger.info(
        #         f"Deleted DB automated snapshot: {delete_db_instance_response['DBInstance']['DBInstanceIdentifier']}"
        #     )

        return delete_db_instance_response["DBInstance"]

    def delete_db_instances_by_tag(
        self,
        tag: Tag = Tag(Key="AtlantiaRDSTest", Value="Test"),
        skip_final_snapshot: bool = True,
    ):
        """Delete AWS DB Instances by Tag

        Args:
            tag (Tag, optional): The Tag to match to existing DB Instances. Defaults to Tag(Key="AtlantiaRDSTest", Value="Test").
            skip_final_snapshot (bool, optional): Skip the final DB snapshot before deleting instance. Defaults to True.
        """
        db_instances_with_tag = self.get_db_instances_by_tag(tag=tag)
        for db_instance in db_instances_with_tag:
            self.delete_db_instance_by_id(
                db_instance_identifier=db_instance["DBInstanceIdentifier"],
                skip_final_snapshot=skip_final_snapshot,
            )

    def get_all_db_instances(self) -> list:
        """Get all DB Instances

        Returns:
            list: A list of AWS DB Instances
        """
        response = self.rds_client.describe_db_instances()

        db_instances = [db for db in response["DBInstances"]]
        logger.info(f"Number of DB Instances: {len(db_instances)}")

        return db_instances

    def get_available_db_instances(self) -> list:
        """Get all DB Instances with 'DBInstanceStatus' equal to 'available'

        Returns:
            list: A list of 'available' AWS DB Instance objects
        """
        all_db_instances = self.get_all_db_instances()

        db_instances = [db for db in all_db_instances if db["DBInstanceStatus"] == "available"]
        logger.info(f"Number of 'available' DB Instances: {len(db_instances)}")

        return db_instances

    def get_available_db_instances_by_tag(self, tag: Tag) -> list:
        """Get all 'available' DB Instances that contain the provided Tag

        Args:
            tag (Tag): The Tag to match to 'available' DB Instances

        Returns:
            list: A list of 'available' AWS DB Instances that contain the provided Tag
        """
        db_instances_by_tag = self.get_db_instances_by_tag(tag=tag)
        db_instances = [db for db in db_instances_by_tag if db["DBInstanceStatus"] == "available"]

        logger.info(f"Number of 'available' DB Instances with '{tag}': {len(db_instances)}")
        return db_instances

    def get_available_db_instances_contains_tag_key(self, tag_key_substring: str) -> list:
        """Get all 'available' DB Instances that have a Tag that contains 'tag_key_substring' in the Tag 'Key'

        Args:
            tag_key_substring (str): The substring to match in the Tag 'Key' field

        Returns:
            list: A list of 'available' AWS DB Instances that have 'tag_key_substring' in a Tag 'Key' field
        """
        available_db_instances = self.get_available_db_instances()
        db_instances = []

        for db_instance in available_db_instances:
            for db_tag in db_instance["TagList"]:
                if tag_key_substring in db_tag["Key"]:
                    db_instances.append(db_instance)
                    # break out to the next DB Instance
                    break

        logger.info(f"Number of 'available' DB Instances containing '{tag_key_substring}': {len(db_instances)}")
        return db_instances

    def stop_db_instance_by_id(self, db_instance_identifier: str):
        """Stop DB Instance by ID

        Args:
            db_instance_identifier (str): Lowercase str name (can NOT end in a "-") that matches existing DB Instance
        """
        stop_db_instance_response = None

        logger.info(f"Stopping DB Instance: {db_instance_identifier}")

        try:
            stop_db_instance_response = self.rds_client.stop_db_instance(
                DBInstanceIdentifier=db_instance_identifier,
            )
        except ClientError as error:
            logger.info(f"Error Code: {error.response['Error']['Code']}")
            logger.info(f"Error Message: {error.response['Error']['Message']}")

        if not stop_db_instance_response:
            logger.info(f"Did not stop DB Instance: {db_instance_identifier}")
            return None

        logger.info(f"wait until DB Instance stopped : {db_instance_identifier}")
        stopped_db_instance = self.wait_for_stop_db(db_instance_identifier=db_instance_identifier)
        logger.info(f"----- Stopped DB Instance {db_instance_identifier} ------ ")
        return stopped_db_instance

    def wait_for_stop_db(self, db_instance_identifier: str):
        """Wait until DB stopped

        Args:
            db_instance_identifier (str): Lowercase str name (can NOT end in a "-") that matches existing DB Instance

        Raises:
            e: TimeoutExpired

        Returns:
            Any | None: The stopped DB Instance if successful, None otherwise
        """
        # first check that the DB Instance exists
        if not self.get_db_instance_by_id(db_instance_identifier=db_instance_identifier):
            logger.info(f"DB Instance not found: {db_instance_identifier}")
            return None

        logger.info("DB stopping in progress")

        def _wait_for_status_stopped():
            db_instance = self.get_db_instance_by_id(db_instance_identifier=db_instance_identifier)
            if db_instance["DBInstanceStatus"] == "stopped":
                return db_instance

        try:
            stopped_db = wait(_wait_for_status_stopped, timeout_seconds=600, sleep_seconds=20)
        except TimeoutExpired as e:
            logger.error(f"DB was not stopped: {e}")
            raise e

        logger.info(f"DB stopped: {stopped_db}")
        return stopped_db

    def start_db_instance_by_id(self, db_instance_identifier: str):
        """Start DB Instance by ID

        Args:
            db_instance_identifier (str): Lowercase str name (can NOT end in a "-") that matches existing DB Instance

        Returns:
            Any | None: The started DB Instance if it succeeds, None otherwise
        """
        start_db_instance_response = None

        logger.info(f"Starting DB Instance: {db_instance_identifier}")
        try:
            start_db_instance_response = self.rds_client.start_db_instance(
                DBInstanceIdentifier=db_instance_identifier,
            )
        except ClientError as error:
            logger.info(f"Error Code: {error.response['Error']['Code']}")
            logger.info(f"Error Message: {error.response['Error']['Message']}")

        if not start_db_instance_response:
            logger.info(f"Did not start DB Instance: {db_instance_identifier}")
            return None

        waiter = self.rds_client.get_waiter("db_instance_available")
        waiter.wait(
            DBInstanceIdentifier=db_instance_identifier,
        )
        logger.info(f"Started DB Instance: {start_db_instance_response['DBInstance']['DBInstanceIdentifier']}")

        # Get the latest DB Instance after waiting, since the DBInstanceStatus should change
        return self.get_db_instance_by_id(db_instance_identifier=db_instance_identifier)

    def reboot_db_instance_by_id(self, db_instance_identifier: str, force_failover: bool = False, wait: bool = True):
        """Reboot DB Instance by ID

        Args:
            db_instance_identifier (str): Lowercase str name (can NOT end in a "-") that matches existing DB Instance
            force_failover (bool, optional): You can't enable force failover if the instance isn't configured for Multi-AZ. Defaults to False.
            wait (bool, optional): Wait for the operation to complete. Defaults to True.

        Returns:
            Any | None: DB Instance ID while reboot is in progress (when wait is set to False) OR successful (when wait
                        is set to True), None otherwise
        """
        reboot_db_instance_response = None

        # Get the status of DB
        db_instance = self.get_db_instance_by_id(db_instance_identifier=db_instance_identifier)

        if not db_instance:
            logger.info(f"DB Instance not found: {db_instance_identifier}")
            return None

        if db_instance["DBInstanceStatus"] != "available":
            logger.info(
                f"Status of DB Instance to be rebooted should be in available status to reboot: {db_instance['DBInstanceStatus']}"
            )
            return None
        logger.info(f"Status of DB Instance to be rebooted: {db_instance['DBInstanceStatus']}")

        logger.info(f"Rebooting DB Instance: {db_instance_identifier}")

        try:
            reboot_db_instance_response = self.rds_client.reboot_db_instance(
                DBInstanceIdentifier=db_instance_identifier,
                ForceFailover=force_failover,
            )
        except ClientError as error:
            logger.info(f"Error Code: {error.response['Error']['Code']}")
            logger.info(f"Error Message: {error.response['Error']['Message']}")

        if not reboot_db_instance_response:
            logger.info(f"Did not reboot DB Instance: {db_instance_identifier}")
            return None

        if wait:
            waiter = self.rds_client.get_waiter("db_instance_available")
            waiter.wait(
                DBInstanceIdentifier=db_instance_identifier,
            )
            logger.info(f"Rebooted DB Instance: {reboot_db_instance_response['DBInstance']['DBInstanceIdentifier']}")

        # Get the latest DB Instance after waiting, since the DBInstanceStatus should change
        return self.get_db_instance_by_id(db_instance_identifier=db_instance_identifier)

    def get_db_instance_ids_by_tag(self, tag: Tag) -> list:
        """Get a list of DB Instance IDs that contain the provided Tag.

        Args:
            tag (Tag): The Tag to match to DB Instances

        Returns:
            list: A list of AWS DB Instance IDs that contain the provided Tag
        """
        all_db_instances = self.get_db_instances_by_tag(tag=tag)

        db_instance_ids = [db["DBInstanceIdentifier"] for db in all_db_instances]
        logger.info(f"Number of DB Instance IDs with '{tag}': {len(db_instance_ids)}")

        return db_instance_ids

    def get_db_instance_address_by_id(self, db_instance_id: str):
        """Get the DB Instance Address for the 'db_instance_id' provided

        Args:
            db_instance_id (str): DB Instance Identifier

        Returns:
            str: Address of the requested DB Instance if successful, None otherwise
        """
        db_instance = self.get_db_instance_by_id(db_instance_identifier=db_instance_id)

        if not db_instance:
            logger.info(f"DB Instance not found: {db_instance_id}")
            return None

        # 'Endpoint': {
        #    'Address': 'mark-test-db-identifier1.csmmnd54u4uv.us-west-2.rds.amazonaws.com',
        #    'Port': 5432,
        #    'HostedZoneId': 'Z1PVIF0B656C1W'
        # }

        db_instance_address = db_instance["Endpoint"]["Address"]
        logger.info(f"DB Instance Address: {db_instance_address}")

        return db_instance_address

    def wait_for_and_return_db_instance(self, db_instance_id: str):
        """If 'ApplyImmediately=True' for a DB Modification, pause and wait for DB Available, and then return the db_instance

        Args:
            db_instance_id (str): The DB Instance Identifier

        Returns:
            Any : AWS DB Instance
        """
        # There is a delay for the 'ApplyImmediately' to start modifying on AWS, so need to wait a minimum of 30 sec
        time.sleep(AWS_DB_APPLY_IMMEDIATELY_DELAY_SECS)
        waiter = self.rds_client.get_waiter("db_instance_available")
        waiter.wait(
            DBInstanceIdentifier=db_instance_id,
        )
        return self.get_db_instance_by_id(db_instance_identifier=db_instance_id)

    def waiter_for_rds_operation(self, db_instance_id: str, waiter: AWSRDSWaiters) -> bool:
        """
        Wait for the respective operation

        Args:
            db_instance_id (str): rds db identifier
            waiter (AWSRDSWaiters): Type of get_waiter.  EG: "db_instance_available", "db_instance_deleted"

        Returns:
            bool: Returns boolean based on the result
        """
        logger.info(f"waiter: {waiter.value}")
        try:
            aws_waiter = self.rds_client.get_waiter(waiter.value)
            aws_waiter.wait(
                DBInstanceIdentifier=db_instance_id,
            )
        except WaiterError as error:
            logger.error(f"Waiter Error: {error.message}")
            return False

        return True

    def modify_db_instance_identifier(
        self,
        db_instance_id: str,
        new_db_instance_identifier: str,
        apply_immediately: bool = True,
    ):
        """Modify existing DB Instance Identifier

        Args:
            db_instance_id (str): Existing DB Instance Identifier
            new_db_instance_identifier (str): New DB Instance Identifier Name
            apply_immediately (bool): Indicates whether modifications are applied ASAP vs during PreferredMaintenanceWindow
        """
        self.rds_client.modify_db_instance(
            DBInstanceIdentifier=db_instance_id,
            ApplyImmediately=apply_immediately,
            NewDBInstanceIdentifier=new_db_instance_identifier,
        )
        logger.info(f"Initiated Modify DB Instance Identifier from {db_instance_id} to {new_db_instance_identifier}")
        if apply_immediately:
            modified_db_instance = self.wait_for_and_return_db_instance(db_instance_id=new_db_instance_identifier)
            assert modified_db_instance["DBInstanceIdentifier"] == new_db_instance_identifier
            logger.info(f"Modified DB Instance: {modified_db_instance['DBInstanceIdentifier']}")

    def modify_db_multi_az(
        self,
        db_instance_id: str,
        multi_az: bool,
        apply_immediately: bool = True,
    ):
        """Modify existing DB multi availability zone to Yes

        Args:
            db_instance_id (str): Existing DB Instance Identifier
            multi_az (bool): Multi availability zone
            apply_immediately (bool): Indicates whether modifications are applied ASAP vs during PreferredMaintenanceWindow
        """
        self.rds_client.modify_db_instance(
            DBInstanceIdentifier=db_instance_id,
            ApplyImmediately=apply_immediately,
            MultiAZ=multi_az,
        )
        logger.info(f"Initiated Modify DB Instance Multi AZ to {multi_az}")
        if apply_immediately:
            modified_db_instance = self.wait_for_and_return_db_instance(db_instance_id=db_instance_id)
            assert modified_db_instance["MultiAZ"] == multi_az
            logger.info(f"Modified DB Instance: {modified_db_instance['MultiAZ']}")

    def modify_db_instance_allocated_storage(
        self, db_instance_id: str, allocated_storage: int, apply_immediately: bool = True, wait: bool = True
    ):
        """Modify existing DB Instance Allocated Storage
           Note: 1. Modifying allocated storage can only be used to increase the size
                    (can NOT decrease, if that is the case must create a new RDS).
                 2. Increasing the size must be at least a 10%

        Args:
            db_instance_id (str): Existing DB Instance Identifier
            allocated_storage (int): New DB Instance Allocated Storage
            apply_immediately (bool): Indicates whether modifications are applied ASAP vs during PreferredMaintenanceWindow
            wait (bool, optional): Wait for the operation to complete. Defaults to True.

        """
        self.rds_client.modify_db_instance(
            DBInstanceIdentifier=db_instance_id,
            AllocatedStorage=allocated_storage,
            ApplyImmediately=apply_immediately,
        )
        logger.info(f"Initiated Modify DB Instance Allocated Storage to {allocated_storage}")
        if wait:
            modified_db_instance = self.wait_for_and_return_db_instance(db_instance_id=db_instance_id)
            assert modified_db_instance["AllocatedStorage"] == allocated_storage
            logger.info(f"Modified DB Instance: {modified_db_instance['AllocatedStorage']}")

    def modify_db_instance_class(
        self,
        db_instance_id: str,
        db_instance_class: str,
        apply_immediately: bool = True,
    ):
        """Modify existing DB Instance Class

        Args:
            db_instance_id (str): Existing DB Instance Identifier
            db_instance_class (str): New DB Instance Class
            apply_immediately (bool): Indicates whether modifications are applied ASAP vs during PreferredMaintenanceWindow
        """
        self.rds_client.modify_db_instance(
            DBInstanceIdentifier=db_instance_id,
            DBInstanceClass=db_instance_class,
            ApplyImmediately=apply_immediately,
        )
        logger.info(f"Initiated Modify DB Instance Class to {db_instance_class}")
        if apply_immediately:
            modified_db_instance = self.wait_for_and_return_db_instance(db_instance_id=db_instance_id)
            assert modified_db_instance["DBInstanceClass"] == db_instance_class
            logger.info(f"Modified DB Instance: {modified_db_instance['DBInstanceClass']}")

    def modify_db_instance_subnet_group_name(
        self,
        db_instance_id: str,
        db_instance_subnet_group_name: str,
        apply_immediately: bool = True,
    ):
        """Modify existing DB Instance Subnet Group Name

        Args:
            db_instance_id (str): Existing DB Instance Identifier
            db_instance_subnet_group_name (str): DB Instance Subnet Group Name
            apply_immediately (bool): Indicates whether modifications are applied ASAP vs during PreferredMaintenanceWindow
        """
        self.rds_client.modify_db_instance(
            DBInstanceIdentifier=db_instance_id,
            DBSubnetGroupName=db_instance_subnet_group_name,
            ApplyImmediately=apply_immediately,
        )
        logger.info(f"Initiated Modify DB Instance Subnet Group Name {db_instance_subnet_group_name}")
        if apply_immediately:
            modified_db_instance = self.wait_for_and_return_db_instance(db_instance_id=db_instance_id)
            assert modified_db_instance["DBSubnetGroup"]["DBSubnetGroupName"] == db_instance_subnet_group_name
            logger.info(f"Modified DB Instance: {modified_db_instance['DBSubnetGroup']['DBSubnetGroupName']}")

    def modify_db_instance_security_groups(
        self,
        db_instance_id: str,
        db_instance_security_groups: list,
        apply_immediately: bool = True,
    ):
        """Modify existing DB Instance Security Groups

        Args:
            db_instance_id (str): Existing DB Instance Identifier
            db_instance_security_groups (list): DB Instance Security Groups
            apply_immediately (bool): Indicates whether modifications are applied ASAP vs during PreferredMaintenanceWindow
        """
        self.rds_client.modify_db_instance(
            DBInstanceIdentifier=db_instance_id,
            DBSecurityGroups=db_instance_security_groups,
            ApplyImmediately=apply_immediately,
        )
        logger.info(f"Initiated Modify DB Instance Security Groups {db_instance_security_groups}")
        if apply_immediately:
            modified_db_instance = self.wait_for_and_return_db_instance(db_instance_id=db_instance_id)
            assert modified_db_instance["DBSecurityGroups"] == db_instance_security_groups
            logger.info(f"Modified DB Instance: {modified_db_instance['DBSecurityGroups']}")

    def modify_db_instance_vpc_security_group_ids(
        self,
        db_instance_id: str,
        db_instance_vpc_security_group_ids: list,
        apply_immediately: bool = True,
    ):
        """Modify existing DB Instance VPC Security Group IDs

        Args:
            db_instance_id (str): Existing DB Instance Identifier
            db_instance_vpc_security_group_ids (list): DB Instance VPC Security Group IDs
            apply_immediately (bool): Indicates whether modifications are applied ASAP vs during PreferredMaintenanceWindow
        """
        self.rds_client.modify_db_instance(
            DBInstanceIdentifier=db_instance_id,
            VpcSecurityGroupIds=db_instance_vpc_security_group_ids,
            ApplyImmediately=apply_immediately,
        )
        logger.info(f"Initiated Modify DB Instance VPC Security Group IDs {db_instance_vpc_security_group_ids}")
        if apply_immediately:
            modified_db_instance = self.wait_for_and_return_db_instance(db_instance_id=db_instance_id)
            for vpc_security_group in modified_db_instance["VpcSecurityGroups"]:
                assert vpc_security_group["VpcSecurityGroupId"] in db_instance_vpc_security_group_ids
            logger.info(f"Modified DB Instance: {modified_db_instance['VpcSecurityGroups']}")

    def modify_db_instance_publicly_accessible(
        self,
        db_instance_id: str,
        db_instance_publicly_accessible: bool,
        apply_immediately: bool = True,
    ):
        """Modify existing DB Instance Publicly Accessible

        Args:
            db_instance_id (str): Existing DB Instance Identifier
            db_instance_publicly_accessible (bool): DB Instance Publicly Accessible
            apply_immediately (bool): Indicates whether modifications are applied ASAP vs during PreferredMaintenanceWindow
        """
        self.rds_client.modify_db_instance(
            DBInstanceIdentifier=db_instance_id,
            ApplyImmediately=apply_immediately,
            PubliclyAccessible=db_instance_publicly_accessible,
        )
        logger.info(f"Initiated Modify DB Instance Publicly Accessible: {db_instance_publicly_accessible}")
        if apply_immediately:
            modified_db_instance = self.wait_for_and_return_db_instance(db_instance_id=db_instance_id)
            assert modified_db_instance["PubliclyAccessible"] == db_instance_publicly_accessible
            logger.info(f"Modified DB Instance: {modified_db_instance['PubliclyAccessible']}")

    def get_db_instance_arn_by_identifier(self, db_instance_id: str) -> str:
        """Get DB Instance arn by DB Identifier

        Args:
            db_instance_id (str): DB Identifier

        Returns:
            DB Instance arn
        """
        db_instance = self.get_db_instance_by_id(db_instance_identifier=db_instance_id)
        logger.info(f"Collected DB Instance arn: {db_instance['DBInstanceArn']}")

        return db_instance["DBInstanceArn"]

    def get_db_instance_class_type_by_identifier(self, db_instance_id: str) -> str:
        """Get DB Instance Class by DB Identifier

        Args:
            db_instance_id (str): DB Identifier

        Returns:
            DB Instance Class
        """
        db_instance = self.get_db_instance_by_id(db_instance_identifier=db_instance_id)
        logger.info(f"Collected DB Instance Class Type: {db_instance['DBInstanceClass']}")

        return db_instance["DBInstanceClass"]

    def get_db_instance_allocated_storage_by_identifier(self, db_instance_id: str) -> str:
        """Get DB Instance Allocated Storage Size by DB Identifier

        Args:
            db_instance_id (str): DB Identifier

        Returns:
            DB Instance Allocated Storage Size
        """
        db_instance = self.get_db_instance_by_id(db_instance_identifier=db_instance_id)
        logger.info(f"Collected DB Instance Allocated Storage Size: {db_instance['AllocatedStorage']}")

        return db_instance["AllocatedStorage"]

    def get_db_instance_state_by_identifier(self, db_instance_id: str) -> str:
        """Get DB Instance Class by DB Identifier

        Args:
            db_instance_id (str): DB Identifier

        Returns:
            DB Instance State
        """
        db_instance = self.get_db_instance_by_id(db_instance_identifier=db_instance_id)
        logger.info(f"Collected DB Instance State: {db_instance['DBInstanceStatus']}")

        return db_instance["DBInstanceStatus"]

    def get_db_instance_subnets_by_identifier(self, db_instance_id: str) -> list:
        """Get DB Instance Class by DB Identifier

        Args:
            db_instance_id (str): DB Identifier

        Returns:
            DB Instance Subnets
        """
        db_instance = self.get_db_instance_by_id(db_instance_identifier=db_instance_id)
        logger.info(f"Collected DB Instance Subnets: {db_instance['DBSubnetGroup']['Subnets']}")

        return db_instance["DBSubnetGroup"]["Subnets"]

    def get_db_instance_availability_zone_by_id(self, db_instance_id: str):
        """Get the Availability Zone of a DB Instance

        Args:
            db_instance_id (str): DB Instance Identifier

        Returns:
            str: Availability Zone of the requested DB Instance if successful, None otherwise
        """
        db_instance = self.get_db_instance_by_id(db_instance_identifier=db_instance_id)

        if not db_instance:
            logger.info(f"DB Instance not found: {db_instance_id}")
            return None

        availability_zone = db_instance["AvailabilityZone"]
        logger.info(f"DB Instance Availability Zone: {availability_zone}")

        return availability_zone

    # https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/accessing-monitoring.html#Overview.DBInstance.Status
    def get_db_instances_not_stopped(self) -> list:
        """Get DB Instances that do not have a 'DBInstanceStatus' of 'stopped' or 'stopping'

        Returns:
            list: A list of AWS DB Instance IDs that do not have a 'DBInstanceStatus' of 'stopped' or 'stopping'
        """
        all_db_instances = self.get_all_db_instances()

        db_instances = [
            db
            for db in all_db_instances
            if db["DBInstanceStatus"] != "stopped" and db["DBInstanceStatus"] != "stopping"
        ]
        logger.info(f"Number of non-stopped DB Instances: {len(db_instances)}")

        return db_instances

    def get_db_snapshots(
        self,
        db_instance_id: str,
        csp_rds_backup_name: str,
        snapshot_type: RDSSnapshotType = RDSSnapshotType.MANUAL,
    ):
        """get the rds db snapshot responses for the instance identifier in AWS

        Args:
            db_instance_id (str): DB Instance Identifier
            csp_rds_backup_name(str): Back up name in DSCC
            snapshot_type (RDSSnapshotType, optional): Type of RDS Snapshot to describe. Defaults to RDSSnapshotType.MANUAL

        Returns:
            responses["DBSnapshots"]: Response of describe db snapshots
        """
        responses = self.rds_client.describe_db_snapshots(
            DBInstanceIdentifier=db_instance_id,
            SnapshotType=snapshot_type.value,
            DBSnapshotIdentifier=csp_rds_backup_name,
        )
        return responses["DBSnapshots"]

    def get_all_db_snapshots(self, snapshot_type: RDSSnapshotType = RDSSnapshotType.MANUAL):
        """Get all RDS DB Snapshots

        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds/client/describe_db_snapshots.html
        SnapshotType (string)
            The type of snapshots to be returned:
            manual - Return all DB snapshots that have been taken by my Amazon Web Services account.

        Args:
            snapshot_type (RDSSnapshotType, optional): Type of RDS Snapshot to describe. Defaults to RDSSnapshotType.MANUAL

        Returns:
            responses["DBSnapshots"]: Response of describe db snapshots
        """
        db_snapshots = self.rds_client.describe_db_snapshots(SnapshotType=snapshot_type.value)
        return db_snapshots["DBSnapshots"]

    def get_snapshots_by_tag(self, tag: Tag, snapshot_type: RDSSnapshotType = RDSSnapshotType.MANUAL) -> list:
        """Returns RDS snapshots filtered by tag

        Args:
            tag (Tag): Tag by which RDS snapshots should be filtered
            snapshot_type (RDSSnapshotType, optional): Type of RDS Snapshot to describe. Defaults to RDSSnapshotType.MANUAL

        Returns:
            list: List of RDS snapshots filtered by tag
        """
        rds_snapshots_with_tag: list = []
        rds_snapshots = self.get_all_db_snapshots()

        for rds_snapshot in rds_snapshots:
            if rds_snapshot["TagList"] and tag in rds_snapshot["TagList"]:
                rds_snapshots_with_tag.append(rds_snapshot)

        return rds_snapshots_with_tag

    def delete_all_db_snapshots(
        self, snapshot_type: RDSSnapshotType = RDSSnapshotType.MANUAL, containing_name: str = ""
    ):
        """Delete all RDS DB Snapshots

        Args:
            snapshot_type (RDSSnapshotType, optional): The RDS snapshot type to delete. Defaults to RDSSnapshotType.MANUAL.
            containing_name (str, optional): If provided, only snapshots containing the value will be deleted. Defaults to "".
        """
        rds_snapshots = self.get_all_db_snapshots(snapshot_type=snapshot_type)
        for rds_snapshot in rds_snapshots:
            if not containing_name or containing_name in rds_snapshot["DBSnapshotIdentifier"]:
                self.delete_snapshot(snapshot_id=rds_snapshot["DBSnapshotIdentifier"])

    # endregion

    # region DB Security Groups
    """
    ***************************************************************************
    DB Security Groups
    ***************************************************************************

    NOTE: Existing methods from security_group_manager.py can be used for DBs as well. Same goes for VPC -> vpc_manager.py
    """

    def describe_db_security_group(self, db_security_group_name: str = None) -> list:
        """Describe DB Security Group

        Args:
            db_security_group_name (str): Name for the Security Group (all lowercase, first character must be a letter, no more than 255 characters, not default, can NOT end in "-")
            NOTE: there is a filter available, can implement later if needed
        Returns:
            List of DBSecurityGroup descriptions or a specified DBSecurityGroup description
        """
        if db_security_group_name is None:
            security_groups = self.rds_client.describe_db_security_group()
        else:
            security_groups = self.rds_client.describe_db_security_group(
                DBSecurityGroupName=db_security_group_name,
            )
        logger.info("Collected DB Security Group(s)")
        return security_groups

    # endregion

    # region DB Subnet Groups
    """
    ***************************************************************************
    DB Subnet Groups
    ***************************************************************************
    """

    def create_db_subnet_group(
        self,
        db_subnet_group_name: str,
        db_subnet_group_description: str,
        subnet_ids: list,
    ):
        """Creates a new DB subnet group. DB subnet groups must contain at least one subnet in at least two AZs in the Amazon Web Services Region.

        Args:
            db_subnet_group_name (str): Name for the Subnet Group (all lowercase, first character must be a letter, no more than 255 characters, not default)
            db_subnet_group_description (str): Description for the DB Subnet Group
            subnet_ids (list): List of Subnet IDs
        """
        created_subnet_group_response = self.rds_client.create_db_subnet_group(
            DBSubnetGroupName=db_subnet_group_name,
            DBSubnetGroupDescription=db_subnet_group_description,
            SubnetIds=subnet_ids,
        )
        logger.info(f"Created DB Subnet Group: {created_subnet_group_response}")
        return created_subnet_group_response

    def delete_db_subnet_group(self, db_subnet_group_name: str):
        """Delete DB Subnet Group

        Args:
            db_subnet_group_name (str): Name for the Subnet Group to be deleted ; must NOT be associated with any DB Instances
        """
        logger.info(f"Deleting DB Subnet Group {db_subnet_group_name}")
        try:
            self.rds_client.delete_db_subnet_group(
                DBSubnetGroupName=db_subnet_group_name,
            )
            logger.info("Deleted DB Subnet Group")
        except self.rds_client.exceptions.DBSubnetGroupNotFoundFault:
            logger.info(f"DB Subnet Group {db_subnet_group_name} not found, ignoring request")

    def describe_db_subnet_groups(self, db_subnet_group_name: str = None) -> list:
        """Describe DB Subnet Group(s)

        Args:
            db_subnet_group_name (str): Name for the Subnet Group to be deleted ; must NOT be associated with any DB Instances
            NOTE: there is a filter available, can implement later if needed
        Returns:
            List of DBSubnetGroup descriptions or a specified DBSubnetGroup description
        """
        if db_subnet_group_name is None:
            subnet_groups = self.rds_client.describe_db_subnet_groups()
        else:
            subnet_groups = self.rds_client.describe_db_subnet_groups(
                DBSubnetGroupName=db_subnet_group_name,
            )
        logger.info("Collected DB Subnet Group(s)")
        return subnet_groups

    def modify_db_subnet_group(
        self,
        db_subnet_group_name: str,
        db_subnet_group_description: str,
        subnet_ids: list,
    ):
        """Modify DB Subnet Group

        Args:
            db_subnet_group_name (str): Name for the Subnet Group (all lowercase, first character must be a letter, no more than 255 characters, not default)
            db_subnet_group_description (str): Description for the DB Subnet Group
            subnet_ids (list): List of Subnet IDs
        """
        modified_subnet_group_response = self.rds_client.modify_db_subnet_group(
            DBSubnetGroupName=db_subnet_group_name,
            DBSubnetGroupDescription=db_subnet_group_description,
            SubnetIds=subnet_ids,
        )
        logger.info(f"Modified DB Subnet Group: {modified_subnet_group_response}")
        return modified_subnet_group_response

    # endregion

    # region RDS Resource
    def get_tags_for_rds_resource_by_arn(self, amazon_resource_name: str) -> list:
        """This function lists all Tags on an Amazon RDS Resource (DBInstance, DBCluster, DBSnapshot, DBProxy, etc)

        Args:
            amazon_resource_name (str): Amazon Resource Name, should be similar to 'arn:aws:rds:us-east-1:992648334831:og:mymysqloptiongroup'
            NOTE: filter (str): Not currently supported at the moment

        Returns:
            list: List of all tags for that resource
        """
        response = self.rds_client.list_tags_for_resource(ResourceName=amazon_resource_name)

        logger.info(f"Collected DB Instance Tags: {response['TagList']}")

        return response["TagList"]

    def add_tags_for_rds_resource_by_arn(self, amazon_resource_name: str, tags: list):
        """Add tags to an RDS Resource by Amazon Resource Name (arn)

        Args:
            amazon_resource_name (str):  Amazon Resource Name
            tags (list): List of Tags wanting to add to RDS Resource
        """
        self.rds_client.add_tags_to_resource(ResourceName=amazon_resource_name, Tags=tags)
        logger.info(f"Added DB Instance Tags: {tags}")

    def remove_tags_for_rds_resource_by_arn(self, amazon_resource_name: str, tag_keys: list[str]):
        """Remove tags of an RDS Resource by Amazon Resource Name (arn)

        Args:
            amazon_resource_name (str):  Amazon Resource Name
            tag_keys (list[str]): List of tag keys wanting to delete from RDS Resource
        """
        self.rds_client.remove_tags_from_resource(ResourceName=amazon_resource_name, TagKeys=tag_keys)
        logger.info(f"Removed Tags: {tag_keys}")

    # endregion
    # Readreplica
    def create_db_instance_read_replica(
        self,
        read_replica_instance_identifier: str,
        source_db_instance_identifier: str,
        availability_zone: AWSAvailabilityZone,
        publicly_accessible: bool = False,
        multi_az: bool = False,
        tags: list = [{"Key": "RDSReadReplicaTest", "Value": "Test"}],
    ):
        """Create read replica for an AWS Database Instance

        Args:
            read_replica_instance_identifier (str): Lowercase str name (can NOT end in a "-")
            source_db_instance_identifier (str): Lowercase str name (can NOT end in a "-")
            availability_zone:RDS database instance to be created in availability zone of AWS Region
            publicly_accessible (bool, optional): Indication whether DB Instance is publicly accessible. Defaults to False.
            multi_az (bool, optional): Indication whether DB Instance to be available in multi available zone. Defaults to False.
            tags (list, optional): Following Key/Value Pairings; Recommended to make use of specific functions via Tag collections. Defaults to [{"Key": "AtlantiaRDSTest", "Value": "Test"}]

        Returns:
            dict: The read replica for an AWS Database Instance if successfully created, None otherwise
        """
        logger.info(
            f"Creating read replica for DB Instance: {read_replica_instance_identifier}, {source_db_instance_identifier}, {tags}"
        )

        #####
        # Validate source DB instance state and it's backup retention period is greater than 0
        #####

        src_db_response = self.get_db_instance_by_id(
            db_instance_identifier=source_db_instance_identifier,
        )

        logger.info(
            f"Status of source DB Instance to create replica : {src_db_response['DBInstanceStatus']} and backup retention period : {src_db_response['BackupRetentionPeriod']}"
        )

        assert (
            src_db_response["DBInstanceStatus"] == "available"
        ), "Source DB instance instance is not in available status"
        assert src_db_response["BackupRetentionPeriod"] > 0, "Source DB backup retention period is 0"

        created_read_replica_response = self.rds_client.create_db_instance_read_replica(
            DBInstanceIdentifier=read_replica_instance_identifier,
            SourceDBInstanceIdentifier=source_db_instance_identifier,
            PubliclyAccessible=publicly_accessible,
            AvailabilityZone=availability_zone.value,
            MultiAZ=multi_az,
            Tags=tags,
        )
        logger.info(f"Initiated Create read replica: {read_replica_instance_identifier}")

        # wait for read replica until available
        waiter = self.rds_client.get_waiter("db_instance_available")
        waiter.wait(
            DBInstanceIdentifier=read_replica_instance_identifier,
        )
        logger.info(
            f"Created read replica for DB instance: {created_read_replica_response['DBInstance']['DBInstanceIdentifier']}"
        )

        src_db_state = self.get_db_instance_state_by_identifier(
            db_instance_id=source_db_instance_identifier,
        )

        logger.info(f"Source DB instance state: {src_db_state}")
        assert (
            src_db_response["DBInstanceStatus"] == "available"
        ), "Source DB instance instance is not in available status"

        # Get the latest after waiting, since the read replica of the DBInstanceStatus should change
        return self.get_db_instance_by_id(db_instance_identifier=read_replica_instance_identifier)

    def delete_snapshot(self, snapshot_id):
        status = self.rds_client.delete_db_snapshot(DBSnapshotIdentifier=snapshot_id)
        waiter = self.rds_client.get_waiter("db_snapshot_deleted")
        waiter.wait(DBSnapshotIdentifier=snapshot_id)
        logger.info(f'Deleted DB snapshot {snapshot_id}, status={status["ResponseMetadata"]["HTTPStatusCode"]}')

    def create_option_group(
        self,
        option_group_name: str,
        engine_name: DBEngine,
        major_engine_version: DBEngineVersion,
        option_group_description: str,
    ):
        """
        Create a new option group
        Args:
            option_group_name (str): Specifies the name of the option group to be created. Must be 1 to 255 letters,
             numbers, or hyphens (can NOT end in a "-"). First character must be a letter.
            engine_name (DBEngine): Specifies the name of the engine that this option group should be associated with.
            Valid values- mariadb, mysql, oracle-ee, oracle-ee-cdb, oracle-se2, oracle-se2-cdb, postgres, sqlserver-ee,
            sqlserver-se, sqlserver-ex, sqlserver-web
            major_engine_version (str): Specifies the major version of the engine that this option group should be
            associated with.
            option_group_description (str): The description of the option group.

        Returns:
            dict: Option group details if successfully created, None otherwise
        """

        response = self.rds_client.create_option_group(
            OptionGroupName=option_group_name,
            EngineName=engine_name.value,
            MajorEngineVersion=major_engine_version.value,
            OptionGroupDescription=option_group_description,
        )

        assert (
            response["ResponseMetadata"]["HTTPStatusCode"] == codes.ok
        ), f"Option group {option_group_name} creation failed"
        logger.info(f"Custom Option group {option_group_name} created successfully")

        return response

    def delete_option_group(self, option_group_name: str):
        """
        Delete an existing option group
        Args:
            option_group_name (str): Specify name of the option group to be deleted.

        Returns: None
        """

        response = self.rds_client.delete_option_group(OptionGroupName=option_group_name)

        assert (
            response["ResponseMetadata"]["HTTPStatusCode"] == codes.ok
        ), f"Option group {option_group_name} deletion failed"
        logger.info(f"Custom Option group {option_group_name} deleted successfully")

    def wait_for_option_group_delete(
        self, option_group_name: str, max_timeout: int = TimeoutManager.standard_task_timeout
    ):
        """Wait for Option Group delete to be successful.

        After an RDS DB is deleted, the System Snapshot for the DB can linger for about 5 minutes before
        it is removed.  Since the System Snapshots have an association to the Option Group, deletion
        is prevented until all associations are removed.

        Args:
            option_group_name (str): The name of the Option Group
            max_timeout (int, optional): The maximum number of seconds to wait for a successful delete. Defaults to TimeoutManager.standard_task_timeout (20 mins).
        """

        def _try_delete():
            try:
                self.rds_client.delete_option_group(OptionGroupName=option_group_name)
                # the Option Group was successfully deleted - we're done
                return True
            except ClientError as error:
                # if the Option Group is not found, we can pass
                if error.response["Error"]["Code"] == ERROR_CODE_OPTION_GROUP_NOT_FOUND:
                    return True
                elif OPTION_GROUP_IN_USE in error.response["Error"]["Message"]:
                    logger.info(f"The Option Group '{option_group_name}' is in use")
                    return False
                else:
                    # we'll raise for any other error
                    raise error

        try:
            wait(_try_delete, timeout_seconds=max_timeout, sleep_seconds=OPTION_GROUP_WAIT)
        except TimeoutExpired as e:
            logger.info(f"Option Group: {option_group_name} is still in use after {max_timeout} seconds")
            raise e

    def modify_option_group(
        self,
        option_group_name: str,
        use_default: bool = True,
        options_to_include: dict = None,
        options_to_remove: list = [],
        apply_immediately: bool = True,
    ):
        """
            Modify an existing option group
            Args:
                option_group_name (str): Specify name of the option group to be modified.
                use_default (bool): Adds timezone option in the option group.
                options_to_include (dict): Dictionary of items to be added in the option group.
                options_to_remove (list): Remove any existing options. Defaults to None.
                apply_immediately (bool): Defaults to True.
                e.g:
                OptionsToInclude=[
            {
                'OptionName': 'string',
                'Port': 123,
                'OptionVersion': 'string',
                'DBSecurityGroupMemberships': [
                    'string',
                ],
                'VpcSecurityGroupMemberships': [
                    'string',
                ],
                'OptionSettings': [
                    {
                        'Name': 'string',
                        'Value': 'string',
                        'DefaultValue': 'string',
                        'Description': 'string',
                        'ApplyType': 'string',
                        'DataType': 'string',
                        'AllowedValues': 'string',
                        'IsModifiable': True|False,
                        'IsCollection': True|False
                    },
                ]
            },
        ]
            Returns:
                dict: Option group response if successful, None otherwise
        """

        if use_default:  # sets both permanent and persistent options to True
            options_to_include = [
                {
                    "OptionName": "Timezone",
                    "OptionSettings": [
                        {
                            "Name": "TIME_ZONE",
                            "Value": "UTC",
                        },
                    ],
                },
            ]
        response = self.rds_client.modify_option_group(
            OptionGroupName=option_group_name,
            OptionsToInclude=options_to_include,
            OptionsToRemove=options_to_remove,
            ApplyImmediately=apply_immediately,
        )

        assert (
            response["ResponseMetadata"]["HTTPStatusCode"] == codes.ok
        ), f"Option group {option_group_name} modification failed"
        option_name: str = response["OptionGroup"]["Options"][0]["OptionName"]
        logger.info(f"Custom Option group {option_group_name} modified successfully with option {option_name}")

        return response

    def modify_db_instance_to_add_a_new_option_group(
        self, db_instance_id: str, option_group_name: str, apply_immediately: bool = True
    ):
        """
        Add a new option group to an existing DB and remove the existing option group
        Args:
            db_instance_id (str): Specify name of the DB to be modified.
            option_group_name (str): Specify name of the option group to be added in DB.
            apply_immediately (bool): Defaults to True.
        Returns:
             dict: Option group response if successful, None otherwise
        """

        response = self.rds_client.modify_db_instance(
            DBInstanceIdentifier=db_instance_id,
            OptionGroupName=option_group_name,
            ApplyImmediately=apply_immediately,
        )

        logger.info(f"Modify DB Instance to add a new option group {option_group_name}")

        if apply_immediately:
            modified_db_instance = self.wait_for_and_return_db_instance(db_instance_id=db_instance_id)
            _option_group_name = modified_db_instance["OptionGroupMemberships"][0]["OptionGroupName"]
            assert _option_group_name == option_group_name
            logger.info(f"Modified DB Instance to a new option group: {option_group_name}")

        return response
