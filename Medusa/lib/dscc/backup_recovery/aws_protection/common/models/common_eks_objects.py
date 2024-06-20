from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ObjectNameResourceType
from lib.common.enums.refresh_status import CSPK8sRefreshStatus
from lib.common.enums.validate_status import CSPK8sValidateStatus
from lib.common.enums.csp_backup_type import CSPBackupType
from lib.common.enums.schedule_status import ScheduleStatus
from lib.dscc.backup_recovery.aws_protection.eks.domain_models.csp_k8s_model import (
    CSPK8sProtectionJobInfoModel,
    CSPK8sValidatePropertiesModel,
    EKSScheduleInfoModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EKSScheduleInfo:
    id: int
    status: ScheduleStatus
    updated_at: str

    def to_domain_model(self):
        return EKSScheduleInfoModel(id=self.id, status=self.status, updated_at=self.updated_at)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sProtectionJobInfo:
    protection_policy_info: ObjectNameResourceType
    resource_uri: str
    schedule_info: list[EKSScheduleInfo]
    type: str

    def to_domain_model(self):
        return CSPK8sProtectionJobInfoModel(
            protection_policy_info=self.protection_policy_info,
            resource_uri=self.resource_uri,
            schedule_info=[item.to_domain_model() for item in self.schedule_info],
            type=self.type,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sRefreshProperties:
    status: CSPK8sRefreshStatus
    refreshed_at: str = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sValidateProperties:
    status: CSPK8sValidateStatus
    validated_at: str = field(default=None)

    def to_domain_model(self):
        return CSPK8sValidatePropertiesModel(status=self.status, validated_at=self.validated_at)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sBackupProperties:
    count: int
    type: CSPBackupType
