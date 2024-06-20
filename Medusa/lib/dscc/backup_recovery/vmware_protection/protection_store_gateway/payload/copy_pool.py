from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from lib.common.enums.aws_regions import AwsStorageLocation


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CopyPool:
    protectionStoreGatewayId: str = ""
    region: str = AwsStorageLocation.AWS_US_EAST_1.value


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionStoresStoreonce:
    """
    This class is used assign the storeonce id and cloud region
    """

    storeOnceId: str = ""
    region: str = AwsStorageLocation.AWS_US_EAST_1.value
