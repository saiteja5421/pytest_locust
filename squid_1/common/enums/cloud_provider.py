from enum import Enum


class CloudProvider(Enum):
    AWS = "CLOUD_PROVIDER_ENUM_AWS"
    AZURE = "CLOUD_PROVIDER_ENUM_AZURE"

    def __str__(self):
        return "CLOUD_PROVIDER_ENUM_" + str(self.name)
