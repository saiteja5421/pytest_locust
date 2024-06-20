from enum import Enum


class RDSSnapshotType(Enum):
    AUTOMATED = "automated"
    MANUAL = "manual"
    SHARED = "shared"
    PUBLIC = "public"
    AWSBACKUP = "awsbackup"
