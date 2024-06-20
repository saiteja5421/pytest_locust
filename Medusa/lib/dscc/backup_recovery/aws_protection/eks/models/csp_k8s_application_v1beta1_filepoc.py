from datetime import datetime
from uuid import UUID

from dataclasses import dataclass, field
from dataclasses_json import config, dataclass_json, LetterCase
from typing import Optional
from lib.dscc.backup_recovery.aws_protection.common.models.common_eks_objects import (
    CSPK8sProtectionJobInfo,
    CSPK8sRefreshProperties,
    CSPK8sBackupProperties,
)
from lib.common.enums.protection_summary import ProtectionStatus
from lib.common.enums.state import State
from lib.dscc.backup_recovery.aws_protection.eks.domain_models.csp_k8s_model import (
    CSPK8sApplicationModel,
    CSPK8sApplicationsListModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sAppStaticMembers:
    k8s_resource_kind: str
    name: str
    resource_uri: str
    state: State
    type: str
    k8s_resource_id: UUID
    storage_classes: list[str]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sMembershipInfo:
    static_members: list[CSPK8sAppStaticMembers]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sCSPInfo:
    region: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sApplication:
    created_at: datetime = field(
        metadata=config(
            encoder=lambda date: date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            decoder=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ"),
        )
    )
    customer_id: str
    generation: int
    id: UUID
    name: str
    resourceUri: str
    type: str
    updated_at: datetime = field(
        metadata=config(
            encoder=lambda date: date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            decoder=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ"),
        )
    )
    backup_info: list[CSPK8sBackupProperties]
    cluster_id: UUID
    account_id: UUID
    membership_info: CSPK8sMembershipInfo
    protection_job_info: list[CSPK8sProtectionJobInfo]
    protection_status: ProtectionStatus
    protection_supported: bool
    protection_unsupported_reasons: list[str]
    refresh_info: CSPK8sRefreshProperties
    state: State
    console_uri: str = None
    csp_info: Optional[CSPK8sCSPInfo] = None

    def to_domain_model(self):
        return CSPK8sApplicationModel(
            id=self.id,
            name=self.name,
            resourceUri=self.resourceUri,
            state=self.state,
            protection_job_info=[protection_job.to_domain_model() for protection_job in self.protection_job_info],
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sApplicationsList:
    items: list[CSPK8sApplication]
    offset: int
    count: int
    total: int

    def to_domain_model(self):
        return CSPK8sApplicationsListModel(items=[item.to_domain_model() for item in self.items])
