from dataclasses import dataclass, field
import datetime
from dataclasses_json import config, dataclass_json, LetterCase
from typing import Optional
import re

from lib.common.enums.account_validation_status import ValidationStatus
from lib.common.enums.csp_type import CspType
from lib.common.enums.inventory_type import InventoryType
from lib.common.enums.refresh_status import CSPK8sRefreshStatus
from lib.dscc.backup_recovery.aws_protection.accounts.domain_models.csp_account_model import (
    CSPAccountModel,
    CSPAccountListModel,
    CSPAccountValidateModel,
    CSPOnboardingTemplateModel,
    PatchCSPAccountModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPAccountRefreshInfo:
    inventory_type: InventoryType
    status: CSPK8sRefreshStatus
    started_at: datetime


# NOTE: This "CSPAccountOnboardingTemplate" object is returned as part of "CSPAccount"
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

    def to_domain_model(self):
        return CSPAccountModel(
            customerId=self.customerId,
            id=self.id,
            name=self.name,
            resourceUri=self.resourceUri,
            suspended=self.suspended,
            cspType=self.cspType,
            cspId=self.cspId,
            validationStatus=self.validationStatus,
            services=self.services,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPAccountList:
    items: list[CSPAccount]
    count: int
    offset: int
    total: int

    def to_domain_model(self):
        account_model_list: list[CSPAccountModel] = []
        for item in self.items:
            account_model_list.append(item.to_domain_model())

        return CSPAccountListModel(
            items=account_model_list,
            count=self.count,
            offset=self.offset,
            total=self.total,
        )


# NOTE: This "CSPOnboardingTemplate" object is returned from API call:  GET /csp-accounts/{id}/onboardingtemplate
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPOnboardingTemplate:
    onboardingTemplate: str = field(metadata=config(field_name="onboardingtemplate"))
    version: str

    # We have the same fields on all clusters and for all versions of API. Adding for consistency
    def to_domain_model(self):
        return CSPOnboardingTemplateModel(onboardingTemplate=self.onboardingTemplate, version=self.version)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PatchCSPAccount:
    name: str
    suspended: bool = False

    @staticmethod
    def from_domain_model(domain_model: PatchCSPAccountModel):
        return PatchCSPAccount(name=domain_model.name, suspended=domain_model.suspended)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPAccountValidate:
    required_action: str = None

    def to_domain_model(self):
        authentication_code = self.required_action.split()[-3] if self.required_action else ""
        device_login_url = re.findall(r"https?://\S+", self.required_action)[0] if self.required_action else ""
        return CSPAccountValidateModel(authentication_code=authentication_code, device_login_url=device_login_url)
