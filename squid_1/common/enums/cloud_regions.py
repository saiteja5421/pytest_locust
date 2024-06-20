from enum import Enum
from itertools import chain

from lib.common.enums.aws_region_zone import AWSRegionZone
from lib.common.enums.az_regions import AZRegion

CloudRegionsStr = Enum("CloudRegionsStr", [(i.name, i.value) for i in chain(AZRegion, AWSRegionZone)])
