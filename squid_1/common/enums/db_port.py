from enum import Enum


class DBPort(Enum):
    MARIADB = 3306
    MYSQL = 3306
    ORACLE = 1521
    POSTGRES = 5432
    SQLSERVER = 1433
