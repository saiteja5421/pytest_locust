from enum import Enum


class DBEngineVersion(Enum):
    # For MySQL 5.6-compatible Aurora
    AURORA = "aurora"

    # For MySQL 5.7-compatible and MySQL 8.0-compatible Aurora
    AURORA_MYSQL = "2.11.1"

    AURORA_POSTGRESQL = "14.6"

    # NOTE: No custom engine version for custom oracle enterprise edition at the moment
    # CUSTOM_ORACLE_EE = "custom-oracle-ee"

    CUSTOM_SQLSERVER_EE = "15.00.4261.1.v1"
    CUSTOM_SQLSERVER_SE = "15.00.4261.1.v1"
    CUSTOM_SQLSERVER_WEB = "15.00.4261.1.v1"
    MARIADB = "10.6.11"
    MYSQL = "8.0.28"
    ORACLE_EE = "19.0.0.0.ru-2023-01.rur-2023-01.r1"
    ORACLE_EE_CDB = "19.0.0.0.ru-2023-01.rur-2023-01.r1"
    ORACLE_SE2 = "19.0.0.0.ru-2023-01.rur-2023-01.r1"
    ORACLE_SE2_CDB = "19.0.0.0.ru-2023-01.rur-2023-01.r1"
    POSTGRES = "14.6"
    SQLSERVER_EE = "15.00.4236.7.v1"
    SQLSERVER_SE = "15.00.4236.7.v1"
    SQLSERVER_EX = "15.00.4236.7.v1"
    SQLSERVER_WEB = "15.00.4236.7.v1"

    # Major Engine Versions

    MAJOR_MARIADB = "10.6"
    MAJOR_MYSQL = "8.0"
    MAJOR_ORACLE_EE = "19"
    MAJOR_ORACLE_EE_CDB = "19"
    MAJOR_ORACLE_SE2 = "19"
    MAJOR_ORACLE_SE2_CDB = "19"
    MAJOR_SQLSERVER_EE = "15.00"
    MAJOR_SQLSERVER_SE = "15.00"
    MAJOR_SQLSERVER_EX = "15.00"
    MAJOR_SQLSERVER_WEB = "15.00"
