from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase, config
from lib.dscc.secret_manager.common.models.common_secret_objects import Subclassifier


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectAzureSPClientModel:
    client_id: str
    client_secret: str
    tenant_id: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectAzureSubclassifierModel:
    azure_sp_client: ObjectAzureSPClientModel = field(metadata=config(field_name="azureSPClient"))


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AddAzureSecretModel:
    name: str
    service: str
    secret: ObjectAzureSubclassifierModel


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PatchSecretModel:
    description: str
    secret: Subclassifier
    groups: list[str]
