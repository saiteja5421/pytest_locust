from enum import Enum

import lib.platform.kafka.protobuf.dataprotection.backup_updates_pb2 as backup


class KafkaBackupType(Enum):
    # Used for Backup Kafka Event
    BACKUP_TYPE_BACKUP = backup.BackupType.DESCRIPTOR.values_by_number[backup.BACKUP_TYPE_BACKUP].name
    BACKUP_TYPE_TRANSIENT_BACKUP = backup.BackupType.DESCRIPTOR.values_by_number[
        backup.BACKUP_TYPE_TRANSIENT_BACKUP
    ].name
    BACKUP_TYPE_CLOUDBACKUP = backup.BackupType.DESCRIPTOR.values_by_number[backup.BACKUP_TYPE_CLOUDBACKUP].name
