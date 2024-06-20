from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json
@dataclass
class VCenterCredentials:
    username: str
    password: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostCreateVcenter:
    allow_credential_reuse = False
    name: str = "vcenter123.hpe.com"
    network_address: str = "192.168.0.1"
    credentials: VCenterCredentials = field(default_factory=VCenterCredentials("username", "password"))
    data_orchestrator_id: str = ""
    hypervisor_manager_type: str = "VMWARE_VCENTER"
    description: str = "Created by api automation script"
