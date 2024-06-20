from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.SNAKE)
@dataclass
class BasicParameters:
    comp_ratio: str
    validate: str
    dedup_ratio: str
    dedup_unit: str


@dataclass_json(letter_case=LetterCase.SNAKE)
@dataclass
class StorageDefinitions:
    storage_definition: str


@dataclass_json(letter_case=LetterCase.SNAKE)
@dataclass
class WorkloadDefinitions:
    workload_definition: str


@dataclass_json(letter_case=LetterCase.SNAKE)
@dataclass
class RunDefinitions:
    run_definition: str
