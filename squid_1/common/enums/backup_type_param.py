from enum import Enum


class BackupTypeParam(Enum):
    # used as URL parameter:
    # hypervisor_manager.get_backups(), hypervisor_manager.delete_backups()
    backups = "backups"
    snapshots = "snapshots"
