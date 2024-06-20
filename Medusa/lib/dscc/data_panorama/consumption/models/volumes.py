from datetime import datetime


from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VolumesConsumption:
    """
    The below dataclass is to get all the volumes related information
        The request URL is /data-observability/v1/volumes-consumption
    Dataclass "VolumesConsumption" has variables below:
    1) id is of type str and it stores endpoint name-collection time (Ex. "volumes-consumption-1645920000000")
    2) name is of type str and it stores sames as id
    3) type is of type str and it stores api endpoint ( Ex: "volumes consumption")
    4) generation is of type int by default 1
    5) resourceUri is of type str and api uri
    6) customerId is of type str and it stores customer id
    7) consoleUri is of type str and is blank for this release
    8) numVolumes is of type int and stores total volume count
    9) totalSizeInBytes is of type int
    10) utilizedSizeInBytes is of type int
    11) cost is of type float
    12) previousMonthCost is of type float
    13) previousMonthUtilizedSizeInBytes is of type int
    14) currentMonthCost is of type float
    15) currentMonthUtilizedSizeInBytes is of type int

    """

    id: str
    name: str
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str
    numVolumes: int
    totalSizeInBytes: int
    utilizedSizeInBytes: int
    cost: float
    previousMonthCost: float
    previousMonthUtilizedSizeInBytes: int
    currentMonthCost: float
    currentMonthUtilizedSizeInBytes: int

    def __init__(
        self,
        id: str,
        name: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
        numVolumes: int,
        totalSizeInBytes: int,
        utilizedSizeInBytes: int,
        cost: float,
        previousMonthCost: float,
        previousMonthUtilizedSizeInBytes: int,
        currentMonthCost: float,
        currentMonthUtilizedSizeInBytes: int,
    ):
        self.id = id
        self.name = name
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri
        self.numVolumes = numVolumes
        self.totalSizeInBytes = totalSizeInBytes
        self.utilizedSizeInBytes = utilizedSizeInBytes
        self.cost = cost
        self.previousMonthCost = previousMonthCost
        self.previousMonthUtilizedSizeInBytes = previousMonthUtilizedSizeInBytes
        self.currentMonthCost = currentMonthCost
        self.currentMonthUtilizedSizeInBytes = currentMonthUtilizedSizeInBytes


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MonthlyVolumesCost:
    """
    The below dataclass is to get the monthly cost for the volumes created
        The request URL is /data-observability/v1/volumes-cost-trend
    This is a part of dataclass "VolumesCostTrend"
    Dataclass "MonthlyVolumesCost" has variables below:
    1) year is of integer type and it stores year of the volume created
    2) month is of integer type and it stores month the volume was created
    3) cost is of float type and it stores the total usage cost
    4) currency is of string type and it stores currency
    5) id is of type str it stores endpoint name-collection time
    6) name is of type str and it stores sames as id
    7) type is of type str and it stores api endpoint
    8) generation is of type int by default 1
    9) resourceUri is of type str and api uri
    10) customerId is of type str and it stores customer id
    11) consoleUri is of type str and is blank for this release

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
        month: int,
        year: int,
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
        self.month = month
        self.year = year
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
class VolumesCostTrend:
    """
    The below dataclass is to get monthly cost for the volumes created
        The request URL is /data-observability/v1/volumes-cost-trend
    This dataclass "VolumesCostTrend" has variables below:
    1) items is a list type which stores details of MonthlyVolumesCost
    2) count is number of records requested as part of API call
    3) Offset is of type integer and starts displaying from that point
    4) total is of integer type and it stores total number of collections

    """

    items: list[MonthlyVolumesCost]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[MonthlyVolumesCost], count: int, offset: int, total: int):
        self.items = [MonthlyVolumesCost(**monthvolcost) for monthvolcost in items]
        self.count = count
        self.offset = offset
        self.total = total


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TotalVolumesUsage:
    """
    The below dataclass is to get overall volumes usage data for the specific time intervals
        The request URL is /data-observability/v1/volumes-usage-trend
    This is a part of dataclass "VolumesUsageTrend"
    Dataclass "TotalVolumesUsage" has variables below:
    1) timeStamp is of datetime type and it stores date and time when it is fetching
    2) totalUsageInBytes is of integer type and it stores total volume usage
    3) id is of type str it stores endpoint name-collection time
    2) name is of type str and it stores sames as id
    3) type is of type str and it stores api endpoint
    6) generation is of type int by default 1
    7) resourceUri is of type str and api uri
    8) customerId is of type str and it stores customer id
    9) consoleUri is of type str and is blank for this release

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
class VolumesUsageTrend:
    """
    The below dataclass is to get overall volumes usage data for the specific time intervals
        The request URL is /data-observability/v1/volumes-usage-trend
    This dataclass "VolumesUsageTrend" has variables below:
    1) items is a list type which stores details of TotalVolumesUsage
    2) count is number of records requested as part of API call
    3) offset is of type integer and starts displaying from that point
    4) total is of integer type and it stores total number of collections
    """

    items: list[TotalVolumesUsage]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[TotalVolumesUsage], count: int, offset: int, total: int):
        self.items = [TotalVolumesUsage(**totvolsuse) for totvolsuse in items]
        self.count = count
        self.offset = offset
        self.total = total


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TotalVolumesCreated:
    """
    The below dataclass is to get volumes created for the specific time intervals
        The request URL is /data-observability/v1/volumes-creation-trend
    This is a part of dataclass "VolumesCreationTrend"
    Dataclass "TotalVolumesCreated" has variables below:
    1) timeStamp is of datetime type and it stores date and time
    2) numVolumes is of integer type and it stores total volumes created at that timestamp
    3) id is of type str it stores endpoint name-collection time
    4) name is of type str and it stores sames as id
    5) type is of type str and it stores api endpoint
    6) generation is of type int by default 1
    7) resourceUri is of type str and api uri
    8) customerId is of type str and it stores customer id
    9) consoleUri is of type str and is blank for this release

    """

    updatedAt: datetime
    numVolumes: int
    aggrWindowTimestamp: datetime
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
        numVolumes: int,
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
        self.numVolumes = numVolumes
        self.id = id
        self.name = name
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VolumesCreationTrend:
    """
    The below dataclass is to get volumes created for the specific time intervals
        The request URL is /data-observability/v1/volumes-creation-trend
    This dataclass "VolumesCreationTrend" has variables below:
    1) items is a list type which stores total volumes created
    2) count is number of records requested as part of API call
    3) offset is of type integer and starts displaying from that point
    4) total is of integer type and it stores total number of colletions

    """

    items: list[TotalVolumesCreated]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[TotalVolumesCreated], count: int, offset: int, total: int):
        self.items = [TotalVolumesCreated(**totvolscreate) for totvolscreate in items]
        self.count = count
        self.offset = offset
        self.total = total


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ActivityTrendDetail:
    """
    The below dataclass is to get all the volumes activity for the specific customer
        The request URL is /data-observability/v1/volumes-activity-trend
    This is a part of dataclass "VolumeActivity" and "VolumesActivityTrend"
    This dataclass "ActivityTrendDetail" has variables below:
    1) timeStamp is a datetime type which stores date time
    2) ioActivity is of float type and it stores ioactivity value

    """

    timeStamp: datetime
    ioActivity: float

    def __init__(self, timeStamp: datetime, ioActivity: float):
        self.timeStamp = timeStamp
        self.ioActivity = ioActivity


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VolumeActivity:
    """
    This dataclass is to get all the volumes activity for the specific customer
        The request URL is /data-observability/v1/volumes-activity-trend
    This is a part of dataclass "VolumesActivityTrend"
    This dataclass "VolumeActivity" has variables below:
    1) id is a string type which stores volume Id
    2) name is of string type and it stores volume name
    3) provisionType is of string type and it stores thick or thin
    4) totalSizeInBytes is of integer type and it stores total space
    5) utilizedSizeInBytes is of integer type and it stores space utilized
    6) createdAt is of datetime type and it stores the time it was created
    7) isConnected is of bool type and it stores connected or not
    8) ioActivity is of float type and it stores ioactivity
    9) array is of string type and it stores array name
    10) activityTrendInfo is of list type and it stores ActivityTrendDetail
    11) type is of type str and it stores api endpoint
    12) generation is of type int by default 1
    13) resourceUri is of type str and api uri
    14) customerId is of type str and it stores customer id
    15) consoleUri is of type str and is blank for this release

    """

    id: str
    name: str
    provisionType: str
    totalSizeInBytes: int
    utilizedSizeInBytes: int
    utilizedPercentage: float
    createdAt: datetime
    ioActivity: float
    system: str
    systemId: str
    # volumeCreationAge: int
    activityTrendInfo: any
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        id: str,
        name: str,
        provisionType: str,
        totalSizeInBytes: int,
        utilizedSizeInBytes: int,
        utilizedPercentage: float,
        createdAt: datetime,
        ioActivity: float,
        system: str,
        systemId: str,
        activityTrendInfo: any,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.id = id
        self.name = name
        self.provisionType = provisionType
        self.totalSizeInBytes = totalSizeInBytes
        self.utilizedSizeInBytes = utilizedSizeInBytes
        self.utilizedPercentage = utilizedPercentage
        self.createdAt = createdAt
        self.ioActivity = ioActivity
        self.system = system
        self.systemId = systemId
        if activityTrendInfo != None:
            self.activityTrendInfo = [ActivityTrendDetail(**acttrenddetail) for acttrenddetail in activityTrendInfo]
        else:
            self.activityTrendInfo = None
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VolumesActivityTrend:
    """
    The dataclass is to get all the volumes activity for the specific customer
        The request URL is /data-observability/v1/volumes-activity-trend
    This dataclass "VolumesActivityTrend" has variables below:
    1) items is a list type which stores VolumeActivity
    2) count is number of records requested as part of API call
    3) offset is of type integer and starts displaying from that point
    4) total is of integer type and it stores total number of colletions

    """

    items: list[VolumeActivity]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[VolumeActivity], count: int, offset: int, total: int):
        self.items = [VolumeActivity(**volact) for volact in items]
        # self.items = items
        self.count = count
        self.offset = offset
        self.total = total


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VolumeUsage:
    """
    The below dataclass is to get the volumes detail for the individual volumes
        The request URL is /data-observability/v1/volumes-consumption/{volume-uuid}/volume-usage
    This dataclass "VolumeUsageDetails" has variables below:
    1) createdAt is a datetime type which stores when array was created
    2) provisionType is a string type which stores thin or thick
    3) utilizedSizeInBytes is a integer type which stores used space
    4) totalSizeInBytes is a integer type which stores total space
    5) id is of type str and it stores endpoint name-collection time
    6) name is same as id
    7) type is api endpoint
    8) generation is of type int by default 1
    9) resourceUri is of type str and api uri
    10) customerId is of type str and it stores customer id
    11) consoleUri is of type str and is blank for this release

    """

    createdAt: datetime
    provisionType: str
    utilizedSizeInBytes: int
    totalSizeInBytes: int
    id: str
    name: str
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        createdAt: datetime,
        provisionType: str,
        utilizedSizeInBytes: int,
        totalSizeInBytes: int,
        id: str,
        name: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.createdAt = createdAt
        self.provisionType = provisionType
        self.utilizedSizeInBytes = utilizedSizeInBytes
        self.totalSizeInBytes = totalSizeInBytes
        self.id = id
        self.name = name
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TotalVolumeUsage:
    """
    The below dataclass is to get the overall individual volume usage data for the specific time intervals
        The request URL is /data-observability/v1/volumes-consumption/{volume-uuid}/volume-usage-trend
    This is a part of dataclass "VolumeUsageTrend"
    This dataclass "VolumeUsage" has variables below:
    1) timeStamp is a datetime type which stores date and time
    2) totalUsageInBytes is of integer type and it stores total volumes usage
    3) id is of type str it stores endpoint name-collection time
    4) name is of type str and it stores sames as id
    5) type is of type str and it stores api endpoint
    6) generation is of type int by default 1
    7) resourceUri is of type str and api uri
    8) customerId is of type str and it stores customer id
    9) consoleUri is of type str and is blank for this release

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
class VolumeUsageTrend:
    """
    The below dataclass is to get the overall individual volume usage data for the specific time intervals
        The request URL is /data-observability/v1/volumes-consumption/{volume-uuid}/volume-usage-trend
    This dataclass "VolumeUsageTrend" has variables below:
    1) items is a list type which stores TotalVolumesUsage dataclass
    2) count is number of records requested as part of API call
    3) offset is of type integer and starts displaying from that point
    4) total is of integer type and it stores total number of colletions

    """

    items: list[TotalVolumeUsage]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[TotalVolumeUsage], count: int, offset: int, total: int):
        self.items = [TotalVolumeUsage(**totvoluse) for totvoluse in items]
        self.count = count
        self.offset = offset
        self.total = total


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TotalIOActivity:
    """
    The below dataclass is to get the overall IO activity data for the specific time intervals
        The request URL is /data-observability/v1/volumes-consumption/{volume-uuid}/volume-io-trend
    This is a part of dataclass "VolumeIoTrend"
    This dataclass "TotalIOActivity" has variables below:
    1) timeStamp is a datetime type which stores date and time
    2) ioActivity is of float type and it stores total IO activity usage
    3) id is of type str it stores endpoint name-collection time
    4) name is of type str and it stores sames as id
    5) type is of type str and it stores api endpoint
    6) generation is of type int by default 1
    7) resourceUri is of type str and api uri
    8) customerId is of type str and it stores customer id
    9) consoleUri is of type str and is blank for this release

    """

    timeStamp: datetime
    ioActivity: float
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
        ioActivity: float,
        id: str,
        name: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.timeStamp = timeStamp
        self.ioActivity = ioActivity
        self.id = id
        self.name = name
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VolumeIoTrend:
    """
    The below dataclass is to get the overall IO activity data for the specific time intervals
        The request URL is /data-observability/v1/volumes-consumption/{volume-uuid}/volume-io-trend
    This dataclass "VolumeIoTrend" has variables below:
    1) items is a list type which has dataclass TotalIOActivity
    2) count is number of records requested as part of API call
    3) offset is of type integer and starts displaying from that point
    4) total is of integer type and it stores total number of colletions


    """

    items: list[TotalIOActivity]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[TotalIOActivity], count: int, offset: int, total: int):
        self.items = [TotalIOActivity(**totioact) for totioact in items]
        self.count = count
        self.offset = offset
        self.total = total


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TotalSnapshotsCopies:
    """
    The below dataclass is to get the fetch the snapshots copies created per volume
        The request URL is /data-observability/v1/volumes-consumption/{volume-uuid}/snapshots
    This is a part of dataclass "SnapshotCopies"
    This dataclass "TotalSnapshotsCopies" has variables below:
    1) timeStamp is a datetime type which stores date and time
    2) periodicSnapshotSizeInBytes is of integer type  and stores size of periodic snapshots
    3) adhocSnapshotSizeInBytes is of integer type  and stores size of adhoc snapshots
    4) numPeriodicSnapshots is of integer type and stores count of periodic snapshots
    5) numAdhocSnapshots is of integer type and stores count of adhoc snapshots
    6) id is of type str it stores endpoint name-collection time
    7) name is of type str and it stores sames as id
    8) type is of type str and it stores api endpoint
    9) generation is of type int by default 1
    10) resourceUri is of type str and api uri
    11) customerId is of type str and it stores customer id
    12) consoleUri is of type str and is blank for this release

    """

    timeStamp: datetime
    periodicSnapshotSizeInBytes: int
    adhocSnapshotSizeInBytes: int
    numPeriodicSnapshots: int
    numAdhocSnapshots: int
    numClones: int
    cloneSizeInBytes: int
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
        periodicSnapshotSizeInBytes: int,
        adhocSnapshotSizeInBytes: int,
        numPeriodicSnapshots: int,
        numAdhocSnapshots: int,
        numClones: int,
        cloneSizeInBytes: int,
        id: str,
        name: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.timeStamp = timeStamp
        self.periodicSnapshotSizeInBytes = periodicSnapshotSizeInBytes
        self.adhocSnapshotSizeInBytes = adhocSnapshotSizeInBytes
        self.numPeriodicSnapshots = numPeriodicSnapshots
        self.numAdhocSnapshots = numAdhocSnapshots
        self.numClones = numClones
        self.cloneSizeInBytes = cloneSizeInBytes
        self.id = id
        self.name = name
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SnapshotCopies:
    """
    The below dataclass is to fetch the snapshots copies created per volume
        The request URL is /data-observability/v1/volumes-consumption/{volume-uuid}/snapshots
    This dataclass "SnapshotCopies" has variables below:
    1) items is a list type which stores TotalSnapshotsCopies dataclass
    2) count is number of records requested as part of API call
    3) offset is of type integer and starts displaying from that point
    4) total is of integer type and it stores total number of colletions

    """

    items: list[TotalSnapshotsCopies]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[TotalSnapshotsCopies], count: int, offset: int, total: int):
        self.items = [TotalSnapshotsCopies(**totsnapcopies) for totsnapcopies in items]
        self.count = count
        self.offset = offset
        self.total = total


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TotalClonesCopies:
    """
    The below dataclass is to fetch the clone copies created per volume
        The request URL is /data-observability/v1/volumes-consumption/{volume-uuid}/clones
    This is a part of dataclass "CloneCopies"
    This dataclass "TotalClonesCopies" has variables below:
    1) timeStamp is a datetime type which stores date and time
    2) sizeInBytes is of integer type  and stores size of clones
    3) numClones is of integer type  and stores total clones
    4) id is of type str it stores endpoint name-collection time
    5) name is of type str and it stores sames as id
    6) type is of type str and it stores api endpoint
    7) generation is of type int by default 1
    8) resourceUri is of type str and api uri
    9) customerId is of type str and it stores customer id
    10) consoleUri is of type str and is blank for this release

    """

    timeStamp: datetime
    sizeInBytes: int
    numClones: int
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
        sizeInBytes: int,
        numClones: int,
        id: str,
        name: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.timeStamp = timeStamp
        self.sizeInBytes = sizeInBytes
        self.numClones = numClones
        self.id = id
        self.name = name
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CloneCopies:
    """
    The below dataclass is to fetch the clone copies created per volume
        The request URL is /data-observability/v1/volumes-consumption/{volume-uuid}/clones
    This dataclass "CloneCopies" has variables below:
    1) items is a list type which stores TotalClonesCopies dataclass
    2) count is number of records requested as part of API call
    3) offset is of type integer and starts displaying from that point
    4) total is of integer type and it stores total number of colletions

    """

    items: list[TotalClonesCopies]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[TotalClonesCopies], count: int, offset: int, total: int):
        self.items = [TotalClonesCopies(**totclonecopies) for totclonecopies in items]
        self.count = count
        self.offset = offset
        self.total = total
