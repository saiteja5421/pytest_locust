from dataclasses import InitVar, dataclass, field
from datetime import datetime
from dataclasses_json import dataclass_json, LetterCase

from lib.common.enums.aws_region_zone import AWSRegionZone

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import CSPTag


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostImportSnapshot:
    aws_regions: InitVar[list[AWSRegionZone]]
    expiration: InitVar[datetime]
    import_tags: list[CSPTag]
    import_volume_snapshots: bool = field(default=False)
    import_machine_instance_images: bool = field(default=False)

    # Not to be used while creating the payload.
    # __post_init__ will take care of populating these fields
    expires_at: str = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    csp_regions: list[str] = field(default_factory=list[str])

    def __post_init__(self, aws_regions: list[AWSRegionZone], expiration: datetime):
        """Populates 'regions' and 'expires_at' fields in the required format

        Args:
            aws_regions (list[AWSRegionZone]): A list of AWSRegionZone
            expiration (datetime): datetime for which the backup / snapshot expiration has to be set
            provide value as
            Example:
            ```
            from datetime import datetime
                                  Y     M   D  H   M   S
            expiration = datetime(2023, 12, 2, 13, 30, 45)
            ```
        """

        self.csp_regions = [region.value for region in aws_regions]
        self.expires_at = expiration.strftime("%Y-%m-%dT%H:%M:%SZ")
