from dataclasses_json import dataclass_json, LetterCase
from dataclasses import dataclass

from lib.common.enums.account_validation_status import ValidationStatus
from lib.common.enums.csp_type import CspType


# NOTE: This "CSPOnboardingTemplateModel" object is for object returned from API call:  GET /csp-accounts/{id}/onboardingtemplate
@dataclass
class CSPOnboardingTemplateModel:
    onboardingTemplate: str
    version: str


@dataclass
class CSPAccountModel:
    customerId: str
    id: str
    name: str
    resourceUri: str
    suspended: bool
    cspType: CspType
    cspId: str
    validationStatus: ValidationStatus
    services: list[str]


@dataclass
class CSPAccountListModel:
    items: list[CSPAccountModel]
    count: int
    offset: int
    total: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PatchCSPAccountModel:
    name: str
    suspended: bool = False


@dataclass
class CSPAccountValidateModel:
    authentication_code: str
    device_login_url: str
    task_id: str = None
