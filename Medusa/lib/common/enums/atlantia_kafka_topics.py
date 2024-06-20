from enum import Enum


class AtlantiaKafkaTopics(Enum):
    CSP_INVENTORY_UPDATES = "csp.inventory.updates"
    CSP_INVENTORY_ACTIONS = "csp.inventory.actions"
    CSP_CAM_UPDATES = "csp.cam.updates"
    CSP_CAM_COMMANDS = "csp.cam.commands"
    ATLAS_POLICY_COMMANDS = "atlas.policy.commands"
    SCHEDULER_ATLAS_POLICY_RESPONSE = "atlas.policy.internal"
    CSP_SCHEDULER_UPDATES = "csp.scheduler.updates"
    ATLAS_REPORT_EVENTS = "atlas.reports.events"
    AUDIT_EVENTS = "audit.events"
    CSP_DATAPROTECTION_BACKUP_UPDATES = "csp.dataprotection.backups.updates"
    CSP_DATAPROTECTION_BACKUP_ACTIONS = "csp.dataprotection.backups.actions"
