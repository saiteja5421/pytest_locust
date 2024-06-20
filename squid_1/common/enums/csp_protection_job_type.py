from enum import Enum


class CSPProtectionJobType(Enum):
    # Used by function tests for Kafka
    CSP_MACHINE_INSTANCE_PROT_JOB = "CSPMachineInstance"
    CSP_VOLUME_PROT_JOB = "CSPVolume"
    CSP_PROTECTION_GROUP_PROT_JOB = "CSPProtectionGroup"
