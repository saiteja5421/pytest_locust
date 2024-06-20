from dataclasses import dataclass, field
import datetime
from dataclasses_json import config, dataclass_json, LetterCase
from typing import Optional

from common.enums.account_validation_status import ValidationStatus
from common.enums.csp_type import CspType
from common.enums.inventory_type import InventoryType
from common.enums.refresh_status import CSPK8sRefreshStatus


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPAccountRefreshInfo:
    inventory_type: InventoryType
    status: CSPK8sRefreshStatus
    started_at: datetime


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPAccountOnboardingTemplate:
    version_applied: str
    latest_version: str
    upgrade_needed: bool
    message: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPAccount:
    customerId: str
    generation: int
    id: str
    name: str
    resourceUri: str
    type: str
    suspended: bool
    cspType: CspType
    cspId: str
    createdAt: str
    updatedAt: str
    validationStatus: ValidationStatus
    validatedAt: str
    onboardingTemplate: CSPAccountOnboardingTemplate
    inventory_refresh_info: list[CSPAccountRefreshInfo]
    validationErrors: list[str] = None
    refreshedAt: Optional[str] = field(default=None)
    services: list[str] = field(default_factory=lambda: [])


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPAccountList:
    items: list[CSPAccount]
    count: int
    offset: int
    total: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPOnboardingTemplate:
    onboardingTemplate: str = field(metadata=config(field_name="onboardingtemplate"))
    version: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPAccountInfoEvent:
    id: str
    name: str
    serviceProviderId: str
    status: int
    type: int
    paused: bool
    validationStatus: int
    generation: int
