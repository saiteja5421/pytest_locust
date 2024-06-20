from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
from uuid import UUID

import datetime
from datetime import timezone
from google.protobuf.timestamp_pb2 import Timestamp
from typing import Any, Optional


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectNameResourceType:
    name: str
    resourceUri: str
    type: str
