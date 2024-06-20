from json import dumps


class ProtectVM:
    payload = {
        "assetInfo": {"id": "uuid", "type": "hybrid-cloud/virtual-machine"},
        "protectionPolicyId": "uuid",
        "overrides": {
            "protections": [
                {
                    "id": "uuid",
                    "schedules": [
                        {
                            "scheduleId": 1,
                            "consistency": "CRASH_CONSISTENT_ON_FAILURE",
                            "backupGranularity": "BACKUP_GRANULARITY_TYPE",
                        }
                    ],
                },
                {
                    "id": "uuid",
                    "schedules": [
                        {
                            "scheduleId": 2,
                            "consistency": "CRASH_CONSISTENT_ON_FAILURE",
                            "backupGranularity": "BACKUP_GRANULARITY_TYPE",
                        }
                    ],
                },
                {
                    "id": "uuid",
                    "schedules": [
                        {
                            "scheduleId": 3,
                            "consistency": "CRASH_CONSISTENT_ON_FAILURE",
                            "backupGranularity": "BACKUP_GRANULARITY_TYPE",
                        }
                    ],
                },
            ]
        },
    }

    def __init__(
        self,
        asset_name,
        asset_type,
        asset_id,
        template_id,
        snapshot_id,
        local_backup_id,
        cloud_backup_id,
        backup_granularity_type,
    ):
        self.asset_name = asset_name
        self.asset_id = asset_id
        self.asset_type = asset_type
        self.template_id = template_id
        self.snapshot_id = snapshot_id
        self.local_backup_id = local_backup_id
        self.cloud_backup_id = cloud_backup_id
        self.asset_info = self.payload["assetInfo"]
        self.protections = self.payload["overrides"]["protections"]
        self.backup_granularity_type = backup_granularity_type

    def create(self):
        self.asset_info["id"] = self.asset_id
        self.asset_info["type"] = self.asset_type
        self.payload["protectionPolicyId"] = self.template_id
        self.protections[0]["id"] = self.snapshot_id
        self.protections[1]["id"] = self.local_backup_id
        self.protections[2]["id"] = self.cloud_backup_id
        for item in self.protections:
            item["schedules"][0]["backupGranularity"] = self.backup_granularity_type
        return dumps(self.payload)

    def create_storeonce(self):
        """
        this method is assign only  local and cloud schedules for vm
        """
        storeonce_payload = {
            "assetInfo": {
                "id": "uuid",
                "type": "hybrid-cloud/virtual-machine",
            },
            "protectionPolicyId": "uuid",
            "overrides": {
                "protections": [
                    {
                        "id": "uuid",
                        "schedules": [
                            {
                                "scheduleId": 1,
                                "consistency": "CRASH_CONSISTENT_ON_FAILURE",
                                "backupGranularity": "VMWARE_CBT",
                            }
                        ],
                    },
                    {
                        "id": "uuid",
                        "schedules": [
                            {
                                "scheduleId": 2,
                                "consistency": "CRASH_CONSISTENT_ON_FAILURE",
                                "backupGranularity": "VMWARE_CBT",
                            }
                        ],
                    },
                ]
            },
        }
        asset_info = storeonce_payload["assetInfo"]
        protections = storeonce_payload["overrides"]["protections"]
        asset_info["id"] = self.asset_id
        asset_info["type"] = self.asset_type
        storeonce_payload["protectionPolicyId"] = self.template_id
        protections[0]["id"] = self.local_backup_id
        protections[1]["id"] = self.cloud_backup_id
        for item in self.protections:
            item["schedules"][0]["backupGranularity"] = self.backup_granularity_type
        return dumps(storeonce_payload)
