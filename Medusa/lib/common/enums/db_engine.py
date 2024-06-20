from enum import Enum


class DBEngine(Enum):
    # For MySQL 5.6-compatible Aurora
    AURORA = "aurora"

    # For MySQL 5.7-compatible and MySQL 8.0-compatible Aurora
    AURORA_MYSQL = "aurora-mysql"

    AURORA_POSTGRESQL = "aurora-postgresql"
    CUSTOM_ORACLE_EE = "custom-oracle-ee"
    CUSTOM_SQLSERVER_EE = "custom-sqlserver-ee"
    CUSTOM_SQLSERVER_SE = "custom-sqlserver-se"
    CUSTOM_SQLSERVER_WEB = "custom-sqlserver-web"
    MARIADB = "mariadb"
    MYSQL = "mysql"
    ORACLE_EE = "oracle-ee"
    ORACLE_EE_CDB = "oracle-ee-cdb"
    ORACLE_SE2 = "oracle-se2"
    ORACLE_SE2_CDB = "oracle-se2-cdb"
    POSTGRES = "postgres"
    SQLSERVER_EE = "sqlserver-ee"
    SQLSERVER_SE = "sqlserver-se"
    SQLSERVER_EX = "sqlserver-ex"
    SQLSERVER_WEB = "sqlserver-web"
