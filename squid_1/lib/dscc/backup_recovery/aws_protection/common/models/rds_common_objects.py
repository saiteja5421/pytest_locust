from dataclasses import dataclass, field
from typing import Optional
from dataclasses_json import dataclass_json, LetterCase, config
from common.enums.db_engine import DBEngine
from common.enums.schedule_status import ScheduleStatus
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    CSPTag,
    ObjectId,
    ObjectName,
    ObjectNameResourceType,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RDSScheduleInfo:
    number: str
    status: ScheduleStatus
    updated_at: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RDSProtectionJobInfo:
    protection_policy_info: ObjectNameResourceType
    resource_uri: str
    schedule_info: list[RDSScheduleInfo]
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RDSMetadata:
    cloud_backup_enabled: bool
    cloud_native_backup_enabled: bool
    not_supported_reason: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RDSStorageInfo:
    allocated_storage_in_gb: int
    max_allocated_storage_in_gb: int
    storage_encrypted: bool
    storage_type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RDSNetworkInfo:
    security_groups: list[str]
    subnet_group: ObjectName
    vpc_info: ObjectId
    vpc_security_group_ids: list[str]


# the ObjectCountType in common_objects had its "type" field renamed to "backupType"
# PR: https://github.hpe.com/nimble/qa_automation/pull/5502
@dataclass
class RDSObjectCountType:
    count: int
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RDSInstanceCSPInfo:
    identifier: str
    csp_reference: str
    csp_region: str
    engine: str
    engine_version: str
    status: str
    multi_az: bool
    availability_zone: str
    secondary_availability_zone: str
    kms_key_id: str
    parameter_group_names: list[str]
    option_group_names: list[str]
    csp_tags: list[CSPTag]
    network_info: RDSNetworkInfo
    storage_info: RDSStorageInfo
    # The the RDS "cspInfo" from DSCC contains a field named "class".
    # Since "class" is a reserved word, we'll use "class_" and give
    # it the "cspInfo.class" value provided.
    class_: str = field(metadata=config(field_name="class"), default=None)


# because the "class_" field in the parent has a default value,
# the 3 additional fields in this object need to be declared Optional
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RDSBackupCSPInfo(RDSInstanceCSPInfo):
    id: Optional[str] = None
    customer_id: Optional[str] = None
    type: Optional[str] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RDSDBEnginesCountsPorts:
    """Object used during creation for tracking a list of RDS DB configurations of DBEngine, Counts, and Ports"""

    db_engine: DBEngine
    db_count: int
    db_port: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RDSDBConnection:
    """Object used during connection to DB

    Args:
        ec2_bastion_id (str): EC2 Instance bastion ID used as parameter for RDSProxy()
        ec2_key_pair_name (str): EC2 key pair name in relation to EC2 Instance bastion used as parameter for RDSProxy()
        rds_instance_identifier (str): AWS RDS DB Instance identifier
        engine (DBEngine): DB Engine
        port (int): DB Port
        local_port (int): DB local port that was fixed during DB bindings for RDSProxy()
        db_host (str): DB host endpoint
        host (str): localhost used during DB connection
        user (str): DB username during DB creation
        password (str): DB password during DB creation
        db_name (str): DB name during DB creation
    """

    ec2_bastion_id: str = None
    ec2_key_pair_name: str = None
    rds_instance_identifier: str = None
    engine: DBEngine = None
    port: int = None
    local_port: int = None
    db_host: str = None
    host: str = "localhost"
    user: str = None
    password: str = None
    db_name: str = None
