from enum import Enum


class AWSRDSWaiters(Enum):
    DB_INSTANCE_AVAILABLE = "db_instance_available"
    DB_INSTANCE_DELETED = "db_instance_deleted"
    DB_SNAPSHOT_AVAILABLE = "db_snapshot_available"
    DB_SNAPSHOT_DELETED = "db_snapshot_deleted"
    DB_SNAPSHOT_COMPLETED = "db_snapshot_completed"
