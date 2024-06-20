from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.common import (
    MSCommonObjectInfo,
    MSBackupProtectionPolicyInfo,
    MSBackupScheduleInfo,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ItemSummary:
    item_type: str
    items_count: int
    size_in_bytes: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365Backup:
    customer_id: str
    generation: int
    id: str
    name: str
    resource_uri: str
    type: str
    account_info: MSCommonObjectInfo
    asset_info: MSCommonObjectInfo
    backup_type: str
    csp_id: str
    csp_type: str
    description: str
    index_state: str
    protection_job_info: MSCommonObjectInfo
    protection_policy_info: MSBackupProtectionPolicyInfo
    schedule_info: MSBackupScheduleInfo
    state: str
    state_reason: str
    status: str
    trigger_type: str
    created_at: Optional[str] = ""
    updated_at: Optional[str] = ""
    expires_at: Optional[str] = ""
    locked_until: Optional[str] = ""
    started_at: Optional[str] = ""
    item_summary: list[ItemSummary] = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365BackupsList:
    count: int
    offset: int
    total: int
    items: list[MS365Backup]
