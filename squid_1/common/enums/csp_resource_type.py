from enum import Enum


class CSPResourceType(Enum):
    # CSP resource types (names modeled after inventory manager const names)
    ACCOUNT_RESOURCE_TYPE = "csp-account"
    INSTANCE_RESOURCE_TYPE = "csp-machine-instance"
    PROTECTION_GROUP_RESOURCE_TYPE = "csp-protection-group"
    VOLUME_RESOURCE_TYPE = "csp-volume"
    MS365_PROTECTION_GROUP = "ms365-protection-group"
