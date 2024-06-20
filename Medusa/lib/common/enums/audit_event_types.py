from enum import Enum


class AuditEvent(Enum):
    PERMISSION_CSP_VOLUME_UPDATE = "data-services.csp-volume.update"
    PERMISSION_CSP_MACHINE_INSTANCE_UPDATE = "data-services.csp-machine-instance.update"
    VOLUME_UPDATE_TAGS_EVENT_CODE = "VOLUME_UPDATE_TAGS"
    INSTANCE_UPDATE_TAGS_EVENT_CODE = "MACHINE_INSTANCE_UPDATE_TAGS"
