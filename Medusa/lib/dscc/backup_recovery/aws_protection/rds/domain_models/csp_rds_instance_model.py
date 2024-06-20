from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ObjectIdUriType,
)
from lib.dscc.backup_recovery.aws_protection.common.models.rds_common_objects import (
    RDSObjectCountType,
    RDSInstanceCSPInfo,
    RDSProtectionJobInfo,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPRDSInstanceModel:
    customer_id: str
    id: str
    name: str
    resource_uri: str
    account_info: ObjectIdUriType
    backup_info: list[RDSObjectCountType]
    csp_info: RDSInstanceCSPInfo
    protection_job_info: list[RDSProtectionJobInfo]
    protection_status: str
    state: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPRDSInstanceListModel:
    count: int
    limit: int
    offset: int
    total: int
    items: list[CSPRDSInstanceModel]
