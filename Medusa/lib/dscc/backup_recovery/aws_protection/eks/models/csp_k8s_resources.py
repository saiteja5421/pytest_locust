from datetime import datetime
from uuid import UUID

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ObjectNameResourceType,
    CSPTag,
    ObjectReference,
)
from lib.common.enums.state import State
from lib.common.enums.csp_k8s_resource_kind import CSPK8sResourceKind
from lib.dscc.backup_recovery.aws_protection.common.models.common_eks_objects import CSPK8sRefreshProperties
from lib.dscc.backup_recovery.aws_protection.eks.domain_models.csp_k8s_model import (
    CSPK8sResourceKubernetesPropertiesModel,
    CSPK8sResourceModel,
    CSPK8sResourcesListModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sResourceKubernetesProperties:
    configuration_in_yaml: str
    created_at: datetime
    generation: int
    id: UUID
    kind: CSPK8sResourceKind
    labels: list[CSPTag]

    def to_domain_model(self):
        return CSPK8sResourceKubernetesPropertiesModel(kind=self.kind, generation=self.generation)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sResource:
    created_at: datetime
    customer_id: str
    generation: int
    id: UUID
    name: str
    resource_uri: str
    type: str
    updated_at: datetime
    application_info: list[ObjectReference]
    cluster_id: UUID
    k8s_info: CSPK8sResourceKubernetesProperties
    namespace_scoped: bool
    refresh_info: CSPK8sRefreshProperties
    state: State
    console_uri: str = None
    namespace_info: ObjectNameResourceType = field(default=None)

    def to_domain_model(self):
        return CSPK8sResourceModel(
            name=self.name,
            type=self.type,
            namespace_scoped=self.namespace_scoped,
            namespace_info=self.namespace_info,
            k8s_info=self.k8s_info,
            application_info=self.application_info,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sResourcesList:
    items: list[CSPK8sResource]
    count: int
    offset: int
    total: int

    def to_domain_model(self):
        return CSPK8sResourcesListModel(items=[item.to_domain_model() for item in self.items])
