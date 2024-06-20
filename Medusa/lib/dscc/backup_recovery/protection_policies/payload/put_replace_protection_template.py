class PutReplaceProtectionTemplate:

    payload = {
        "name": "Gold-template",
        "protections": [
            {
                "schedules": [
                    {
                        "id": 0,
                        "schedule": {
                            "activeTime": {
                                "activeFromTime": "16:15",
                                "activeUntilTime": "20:15",
                            },
                            "recurrence": "ByMinutes",
                            "repeatInterval": {"every": 0},
                        },
                    }
                ],
                "type": "Snapshot",
            }
        ],
    }

    def __init__(
        self,
        name,
        protections_id,
        activeFromTime,
        activeUntilTime,
        recurrence,
        every,
        protection_type,
        description=None,
        copyPoolId=None,
        expireAfter_unit=None,
        expireAfter_value=None,
        lockFor_unit=None,
        lockFor_value=None,
        schedule_name=None,
        pattern_format=None,
        on=None,
        startTime=None,
        sourceProtectionScheduleId=None,
        verify=None,
    ):
        self.name = name
        self.description = description
        self.id = protections_id
        self.copyPoolId = copyPoolId
        self.activeFromTime = activeFromTime
        self.activeUntilTime = activeUntilTime
        self.expireAfter_unit = expireAfter_unit
        self.expireAfter_value = expireAfter_value
        self.lockFor_unit = lockFor_unit
        self.lockFor_value = lockFor_value
        self.schedule_name = schedule_name
        self.format = pattern_format
        self.recurrence = recurrence
        self.every = every
        self.on = on
        self.type = protection_type
        self.protections = self.payload["protections"][0]
        self.schedules = self.protections["schedules"][0]
        self.schedule = self.schedules["schedule"]
        self.activeTime = self.schedule["activeTime"]
        self.startTime = startTime
        self.sourceProtectionScheduleId = sourceProtectionScheduleId
        self.repeatInterval = self.schedule["repeatInterval"]
        self.verify = verify

    def update(self):
        self.payload["name"] = self.name
        self.schedules["id"] = self.id
        self.activeTime["activeFromTime"] = self.activeFromTime
        self.activeTime["activeUntilTime"] = self.activeUntilTime
        self.schedule["recurrence"] = self.recurrence
        self.repeatInterval["every"] = self.every
        self.protections["type"] = self.type

        if self.description:
            self.payload["description"] = self.description

        if self.copyPoolId:
            self.protections.update({"copyPoolId": self.copyPoolId})

        if self.expireAfter_unit and self.expireAfter_value:
            self.schedules.update(
                {
                    "afterTime": {
                        "unit": self.expireAfter_unit,
                        "value": self.expireAfter_value,
                    }
                }
            )

        if self.lockFor_unit and self.lockFor_value:
            self.schedules.update({"lockFor": {"unit": self.lockFor_unit, "value": self.lockFor_value}})

        if self.schedule_name:
            self.schedules.update({"name": self.schedule_name})

        if self.format:
            self.schedules.update({"pattern": {"format": self.format}})

        if self.on:
            self.repeatInterval.update({"on": self.on})

        if self.startTime:
            self.schedule.update({"startTime": self.startTime})

        if self.sourceProtectionScheduleId:
            self.schedules.update({"sourceProtectionScheduleId": self.sourceProtectionScheduleId})

        if self.verify is not None:
            self.schedules.update({"verify": self.verify})

        return self.payload
