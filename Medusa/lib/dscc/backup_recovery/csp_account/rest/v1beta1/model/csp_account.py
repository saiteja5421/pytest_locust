from dataclasses import dataclass
import datetime
from uuid import UUID
from dataclasses_json import dataclass_json, LetterCase
from lib.common.enums.account_validation_status import ValidationStatus

from lib.common.enums.csp_type import CspType
from lib.common.enums.refresh_status import CSPK8sRefreshStatus


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPAccountOnboardingTemplate:
    version_applied: str
    message: str
    upgrade_needed: bool
    latest_version: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPAccountRefreshInfo:
    inventory_type: str
    status: CSPK8sRefreshStatus
    started_at: datetime


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPAccount:
    csp_id: str
    csp_type: CspType
    onboarding_template: CSPAccountOnboardingTemplate
    inventory_refresh_info: list[CSPAccountRefreshInfo]
    services: list[str]
    suspended: bool
    validated_at: datetime
    validation_errors: list[str]
    validation_status: ValidationStatus
    created_at: datetime
    customer_id: str
    generation: int
    id: UUID
    name: str
    resource_uri: str
    type: str
    updated_at: datetime


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
    onboardingtemplate: str
    version: str
