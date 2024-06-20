from enum import Enum


class OnPremProtectionJobType(Enum):
    # Used by function tests for Kafka
    VOLUME_PROTECTION_GROUP_PROT_JOB = "VolumeProtectionGroup"
    MSSQL_DATABASE_PROTECTION_GROUP = "MSSQLDatabaseProtectionGroup"
