from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase, config
from lib.dscc.secret_manager.common.models.common_secret_objects import Subclassifier

from lib.dscc.secret_manager.models.domain_model.secret_payload_model import (
    AddAzureSecretModel,
    ObjectAzureSPClientModel,
    ObjectAzureSubclassifierModel,
    PatchSecretModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectAzureSPClient:
    client_id: str
    client_secret: str
    tenant_id: str

    def from_domain_model(domain_model: ObjectAzureSPClientModel):
        return ObjectAzureSPClient(
            client_id=domain_model.client_id,
            client_secret=domain_model.client_secret,
            tenant_id=domain_model.tenant_id,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectAzureSubclassifier:
    azure_sp_client: ObjectAzureSPClient = field(metadata=config(field_name="azureSPClient"))

    def from_domain_model(domain_model: ObjectAzureSubclassifierModel):
        return ObjectAzureSubclassifier(azure_sp_client=domain_model.azure_sp_client)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AddAzureSecret:
    name: str
    service: str
    secret: ObjectAzureSubclassifier

    def from_domain_model(domain_model: AddAzureSecretModel):
        return AddAzureSecret(name=domain_model.name, service=domain_model.service, secret=domain_model.secret)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PatchSecret:
    description: str
    secret: Subclassifier
    groups: list[str]

    def from_domain_model(domain_model: PatchSecretModel):
        return PatchSecret(description=domain_model.description, secret=domain_model.secret, groups=domain_model.groups)
