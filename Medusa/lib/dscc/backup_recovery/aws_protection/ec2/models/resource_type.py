from enum import Enum


class ResourceType(Enum):
    CSP_MACHINE_INSTANCE = "hybrid-cloud/csp-machine-instance"
    CSP_PROTECTION_GROUP = "backup-recovery/csp-protection-group"
    CSP_TAG = "hybrid-cloud/csp-tag"
    CSP_TAG_KEY = "hybrid-cloud/csp-tag-key"
    CSP_VOLUME = "hybrid-cloud/csp-volume"
