from dataclasses import dataclass, field, InitVar
from dataclasses_json import dataclass_json, LetterCase
from datetime import datetime
from typing import Optional, Union
from uuid import UUID

from lib.common.enums.aws_region_zone import AWSRegionZone
from lib.common.enums.ec2_restore_operation import Ec2RestoreOperation
from lib.common.enums.az_regions import AZRegion

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import CSPTag

from lib.dscc.backup_recovery.aws_protection.backup_restore.models.csp_backup_v1beta1_filepoc import (
    VolumeAttachmentInfo,
)
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_payload_model import (
    RestoreEBSAWSInfoModel,
    RestoreEC2AWSInfoModel,
    TargetMachineInstanceInfoModel,
    TargetVolumeInfoModel,
    InstanceAttachmentInfoModel,
    PostRestoreCspMachineInstanceModel,
    PostRestoreCspVolumeFromCspInstanceBackupModel,
    PostRestoreCspVolumeModel,
    PatchEC2EBSBackupsModel,
    PostImportSnapshotModel,
    OriginalMachineInstanceInfoModel,
    RestoreAzureDiskInfoModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
# NOTE: name & description not included in PATCH API for release at the moment
class PatchEC2EBSBackups:
    # name: str
    # description: str
    expires_at: str

    @staticmethod
    def from_domain_model(domain_model: PatchEC2EBSBackupsModel):
        return PatchEC2EBSBackups(expires_at=domain_model.expires_at)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostImportSnapshot:
    aws_regions: InitVar[list[AWSRegionZone]]
    expiration: InitVar[datetime]
    import_tags: list[CSPTag]
    import_volume_snapshots: bool = field(default=False)
    import_machine_instance_images: bool = field(default=False)

    # Not to be used while creating the payload.
    # __post_init__ will take care of populating these fields
    expires_at: str = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    csp_regions: list[str] = field(default_factory=list[str])

    def __post_init__(self, aws_regions: list[AWSRegionZone], expiration: datetime):
        """Populates 'regions' and 'expires_at' fields in the required format

        Args:
            aws_regions (list[AWSRegionZone]): A list of AWSRegionZone
            expiration (datetime): datetime for which the backup / snapshot expiration has to be set
            provide value as
            Example:
            ```
            from datetime import datetime
                                  Y     M   D  H   M   S
            expiration = datetime(2023, 12, 2, 13, 30, 45)
            ```
        """

        self.csp_regions = [region.value for region in aws_regions]
        self.expires_at = expiration.strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def from_domain_model(domain_model: PostImportSnapshotModel):
        return PostImportSnapshot(
            aws_regions=domain_model.aws_regions,
            expiration=domain_model.expiration,
            import_tags=domain_model.import_tags,
            import_volume_snapshots=domain_model.import_volume_snapshots,
            import_machine_instance_images=domain_model.import_machine_instance_images,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RestoreEBSAWSInfo:
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

    @staticmethod
    def from_domain_model(domain_model: RestoreEBSAWSInfoModel):
        return RestoreEBSAWSInfo(
            availability_zone=domain_model.availability_zone,
            csp_region=domain_model.csp_region,
            size_inGiB=domain_model.size_inGiB,
            volume_type=domain_model.volume_type,
            is_encrypted=domain_model.is_encrypted,
            csp_tags=domain_model.csp_tags,
            multiattach=domain_model.multiattach,
            iops=domain_model.iops,
            throughput_inMiBps=domain_model.throughput_inMiBps,
            encryption_keyARN=domain_model.encryption_keyARN,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RestoreAzureDiskInfo:
    csp_region: AZRegion
    resource_group_id: str
    size_inGiB: int
    sku_name: str
    csp_tags: list[CSPTag] = field(default_factory=list)
    disk_iops_read_write: Optional[int] = None
    disk_mbps_read_write: Optional[int] = None
    availability_zones: Optional[list[str]] = field(default_factory=list)

    @staticmethod
    def from_domain_model(domain_model: RestoreAzureDiskInfoModel):
        return RestoreAzureDiskInfo(
            csp_region=domain_model.csp_region,
            resource_group_id=domain_model.resource_group_id,
            size_inGiB=domain_model.size_inGiB,
            sku_name=domain_model.sku_name,
            csp_tags=domain_model.csp_tags,
            disk_iops_read_write=domain_model.disk_iops_read_write,
            disk_mbps_read_write=domain_model.disk_mbps_read_write,
            availability_zones=domain_model.availability_zones,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TargetVolumeInfo:
    account_id: UUID
    csp_info: Union[RestoreEBSAWSInfo, RestoreAzureDiskInfo]
    name: str = "Target volume name"

    @staticmethod
    def from_domain_model(domain_model: TargetVolumeInfoModel):
        if isinstance(domain_model.csp_info, RestoreEBSAWSInfoModel):
            csp_info = RestoreEBSAWSInfo.from_domain_model(domain_model=domain_model.csp_info)
        elif isinstance(domain_model.csp_info, RestoreAzureDiskInfoModel):
            csp_info = RestoreAzureDiskInfo.from_domain_model(domain_model=domain_model.csp_info)
        return TargetVolumeInfo(account_id=domain_model.account_id, csp_info=csp_info, name=domain_model.name)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreCspVolumeFromCspInstanceBackup:
    device_name: str
    target_volume_info: TargetVolumeInfo

    @staticmethod
    def from_domain_model(domain_model: PostRestoreCspVolumeFromCspInstanceBackupModel):
        target_volume_info = TargetVolumeInfo.from_domain_model(domain_model=domain_model.target_volume_info)
        return PostRestoreCspVolumeFromCspInstanceBackup(
            device_name=domain_model.device_name, target_volume_info=target_volume_info
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class InstanceAttachmentInfo:
    machine_instance_id: UUID
    attachment_type: str = "REPLACE"
    delete_original_volume: bool = False
    device: Optional[str] = field(default=None)

    @staticmethod
    def from_domain_model(domain_model: InstanceAttachmentInfoModel):
        return InstanceAttachmentInfo(
            machine_instance_id=domain_model.machine_instance_id,
            attachment_type=domain_model.attachment_type,
            delete_original_volume=domain_model.delete_original_volume,
            device=domain_model.device,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreCspVolume:
    target_volume_info: TargetVolumeInfo
    instance_attachment_info: list[InstanceAttachmentInfo] = field(default_factory=list)

    @staticmethod
    def from_domain_model(domain_model: PostRestoreCspVolumeModel):
        target_volume_info = TargetVolumeInfo.from_domain_model(domain_model=domain_model.target_volume_info)

        instance_attachment_info = []
        if domain_model.instance_attachment_info:
            for attachment_info in domain_model.instance_attachment_info:
                instance_attachment_info.append(InstanceAttachmentInfo.from_domain_model(attachment_info))

        return PostRestoreCspVolume(
            target_volume_info=target_volume_info, instance_attachment_info=instance_attachment_info
        )


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

    @staticmethod
    def from_domain_model(domain_model: RestoreEC2AWSInfoModel):
        block_device_mappings = None
        if domain_model.block_device_mappings:
            block_device_mappings = []
            for block_device in domain_model.block_device_mappings:
                block_device_mappings.append(VolumeAttachmentInfo.from_domain_model(block_device))
        return RestoreEC2AWSInfo(
            availability_zone=domain_model.availability_zone,
            csp_region=domain_model.csp_region,
            instance_type=domain_model.instance_type,
            key_pair_name=domain_model.key_pair_name,
            security_group_ids=domain_model.security_group_ids,
            disable_termination=domain_model.disable_termination,
            csp_tags=domain_model.csp_tags,
            iam_instance_profile=domain_model.iam_instance_profile,
            private_ip_address=domain_model.private_ip_address,
            subnet_csp_id=domain_model.subnet_csp_id,
            block_device_mappings=block_device_mappings,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class OriginalMachineInstanceInfo:
    terminate_original: bool = False

    @staticmethod
    def from_domain_model(domain_model: OriginalMachineInstanceInfoModel):
        return OriginalMachineInstanceInfo(terminate_original=domain_model.terminate_original)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TargetMachineInstanceInfo:
    account_id: UUID
    csp_info: RestoreEC2AWSInfo
    name: Optional[str] = ""

    @staticmethod
    def from_domain_model(domain_model: TargetMachineInstanceInfoModel):
        csp_info = RestoreEC2AWSInfo.from_domain_model(domain_model=domain_model.csp_info)
        return TargetMachineInstanceInfo(account_id=domain_model.account_id, csp_info=csp_info, name=domain_model.name)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreCspMachineInstance:
    target_machine_instance_info: TargetMachineInstanceInfo
    original_machine_instance_info: OriginalMachineInstanceInfo
    operation_type: str = Ec2RestoreOperation.CREATE.value

    @staticmethod
    def from_domain_model(domain_model: PostRestoreCspMachineInstanceModel):
        target_machine_instance_info = TargetMachineInstanceInfo.from_domain_model(
            domain_model=domain_model.target_machine_instance_info
        )
        original_machine_instance_info = OriginalMachineInstanceInfo.from_domain_model(
            domain_model=domain_model.original_machine_instance_info
        )
        return PostRestoreCspMachineInstance(
            target_machine_instance_info=target_machine_instance_info,
            original_machine_instance_info=original_machine_instance_info,
            operation_type=domain_model.operation_type,
        )
