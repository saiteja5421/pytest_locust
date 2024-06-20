"""
Test Case:

The following steps iterates across the 5 RDS DBs in db_instance_list - mysql, mssql, postgres, mariadb, oracle
1.  Check RDS DB & EC2 Bastion details provided & check AvailabilityZones
2.  If no details provided, Create RDS DB & EC2 Bastion in the same AvailabilityZone
    a)  Security Group for EC2 Bastion -> Egress outgoing rule -> all traffic for RDS DB SG
    b)  Security Group for RDS DB -> Ingress ingoing rule -> all traffic for EC2 Bastion SG
3.  Test the jumphost connection -> EC2 Bastion -> RDS DB
    a)  _test_jumphost_connection()
4.  Test creation of 2 tables
    a)  _test_populate_two_tables_and_compare_hash()
5.  Update 1 table
    a)  _test_update_one_table_and_compare_hash()
6.  Test inserting records into table
    a)  _test_insert_records_get_hash()
7.  Test creation of 2 tables, records, & cleanup of tables
    a)  _test_create_fill_cleanup_databases()
8.  Perform cleanup of RDS DB & EC2 Bastion if created
"""

import logging

from pytest import fixture, mark
from lib.common.enums.db_instance_class import DBInstanceClass
from lib.common.enums.db_port import DBPort
from lib.dscc.backup_recovery.aws_protection.common.models.rds_common_objects import (
    RDSDBConnection,
    RDSDBEnginesCountsPorts,
)

from lib.platform.rds.db_factory import DBFactory
from lib.platform.rds.rds_proxy import DBBindings, RDSProxy
from lib.common.enums.db_engine import DBEngine

from tests.e2e.aws_protection.context import SanityContext

from tests.steps.aws_protection.rds import aws_rds_steps
from lib.common.enums.aws_availability_zone import AWSAvailabilityZone

from lib.platform.aws_boto3.aws_factory import AWS
from tests.steps.aws_protection.rds.aws_rds_steps import (
    establish_and_validate_db_connection,
    seed_data_to_rds_instances,
)

logger = logging.getLogger()

DB_ENGINE = None
DB_INFO = None

EC2_BASTION_ID = None
EC2_KEY_PAIR_NAME = None
POSTGRES_DB_CONNECTION = None
MYSQL_DB_CONNECTION = None
MARIA_DB_CONNECTION = None
ORACLE_DB_CONNECTION = None


def _test_jumphost_connection(db_engine, db_info):
    db = DBFactory.get_db(db_engine)
    params = db_info
    params["port"] = params["local_port"]
    params.pop("db-host")
    params.pop("engine")
    params.pop("local_port")
    db.initialize_db_properties(**params)
    dbname = db.get_database_type()
    print(dbname)
    print(db.get_database_version())
    size = db.get_size_of_db_in_MB(db_name=db_info["database"])
    print(size)
    db.close_db_connection()


def _test_insert_records_get_hash():
    db = DBFactory.get_db(DB_ENGINE)
    params = DB_INFO
    print(params)
    db.initialize_db_properties(**params)
    db.insert_records_in_db(num_of_records=50, db_name="testing", table_names=["mytbl1"])
    checksum = db.generate_checksum(table_name="mytbl1", db_name="testing")
    print(checksum)
    db.close_db_connection()


def _test_populate_two_tables_and_compare_hash():
    db = DBFactory.get_db(DB_ENGINE)
    params = DB_INFO
    print(params)
    db.initialize_db_properties(**params)
    tables = ["demo1", "demo2"]
    db.insert_records_in_db(num_of_records=20, db_name="testing", table_names=tables)
    checksum1 = db.generate_checksum(table_name=tables[0], db_name="testing")
    checksum2 = db.generate_checksum(table_name=tables[1], db_name="testing")
    assert checksum1 == checksum2, f"Records for {tables[0]} and {tables[1]} don't match"
    db.close_db_connection()


def _test_update_one_table_and_compare_hash():
    db = DBFactory.get_db(DB_ENGINE)
    params = DB_INFO
    print(params)
    db.initialize_db_properties(**params)
    db.insert_records_in_db(db_name="testing", table_names=["mytbl2"], num_of_records=50)
    checksum1 = db.generate_checksum(table_name="mytbl2", db_name="testing")
    db.insert_records_in_db(db_name="testing", table_names=["mytbl2"], num_of_records=5)
    checksum2 = db.generate_checksum(table_name="mytbl2", db_name="testing")
    assert checksum1 != checksum2, "Hash of mytbl2 is not updated as expected"
    db.close_db_connection()


def _test_create_fill_cleanup_databases():
    db = DBFactory.get_db(DB_ENGINE)
    params = DB_INFO
    print(params)
    db.initialize_db_properties(**params)
    dbname = db.get_database_type()
    print(dbname)
    print(db.get_database_version())
    db.insert_blob(
        table_names=["large_table"],
        num_of_records=2,
        db_name="testing",
        file_path="C:\\Users\\baviskav\\Documents\\my4MB.txt",
    )
    size = db.get_size_of_db_in_MB(db_name="testing")
    checksum = db.generate_checksum(table_name="large_table", db_name="testing")
    print(f"size = {size} and checksum is {checksum}")
    db.fill_database_to_size(
        db_name="testing",
        table_name_prefix="large_table",
        target_size_in_GB=1,
        file_path="C:\\Users\\baviskav\\Documents\\my4MB.txt",
    )
    db.cleanup_database(db_name="testing", table_name_prefix="large_table")
    db.insert_records_in_db(num_of_records=50, db_name="testing", table_names=["mytbl1"])
    db.delete_table(db_name="testing", table_names=["mytbl1"])
    db.close_db_connection()


@fixture(scope="module")
def context():
    global EC2_BASTION_ID, EC2_KEY_PAIR_NAME, POSTGRES_DB_CONNECTION, MYSQL_DB_CONNECTION, MARIA_DB_CONNECTION, ORACLE_DB_CONNECTION
    context = SanityContext(set_static_policy=False)
    context.aws_two = AWS(
        region_name="us-east-1",
        # Profile one
        aws_access_key_id=context.account_key_one,
        aws_secret_access_key=context.account_secret_one,
        account_name=context.aws_two_account_name,
    )
    """
    rds_mysql_postgres_mariadb_list = aws_rds_steps.create_rds_instances_with_custom_configurations(
        aws=context.aws_two,
        db_name="dbONE",
        db_identifier_prefix="pqa-db-automation",
        allocated_storage=20,
        availability_zone=AWSAvailabilityZone.US_EAST_1A,
        max_allocated_storage=60,
        db_engines_counts_ports=[
            # RDSDBEnginesCountsPorts(db_engine=DBEngine.MYSQL, db_count=1, db_port=DBPort.MYSQL.value),
            # RDSDBEnginesCountsPorts(db_engine=DBEngine.POSTGRES, db_count=1, db_port=DBPort.POSTGRES.value),
            RDSDBEnginesCountsPorts(db_engine=DBEngine.MARIADB, db_count=1, db_port=DBPort.MARIADB.value),
            # RDSDBEnginesCountsPorts(db_engine=DBEngine.SQLSERVER_EE, db_count=1, db_port=DBPort.SQLSERVER.value)
        ]
    )

    # NOTE: For Oracle, Publicly Accessible needs to be TRUE
    rds_oracle_list = aws_rds_steps.create_rds_instances_with_custom_configurations(
        aws=context.aws_two,
        db_name="orcl",
        db_identifier_prefix="pqa-db-automation",
        allocated_storage=20,
        availability_zone=AWSAvailabilityZone.US_EAST_1A,
        max_allocated_storage=60,
        db_engines_counts_ports=[
            RDSDBEnginesCountsPorts(db_engine=DBEngine.ORACLE_EE, db_count=1, db_port=DBPort.ORACLE.value)],
        db_instance_class=DBInstanceClass.DB_M5_X_LARGE
    )
    """
    EC2_BASTION_ID = "i-0c25b01364fd333d9"
    EC2_KEY_PAIR_NAME = "ec2_rds_bastion-de6bb6f5-cee6-4ee8-bd68-0695cac145ba"

    POSTGRES_DB_CONNECTION = RDSDBConnection(
        ec2_bastion_id=EC2_BASTION_ID,
        ec2_key_pair_name=EC2_KEY_PAIR_NAME,
        rds_instance_identifier="db-automation-postgres-0",
        engine=DBEngine.POSTGRES,
        port=DBPort.POSTGRES.value,
        local_port=DBPort.POSTGRES.value,
        db_host="db-automation-postgres-0.c3t4cyg5r3yb.us-east-1.rds.amazonaws.com",
        host="localhost",
        user="AtlantiaTestRDS",
        password=aws_rds_steps.get_rds_password(),
        db_name="dbONE",
    )

    MYSQL_DB_CONNECTION = RDSDBConnection(
        ec2_bastion_id=EC2_BASTION_ID,
        ec2_key_pair_name=EC2_KEY_PAIR_NAME,
        rds_instance_identifier="db-automation-mysql-0",
        engine=DBEngine.MYSQL,
        port=DBPort.MYSQL.value,
        local_port=DBPort.MYSQL.value,
        db_host="db-automation-mysql-0.c3t4cyg5r3yb.us-east-1.rds.amazonaws.com",
        host="localhost",
        user="AtlantiaTestRDS",
        password=aws_rds_steps.get_rds_password(),
        db_name="dbONE",
    )
    """
    # NOTE: Did not test yet
    SQLSERVER_DB_CONNECTION = RDSDBConnection(
        ec2_bastion_id=EC2_BASTION_ID,
        ec2_key_pair_name=EC2_KEY_PAIR_NAME,
        rds_instance_identifier="db-automation-mysql-0",
        engine=DBEngine.SQLSERVER_EE,
        port=DBPort.SQLSERVER.value,
        local_port=DBPort.SQLSERVER.value,
        db_host="db-automation-mysql-0.c3t4cyg5r3yb.us-east-1.rds.amazonaws.com",
        host="localhost",
        user="AtlantiaTestRDS",
        password=aws_rds_steps.get_rds_password(),
        db_name="dbONE"
    )
    # NOTE: Issue with connect from automation, manual connection works
    MARIA_DB_CONNECTION = RDSDBConnection(
        ec2_bastion_id=EC2_BASTION_ID,
        ec2_key_pair_name=EC2_KEY_PAIR_NAME,
        rds_instance_identifier="pqa-db-automation-mariadb-0",
        engine=DBEngine.MARIADB,
        port=DBPort.MARIADB.value,
        local_port=DBPort.MARIADB.value,
        db_host="pqa-db-automation-mariadb-0.c3t4cyg5r3yb.us-east-1.rds.amazonaws.com",
        host="localhost",
        user="AtlantiaTestRDS",
        password=aws_rds_steps.get_rds_password(),
        db_name="dbONE"
    )
    """
    ORACLE_DB_CONNECTION = RDSDBConnection(
        ec2_bastion_id=EC2_BASTION_ID,
        ec2_key_pair_name=EC2_KEY_PAIR_NAME,
        rds_instance_identifier="pqa-db-automation-oracle-ee-0",
        engine=DBEngine.ORACLE_EE,
        port=DBPort.ORACLE.value,
        local_port=DBPort.ORACLE.value,
        db_host="pqa-db-automation-oracle-ee-0.c3t4cyg5r3yb.us-east-1.rds.amazonaws.com",
        host="localhost",
        user="AtlantiaTestRDS",
        password=aws_rds_steps.get_rds_password(),
        db_name="orcl",
    )

    db_bindings = [
        (DBBindings(POSTGRES_DB_CONNECTION.db_host, POSTGRES_DB_CONNECTION.port, POSTGRES_DB_CONNECTION.local_port)),
        (DBBindings(MYSQL_DB_CONNECTION.db_host, MYSQL_DB_CONNECTION.port, MYSQL_DB_CONNECTION.local_port)),
        # (DBBindings(MARIA_DB_CONNECTION.db_host, MARIA_DB_CONNECTION.port, MARIA_DB_CONNECTION.local_port)),
        (DBBindings(ORACLE_DB_CONNECTION.db_host, ORACLE_DB_CONNECTION.port, ORACLE_DB_CONNECTION.local_port)),
    ]
    rds_proxy = RDSProxy(
        aws=context.aws_two,
        web_proxy=context.proxy,
        db_bindings=db_bindings,
        ec2_bastion_id=EC2_BASTION_ID,
        key_pair_name=EC2_KEY_PAIR_NAME,
    )

    # Initialize DB / Re-establish Connection
    postgres_db = establish_and_validate_db_connection(rds_db_connection=POSTGRES_DB_CONNECTION)
    mysql_db = establish_and_validate_db_connection(rds_db_connection=MYSQL_DB_CONNECTION)
    # maria_db = establish_and_validate_db_connection(rds_db_connection=MARIA_DB_CONNECTION)
    oracle_db = establish_and_validate_db_connection(rds_db_connection=ORACLE_DB_CONNECTION)

    yield context

    logger.info(f"\n{'Teardown Start: Context'.center(40, '*')}")
    postgres_db.cleanup_database(db_name=POSTGRES_DB_CONNECTION.db_name, table_name_prefix="test1")
    postgres_db.close_db_connection()
    mysql_db.cleanup_database(db_name=MYSQL_DB_CONNECTION.db_name, table_name_prefix="test1")
    mysql_db.close_db_connection()
    # maria_db.cleanup_database(db_name=MARIA_DB_CONNECTION.db_name, table_name_prefix="test1")
    # maria_db.close_db_connection()
    oracle_db.cleanup_database(db_name=ORACLE_DB_CONNECTION.db_name, table_name_prefix="test1")
    oracle_db.close_db_connection()
    rds_proxy.close_proxy()
    logger.info(f"\n{'Teardown Complete: Context'.center(40, '*')}")


@mark.order(130)
def test_rds_connect_db_instances(context: SanityContext):
    postgres_response_dict = seed_data_to_rds_instances(
        rds_db_connection=POSTGRES_DB_CONNECTION,
        table_names=["test1"],
        num_of_records=1,
    )
    logger.info(f"response: {postgres_response_dict}")
    mysql_response_dict = seed_data_to_rds_instances(
        rds_db_connection=MYSQL_DB_CONNECTION,
        table_names=["test1"],
        num_of_records=1,
    )
    logger.info(f"response: {mysql_response_dict}")
    # mariadb_response_dict = seed_data_to_rds_instances(rds_db_connection=MARIA_DB_CONNECTION, table_names=["test1"], num_of_records=1)
    # logger.info(f"response: {mariadb_response_dict}")
    oracle_response_dict = seed_data_to_rds_instances(
        rds_db_connection=ORACLE_DB_CONNECTION,
        table_names=["test1"],
        num_of_records=1,
    )
    logger.info(f"response: {oracle_response_dict}")
