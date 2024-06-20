from dataclasses import InitVar, dataclass, field
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Network:
    name: str
    network_address: str
    subnet_mask: str
    gateway: str
    network_type: str = "STATIC"
    dns: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.dns.append({"networkAddress": "10.157.24.201"})


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Override:
    cpu: int
    ram_in_giB: int
    storage_in_tiB: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VmConfig:
    host_id: str
    cluster_id: str
    content_library_id: str
    folder_id: str
    resource_pool_id: str
    max_in_cloud_daily_protected_data_in_tiB: float
    max_in_cloud_retention_days: int
    max_on_prem_daily_protected_data_in_tiB: float
    max_on_prem_retention_days: int
    network: Network = Network("name", "network_address", "subnet_mask", "gatway", "network_type")
    override: Override = Override("cpu", "ram_in_giB", "storage_in_tiB")
    datastore_ids: list[str] = field(default_factory=list)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostCreateCatalystGateway:
    name: str
    hypervisor_manager_id: str
    vm_config: VmConfig = VmConfig(
        "datastore_id",
        "host_id",
        "cluster_id",
        "content_library_id",
        "folder_id",
        "resource_pool_id",
        "max_in_cloud_daily_protected_data_in_tiB",
        "max_in_cloud_retention_days",
        "max_on_prem_daily_protected_data_in_tiB",
        "max_on_prem_retention_days",
        "network",
        "override",
    )
