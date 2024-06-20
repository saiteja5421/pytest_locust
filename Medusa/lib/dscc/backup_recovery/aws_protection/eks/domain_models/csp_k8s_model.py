from dataclasses import dataclass, field
from uuid import UUID

from dataclasses_json import LetterCase, dataclass_json
from lib.common.enums.csp_k8s_cluster_registration_status import CSPK8sClusterRegistrationStatus

from lib.common.enums.csp_k8s_resource_kind import CSPK8sResourceKind
from lib.common.enums.schedule_status import ScheduleStatus
from lib.common.enums.state import State
from lib.common.enums.validate_status import CSPK8sValidateStatus
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ObjectNameResourceType, ObjectReference


@dataclass_json
@dataclass
class EKSScheduleInfoModel:
    id: int
    status: ScheduleStatus
    updated_at: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sProtectionJobInfoModel:
    protection_policy_info: ObjectNameResourceType
    resource_uri: str
    schedule_info: list[EKSScheduleInfoModel]
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sApplicationModel:
    id: UUID
    name: str
    resourceUri: str
    state: State
    protection_job_info: list[CSPK8sProtectionJobInfoModel]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sApplicationsListModel:
    items: list[CSPK8sApplicationModel]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sValidatePropertiesModel:
    status: CSPK8sValidateStatus
    validated_at: str = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sClustersModel:
    name: str
    id: UUID
    registration_status: CSPK8sClusterRegistrationStatus
    validation_info: CSPK8sValidatePropertiesModel
    application_count: int
    state: State


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sClustersListModel:
    items: list[CSPK8sClustersModel]
    total: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sResourceKubernetesPropertiesModel:
    kind: CSPK8sResourceKind
    generation: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sResourceModel:
    name: str
    type: str
    namespace_scoped: bool
    k8s_info: CSPK8sResourceKubernetesPropertiesModel
    application_info: list[ObjectReference]
    namespace_info: ObjectNameResourceType = field(default=None)

    def compare_static_values(self, other):
        if isinstance(other, CSPK8sResourceModel):
            return (
                self.name == other.name
                and self.type == other.type
                and self.namespace_scoped == other.namespace_scoped
                and self.namespace_info.name == other.namespace_info.name
                and self.namespace_info.type == other.namespace_info.type
                and self.k8s_info.kind == other.k8s_info.kind
                and self.k8s_info.generation == other.k8s_info.generation
            )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sResourcesListModel:
    items: list[CSPK8sResourceModel]
