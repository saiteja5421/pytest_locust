from json import dumps, loads
from copy import deepcopy


class PostProtectionPolicy:
    payload = {
        "applicationType": "VMWARE",
        "name": "Temp_policy",
        "protections": [],
    }

    snapshot_payload = {
        "type": "SNAPSHOT",
        "schedules": [
            {
                "scheduleId": 1,
                "name": "Array_Snapshot_1",
                "namePattern": {"format": "Array_Snapshot_{DateFormat}"},
                "expireAfter": {"unit": "DAYS", "value": 1},
                "schedule": {
                    "recurrence": "HOURLY",
                    "repeatInterval": {"every": 4},
                    "activeTime": {"activeFromTime": "00:00", "activeUntilTime": "23:59"},
                },
            }
        ],
    }

    on_premises_payload = {
        "type": "BACKUP",
        "protectionStoreId": "5cd951c6-4c00-4f42-b5b6-1ffec1ba7c31",
        "schedules": [
            {
                "scheduleId": 2,
                "name": "On-Premises_Protection_Store_2",
                "sourceProtectionScheduleId": 1,
                "namePattern": {"format": "On-Premises_Protection_Store_{DateFormat}"},
                "expireAfter": {"unit": "MONTHS", "value": 3},
                "schedule": {"recurrence": "DAILY", "repeatInterval": {"every": 1, "on": [1]}, "startTime": "00:00"},
            }
        ],
    }

    cloud_payload = {
        "type": "CLOUD_BACKUP",
        "protectionStoreId": "c9c394c7-245b-4cea-af5a-cdd8e64fa888",
        "schedules": [
            {
                "scheduleId": 3,
                "name": "HPE_Cloud_Protection_Store_3",
                "sourceProtectionScheduleId": 2,
                "namePattern": {"format": "HPE_Cloud_Protection_Store_{DateFormat}"},
                "expireAfter": {"unit": "YEARS", "value": 1},
                "schedule": {"recurrence": "WEEKLY", "repeatInterval": {"every": 1, "on": [1]}, "startTime": "00:00"},
            }
        ],
    }

    def __init__(
        self,
        name,
        expire_after_unit,
        onprem_expire_value: int,
        cloud_expire_value: int,
        recurrence,
        repeat_every: int,
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    ):
        self.no_of_onprem_stores = len(onprem_protection_store_id_list)
        self.no_of_cloud_stores = len(cloud_protection_store_id_list)

        self.name = name
        self.onprem_protection_store_id_list = onprem_protection_store_id_list
        self.cloud_protection_store_id_list = cloud_protection_store_id_list
        self.expire_after_unit = expire_after_unit
        self.onprem_expire_value = int(onprem_expire_value)
        self.cloud_expire_value = int(cloud_expire_value)
        self.recurrence = recurrence
        self.repeat_every = int(repeat_every)
        self.onprem_protections = self.on_premises_payload
        self.onprem_schedules = self.onprem_protections["schedules"][0]
        self.onprem_schedule = self.onprem_schedules["schedule"]
        self.onprem_schedules["expireAfter"]["unit"] = self.expire_after_unit
        self.onprem_schedules["expireAfter"]["value"] = self.onprem_expire_value
        self.onprem_schedule["recurrence"] = self.recurrence
        self.onprem_schedule["repeatInterval"]["every"] = self.repeat_every
        self.cloud_protections = self.cloud_payload
        self.cloud_schedules = self.cloud_protections["schedules"][0]
        self.cloud_schedule = self.cloud_schedules["schedule"]
        self.cloud_schedules["expireAfter"]["unit"] = self.expire_after_unit
        self.cloud_schedules["expireAfter"]["value"] = self.cloud_expire_value
        self.cloud_schedule["recurrence"] = self.recurrence
        self.cloud_schedule["repeatInterval"]["every"] = self.repeat_every
        self.payload["protections"] = []

    def create(self):
        self.payload["name"] = self.name
        self.payload["protections"].append(self.snapshot_payload)

        if self.no_of_onprem_stores == 0:
            cloud_id_start = 2
            for cloud_id, cloud_store in enumerate(self.cloud_protection_store_id_list, start=cloud_id_start):
                cloud_protections = deepcopy(self.cloud_payload)
                cloud_protections["protectionStoreId"] = cloud_store
                cloud_schedules = cloud_protections["schedules"][0]
                cloud_schedules["scheduleId"] = cloud_id
                cloud_schedules["name"] = cloud_schedules["name"][:-1] + str(cloud_id)
                self.payload["protections"].append(cloud_protections)
                cloud_schedules["sourceProtectionScheduleId"] = 1

        elif (self.no_of_onprem_stores == 1) and (self.no_of_cloud_stores == 1):
            self.onprem_protections["protectionStoreId"] = self.onprem_protection_store_id_list[0]
            self.cloud_protections["protectionStoreId"] = self.cloud_protection_store_id_list[0]
            self.payload["protections"].append(self.on_premises_payload)
            self.payload["protections"].append(self.cloud_payload)

        else:
            cloud_id_start = self.no_of_onprem_stores + 2
            for op_id, op_store in enumerate(self.onprem_protection_store_id_list, start=2):
                onprem_protections = deepcopy(self.on_premises_payload)
                onprem_protections["protectionStoreId"] = op_store
                onprem_schedules = onprem_protections["schedules"][0]
                onprem_schedules["scheduleId"] = op_id
                onprem_schedules["name"] = onprem_schedules["name"][:-1] + str(op_id)
                self.payload["protections"].append(onprem_protections)

            for cloud_id, cloud_store in enumerate(self.cloud_protection_store_id_list, start=cloud_id_start):
                cloud_protections = deepcopy(self.cloud_payload)
                cloud_protections["protectionStoreId"] = cloud_store
                cloud_schedules = cloud_protections["schedules"][0]
                cloud_schedules["scheduleId"] = cloud_id
                cloud_schedules["name"] = cloud_schedules["name"][:-1] + str(cloud_id)
                self.payload["protections"].append(cloud_protections)
        return dumps(self.payload)

    def create_storeonce_payload(self):
        self.payload["name"] = self.name

        cloud_id_start = self.no_of_onprem_stores + 1
        for op_id, op_store in enumerate(self.onprem_protection_store_id_list, start=1):
            onprem_protections = deepcopy(self.on_premises_payload)
            onprem_protections["protectionStoreId"] = op_store
            onprem_schedules = onprem_protections["schedules"][0]
            onprem_schedules["scheduleId"] = op_id
            onprem_schedules["name"] = onprem_schedules["name"][:-1] + str(op_id)
            del onprem_schedules["sourceProtectionScheduleId"]
            self.payload["protections"].append(onprem_protections)

        for cloud_id, cloud_store in enumerate(self.cloud_protection_store_id_list, start=cloud_id_start):
            cloud_protections = deepcopy(self.cloud_payload)
            cloud_protections["protectionStoreId"] = cloud_store
            cloud_schedules = cloud_protections["schedules"][0]
            cloud_schedules["sourceProtectionScheduleId"] = 1
            cloud_schedules["scheduleId"] = cloud_id
            cloud_schedules["name"] = cloud_schedules["name"][:-1] + str(cloud_id)
            if self.no_of_onprem_stores == 0:
                del cloud_schedules["sourceProtectionScheduleId"]
            self.payload["protections"].append(cloud_protections)

        return dumps(self.payload)
