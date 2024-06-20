from lib.platform.rds.abstract_db_factory import AbstractDatabase
import pymysql
import pandas as pd
import sqlalchemy as sal
from sqlalchemy.dialects.mysql import LONGTEXT

import logging

logger = logging.getLogger()


class MySQLDB(AbstractDatabase):
    def __init__(self):
        self.DB = "MySQLDB"
        # NOTE: Both self.connection and self.dbConnection are required (differernt value objects)
        # self.dbConnection -> establishes/closes DB connection
        # self.connection -> after self.dbConnection, establishes construct for db operations/queries
        self.connection = None
        self.dbConnection = None
        self.db_name = None

    def initialize_db_properties(self, database, user, password, host, port):
        """Function to create DB connection and initialize params needed for connection
        Args:
        database: DB name
        user: DB user name
        password: Password
        host: DB host name/url/IP
        port: DB port
        """
        super().initialize_db_properties(database, user, password, host, port)
        if not self.connection:
            try:
                self.connection = pymysql.connect(
                    host=host, user=user, password=password, port=port, connect_timeout=60
                )
                self.connection.autocommit = True
            except Exception as e:
                logger.error(f"Connection to DB failed with error {e}")

    def get_database_type(self):
        """This function returns the DB type ex. Oracle, MySQL etc"""
        return f"DB Type: {self.DB}"

    def get_database_version(self):
        """This function returns DB version"""
        query = "SELECT VERSION()"
        version = self.execute_sql_query(query=query)
        logger.info("Database version: {} ".format(version[0][0]))
        return version[0][0]

    def create_database(self, db_name):
        """This function will create DB
        Args:
        db_name: Name of DB to be created
        """
        pass

    def set_db_connection(self, db_name):
        """Function to setup DB connection
        Args:
        db_name: Name of database
        """
        if (not self.dbConnection) or (self.db_name and db_name != self.db_name):
            connstr = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{db_name}"
            super().make_connection(connection_string=connstr, db_name=db_name)

    def generate_checksum(self, table_name, db_name=None):
        """Returns checksum/hash for given table within db_name
        Args:
        table_name: Table name for checksum to be calculated
        db_name: DB name where table is present
        Returns:
        checksum as string
        """
        query = f"CHECKSUM TABLE {table_name}"
        if db_name:
            self.set_db_connection(db_name)
        data = self.dbConnection.execute(query)
        result = data.fetchall()
        return result[0][1]

    def get_size_of_db_in_MB(self, db_name=None):
        """Returns size of the DB in MB
        Args:
        db_name: Name of DB whose size is to be returned.
        Returns:
        Size of DB in MB as an Integer
        """
        if db_name:
            self.set_db_connection(db_name)
        else:
            db_name = self.db_name
        query = 'SELECT table_schema "DB Name", ROUND(SUM(data_length + index_length) / 1024 / 1024, 1) "DB Size in MB" FROM information_schema.tables GROUP BY table_schema;'
        rows = self.execute_sql_query(query=query)
        for schema_name, size in rows:
            if schema_name == db_name:
                return int(size)

    def insert_db_records_of_size(self, db_name, table_names: list, record_size_in_mb=1, num_of_records=1):
        """Insert records in the DB
        Args:
        db_name: Name of DB
        table_names: List of names of table in which db records are to be inserted
        record_size_in_mb: size of each record to be inserted (default:1)
        num_of_records: count of records to be inserted
        """
        self.set_db_connection(db_name)
        df = pd.DataFrame(super().create_records_of_size(record_size_in_mb, num_of_records))
        for table in table_names:
            df.to_sql(table, con=self.dbConnection, index=False, if_exists="append")
            logger.info(f"Inserted {num_of_records} records in table {table}")

    def insert_blob(self, db_name, file_path, table_names, num_of_records=1):
        """Insert blobs in the DB
        Args:
        db_name: Name of DB
        table_names: List of names of table in which db records are to be inserted
        num_of_records: count of records to be inserted
        """
        self.set_db_connection(db_name)
        df = pd.DataFrame(super().create_blob(file_path=file_path, num_of_records=num_of_records))
        dtype = {
            "id": sal.types.TEXT(),
            "misc": LONGTEXT(),
            "large_data": LONGTEXT(),
            "address": sal.types.TEXT(),
        }
        for table in table_names:
            for i in range(num_of_records):
                sub_df = df.iloc[i : i + 1, :]
                sub_df.to_sql(table, con=self.dbConnection, index=False, if_exists="append", dtype=dtype)
            logger.info(f"Inserted {num_of_records} records in table {table}")

    def cleanup_database(self, db_name, table_name_prefix):
        """Function to cleanup the database
        Args:
        db_name: Name of DB whose disk footprint has to be cleaned up
        table_name_prefix : tables name having given prefix will be deleted
        """
        self.set_db_connection(db_name)
        logger.info(f"Cleaning up database {db_name}, dropping tables with prefix {table_name_prefix}")
        querystr = f"select TABLE_NAME from information_schema.tables where TABLE_SCHEMA='{db_name}' and TABLE_NAME LIKE \"%%{table_name_prefix}%%\";"
        rows = self.execute_sql_query(query=querystr)
        tables = [row[0] for row in rows]
        if len(tables):
            self.delete_table(db_name=db_name, table_names=tables)
        else:
            logger.info(f"No tables with prefix {table_name_prefix} found in DB {db_name}")

    def delete_table(self, db_name, table_names):
        """Function to delete given table from the database
        Args:
        db_name: Name of DB where table to be deleted is located
        table_names: list of names of the table to be deleted
        """
        self.set_db_connection(db_name)
        for table in table_names:
            logger.info(f"Dropping table {table}")
            query = f"DROP table IF EXISTS {table};"
            self.execute_sql_query_no_return(query=query)
