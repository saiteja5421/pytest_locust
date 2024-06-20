import logging
import psycopg2
from psycopg2.extras import NamedTupleCursor
from lib.common.config.config_manager import ConfigManager

logger = logging.getLogger()


class PostgresManager:
    def __init__(self) -> None:
        config = ConfigManager.get_config()
        self.postgres_config = config["POSTGRES"]
        self.user = self.postgres_config["user"]
        self.password = self.postgres_config["password"]

    def create_db_connection(self, db_name: str, host: str, port: str):
        """Establishes connection to the Postgres DB

        Args:
            db_name (str): DB Name to run query against.
            Eg. 'cam-dev', 'csp-inventory-dev'
            host (str): Host of Postgres DB, eg. 127.0.0.1 or ccs-pg
            port (str): Port at which Postgres is running, eg. 5432

        Returns:
            Connection : connection object to the DB which can be used to run query
        """
        # establishing the connection
        connection = psycopg2.connect(database=db_name, user=self.user, password=self.password, host=host, port=port)

        return connection

    def __get_cursor(self, connection):
        """Private method returns cursor to execute DB queries

        Args:
            connection (_type_): DB connection acquired using create_db_connection() method

        Returns:
            _type_: cursor to execute DB query
        """
        cursor = connection.cursor(cursor_factory=NamedTupleCursor)
        return cursor

    def execute_query(self, connection, query: str):
        """Uses the connection created using create_db_connection() method
        and return the query results

        Args:
            connection (_type_): Use create_db_connection() method to create a connect and pass to this method
            query (str): Query to be executed

        Returns:
            _type_: Query Results
        """
        cursor = self.__get_cursor(connection=connection)
        cursor.execute(query)
        query_results = cursor.fetchall()
        logger.info(f"Query = {query} \n Result = {query_results}")
        return query_results

    def close_db_connection(self, connection):
        """Teardown method to close DB Connection

        Args:
            connection (_type_): DB connection acquired using create_db_connection() method
        """
        self.__get_cursor(connection=connection).close()
        connection.close()
