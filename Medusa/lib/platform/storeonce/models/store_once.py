from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.SNAKE)
@dataclass
class StoreOnceCredentials:
    username: str
    password: str
    grant_type: str = "password"


@dataclass_json(letter_case=LetterCase.SNAKE)
@dataclass
class StoreOnceAuthentication:
    expires_in: str
    refresh_token: str
    access_token: str
    sessionID: str
    userName: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class StatusSummary:
    num_ok: int
    num_warning: int
    num_critical: int
    num_unknown: int
    total: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Summary:
    status_summary: StatusSummary


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class StoreOnceInformation:
    software_version: str
    hostname: str
    product_sku: str
    product_name: str
    serial_number: str
    warranty_serial_number: str
    system_uuid: str
    management_address: str
    system_location: str
    contact_name: str
    contact_number: str
    contact_email: str
    ope_token: str
    cat_gateway_id: str
    platform_customer_id: str
    application_customer_id: str
    operational_mode: str


class CollectionMode(Enum):
    AUTOMATIC = "Automatic"
    COMPREHENSIVE = "Comprehensive"
    MANUAL = "Manual"


class CatalogName(Enum):
    LOGCOLLECTION_BUSINESS_EXCEPTIONS = "logcollection-business-exceptions"


class MessageKey(Enum):
    COLLECTION_MODE_AUTOMATIC = "collection.mode.automatic"
    COLLECTION_MODE_MANUAL = "collection.mode.manual"
    COLLECTION_TYPE_COMPREHENSIVE = "collection.type.comprehensive"


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CollectionEInfo:
    catalog_name: CatalogName
    message_key: MessageKey
    message_for_current_locale: CollectionMode


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class StoreOnceLogCollection:
    name: str
    collection_type: str
    collection_mode: CollectionMode
    force_transfer: bool
    start_time: str
    collection_path: str
    download_uri: str
    status: str
    duration_seconds: int
    size_bytes: int
    size_bytes_long: int
    description: str
    cluster_name: str
    collection_type_info: CollectionEInfo
    collection_mode_info: CollectionEInfo
    identifier: str = ""
    completed_nodes: List[str] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class HealthState:
    state: str
    associated_message: dict
    corrective_action: dict


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class NTPInfo:
    enabled: bool
    health_state: HealthState
    ntp_server_name: list[str]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AwsDetails:
    customerAccountID: str = "618991318870"
    # externalID allows to assume role 'arn:aws:iam::618991318870:role/hpe-cam-data-extractor' from our AWS account.
    # Role can be assumed just by providing the 'externalID', which makes our tests work on all environments.
    externalID: str = "4b793b9610b611ecbda96250d9ed3dec"
    region: str = "eu-west-1"
    proxy_host: None = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EbsDetails:
    snapshot_sizein_gi_b: int = 1
    parent_snapshot: None = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VolumeCopy:
    target_identifier: str
    client_password: str
    client_user: str = "store"
    ebs_details: EbsDetails = field(default=EbsDetails())
    aws_details: AwsDetails = field(default=AwsDetails())
    checkpoint_data: None = None
    verify: bool = False
    source_identifier: str = "snap-097d5b6f08b4ed14c"
    resume: bool = False
    num_streams: int = 2
    num_objects: int = 2
    dedupe_block_size_bytes: int = 4096
    source_type: str = "EBS"
    parent_object_uuid: None = None
    target_type: str = "CATALYST"
    server_address: str = "127.0.0.1"
    backup_type: str = "OPTIMIZED"


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SSLCertificateDetails:
    subject_common_name: str
    subject_organisation: str
    subject_organisational_unit: str
    serial_number: str
    issuer_common_name: str
    issuer_organisation: str
    issuer_organisational_unit: str
    certificate_start_date: str
    certificate_end_date: str
    sha1_fingerprint: str
    sha256_fingerprint: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CloudStoreDetails:
    percentage_recovery_complete: int
    estimated_time_to_connect_seconds: int
    local_disk_bytes: int
    cloud_disk_bytes: int
    cloud_store_id: str
    csp_vendor: int
    csp_vendor_string: str
    csp_protocol: int
    csp_protocol_string: str
    csp_container: str
    csp_authentication_id: str
    csp_authentication_version: int
    csp_authentication_version_string: int
    csp_address: str
    csp_port: int
    csp_addressing_style: int
    csp_addressing_style_string: str
    ssl_certificate_details: SSLCertificateDetails
    archive_status: int
    archive_status_string: str
    last_archive_failed_reason: int
    last_archive_failed_reason_string: str
    attach_read_only_enabled: bool
    proxy_connection_enabled: bool
    secure_connection_enabled: bool
    connection_stage: int
    connection_stage_string: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CloudStore:
    id: int
    name: str
    description: str
    created_date: str
    version: int
    variable_block_dedupe_supported: bool
    fixed_block_dedupe_supported: bool
    no_dedupe_supported: bool
    sparse_write_supported: bool
    write_in_place_supported: bool
    raw_read_write_supported: bool
    multiple_object_openers_supported: bool
    multiple_object_writes_supported: bool
    clone_extent_supported: bool
    primary_transfer_policy: int
    primary_transfer_policy_string: str
    secondary_transfer_policy: int
    secondary_transfer_policy_string: str
    size_on_disk_quota_enabled: bool
    size_on_disk_quota_bytes: int
    user_data_stored_quota_enabled: bool
    user_data_stored_quota_bytes: int
    data_job_retention_days: int
    copy_job_retention_days: int
    user_bytes: int
    disk_bytes: int
    dedupe_ratio: float
    num_items: int
    num_data_jobs: int
    num_inbound_copy_jobs: int
    num_outbound_copy_jobs: int
    health_level: int
    health_level_string: str
    store_status: int
    store_status_string: str
    encryption_enabled: bool
    secure_erase_mode_string: str
    secure_erase_mode: int
    modified_date: str
    dedupe_store_id: int
    security_mode: int
    security_mode_string: str
    data_immutability_grace_enabled: bool
    data_immutability_grace_seconds: int
    data_immutability_retention_seconds: int
    data_immutability_retention_enabled: bool
    aligned4_k_boverride_enabled: bool
    ssl_certificate: str
    cloud_store_enabled: bool
    cloud_store_details: CloudStoreDetails
    data_immutability_max_isv_retention_seconds: int = 0


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CheckpointDatum:
    object_fragment_number: int
    bytes_processed: int
    num_blocks_read_or_written: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EbsAPIStatistics:
    num_list_blocks_calls: int
    num_list_changed_blocks_calls: int
    num_get_or_put_snapshot_block_calls: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProgressInformation:
    timestamp: str
    job_progress: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VolumeCopyJob:
    uuid: UUID
    job_state: str
    job_state_string: str
    job_type: str
    job_type_string: str
    created_date: str
    updated_date: str
    completed_date: str
    task_uuid: str
    marked_for_cancellation: bool
    device_id: str
    checkpoint_data: List[CheckpointDatum]
    progress_information: List[ProgressInformation]
    ebs_api_statistics: EbsAPIStatistics = None
    statistics: Optional[Dict[str, int]] = field(default_factory=lambda: {})


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CloudStorePermission:
    allowAccess: bool = True


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CloudStorePermissions:
    id: int
    name: str
    description: str
    allow_access: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class UserEntryDetails:
    userName: str = ""
    password: str = ""
    roles: list = 1


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CloudStoreProxy:
    enabled: bool = True
    address: str = ""
    port: int = 0
    username: str = ""
    password: str = ""


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Members:
    local_user_bytes: int
    local_free_bytes: int
    local_capacity_bytes: int
    cloud_disk_bytes: int
    cloud_user_bytes: int
    cloud_free_bytes: int
    cloud_capacity_bytes: int
    appliance_status: str
    data_services_status: str
    license_status: str
    remote_support_status: str
    software_update_recommended: bool


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ResourceInfo:
    count: int
    total: int
    un_filtered_total: int
    start: int
    category: str
    members: list[Members]
