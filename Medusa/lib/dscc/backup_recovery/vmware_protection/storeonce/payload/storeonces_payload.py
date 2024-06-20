from dataclasses import dataclass
from dataclasses_json import CatchAll, Undefined, dataclass_json, LetterCase


@dataclass
class Credentials:
    username: str
    password: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RegisterStoreOncePayload:
    networkAddress: str
    serialNumber: str
    name: str
    credentials: Credentials
    description: str = ""


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PatchStoreOncePayload:
    networkAddress: str
    description: str = ""
