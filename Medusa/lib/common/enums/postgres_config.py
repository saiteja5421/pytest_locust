from enum import Enum


class PostgresConfig(Enum):
    CAM_DB = "cam-dev"
    IM_DB = "csp-inventory-dev"
    SCHEDULER_DB = "csp_scheduler"
    PG_HOST = "ccs-pg"
    PG_PORT = "5432"
