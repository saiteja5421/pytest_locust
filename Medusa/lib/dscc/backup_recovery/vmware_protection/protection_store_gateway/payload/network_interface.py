from dataclasses import dataclass
from typing import Optional

from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CreateNetworkInterfaceDetails:
    network_address: str
    network_name: str
    network_type: str
    subnet_mask: str
    gateway: str = ""


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class UpdateNetworkInterfaceDetails:
    id: str
    network_address: str
    network_name: str
    network_type: str
    subnet_mask: str
    gateway: str = ""
    force: Optional[bool] = True


@dataclass_json
@dataclass
class DeleteNetworkInterfaceDetails:
    id: str


@dataclass_json
@dataclass
class CreateNetworkInterface:
    nic: CreateNetworkInterfaceDetails


@dataclass_json
@dataclass
class UpdateNetworkInterface:
    nic: UpdateNetworkInterfaceDetails


@dataclass_json
@dataclass
class DeleteNetworkInterface:
    nic: DeleteNetworkInterfaceDetails
