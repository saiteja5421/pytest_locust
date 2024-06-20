from abc import ABC, abstractmethod
from faker import Faker
import pandas as pd
import logging
import uuid
from sqlalchemy import create_engine

fake = Faker()

logger = logging.getLogger()


class AbstractDatabase(ABC):
    def __init__(self):
        # NOTE: Both self.connection and self.dbConnection are required (differernt value objects)
        # self.dbConnection -> establishes/closes DB connection
        # self.connection -> after self.dbConnection, establishes construct for db operations/queries
        self.connection = None
        self.dbConnection = None

    @abstractmethod
    def get_database_type(self):
        """This function returns the DB type ex. Oracle, MySQL etc"""
        pass

    @abstractmethod
    def get_database_version(self, connection):
        """This function returns DB version

        Args:
        connection: DB connection

        Returns : String of DB version
        """
        pass

    def execute_sql_query_no_return(self, query):
        """This function executed sql query and does not return any value
        Args:
        query : Query to be executed on the DB
        """
        self.dbConnection.execute(query)

    def execute_sql_query(self, query):
        """This function executes the query on the DB
        Args:
        query : Query to be executed on the DB

        Returns:
        Query result
        """
        cur = self.connection.cursor()
        cur.execute(query)
        result = cur.fetchall()
        cur.close()
        return result

    def create_records(self, num_of_records=1):
        """This function creates records to be inserted in the DB.
        Args:
        num_of_records: Count of records to be created

        Returns:
        Array of records
        """
        output = [
            {
                "name": fake.name(),
                "address": fake.address(),
                "email": fake.email(),
                "city": fake.city(),
                "state": fake.state(),
                "date_time": fake.date_time(),
            }
            for x in range(num_of_records)
        ]
        return output

    def create_records_of_size(self, size_in_mb=1, num_of_records=1):
        """creates records of the requested size
        Args:
        size_in_mb: Integer for size of record to be created
        num_of_records: Integer count of records to be created
        Returns:
        Array of records
        """
        length = 1024 * 1024 * size_in_mb
        output = [{"id": fake.name(), "misc": fake.binary(length=length)} for x in range(num_of_records)]
        return output

    def create_blob(self, file_path, num_of_records=1):
        """Creates blob by reading binary file, which can then be inserted in the DB for bloating it.
        Args:
        file_path: Path of binary file which will be used to form the blob
        num_of_records: Count of blob records to be created.
        Returns:
        Array of Blob records to be inserted in DB
        """
        data = self.read_file(file_path)
        output = []
        for x in range(num_of_records):
            data_name = bytes(fake.name(), encoding="utf-8") + data + bytes(fake.name(), encoding="utf-8")
            data_address = bytes(fake.address(), encoding="utf-8") + data + bytes(fake.address(), encoding="utf-8")
            output.append(
                {
                    "id": fake.name(),
                    "misc": data_name,
                    "large_data": data_address,
                    "address": fake.address(),
                }
            )
        return output

    @abstractmethod
    def get_size_of_db_in_MB(db_name=None):
        """Returns size of DB in MB
        Args:
        db_name: Name of DB whose size is to be returned (optional else default DB name used while created DB connection will be used)
        """
        pass

    def read_file(self, file_path):
        """Reads binary file which will be used for creating BLOBs records to be inserted in DB.
        Args:
        file_path : Binary file path used to created BLOB records to be inserted in DB
        Returns:
        File content
        """
        with open(file_path, "rb") as f:
            obj = f.read()
        return obj

    def initialize_db_properties(self, database, user, password, host, port):
        """Function to create DB connection and initialize params needed for connection
        Args:
        database: DB name
        user: DB user name
        password: Password
        host: DB host name/url/IP
        port: DB port
        """
        self.database = database
        self.user = user
        self.password = password
        self.host = host
        self.port = port

    @abstractmethod
    def set_db_connection(self, db_name):
        """Function to setup DB connection
        Args:
        db_name: Name of database
        """
        pass

    def insert_records_in_db(self, db_name, table_names: list, num_of_records):
        """Function used to insert preformed data records in DB
        Args:
        db_name: Name of database where records will be inserted
        table_names: list of names of tables in which records will be inserted
        num_of_records: Count of table rows which will be inserted in each table
        """
        self.set_db_connection(db_name)
        df = pd.DataFrame(self.create_records(num_of_records))
        for table in table_names:
            df.to_sql(table, con=self.dbConnection, index=False, if_exists="append")
            logger.info(f"Inserted records in table {table}")

    def close_db_connection(self):
        """This function will close db connection"""
        self.connection.close()

    def fill_database_to_size(self, db_name, table_name_prefix, file_path, target_size_in_GB=1):
        """Function to populated DBs with records so that its disk footprint grows to target size
        Args:
        db_name: Name of DB whose disk footprint has to be grown
        table_name_prefix : This prefix will be added to tables being created for growing db size
        target_size_in_GB: Size upto which DB disk footprint has to be grown
        """
        num_of_records = 20
        myuuidstr = str(uuid.uuid4()).split("-")[0]
        initial_size = int(self.get_size_of_db_in_MB(db_name))
        target_size_in_MB = int(target_size_in_GB) * 1024
        logger.info(f"Initial size in MB {initial_size} and target size in MB {target_size_in_MB}")
        current_size = initial_size
        counter = 1
        while current_size < target_size_in_MB:
            table_name = table_name_prefix + "_" + myuuidstr + "_" + str(counter)
            self.insert_blob(db_name, file_path, table_names=[table_name], num_of_records=num_of_records)
            current_size = self.get_size_of_db_in_MB(db_name)
            logger.info(f"current_size in MB {current_size}")
            counter += 1
        logger.info(f"Successfully filled {db_name} to size {current_size}")

    def make_connection(self, connection_string, db_name):
        """Helper function used across DBs to create connection
        Args:
            connection_string (string): connection string
            db_name (string): DB anme
        """
        cnx = create_engine(connection_string)
        self.dbConnection = cnx
        self.db_name = db_name
