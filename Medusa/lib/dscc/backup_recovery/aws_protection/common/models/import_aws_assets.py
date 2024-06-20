from dataclasses_json import dataclass_json, LetterCase
from dataclasses import dataclass, field

from lib.common.enums.aws_region_zone import AWSRegionZone


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ImportAWSAssetsByRegion:
    region: AWSRegionZone = None
    num_expected: int = 0
    asset_names: list[str] = field(default_factory=list)
