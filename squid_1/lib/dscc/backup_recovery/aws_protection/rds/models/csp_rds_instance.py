from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    RefreshInfo,
    ObjectIdUriType,
)
from lib.dscc.backup_recovery.aws_protection.common.models.rds_common_objects import (
    RDSObjectCountType,
    RDSInstanceCSPInfo,
    RDSMetadata,
    RDSProtectionJobInfo,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPRDSInstance:
    created_at: str
    customer_id: str
    generation: int
    id: str
    name: str
    resource_uri: str
    type: str
    updated_at: str
    account_info: ObjectIdUriType
    backup_info: list[RDSObjectCountType]
    csp_info: RDSInstanceCSPInfo
    metadata: RDSMetadata
    protection_job_info: list[RDSProtectionJobInfo]
    protection_status: str
    refresh_info: RefreshInfo
    state: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPRDSInstanceList:
    count: int
    limit: int
    offset: int
    total: int
    items: list[CSPRDSInstance]
