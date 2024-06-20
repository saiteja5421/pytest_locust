from json import dumps, loads


class PostNewProtectionTemplate:
    payload = {
        "name": "TempCloud",
        "protections": [
            {
                "type": "SNAPSHOT",
                "applicationType": "VMWARE",
                "schedules": [
                    {
                        "id": 1,
                        "name": "Array_Snapshot_1",
                        "namePattern": {"format": "Array_Snapshot_{DateFormat}"},
                        "expireAfter": {"unit": "DAYS", "value": 1},
                        "schedule": {
                            "recurrence": "DAILY",
                            "repeatInterval": {"every": 1},
                        },
                    }
                ],
            },
            {
                "type": "BACKUP",
                "applicationType": "VMWARE",
                "schedules": [
                    {
                        "id": 2,
                        "name": "On-Premises_Protection_Store_2",
                        "namePattern": {"format": "On-Premises_Protection_Store_{DateFormat}"},
                        "expireAfter": {"unit": "WEEKS", "value": 1},
                        "schedule": {
                            "recurrence": "WEEKLY",
                            "repeatInterval": {"every": 1, "on": [5]},
                            "startTime": "00:00",
                        },
                        "sourceProtectionScheduleId": 1,
                    }
                ],
                "protectionStoreId": "ecce40e3-b3db-4ef9-b76c-5db2c264fca5",
            },
            {
                "type": "CLOUD_BACKUP",
                "applicationType": "VMWARE",
                "schedules": [
                    {
                        "id": 3,
                        "name": "HPE_Cloud_Protection_Store_3",
                        "namePattern": {"format": "HPE_Cloud_Protection_Store_{DateFormat}"},
                        "expireAfter": {"unit": "MONTHS", "value": 1},
                        "schedule": {
                            "recurrence": "MONTHLY",
                            "repeatInterval": {"every": 1, "on": [6]},
                        },
                        "sourceProtectionScheduleId": 2,
                    }
                ],
                "protectionStoreId": "a8061e02-3672-42e1-9a39-73c4ce2209c9",
            },
        ],
    }

    def __init__(
        self,
        name,
        expire_after_unit,
        expire_after_value: int,
        recurrence,
        repeat_every: int,
        onprem_protection_store_id,
        cloud_protection_store_id,
    ):
        self.name = name
        self.onprem_protection_store_id = onprem_protection_store_id
        self.cloud_protection_store_id = cloud_protection_store_id
        self.expire_after_unit = expire_after_unit
        self.expire_after_value = int(expire_after_value)
        self.recurrence = recurrence
        self.repeat_every = int(repeat_every)
        self.local_protections = self.payload["protections"][1]
        self.local_schedules = self.local_protections["schedules"][0]
        self.local_schedule = self.local_schedules["schedule"]
        self.cloud_protections = self.payload["protections"][2]
        self.cloud_schedules = self.cloud_protections["schedules"][0]
        self.cloud_schedule = self.cloud_schedules["schedule"]

        # clearing the payload of the multiple cloud protection template(previous payloads)
        protection_store_count = len(self.payload["protections"])
        for ps_count in range(0, protection_store_count):
            if ps_count >= 3:
                del self.payload["protections"][ps_count]

    def create(self):
        self.payload["name"] = self.name
        self.local_schedules["expireAfter"]["unit"] = self.expire_after_unit
        self.local_schedules["expireAfter"]["value"] = self.expire_after_value
        self.local_schedule["recurrence"] = self.recurrence
        self.local_schedule["repeatInterval"]["every"] = self.repeat_every
        self.local_protections["protectionStoreId"] = self.onprem_protection_store_id
        self.cloud_protections["protectionStoreId"] = self.cloud_protection_store_id
        return dumps(self.payload)

    def create_storeonce_payload(self):
        """This method generates/returns a JSON, can be used in creating protection policy only local and cloud schedules for storeonce.
        Returns:
            _type_: JSON
        """
        storeonce_payload = {
            "name": "for_payload",
            "protections": [
                {
                    "type": "BACKUP",
                    "protectionStoreId": "824b6ea3-d86d-4407-9b9e-31d5b45a6a3f",
                    "schedules": [
                        {
                            "id": 1,
                            "name": "On-Premises_Protection_Store_1",
                            "namePattern": {"format": "On-Premises_Protection_Store_{DateFormat}"},
                            "expireAfter": {"unit": "WEEKS", "value": 1},
                            "schedule": {
                                "recurrence": "WEEKLY",
                                "repeatInterval": {"every": 1, "on": [2]},
                            },
                        }
                    ],
                    "applicationType": "VMWARE",
                },
                {
                    "type": "CLOUD_BACKUP",
                    "protectionStoreId": "6c6f940b-3c5f-444e-90f4-205ee6aa687b",
                    "schedules": [
                        {
                            "id": 2,
                            "name": "HPE_Cloud_Protection_Store_2",
                            "sourceProtectionScheduleId": 1,
                            "namePattern": {"format": "HPE_Cloud_Protection_Store_{DateFormat}"},
                            "expireAfter": {"unit": "MONTHS", "value": 1},
                            "schedule": {
                                "recurrence": "MONTHLY",
                                "repeatInterval": {"every": 1, "on": [6]},
                            },
                        }
                    ],
                    "applicationType": "VMWARE",
                },
            ],
        }

        storeonce_payload["name"] = self.name
        local_protections = storeonce_payload["protections"][0]
        local_schedules = local_protections["schedules"][0]
        local_schedule = local_schedules["schedule"]
        cloud_protections = storeonce_payload["protections"][1]
        cloud_schedules = cloud_protections["schedules"][0]
        cloud_schedule = cloud_schedules["schedule"]
        local_schedules["expireAfter"]["unit"] = self.expire_after_unit
        local_schedules["expireAfter"]["value"] = self.expire_after_value
        local_schedule["recurrence"] = self.recurrence
        local_schedule["repeatInterval"]["every"] = self.repeat_every
        local_protections["protectionStoreId"] = self.onprem_protection_store_id
        cloud_protections["protectionStoreId"] = self.cloud_protection_store_id
        return dumps(storeonce_payload)

    # This method Tested successfully but not using currently, keeping it only for future purpose
    def create_cloud_protections_with_multiple_schedules_same_region(self):
        """This method generates/returns a JSON, can be used in creating protection policy with multiple cloud schedules.
        Returns:
            _type_: JSON
        """
        second_cloud_dict = {
            "id": 4,
            "name": "HPE_Cloud_Protection_Store_4",
            "namePattern": {"format": "HPE_Cloud_Protection_Store_{DateFormat}"},
            "expireAfter": {"unit": "YEARS", "value": 1},
            "schedule": {
                "recurrence": "MONTHLY",
                "repeatInterval": {"every": 1, "on": [6]},
            },
            "sourceProtectionScheduleId": 2,
        }
        self.payload["name"] = self.name
        self.cloud_protections["schedules"].append(second_cloud_dict)
        self.local_schedules["expireAfter"]["unit"] = self.expire_after_unit
        self.local_schedules["expireAfter"]["value"] = self.expire_after_value
        self.local_schedule["recurrence"] = self.recurrence
        self.local_schedule["repeatInterval"]["every"] = self.repeat_every
        self.local_protections["protectionStoreId"] = self.onprem_protection_store_id
        self.cloud_protections["protectionStoreId"] = self.cloud_protection_store_id
        return dumps(self.payload)

    def create_cloud_protections_with_multiple_cloud_regions(self, cloud_protection_store_id_list):
        """This method generates/returns a JSON, can be used in creating protection policy with multiple cloud region schedules.
        Args:
            cloud_protection_store_id_list: list type: provide multiple cloud uuids to create multiple regions.
        Returns:
            _type_: JSON
        """
        cloud_backup_dict = {
            "type": "CLOUD_BACKUP",
            "applicationType": "VMWARE",
            "schedules": [
                {
                    "id": 4,
                    "name": "HPE_Cloud_Protection_Store_4",
                    "namePattern": {"format": "HPE_Cloud_Protection_Store_{DateFormat}"},
                    "expireAfter": {"unit": "YEARS", "value": 1},
                    "schedule": {
                        "recurrence": "MONTHLY",
                        "repeatInterval": {"every": 1, "on": [6]},
                    },
                    "sourceProtectionScheduleId": 2,
                }
            ],
            "protectionStoreId": "a8061e02-3672-42e1-9a39-73c4ce2209c9",
        }
        self.payload["name"] = self.name
        self.payload["protections"].append(cloud_backup_dict)
        self.cloud_protections2 = self.payload["protections"][3]
        self.local_schedules["expireAfter"]["unit"] = self.expire_after_unit
        self.local_schedules["expireAfter"]["value"] = self.expire_after_value
        self.local_schedule["recurrence"] = self.recurrence
        self.local_schedule["repeatInterval"]["every"] = self.repeat_every
        self.local_protections["protectionStoreId"] = self.onprem_protection_store_id
        self.cloud_protections["protectionStoreId"] = cloud_protection_store_id_list[0]
        self.cloud_protections2["protectionStoreId"] = cloud_protection_store_id_list[1]
        return dumps(self.payload)

    def create_cloud_protections_with_multiple_cloud_regions_for_storeonce(self, cloud_protection_store_id_list):
        """This method generates/returns a JSON, can be used in creating protection policy with multiple cloud region schedules.
        Args:
            cloud_protection_store_id_list: list type: provide multiple cloud uuids to create multiple regions.
        Returns:
            _type_: JSON
        """
        cloud_backup_dict = {
            "type": "CLOUD_BACKUP",
            "protectionStoreId": "d05e01cc-7059-4019-87e3-1331f84157b4",
            "schedules": [
                {
                    "id": 3,
                    "name": "HPE_Cloud_Protection_Store_3",
                    "sourceProtectionScheduleId": 1,
                    "namePattern": {"format": "HPE_Cloud_Protection_Store_{DateFormat}"},
                    "expireAfter": {"unit": "YEARS", "value": 1},
                    "schedule": {
                        "recurrence": "MONTHLY",
                        "repeatInterval": {"every": 1, "on": [6]},
                    },
                }
            ],
            "applicationType": "VMWARE",
        }
        one_region_payload = self.create_storeonce_payload()
        cloud_with_one_region_payload = loads(one_region_payload)
        cloud_with_one_region_payload["protections"].append(cloud_backup_dict)
        cloud_with_one_region_payload["name"] = self.name
        local_protections = cloud_with_one_region_payload["protections"][0]
        local_schedules = local_protections["schedules"][0]
        local_schedule = local_schedules["schedule"]
        cloud_protections = cloud_with_one_region_payload["protections"][1]
        cloud_protections2 = cloud_with_one_region_payload["protections"][2]
        local_schedules["expireAfter"]["unit"] = self.expire_after_unit
        local_schedules["expireAfter"]["value"] = self.expire_after_value
        local_schedule["recurrence"] = self.recurrence
        local_schedule["repeatInterval"]["every"] = self.repeat_every
        local_protections["protectionStoreId"] = self.onprem_protection_store_id
        cloud_protections["protectionStoreId"] = cloud_protection_store_id_list[0]
        cloud_protections2["protectionStoreId"] = cloud_protection_store_id_list[1]
        return dumps(cloud_with_one_region_payload)
