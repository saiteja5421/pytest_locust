import datetime
from uuid import UUID
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ObjectId,
    CSPTag,
)
from lib.dscc.backup_recovery.aws_protection.common.models.common_eks_objects import (
    CSPK8sRefreshProperties,
    CSPK8sValidateProperties,
)

from lib.common.enums.csp_k8s_cluster_registration_status import CSPK8sClusterRegistrationStatus
from lib.common.enums.state import State
from lib.common.enums.ipfamily_type import K8sResourceIPType
from lib.dscc.backup_recovery.aws_protection.eks.domain_models.csp_k8s_model import (
    CSPK8sClustersListModel,
    CSPK8sClustersModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class K8sResourceIPDetails:
    cidr_block: str
    ip_family: K8sResourceIPType


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sNetworkProperties:
    ip_details: K8sResourceIPDetails
    subnets: list[ObjectId]
    vpc: ObjectId


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sAwsEksClusterInfo:
    platform_version: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sClusterEncryptionInfo:
    encryption_key_id: str
    resource_types: list[str]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EKSCSPInfo:
    access_profile_id: str
    aws_eks: CSPK8sAwsEksClusterInfo
    encryption_info: list[CSPK8sClusterEncryptionInfo]
    id: str
    endpoint: str
    endpoint_public_access: bool
    network_info: CSPK8sNetworkProperties
    region: str
    state: str
    csp_tags: list[CSPTag]
    created_at: datetime = field(
        default=None,
        metadata=dict(
            encoder=lambda date: date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            decoder=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ") if date else None,
        ),
    )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sClusters:
    customer_id: str
    generation: int
    id: UUID
    name: str
    resource_uri: str
    type: str
    account_id: UUID
    application_count: int
    csp_info: EKSCSPInfo
    data_protection_supported: bool
    data_protection_unsupported_reason: list[str]
    k8s_version: str
    refresh_info: CSPK8sRefreshProperties
    registration_status: CSPK8sClusterRegistrationStatus
    state: State
    validation_info: CSPK8sValidateProperties
    created_at: datetime = field(
        default=None,
        metadata=dict(
            encoder=lambda date: date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            decoder=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ") if date else None,
        ),
    )
    updated_at: datetime = field(
        default=None,
        metadata=dict(
            encoder=lambda date: date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            decoder=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ") if date else None,
        ),
    )
    console_uri: str = None

    def to_domain_model(self):
        return CSPK8sClustersModel(
            name=self.name,
            id=self.id,
            registration_status=self.registration_status,
            validation_info=self.validation_info,
            application_count=self.application_count,
            state=self.state,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sClustersList:
    items: list[CSPK8sClusters]
    count: int
    offset: int
    total: int

    def to_domain_model(self):
        return CSPK8sClustersListModel(items=[item.to_domain_model() for item in self.items], total=self.total)
