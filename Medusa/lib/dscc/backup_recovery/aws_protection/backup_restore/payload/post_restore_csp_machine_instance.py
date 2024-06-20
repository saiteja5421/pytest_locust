from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID
from dataclasses_json import dataclass_json, LetterCase
from lib.common.enums.ec2_restore_operation import Ec2RestoreOperation
from lib.dscc.backup_recovery.aws_protection.backup_restore.models.csp_backup import VolumeAttachmentInfo
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import CSPTag


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RestoreEC2AWSInfo:
    availability_zone: str
    csp_region: str
    instance_type: str
    key_pair_name: str = "my-key-pair"
    security_group_ids: list[str] = field(default_factory=list)
    disable_termination: Optional[bool] = False
    csp_tags: Optional[list[CSPTag]] = field(default_factory=list)
    iam_instance_profile: Optional[str] = None
    private_ip_address: Optional[str] = None
    subnet_csp_id: Optional[str] = None
    block_device_mappings: Optional[list[VolumeAttachmentInfo]] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class OriginalMachineInstanceInfo:
    terminate_original: bool = False


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TargetMachineInstanceInfo:
    account_id: UUID
    csp_info: RestoreEC2AWSInfo
    name: Optional[str] = ""


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreCspMachineInstance:
    target_machine_instance_info: TargetMachineInstanceInfo
    original_machine_instance_info: OriginalMachineInstanceInfo
    operation_type: str = Ec2RestoreOperation.CREATE.value
