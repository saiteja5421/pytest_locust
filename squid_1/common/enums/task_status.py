from enum import Enum


class TaskStatus(Enum):
    success = "SUCCEEDED"
    unspecified = "UNSPECIFIED"
    initialized = "INITIALIZED"
    running = "RUNNING"
    failed = "FAILED"
    timedout = "TIMEDOUT"
    paused = "PAUSED"
