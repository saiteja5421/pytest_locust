class PatchUpdateProtectionTemplate:
    payload = {
        "protections": [
            {
                "schedules": [
                    {
                        "expireAfter": {"unit": "Hours", "value": 0},
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
                ]
            }
        ]
    }

    def __init__(
        self,
        schedules_id,
        activeFromTime,
        activeUntilTime,
        recurrence,
        every,
        description=None,
        name=None,
        protections_id=None,
        expireAfter_unit=None,
        expireAfter_value=None,
        lockFor_unit=None,
        lockFor_value=None,
        schedules_name=None,
        pattern_format=None,
        on=None,
        startTime=None,
    ):

        self.name = name
        self.description = description
        self.schedules_id = schedules_id
        self.id = protections_id
        self.activeFromTime = activeFromTime
        self.activeUntilTime = activeUntilTime
        self.expireAfter_unit = expireAfter_unit
        self.expireAfter_value = expireAfter_value
        self.lockFor_unit = lockFor_unit
        self.lockFor_value = lockFor_value
        self.schedules_name = schedules_name
        self.recurrence = recurrence
        self.every = every
        self.on = on
        self.pattern_format = pattern_format
        self.protections = self.payload["protections"][0]
        self.schedules = self.protections["schedules"][0]
        self.schedule = self.schedules["schedule"]
        self.startTime = startTime

    def update(self):

        self.schedules["id"] = self.schedules_id
        self.schedule["activeTime"]["activeFromTime"] = self.activeFromTime
        self.schedule["activeTime"]["activeUntilTime"] = self.activeUntilTime
        self.schedule["recurrence"] = self.recurrence
        self.schedule["repeatInterval"]["every"] = self.every

        if self.description:
            self.payload.update({"description": self.description})

        if self.name:
            self.payload.update({"name": self.name})

        if self.id:
            self.protections.update({"id": self.id})

        if self.expireAfter_unit and self.expireAfter_value:
            self.schedules.update(
                {
                    "expireAfter": {
                        "unit": self.expireAfter_unit,
                        "value": self.expireAfter_value,
                    }
                }
            )

        if self.lockFor_unit and self.lockFor_value:
            self.schedules.update({"lockFor": {"unit": self.lockFor_unit, "value": self.lockFor_value}})

        if self.schedules_name:
            self.schedules.update({"name": self.schedules_name})

        if self.pattern_format:
            self.schedules.update({"patternFormat": {"format": self.pattern_format}})

        if self.on:
            self.schedule["repeatInterval"].update({"on": self.on})

        if self.startTime:
            self.schedule.update({"startTime": self.startTime})

        return self.payload
