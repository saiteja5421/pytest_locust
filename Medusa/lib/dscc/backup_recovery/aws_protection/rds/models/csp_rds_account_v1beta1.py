from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import RefreshInfo
from lib.dscc.backup_recovery.aws_protection.rds.domain_models.csp_rds_account_model import CSPRDSAccountModel


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPRDSAccount:
    created_at: str
    customer_id: str
    generation: int
    id: str
    name: str
    resource_uri: str
    type: str
    updated_at: str
    refresh: RefreshInfo

    def to_domain_model(self):
        return CSPRDSAccountModel(
            customer_id=self.customer_id,
            id=self.id,
            name=self.name,
            resource_uri=self.resource_uri,
            type=self.type,
            refresh=self.refresh,
        )
