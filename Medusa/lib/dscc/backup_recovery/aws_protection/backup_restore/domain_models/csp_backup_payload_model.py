from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase, config
from datetime import datetime
from uuid import UUID
from typing import Optional, Union, cast

from lib.common.enums.aws_region_zone import AWSRegionZone
from lib.common.enums.az_regions import AZRegion
from lib.common.enums.ec2_restore_operation import Ec2RestoreOperation

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import CSPTag
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_model import (
    VolumeAttachmentInfoModel,
)

SENTINEL = cast(object, None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
# NOTE: name & description not included in PATCH API for release at the moment
class PatchEC2EBSBackupsModel:
    # name: str
    # description: str
    expires_at: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostImportSnapshotModel:
    aws_regions: list[AWSRegionZone]
    expiration: datetime
    import_tags: list[CSPTag]
    import_volume_snapshots: bool = field(default=False)
    import_machine_instance_images: bool = field(default=False)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RestoreEBSAWSInfoModel:
    availability_zone: str
    csp_region: str
    size_inGiB: int
    volume_type: str
    is_encrypted: bool = False
    csp_tags: list[CSPTag] = field(default_factory=list)
    multiattach: Optional[bool] = None
    iops: Optional[int] = None
    throughput_inMiBps: Optional[int] = None
    encryption_keyARN: Optional[str] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RestoreAzureDiskInfoModel:
    csp_region: AZRegion
    resource_group_id: str
    size_inGiB: int
    sku_name: str
    csp_tags: list[CSPTag] = field(default_factory=list)
    disk_iops_read_write: Optional[int] = None
    disk_mbps_read_write: Optional[int] = None
    availability_zones: Optional[list[str]] = field(default_factory=list)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TargetVolumeInfoModel:
    account_id: UUID
    csp_info: Union[RestoreEBSAWSInfoModel, RestoreAzureDiskInfoModel]
    name: str = "Target volume name"


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreCspVolumeFromCspInstanceBackupModel:
    device_name: str
    target_volume_info: TargetVolumeInfoModel


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class InstanceAttachmentInfoModel:
    machine_instance_id: UUID
    attachment_type: str = "REPLACE"
    delete_original_volume: bool = False
    device: Optional[str] = field(default=SENTINEL, metadata=config(exclude=lambda x: x is SENTINEL))
    lun: Optional[int] = field(default=SENTINEL, metadata=config(exclude=lambda x: x is SENTINEL))


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreCspVolumeModel:
    target_volume_info: TargetVolumeInfoModel
    instance_attachment_info: list[InstanceAttachmentInfoModel] = field(default_factory=list)


####
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RestoreEC2AWSInfoModel:
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
    block_device_mappings: Optional[list[VolumeAttachmentInfoModel]] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class OriginalMachineInstanceInfoModel:
    terminate_original: bool = False


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TargetMachineInstanceInfoModel:
    account_id: UUID
    csp_info: RestoreEC2AWSInfoModel
    name: Optional[str] = ""


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreCspMachineInstanceModel:
    target_machine_instance_info: TargetMachineInstanceInfoModel
    original_machine_instance_info: OriginalMachineInstanceInfoModel
    operation_type: str = Ec2RestoreOperation.CREATE.value
