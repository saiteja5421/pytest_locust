from datetime import datetime
from uuid import UUID

from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import AssetInfo

# Kafka uses the v1 REST encodings for PolicySchedule
from lib.dscc.backup_recovery.protection_policies.models.protection_policies import PolicySchedule


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionKafkaResponse:
    id: UUID
    type: str
    schedules: PolicySchedule

    def __init__(self, id: UUID, type: str, schedules: list[PolicySchedule]) -> None:
        self.id = id
        self.type = type
        self.schedules = (
            [
                PolicySchedule.from_json(schedule) if not isinstance(schedule, PolicySchedule) else schedule
                for schedule in schedules
            ]
            if schedules
            else schedules
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionPolicyKafkaResponse:
    name: str
    id: UUID
    protections: list[ProtectionKafkaResponse]

    def __init__(self, name: str, id: UUID, protections: list[ProtectionKafkaResponse]) -> None:
        self.name = name
        self.id = id
        self.protections = (
            [
                ProtectionKafkaResponse(**protection)
                if not isinstance(protection, ProtectionKafkaResponse)
                else protection
                for protection in protections
            ]
            if protections
            else protections
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionJobKafkaResponse:
    id: UUID
    asset_info: AssetInfo
    # effective_from_date_time: datetime
    protection_policy: ProtectionPolicyKafkaResponse

    def __init__(
        self,
        id: UUID,
        asset_info: AssetInfo,
        # effective_from_date_time: datetime,
        protection_policy: ProtectionPolicyKafkaResponse,
    ):
        self.id = id
        self.asset_info = AssetInfo(**asset_info) if not isinstance(asset_info, AssetInfo) else asset_info
        # self.effective_from_date_time = effective_from_date_time
        self.protection_policy = (
            ProtectionPolicyKafkaResponse(**protection_policy)
            if not isinstance(protection_policy, ProtectionPolicyKafkaResponse)
            else protection_policy
        )
