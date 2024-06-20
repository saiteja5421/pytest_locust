from enum import Enum

# From: https://pages.github.hpe.com/cloud/storage-api/#get-/protection-jobs/{id}
# Ok, Error, Warning, InProgress, Skipped


class ExecutionStatus(Enum):
    OK = "OK"
    ERROR = "Error"
    WARNING = "Warning"
    IN_PROGRESS = "InProgress"
    SKIPPED = "Skipped"
