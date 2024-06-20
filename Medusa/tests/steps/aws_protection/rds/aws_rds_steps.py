"""aws_rds_steps.py contains the relevant steps/commands to help perform RDS related tests.

Below are the following Region categories of this file:
-   Create/Delete RDS Instance
-   RDS Connection / Seeding Data

"""

import logging
from datetime import datetime

# Internal libraries
from lib.common.enums.aws_availability_zone import AWSAvailabilityZone
from lib.common.enums.db_instance_class import DBInstanceClass
from lib.common.enums.db_engine import DBEngine
from lib.common.enums.aws_rds_waiters import AWSRDSWaiters
from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.rds.db_factory import DBFactory
from lib.dscc.backup_recovery.aws_protection.common.models.rds_common_objects import (
    RDSDBConnection,
    RDSDBEnginesCountsPorts,
)
from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.rds.rds_proxy import DBBindings, RDSProxy
from utils.common_helpers import decode_base64

# Steps
from tests.e2e.aws_protection.context import Context
from tests.steps.aws_protection.rds.csp_rds_inventory_manager_steps import (
    get_db_identifier_using_csp_rds_instance_id,
)

logger = logging.getLogger()


# region Create/Delete RDS Instance


def get_rds_password() -> str:
    return decode_base64("VGVzdGluZzEyMyE=")


def delete_rds_db_instances_by_identifier(aws: AWS, db_identifier_list: list, wait_for_deletion: bool = True) -> bool:
    """Delete AWS DB Instance by list of ID
    Args:
        db_identifier_list (list): list of identifiers which should be Lowercase str name (can NOT end in a "-")
            that matches existing DB Instance
        aws (AWS): AWS Account
        wait_for_deletion (bool): Default value is set to True in order to wait for deletion
    Returns:
        bool: Returns boolean based on the result
    """
    result = True
    for db_instance_identifier in db_identifier_list:
        logger.info(f"Deleting DB Instance: {db_instance_identifier}")
        rds_db_id = aws.rds.delete_db_instance_by_id(
            db_instance_identifier=db_instance_identifier, wait_for_deletion=False
        )
        if not rds_db_id:
            result = False

    if wait_for_deletion:
        for db_identifier in db_identifier_list:
            waiter_status = aws.rds.waiter_for_rds_operation(
                db_instance_id=db_identifier, waiter=AWSRDSWaiters.DB_INSTANCE_DELETED
            )
            if waiter_status:
                logger.info(f"RDS DB {db_identifier} is deleted successfully")
            else:
                result = False
                logger.error(f"RDS Waiter db_instance_deleted has failed for RDS DB {db_identifier}")
    return result


def create_rds_instances_with_custom_configurations(
    aws: AWS,
    db_name: str,
    db_identifier_prefix: str,
    allocated_storage: int,
    availability_zone: AWSAvailabilityZone,
    max_allocated_storage: int,
    db_engines_counts_ports: list[RDSDBEnginesCountsPorts] = [
        RDSDBEnginesCountsPorts(db_engine=DBEngine.POSTGRES, db_count=1, db_port=5432),
    ],
    option_group_name: str = "",
    encrypted: bool = False,
    key_id: str = None,
    master_username: str = "AtlantiaTestRDS",
    master_password: str = get_rds_password(),
    db_instance_class: DBInstanceClass = DBInstanceClass.DB_T3_MICRO,
    publicly_accessible: bool = True,
    multi_az: bool = False,
    tags: list[Tag] = [Tag(Key="AtlantiaRDSTest", Value="Test")],
    wait_for_creation: bool = True,
    ec2_bastion_id: str = None,
    ec2_key_pair_name: str = None,
) -> list[RDSDBConnection]:
    """Function creates multiple RDS instance based on the common configuration.

    Args:
        aws (AWS): AWS factory object
        db_name (str): 8 characters max, must begin with a letter and contain only alphanumeric characters.
        db_identifier_prefix (str): RDS instance name to be prefixed; must be unique root string among different RDS DBs, function will add DBEngine.value & count to the end of prefix.
        allocated_storage (int): size of the EBS volume in GB.
        availability_zone (AWSAvailabilityZone): AWS availability zone.
        max_allocated_storage (int): Max DB size in GB.
        db_engines_counts_ports ([RDSDBEnginesCountsPorts]): list of DB Engine Types, DB Counts, and DB Ports.
        option_group_name (str, optional): Create DB instance with custom option group. Defaults to None.
        encrypted (bool, optional): Set this parameter to true or leave it unset. If you set this parameter to false , RDS reports an error.
        key_id (str): key used to encrypt RDS intance. If left unset, AWS will use default key.
        master_username (str): Master username for the RDS instance.
        master_password (str): Master password for the RDS instance.
        db_instance_class (DBInstanceClass, optional): AWS instance type. Defaults to DBInstanceClass.DB_T3_MICRO.
        publicly_accessible (bool, optional): Enable RDS accessible from public network. Defaults to False.
        multi_az (bool, optional): Enable multi-az cluster. Defaults to False.
        tags list[Tag]: tag key value list
        wait_for_creation (bool, optional): Wait for the creation of the RDS and return to ok state. Defaults to True.
        ec2_bastion_id (str): EC2 bastion ID used for RDS Proxy -> DB connection
        ec2_key_pair_name (str): EC2 key pair name used for RDS Proxy -> DB connection
    Returns:
        rds_db_connect_objects (list[RDSDBConnection]): List of RDS DB Connection objects
    """
    rds_db_connect_objects: list[RDSDBConnection] = []

    # Iterate through the different RDS DB sets listed
    for rds_dict_set in db_engines_counts_ports:
        # parameter updated for oracle and sqlserver RDS DB
        if "oracle" in rds_dict_set.db_engine.value:
            db_instance_class = DBInstanceClass.DB_T3_SMALL
        elif "sqlserver" in rds_dict_set.db_engine.value:
            db_instance_class = DBInstanceClass.DB_T3_SMALL
            db_name = ""
            allocated_storage = 20
            max_allocated_storage = 30
        else:
            db_instance_class = DBInstanceClass.DB_T3_MICRO
        # Iterate through the number of RDS DBs to create
        for counter in range(0, rds_dict_set.db_count):
            now = datetime.now()
            time = now.strftime("-%d-%m-%Y-%H-%M-%S")
            updated_db_identifier: str = (
                db_identifier_prefix + "-" + rds_dict_set.db_engine.value + "-" + str(counter) + time
            ).lower()
            rds = aws.rds.create_db_instance(
                db_name=db_name,
                db_instance_identifier=updated_db_identifier,
                allocated_storage=allocated_storage,
                availability_zone=availability_zone,
                max_allocated_storage=max_allocated_storage,
                db_instance_class=db_instance_class,
                db_engine=rds_dict_set.db_engine,
                port=rds_dict_set.db_port,
                master_username=master_username,
                master_user_password=master_password,
                publicly_accessible=publicly_accessible,
                multi_az=multi_az,
                tags=tags,
                option_group_name=option_group_name,
                encrypted=encrypted,
                key_id=key_id,
                wait_for_creation=False,
            )
            # NOTE: 'rds' response will vary if not wait_for_creation
            logger.info(f"RDS DB {updated_db_identifier} was created with DBEngine {rds_dict_set.db_engine}")
            rds_db_connection = RDSDBConnection(
                ec2_bastion_id=ec2_bastion_id,
                ec2_key_pair_name=ec2_key_pair_name,
                rds_instance_identifier=updated_db_identifier,
                engine=rds_dict_set.db_engine,
                port=rds_dict_set.db_port,
                user=master_username,
                password=master_password,
                db_name=db_name,
            )
            rds_db_connect_objects.append(rds_db_connection)

    if wait_for_creation:
        for rds_db_connect_object in rds_db_connect_objects:
            waiter_status = aws.rds.waiter_for_rds_operation(
                db_instance_id=rds_db_connect_object.rds_instance_identifier,
                waiter=AWSRDSWaiters.DB_INSTANCE_AVAILABLE,
            )
            if waiter_status:
                logger.info(f"RDS DB {rds_db_connect_object.rds_instance_identifier} is created successfully")
            else:
                logger.error(
                    f"RDS DB {rds_db_connect_object.rds_instance_identifier} is created but is not in available state!!"
                )
            rds_db = aws.rds.get_db_instance_by_id(db_instance_identifier=rds_db_connect_object.rds_instance_identifier)
            rds_db_connect_object.db_host = rds_db["Endpoint"]["Address"]
    return rds_db_connect_objects


def delete_rds_db_instance_by_csp_rds_instance_id_list(context: Context, aws: AWS, csp_rds_instance_id_list: list[str]):
    """Delete rds insances using csp rds instance id

    Args:
        context (Context): Atlantia Context object
        aws (AWS): AWS Factory object
        csp_rds_instance_id_list (list[str]): list of csp rds instance id to delete
    """
    db_identifier_list: list = list()
    for csp_rds_instance_id in csp_rds_instance_id_list:
        rds_identifier = get_db_identifier_using_csp_rds_instance_id(
            context=context, csp_rds_instance_id=csp_rds_instance_id
        )
        db_identifier_list.append(rds_identifier)
    delete_rds_db_instances_by_identifier(aws=aws, db_identifier_list=db_identifier_list)


# endregion

# region RDS Connection / Seeding Data


def establish_and_validate_db_connection(rds_db_connection: RDSDBConnection):
    """Function validates DB Connection, will re-initialize DB if connection is lost
        NOTE: Should run this function at the beginning of Context fixture and within DB functions (like seeding data)

    Args:
        rds_db_connection (RDSDBConnection):

    Returns:
        db: DB connect object
    """

    # NOTE: local_port should be fixed in context fixture after DB Creation
    logger.info(f"Validating connection for RDS DB {rds_db_connection} . . .")

    # Initialize DB / Re-establish Connection
    # NOTE: Need to pass local port that was used during DB binding for RDSProxy()
    db = DBFactory.get_db(rds_db_connection.engine)
    db.initialize_db_properties(
        database=rds_db_connection.engine.value,
        user=rds_db_connection.user,
        password=rds_db_connection.password,
        host=rds_db_connection.host,
        port=rds_db_connection.local_port,
    )
    return db


def seed_data_to_rds_instances(
    rds_db_connection: RDSDBConnection,
    table_names: list = ["testpqa"],
    num_of_records: int = 100000,
) -> dict:
    """Function write data to the list of RDS instance and generate checksum
    Args:
        rds_db_connection (RDSDBConnection): RDSDBConnection object that has all DB info & EC2 bastion info
        table_names (list): list of table to insert records
        num_of_records (int): no. of records(rows) data to be inserted
    Returns:
        tbl_checksum (dict): Object containing tablenames and its checksum.
        [
            {
                table_name: str
                checksum: str
            },
        ]
    """
    # Validate DB Connection
    db = establish_and_validate_db_connection(rds_db_connection=rds_db_connection)

    tbl_checksum = {}
    db.insert_records_in_db(num_of_records=num_of_records, db_name=rds_db_connection.db_name, table_names=table_names)
    logger.info(
        f"Number of records {num_of_records} on the table {table_names} for the DB {rds_db_connection.db_name} are successful"
    )
    for table_name in table_names:
        checksum = db.generate_checksum(table_name=table_name, db_name=rds_db_connection.db_name)
        tbl_checksum[table_name] = checksum
        logger.info(f"Table name {table_name} has the checksum as {tbl_checksum.get(table_name)}")
    return tbl_checksum


def create_db_bindings_rds_proxy_and_establish_db_connection(
    context: Context, aws: AWS, rds_db_connection: RDSDBConnection, ec2_bastion_id: str, ec2_key_pair_name: str
):
    """Create DB Bindings, RDSProxy, and establish/initialize the DB

    NOTE: This function will only take into account 1 DBConnection object at a time, thus 1 DBBinding
            If you need to create multiple DBBindings to be passed into RDSProxy, do that manually

    Args:
        context (Context): context
        aws (AWS): aws
        rds_db_connection (RDSDBConnection): RDS DB Connection object
        ec2_bastion_id (str): EC2 bastion ID
        ec2_key_pair_name (str): EC2 key pair name

    Returns:
        RDSProxy, DB: The newly created RDSProxy and DB that was established/initialized
    """

    db_bindings = [
        (DBBindings(rds_db_connection.db_host, rds_db_connection.port, rds_db_connection.local_port)),
    ]
    logger.info(f"Created DB Bindings {db_bindings}")
    logger.info("Creating RDS Proxy . . .")
    rds_proxy = RDSProxy(
        aws=aws,
        web_proxy=context.proxy,
        db_bindings=db_bindings,
        ec2_bastion_id=ec2_bastion_id,
        key_pair_name=ec2_key_pair_name,
    )
    logger.info("Establishing/initializing DB connection . . .")
    db = establish_and_validate_db_connection(rds_db_connection=rds_db_connection)
    return rds_proxy, db


# endregion


def verify_db_snapshot_tag(aws: AWS, db_instance_id: str, csp_rds_backup_name: str, tag: Tag) -> bool:
    """
    Validate snapshot property of the RDS instance in AWS
    Args:
        aws (AWS): AWS Factory object
        db_instance_id (str): DB Instance Identifier
        csp_rds_backup_name(str): Back up name in DSCC
        tag (Tag): Key, Value to check if it exists on snapshot
    Return:
        exists(bool) : if exists True otherwise false
    """
    exists = False
    response = aws.rds.rds_client.describe_db_snapshots(
        DBInstanceIdentifier=db_instance_id,
        DBSnapshotIdentifier=csp_rds_backup_name,
    )
    for db_snapshot in response["DBSnapshots"]:
        if db_snapshot["TagList"]:
            for i in range(len(db_snapshot["TagList"])):
                if db_snapshot["TagList"][i]["Key"] == tag.Key and db_snapshot["TagList"][i]["Value"] == tag.Value:
                    exists = True
                    logger.info(f"DB Snapshot: {db_instance_id} has tag {tag}")
                    break

    return exists


def wait_rds_instance(aws: AWS, db_identifier_list: list, waiter: AWSRDSWaiters) -> bool:
    """Waits for the RDS operation to complete and return their status for the list of RDS

    Args:
        aws (AWS): aws object
        db_identifier_list (list): database identier list
        waiter (AWSRDSWaiters): AWSRDSWaiters - type of waiter operation

    Returns:
        result: Returns boolean based on the results
    """
    result = True
    for db_identifier in db_identifier_list:
        waiter_status = aws.rds.waiter_for_rds_operation(db_instance_id=db_identifier, waiter=waiter)
        if waiter_status:
            logger.info(f"RDS DB {db_identifier} is {waiter} successfully")
        else:
            result = False
            logger.error(f"RDS Waiter {waiter} has failed for RDS DB {db_identifier}")

    return result
