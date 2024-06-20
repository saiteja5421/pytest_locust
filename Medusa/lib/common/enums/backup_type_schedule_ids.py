from enum import Enum


class BackupTypeScheduleIDs(Enum):
    snapshot = [1]
    local = [2]
    cloud = [3, 1]
    all = [3, 2, 1]
    schedule_id_4 = [4, 3, 2, 1]
    schedule_id_5 = [5, 4, 3, 2, 1]
    # used for storeonce assign local and cloud
    storeonce = [2, 1]
