from datetime import datetime
from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SnapshotConsumption:
    """
    The  dataclass is construct data object for snapshots related information for a specific customer id
    The request URL is /data-observability/v1alpha1/snapshots-consumption
    : Arguments -
        : id: str
        : name: str
        : type: str
        : generation:	int
        : resourceUri: str
        : customerId: str
        : consoleUri: str
        : numSnapshots - int
        : totalSizeInBytes - int
        : cost - float
        : previousMonthCost - float
        : currentMonthCost - float
    1) id is of type str and it stores Snapshot id
    2) name is of type str and it stores Snapshot name
    3) type is of type str and it stores Snapshot type
    4) generation is of type int by default 1
    5) resourceUri is of type str and api uri
    6) customerId is of type str and it stores customer id
    7) consoleUri is of type string and it will empty for release 1
    8) numSnapshots is of type int and stores total Snapshot count
    9) totalSizeInBytes is of type int
    10) cost is of type float
    11) previousMonthCost is of type float
    12) currentMonthCost is of type float
    """

    numSnapshots: int
    totalSizeInBytes: int
    cost: float
    previousMonthCost: float
    currentMonthCost: float
    id: str
    name: str
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        numSnapshots: int,
        totalSizeInBytes: int,
        cost: float,
        previousMonthCost: float,
        currentMonthCost: float,
        id: str,
        name: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.numSnapshots = numSnapshots
        self.totalSizeInBytes = totalSizeInBytes
        self.cost = cost
        self.previousMonthCost = previousMonthCost
        self.currentMonthCost = currentMonthCost
        self.id = id
        self.name = name
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MonthlySnapshotsCost:
    """
    The dataclass is construct data object for monthly volume cost
    The request URL is /data-observability/v1alpha1/snapshots-cost-trend
    This is a part of dataclass "snapshots-cost-trend"
        : Arguments -
            : month - int
            : year - int
            : cost - float
            : currency - str
            : id - str
            : name - str
            : type - str
            : generation - int
            : resourceUri - str
            : customerId -	str
            : consoleUri: str
        1) month is of integer type and it stores month the Snapshto was created
        2) year is of integer type and it stores year of the Snapshot created
        3) cost is of float type and it stores the total usage cost
        4) currency is of string type and it stores currency
        5) id is of type str and it stores Snapshot id
        6) name is of type str and it stores Snapshot name
        7) type is of type str and it stores
        8) generation is of type int by default 1
        9) resourceUri is of type str and api uri
        10) customerId is of type str and it stores customer id
        11) consoleUri is of type string and it will empty for release 1
    """

    month: int
    year: int
    cost: float
    currency: str
    id: str
    name: str
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        year: int,
        month: int,
        cost: float,
        currency: str,
        id: str,
        name: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.year = year
        self.month = month
        self.cost = cost
        self.currency = currency
        self.id = id
        self.name = name
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SnapshotCostTrend:
    """
    The dataclass is construct data object for the Snapshot cost trend
    The request URL is /data-observability/v1alpha1/snapshots-cost-trend
    : Arguments -
        : items - List[MonthlySnapshotsCost]
        : count: int
        : offset: int
        : total: int
    This dataclass "SnapshotCostTrend" has variables below:
    1) items is a list type which stores details of MonthlySnapshotCost
    2) count is number of records requested as part of API call
    3) offset is of type integer and starts displaying from that point
    4) total is of integer type and it stores total number of collections
    """

    items: list[MonthlySnapshotsCost]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[MonthlySnapshotsCost], count: int, offset: int, total: int):
        self.items = [MonthlySnapshotsCost(**month_vol_cost) for month_vol_cost in items]
        self.count = count
        self.offset = offset
        self.total = total


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TotalSnapshotsUsage:
    """
    The dataclass is construct data object for Total Snapshot cost
    The request URL is /data-observability/v1alpha1/snapshots-usage-trend
    : Arguments -
        : timeStamp - datetime
        : totalUsageInBytes - int
        : id - str
        : name: str
        : type: str
        : generation: int
        : resourceUri: str
        : customerId:	str
        : consoleUri: str
    1) timeStamp is of datetime type and it stores date and time when it is fetching
    2) totalUsageInBytes is of integer type and it stores total Snapshot usage
    3) id is of type str it stores endpoint name-collection time
    2) name is of type str and it stores sames as id
    3) type is of type str and it stores api endpoint
    6) generation is of type int by default 1
    7) resourceUri is of type str and api uri
    8) customerId is of type str and it stores customer id
    9) consoleUri is of type string and it will empty for release 1
    """

    timeStamp: datetime
    totalUsageInBytes: int
    id: str
    name: str
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        timeStamp: datetime,
        totalUsageInBytes: int,
        id: str,
        name: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.timeStamp = timeStamp
        self.totalUsageInBytes = totalUsageInBytes
        self.id = id
        self.name = name
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SnapshotUsageTrend:
    """
    The dataclass is construct data object for overall snapshots usage data for the specific time intervals
    The request URL is /data-observability/v1alpha1/snapshots-usage-trend
    : Arguments -
        : items: list[TotalSnapshotsUsage]
        : count: int
        : offset: int
        : total: int
    1) items is a list type which stores details of Total Snapshot Usage
    2) count is number of records requested as part of API call
    3) offset is of type integer and starts displaying from that point
    4) total is of integer type and it stores total number of collections
    """

    items: list[TotalSnapshotsUsage]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[TotalSnapshotsUsage], count: int, offset: int, total: int):
        self.items = [TotalSnapshotsUsage(**total_snap_usage) for total_snap_usage in items]
        self.count = count
        self.offset = offset
        self.total = total


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TotalSnapshotsCreated:
    """
    The dataclass is construct data object for  the Total snapshots created
    The request URL is /data-observability/v1alpha1/snapshots-creation-trend
    : Arguments -
        : timeStamp: datetime
        : numAdhocSnapshots: int
        : numPeriodicSnapshots: int
        : id: str
        : name: str
        : type: str
        : generation: int
        : resourceUri: str
        : customerId: str
        : consoleUri: str
    1) timeStamp is of datetime type and it stores date and time
    2) numAdhocSnapshots is of integer type and it stores total Adhoc SNapshot created at that timestamp
    3) numPeriodicSnapshots  is of integer type and it stores total Periodic SNapshot created at that timestamp
    4) id is of type str it stores endpoint name-collection time
    5) name is of type str and it stores sames as id
    6) type is of type str and it stores api endpoint
    7) generation is of type int by default 1
    8) resourceUri is of type str and api uri
    9) customerId is of type str and it stores customer id
    10) consoleUri is of type string and it will empty for release 1

    """

    updatedAt: datetime
    aggrWindowTimestamp: datetime
    numAdhocSnapshots: int
    numPeriodicSnapshots: int
    id: str
    name: str
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        updatedAt: datetime,
        aggrWindowTimestamp: datetime,
        numAdhocSnapshots: int,
        numPeriodicSnapshots: int,
        id: str,
        name: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.updatedAt = updatedAt
        self.aggrWindowTimestamp = aggrWindowTimestamp
        self.numAdhocSnapshots = numAdhocSnapshots
        self.numPeriodicSnapshots = numPeriodicSnapshots
        self.id = id
        self.name = name
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SnapshotCreationTrend:
    """
    The dataclass is construct data object for the snapshots created for the specific time intervals
    The request URL is /data-observability/v1alpha1/snapshots-creation-trend
    : Arguments -
        : items - List[TotalSnapshotsCreated]
        : count - int
        : offset - int
        : total - int
    1) items is a list type which stores details of Total Snapshot Created
    2) count is number of records requested as part of API call
    3) offset is of type integer and starts displaying from that point
    4) total is of integer type and it stores total number of collections
    """

    items: list[TotalSnapshotsCreated]
    total: int
    count: int
    offset: int

    def __init__(self, items: list[TotalSnapshotsCreated], count: int, offset: int, total: int):
        self.items = [TotalSnapshotsCreated(**total_snap_create) for total_snap_create in items]
        self.total = total
        self.count = count
        self.offset = offset


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SnapshotSize:
    """
    The dataclass is construct data object for  the Snapshot Size
    The request URL is /data-observability/v1alpha1/snapshots-age-trend
    : Arguments -
        : numSnapshots - int
    numSnapshots is of type integer and stored number of Snapshots
    """

    numSnapshots: int

    def __init__(self, numSnapshots: int):
        self.numSnapshots = numSnapshots


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SnapshotAge:
    age: str
    bucket: int
    sizeUnit: str
    updatedAt : datetime
    sizeInfo: list[SnapshotSize]
    id: str
    name: str
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        age: str,
        bucket: int,
        sizeUnit: str,
        updatedAt: datetime,
        sizeInfo: list[SnapshotSize],
        id: str,
        name: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        """
        The dataclass is construct data object for the Snapshot Age
        The request URL is /data-observability/v1alpha1/snapshots-age-trend
        : Arguments -
            : age: str
            : bucket: int
            : sizeUnit: str
            : updatedAt :datetime
            : sizeInfo: list[SnapshotSize]
            : id: str
            : name: str
            : type: str
            : generation: int
            : resourceUri: str
            : customerId: str
            : consoleUri: str
        age is of string type and it stores age tags Eg 0-6 Months, 1-2 Years
        bucket is of integer type and it stores bucket type
        sizeUnit  is of string type and it stores size unit Eg GB,MB
        updatedAt is datetime which is time when collection is processe by etl
        sizeInfo is of type list it stores details of Snapshot Size
        id is of type str it stores endpoint name-collection time
        name is of type str and it stores sames as id
        type is of type str and it stores api endpoint
        generation is of type int by default 1
        resourceUri is of type str and api uri
        customerId is of type str and it stores customer id
        consoleUri is of type string and it will empty for release 1
        """
        self.age = age
        self.bucket = bucket
        self.sizeUnit = sizeUnit
        self.updatedAt =updatedAt
        self.sizeInfo = [SnapshotSize(**snap_size) for snap_size in sizeInfo]
        self.id = id
        self.name = name
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SnapshotAgeTrend:
    items: list[SnapshotAge]
    total: int
    count: int
    offset: int

    def __init__(self, items: list[SnapshotAge], count: int, offset: int, total: int):
        """
        The dataclass is construct data object forthe snapshots age size related information for the specific time intervals
        The request URL is /data-observability/v1alpha1/snapshots-age-trend
        : Arguments -
            : items - List[SnapshotAge]
            : count - int
            : offset - int
            : total - int
        1) items is a list type which stores details of Total Snapshot Age
        2) count is number of records requested as part of API call
        3) offset is of type integer and starts displaying from that point
        4) total is of integer type and it stores total number of collections

        """
        self.items = [SnapshotAge(**snap_age) for snap_age in items]
        self.total = total
        self.count = count
        self.offset = offset


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SnapshotRetention:
    """
    The dataclass is construct data object for the Snapshot Retention
    The request URL is /data-observability/v1alpha1/snapshots-retention-trend
    : Arguments -
        : range - str
        : numPeriodicSnapshots - int
        : numAdhocSnapshots - int
        : id - str
        : name - str
        : type - str
        : generation - int
        : resourceUri - str
        : customerId - str
        : consoleUri: str
    1) range is of string type and it stores snapshot range
    2) numPeriodicSnapshots is of integer type and it stores number of periodic snapshot
    3) numAdhocSnapshots  is of integer type and it stores number of adhoc snapshot
    4) id is of type str it stores endpoint name-collection time
    5) name is of type str and it stores sames as id
    6) type is of type str and it stores api endpoint
    7) generation is of type int by default 1
    8) resourceUri is of type str and api uri
    9) customerId is of type str and it stores customer id
    10) consoleUri is of type string and it will empty for release 1
    """

    range: str
    numPeriodicSnapshots: int
    numAdhocSnapshots: int
    id: str
    name: str
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        range: str,
        numPeriodicSnapshots: int,
        numAdhocSnapshots: int,
        id: str,
        name: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.range = range
        self.numPeriodicSnapshots = numPeriodicSnapshots
        self.numAdhocSnapshots = numAdhocSnapshots
        self.id = id
        self.name = name
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SnapshotRetentionTrend:
    """
    The dataclass is construct data object for the snapshots retention related information for the specific time intervals
    The request URL is /data-observability/v1alpha1/snapshots-retention-trend
    : Arguments -
            items: list[SnapshotRetention],
            count: int,
            offset: int,
            total: int
    1) items is a list type which stores details of Snapshot Retention
    2) count is number of records requested as part of API call
    3) offset is of type integer and starts displaying from that point
    4) total is of integer type and it stores total number of collections
    """

    items: list[SnapshotRetention]
    total: int
    count: int
    offset: int

    def __init__(self, items: list[SnapshotRetention], count: int, offset: int, total: int):
        self.items = [SnapshotRetention(**snap_ret) for snap_ret in items]
        self.count = count
        self.offset = offset
        self.total = total


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SnapshotsDetail:
    """
    The  dataclass is construct data object for snapshots related information for a specific customer id
    The request URL is /data-observability/v1alpha1/snapshots
    : Arguments -
        : name - str
        : systemName - str
        : systemId - str
        : createdAt - datetime
        : updatedAt - datetime
        : id - str
        : type - str
        : generation -	int
        : resourceUri - str
        : customerId - str
        : consoleUri: str
    name is of string type and it stores snapshot name
    systemName is of type string and stores system name
    systemId is of type string and stores system id
    createdAt is of type timestamp and stores date time of snapshot created
    updatedAt is of type timestamp and stores date time of eTL processing time (Colletcion end time)
    id is of type str it stores endpoint name-collection time
    type is of type str and it stores api endpoint
    generation is of type int by default 1
    resourceUri is of type str and api uri
    customerId is of type str and it stores customer id
    consoleUri is of type string and it will empty for release 1
    """

    name: str
    system: str
    systemId: str
    createdAt: datetime
    updatedAt: datetime
    id: str
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        name: str,
        system: str,
        systemId: str,
        createdAt: datetime,
        updatedAt: datetime,
        id: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.name = name
        self.system = system
        self.systemId = systemId
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.id = id
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Snapshots:
    """
    The dataclass is construct data object for the Sdetails of SnapshotsInfo
    The request URL is /data-observability/v1alpha1/snapshots
    : Arguments -
        : items - List[SnapshotsDetail]
        : count: int
        : offset: int
        : total: int
    1) items is a list type which stores details of Snapshot
    2) count is number of records requested as part of API call
    3) offset is of type integer and starts displaying from that point
    4) total is of integer type and it stores total number of collections
    """

    items: list[SnapshotsDetail]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[SnapshotsDetail], count: int, offset: int, total: int):
        self.items = [SnapshotsDetail(**month_snaps_cost) for month_snaps_cost in items]
        self.count = count
        self.offset = offset
        self.total = total
