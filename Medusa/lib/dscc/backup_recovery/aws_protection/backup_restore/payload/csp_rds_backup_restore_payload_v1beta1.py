from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_rds_backup_restore_payload_model import (
    PostRestoreCspRdsInstanceModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreCspRdsInstance:
    database_identifier: str  # Name of the restored RDS instance identifier

    def from_domain_model(domain_model: PostRestoreCspRdsInstanceModel):
        return PostRestoreCspRdsInstance(database_identifier=domain_model.database_identifier)
