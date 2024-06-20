from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
import datetime
from uuid import UUID
from lib.common.enums.backup_state import BackupState
from lib.common.enums.csp_backup_type import CSPBackupType
from lib.common.enums.status import Status
from lib.dscc.backup_recovery.aws_protection.common.models.rds_common_objects import RDSBackupCSPInfo


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPRDSInstanceBackupModel:
    id: UUID
    name: str
    backup_type: CSPBackupType
    csp_info: RDSBackupCSPInfo
    expires_at: datetime
    point_in_time: datetime
    state: BackupState
    status: Status


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPRDSInstanceBackupListModel:
    count: int
    limit: int
    offset: int
    total: int
    items: list[CSPRDSInstanceBackupModel]
