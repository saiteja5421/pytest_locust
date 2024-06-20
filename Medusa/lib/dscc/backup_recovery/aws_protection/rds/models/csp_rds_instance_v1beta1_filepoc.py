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
from lib.dscc.backup_recovery.aws_protection.rds.domain_models.csp_rds_instance_model import (
    CSPRDSInstanceListModel,
    CSPRDSInstanceModel,
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

    def to_domain_model(self):
        return CSPRDSInstanceModel(
            customer_id=self.customer_id,
            id=self.id,
            name=self.name,
            resource_uri=self.resource_uri,
            account_info=self.account_info,
            backup_info=self.backup_info,
            csp_info=self.csp_info,
            protection_job_info=self.protection_job_info,
            protection_status=self.protection_status,
            state=self.state,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPRDSInstanceList:
    count: int
    limit: int
    offset: int
    total: int
    items: list[CSPRDSInstance]

    def to_domain_model(self):
        return CSPRDSInstanceListModel(
            items=[item.to_domain_model() for item in self.items],
            limit=self.limit,
            count=self.count,
            offset=self.offset,
            total=self.total,
        )
