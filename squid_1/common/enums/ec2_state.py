from enum import Enum


class Ec2State(Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    PENDING = "pending"
    RUNNING = "running"
    SHUTTINGDOWN = "shuttingDown"
    STOPPED = "stopped"
    STOPPING = "stopping"
    TERMINATED = "terminated"
