from lib.platform.rds.abstract_db_factory import AbstractDatabase
import cx_Oracle
import pandas as pd
from sqlalchemy import create_engine

import logging

logger = logging.getLogger()


# Need to provide path where oracle client lib is installed
cx_Oracle.init_oracle_client(lib_dir=r"/opt/oracle/instantclient_21_9")


class OracleDB(AbstractDatabase):
    def __init__(self):
        self.DB = "OracleDB"
        # NOTE: For oracle we are using hardcoded db_name as 'orcl', required for connection
        self.db_name = "orcl"
        # NOTE: Both self.connection and self.dbConnection are required (differernt value objects)
        # self.dbConnection -> establishes/closes DB connection
        # self.connection -> after self.dbConnection, establishes construct for db operations/queries
        self.connection = None
        self.dbConnection = None

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
            connstr = f"{user}/{password}@{host}:{port}/{self.db_name}"
            try:
                self.connection = cx_Oracle.connect(connstr)
                self.sid = cx_Oracle.makedsn(host, port, sid=self.db_name)
            except Exception as e:
                logger.error(f"Connection to DB failed with error {e}")

    def get_database_type(self):
        """This function returns the DB type ex. Oracle, MySQL etc"""
        return f"DB Type: {self.DB}"

    def get_database_version(self):
        """This function returns DB version"""
        query = "SELECT * FROM v$version"
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
        if not self.dbConnection:
            # Ideally here we should reform self.sid as commented line below, but using db_name="orcl" as of now
            # self.sid = cx_Oracle.makedsn(self.host, self.port, sid=db_name)
            connstr = f"oracle://{self.user}:{self.password}@{self.sid}"
            # Here not calling super().make_connection as we are using "orcl" as db_name
            cnx = create_engine(connstr)
            self.dbConnection = cnx

    def generate_checksum(self, table_name, db_name=None):
        """Returns checksum/hash for given table within db_name
        Args:
        table_name: Table name for checksum to be calculated
        db_name: DB name where table is present
        Returns:
        checksum as string
        """
        table_name = str(table_name).upper()
        query = f"select dbms_sqlhash.gethash('select * from {table_name}', 2) as md5_hash FROM dual"
        if db_name:
            self.set_db_connection(db_name)
        checksum = self.execute_sql_query(query=query)
        return checksum[0][0]

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
            self.set_db_connection(db_name="orcl")
        query = 'select "Reserved_Space(MB)" - "Free_Space(MB)" "Used_Space(MB)" from(select (select sum(bytes/(1014*1024)) from dba_data_files) "Reserved_Space(MB)",(select sum(bytes/(1024*1024)) from dba_free_space) "Free_Space(MB)" from dual)'
        size = self.execute_sql_query(query=query)
        return int(size[0][0])

    def insert_blob(self, db_name, file_path, table_names: list, num_of_records=1):
        """Insert blobs in the DB
        Args:
        db_name: Name of DB
        table_names: list of names of table where blob is to be inserted
        num_of_records: count of records to be inserted
        """
        self.set_db_connection(db_name)
        df = pd.DataFrame(super().create_blob(file_path, num_of_records))
        for table in table_names:
            df.to_sql(table, con=self.dbConnection, index=False, if_exists="append")
            logger.info(f"Inserted {num_of_records} records in table {table}")

    def cleanup_database(self, db_name, table_name_prefix):
        """Function to cleanup the database
        Args:
        db_name: Name of DB whose disk footprint has to be cleaned up
        table_name_prefix : tables name having given prefix will be deleted
        """
        table_name_prefix = str(table_name_prefix).upper()
        logger.info(f"Cleaning up database {db_name}, dropping tables with prefix {table_name_prefix}")
        querystr = f"SELECT table_name FROM user_tables WHERE table_name LIKE '%%{table_name_prefix}%%'"
        rows = self.execute_sql_query(query=querystr)
        tables = [row[0] for row in rows]
        if len(tables):
            self.delete_table(db_name=db_name, table_names=tables)
        else:
            logger.info(f"No tables with prefix {table_name_prefix} found in DB {db_name}")

    def delete_table(self, db_name, table_names: list):
        """Function to delete given table from the database
        Args:
        db_name: Name of DB where table to be deleted is located
        table_names: list of names of the table to be deleted
        """
        self.set_db_connection(db_name)
        for table in table_names:
            logger.info(f"Dropping table {table}")
            query = f"DROP table {table} PURGE"
            self.execute_sql_query_no_return(query=query)
