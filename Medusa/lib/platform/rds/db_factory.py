from lib.platform.rds.mssql_db import MSSQLDB
from lib.platform.rds.mysql_db import MySQLDB
from lib.platform.rds.oracle_db import OracleDB
from lib.platform.rds.postgres_sql import PostgresSQLDB
from lib.platform.rds.maria_db import MariaDB
from lib.common.enums.db_engine import DBEngine
import logging

logger = logging.getLogger()


class DBFactory:
    """
    Base class factory to return the DB object as per input db type passed as input
    """

    @staticmethod
    def get_db(db: DBEngine):
        try:
            if "mysql" in db.value:
                return MySQLDB()
            elif "sqlserver" in db.value:
                return MSSQLDB()
            elif "oracle" in db.value:
                return OracleDB()
            elif "postgres" in db.value:
                return PostgresSQLDB()
            elif "mariadb" in db.value:
                return MariaDB()
            raise AssertionError("DB type is not valid.")
        except AssertionError as e:
            logger.error(f"Database {db} not found, returning error {e}")
