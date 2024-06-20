import json
from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from uuid import UUID
from typing import Union

from lib.common.enums.secret_subclassifier_properties import SubclassifierProperties


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectNameUriId:
    id: UUID
    name: str
    uri: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectCreateUpdateBy:
    CREATED_BY: str
    LAST_UPDATED_BY: str
    # DESCRIPTION: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Domain:
    name: str
    properties: ObjectCreateUpdateBy = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectSSHKeyPair:
    PUBLIC_KEY: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectBasicAuth:
    USERNAME: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectBearerAuth:
    TOKEN: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectOAuthClient:
    CLIENT_ID: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectAzureSPClient:
    CLIENT_ID: str
    TENANT_ID: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Subclassifier:
    name: SubclassifierProperties
    properties: Union[ObjectBasicAuth, ObjectAzureSPClient, ObjectSSHKeyPair]

    def __init__(self, **kwargs):
        self.name: SubclassifierProperties = kwargs["name"]
        for key, value in kwargs.items():
            if key == "properties" and self.name.value == SubclassifierProperties.AZURE_SPCLIENT.value:
                self.properties = ObjectAzureSPClient.from_json(json.dumps(value))
            elif key == "properties" and self.name.value == SubclassifierProperties.BASIC_AUTH.value:
                self.properties = ObjectBasicAuth.from_json(json.dumps(value))
            elif key == "properties" and self.name.value == SubclassifierProperties.SSH_KEYPAIR.value:
                self.properties = ObjectSSHKeyPair.from_json(json.dumps(value))
            else:
                super().__setattr__(key, value)
