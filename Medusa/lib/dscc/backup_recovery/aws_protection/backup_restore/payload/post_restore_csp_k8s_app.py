from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreK8sApp:
    backup_id: str
    cluster_id: str
    force_restore: bool  # Set to true, will replace the existing namespace
    target_namespace: str
