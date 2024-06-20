from lib.platform.rds.abstract_db_factory import AbstractDatabase

import pymssql
import pandas as pd
from sqlalchemy.dialects.mysql import VARCHAR, NVARCHAR
import logging

logger = logging.getLogger()


class MSSQLDB(AbstractDatabase):
    """Class for MSSQLDB"""

    def __init__(self):
        self.DB = "MSSQLDB"
        # NOTE: Both self.connection and self.dbConnection are required (differernt value objects)
        # self.dbConnection -> establishes/closes DB connection
        # self.connection -> after self.dbConnection, establishes construct for db operations/queries
        self.connection = None
        self.dbConnection = None
        self.db_name = None

    def initialize_db_properties(self, database, user, password, host, port):
        """Function to create DB connection and initialize params needed for connection
        Args:
        user: DB user name
        password: Password
        host: DB host name/url/IP
        port: DB port
        """
        super().initialize_db_properties(database, user, password, host, port)
        if not self.connection:
            try:
                self.connection = pymssql.connect(
                    host=self.host, user=self.user, password=self.password, port=self.port
                )
            except Exception as e:
                logger.error(f"Connection to DB failed with error {e}")

    def get_database_type(self):
        """This function returns the DB type ex. Oracle, MySQL etc"""
        return f"DB Type: {self.DB}"

    def get_database_version(self):
        """This function returns DB version"""
        query = "SELECT @@VERSION AS 'SQL Server Version Details'"
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
        self.connection = pymssql.connect(host=self.host, user=self.user, password=self.password, port=self.port)
        if (not self.dbConnection) or (self.db_name and db_name != self.db_name):
            connstr = f"mssql+pymssql://{self.user}:{self.password}@{self.host}:{self.port}/{db_name}"
            super().make_connection(connection_string=connstr, db_name=db_name)

    def generate_checksum(self, table_name, db_name):
        """Returns checksum/hash for given table within db_name
        Args:
        table_name: Table name for checksum to be calculated
        db_name: DB name where table is present
        Returns:
        checksum as string
        """
        query = f"SELECT CHECKSUM_AGG(CHECKSUM(*)) FROM {table_name}"
        if db_name:
            self.set_db_connection(db_name)
        data = self.dbConnection.execute(query)
        result = data.fetchall()
        return result[0][0]

    def get_size_of_db_in_MB(self, db_name):
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
        query = f"SELECT SUM(SizeMB) FROM (SELECT DB_NAME(database_id) AS DatabaseName, Name AS Logical_Name, Physical_Name, (size * 8) / 1024 SizeMB FROM sys.master_files WHERE DB_NAME(database_id) = '{db_name}') AS TEMP"
        result = self.execute_sql_query(query=query)
        return int(result[0][0])

    def insert_blob(self, db_name, file_path, table_names: list, num_of_records=1):
        """Insert blobs in the DB
        Args:
        db_name: Name of DB
        table_name: Name of table
        num_of_records: count of records to be inserted
        """
        self.set_db_connection(db_name)
        df = pd.DataFrame(super().create_blob(file_path, num_of_records))
        dtype = {
            "id": VARCHAR(),
            "misc": NVARCHAR(),
            "large_data": NVARCHAR(),
            "address": VARCHAR(),
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
        querystr = f"SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_CATALOG='{db_name}' and TABLE_NAME LIKE '%%{table_name_prefix}%%';"
        data = self.dbConnection.execute(querystr)
        rows = data.fetchall()
        tables = [row[0] for row in rows]
        if len(tables):
            self.delete_table(db_name=db_name, table_names=tables)
        else:
            logger.info(f"No tables with prefix {table_name_prefix} found in DB {db_name}")

    def delete_table(self, db_name, table_names: list):
        """Function to delete given table from the database
        Args:
        db_name: Name of DB where table to be deleted is located
        table_name: name of the table to be deleted
        """
        self.set_db_connection(db_name)

        for table in table_names:
            logger.info(f"Dropping table {table}")
            query = f"DROP table IF EXISTS {table};"
            self.execute_sql_query_no_return(query=query)
