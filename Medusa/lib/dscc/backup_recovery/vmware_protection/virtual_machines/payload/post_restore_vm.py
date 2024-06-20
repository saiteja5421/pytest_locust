from dataclasses import InitVar, dataclass, field
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VmInfo:
    name: str
    host_id: str
    power_on: bool
    datastore_id: InitVar[str]
    app_info: dict = field(default_factory=dict)

    def __post_init__(self, datastore_id):
        self.app_info.update({"vmware": {"datastoreId": datastore_id}})


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreNewVMbackup:
    backup_id: str
    restore_type: str
    targetVmInfo: VmInfo = field(default_factory=VmInfo("name", "host_id", "power_on", "datastore_id"))


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreNewVMsnapshot:
    snapshot_id: str
    restore_type: str
    targetVmInfo: VmInfo = field(default_factory=VmInfo("name", "host_id", "power_on", "datastore_id"))


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreExistingVMbackup:
    backup_id: str
    restore_type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreExistingVMsnapshot:
    snapshot_id: str
    restore_type: str
