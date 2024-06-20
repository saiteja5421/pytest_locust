from datetime import datetime

from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase

from lib.dscc.data_panorama.consumption.models.volumes import TotalIOActivity


# Dataclass definition of response body for API /api/v1/clones-consumption
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ClonesConsumption:
    """
    Dataclass definition of response body for API /api/v1/clones-consumption
    This API fetches all the clones related information for a specific customer ID
    Content of response body or variables in dataclass:
    totalNumberOfClonesCreated - Gives total number of clones created
    totalSizeInBytes - Gives total space occupied by the clones
    utilizedSizeInBytes - Gives total space utilized by the clones
    unutilizedSpace - Gives information about unutilized space
    cost - Gives information about total cost
    changeInCostPercentage - Gives information about change in cost in term of percentage
    changeInCosumptionPercentage - Gives information about change in consumption in term of percentage
    id - {type}-Collection time
    name - {type}-Collection time
    type - API endpoint name
    generation - Default value is 1
    resourceUri - complete path of REST endpoint
    customerId - Unique ID generated for each customer
    """

    numClones: int
    totalSizeInBytes: int
    utilizedSizeInBytes: int
    cost: float
    previousMonthCost: float
    previousMonthUtilizedSizeInBytes: int
    currentMonthCost: float
    currentMonthUtilizedSizeInBytes: int
    id: str
    name: str
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        numClones: int,
        totalSizeInBytes: int,
        utilizedSizeInBytes: int,
        cost: float,
        previousMonthCost: float,
        previousMonthUtilizedSizeInBytes: int,
        currentMonthCost: float,
        currentMonthUtilizedSizeInBytes: int,
        id: str,
        name: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.numClones = numClones
        self.totalSizeInBytes = totalSizeInBytes
        self.utilizedSizeInBytes = utilizedSizeInBytes
        self.cost = cost
        self.previousMonthCost = previousMonthCost
        self.previousMonthUtilizedSizeInBytes = previousMonthUtilizedSizeInBytes
        self.currentMonthCost = currentMonthCost
        self.currentMonthUtilizedSizeInBytes = currentMonthUtilizedSizeInBytes
        self.id = id
        self.name = name
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


# Dataclass definition of response body for API /api/v1/clones-cost-trend
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MonthlyVolumesCost:
    """
    Dataclass definition of response body for API /api/v1/clones-cost-trend
    This API fetches the monthly cost for the clones created
    This is Dataclass definition of one of the parameter "list of [MonthlyVolumesCost]" of another Dataclass ClonesCostTrend
    Content of response body or variables in dataclass:
    month - Specifies the month for which the cost is calculated.
    year - Specifies the year for which the cost is calculated.
    cost - Specifies the total cost usage for the specified month.
    currency - Gives information about the type of currency being used. eg: USD
    id - {type}-Collection time
    name - {type}-Collection time
    type - API endpoint name
    generation - Default value is 1
    resourceUri - complete path of REST endpoint
    customerId - Unique ID generated for each customer
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


# Dataclass definition of response body for API /api/v1/clones-cost-trend
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ClonesCostTrend:
    """
    Dataclass definition of response body for API /api/v1/clones-cost-trend
    This API fetches the monthly cost for the clones created
    Content of response body or variables in dataclass:
    items - Gives the total clones cost. This parameter is list[MonthlyVolumesCost] where the list parameters are defined in another Dataclass MonthlyVolumesCost.
    count - Default value for pageLimit is 10 and maximum "pageLimit" value is 1000 . Number of data points fetched per API call
    offset - Default value for pageOffset is 0. Determines from which offset data should be read.
    total - Specifies the total number of items
    """

    items: list[MonthlyVolumesCost]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[MonthlyVolumesCost], count: int, offset: int, total: int):
        self.items = [MonthlyVolumesCost(**monthly_volumes_cost) for monthly_volumes_cost in items]
        self.count = count
        self.offset = offset
        self.total = total


# Dataclass definition of response body for API /api/v1/clones-usage-trend
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TotalClonesUsage:
    """
    Dataclass definition of response body for API /api/v1/clones-usage-trend
    This API fetches the overall clones usage data for the specific time intervals
    This is Dataclass definition of one of the parameter "list of [TotalClonesUsage]" of another Dataclass ClonesUsageTrend
    Content of response body or variables in dataclass:
    timeStamp - Gives the specific time stamp of the clone
    totalUsageInBytes - Gives information about total clone usage for the specified time interval.
    id - Individual Clone ID
    name - Individual Clone Name
    type - API endpoint name
    generation - Default value is 1
    resourceUri - complete path of REST endpoint
    customerId - Unique ID generated for each customer
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


# Dataclass definition of response body for API /api/v1/clones-usage-trend
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ClonesUsageTrend:
    """
    Dataclass definition of response body for API /api/v1/clones-usage-trend
    This API fetches the overall clones usage data for the specific time intervals
    Content of response body or variables in dataclass:
    items - Gives the total clones usage for the specified time interval. This parameter is list[TotalClonesUsage] where the list parameters are defined in another Dataclass TotalClonesUsage.
    count - Default value for pageLimit is 10 and maximum "pageLimit" value is 1000 . Number of data points fetched per API call
    offset - Default value for pageOffset is 0. Determines from which offset data should be read.
    total - Specifies the total number of items
    """

    items: list[TotalClonesUsage]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[TotalClonesUsage], count: int, offset: int, total: int):
        self.items = [TotalClonesUsage(**total_clones_usuage) for total_clones_usuage in items]
        self.count = count
        self.offset = offset
        self.total = total


# Dataclass definition of response body for API /api/v1/clones-creation-trend
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TotalClonesCreated:
    """
    Dataclass definition of response body for API /api/v1/clones-creation-trend
    This API fetches the clones created for the specific time intervals.
    This is Dataclass definition of one of the parameter "list of [TotalClonesCreated]" of another Dataclass ClonesCreationTrend
    Content of response body or variables in dataclass:
    timeStamp - Gives the specific time stamp of the clone
    numClones - Gives information about total clones created in the specified time interval.
    id - {type}-Collection time
    name - {type}-Collection time
    type - API endpoint name
    generation - Default value is 1
    resourceUri - complete path of REST endpoint
    customerId - Unique ID generated for each customer
    """

    updatedAt: datetime
    aggrWindowTimestamp: datetime
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
        updatedAt: datetime,
        aggrWindowTimestamp: datetime,
        numClones: int,
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
        self.numClones = numClones
        self.id = id
        self.name = name
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


# Dataclass definition of response body for API /api/v1/clones-creation-trend
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ClonesCreationTrend:
    """
    Dataclass definition of response body for API /api/v1/clones-creation-trend
    This API fetches the clones created for the specific time intervals
    Content of response body or variables in dataclass:
    items: Gives the total clones created in that time. This parameter is list[TotalClonesCreated] where the list parameters are defined in another Dataclass TotalClonesCreated.
    count - Default value for pageLimit is 10 and maximum "pageLimit" value is 1000 . Number of data points fetched per API call
    offset - Default value for pageOffset is 0. Determines from which offset data should be read.
    total - Specifies the total number of items
    """

    items: list[TotalClonesCreated]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[TotalClonesCreated], count: int, offset: int, total: int):
        self.items = [TotalClonesCreated(**total_clones_created) for total_clones_created in items]
        self.count = count
        self.offset = offset
        self.total = total


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CloneActivityTrendDetail:
    """
    The below dataclass is to get all the clones activity for the specific customer
        The request URL is /data-observability/v1/clones-activity-trend
    This is a part of dataclass "CloneActivity" and "CloneActivityTrend"
    This dataclass "CloneActivityTrendDetail" has variables below:
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
class ClonesIoTrend:
    """
    The below dataclass is to get the overall IO activity data for the specific time intervals
        The request URL is /data-observability/v1/volumes-consumption/{volume-uuid}/volume-io-trend
        /data-observability/v1alpha1/systems/{system-id}/clones/{clone-uuid}/clone-io-trend?start-time=2023-03-15T00:00:00.000Z&end-time=2023-08-05T00:00:00.000Z
    This dataclass "ClonesIoTrend" has variables below:
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


# Dataclass definition of response body for API /api/v1/clones-activity-trend
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CloneActivity:
    """
    Dataclass definition of response body for API /api/v1/clones-activity-trend
    This API fetches all the volumes activity for the specific customer.
    This is Dataclass definition of one of the parameter "list of [CloneActivity]" of another Dataclass ClonesActivityTrend
    Content of response body or variables in dataclass:
    name - Gives the name of the clone
    provisionType - Specifies thin or thick provision
    utilizedSizeInBytes - Gives information about space utilization
    totalSizeInBytes is of integer type and it stores total space
    createdAt - Specifies clone creation time
    ioActivity - Gives details about the io Activity on the clone
    activityTrendInfo is of list type and it stores ActivityTrendDetail
    id - Clone ID
    type - API endpoint name
    generation - Default value is 1
    resourceUri - complete path of REST endpoint
    customerId - Unique ID generated for each customer
    """

    name: str
    provisionType: str
    systemId: str
    system: str
    utilizedSizeInBytes: int
    utilizedPercentage: float
    totalSizeInBytes: int
    createdAt: datetime
    ioActivity: float
    activityTrendInfo: any
    id: str
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        name: str,
        provisionType: str,
        systemId: str,
        system: str,
        utilizedSizeInBytes: float,
        utilizedPercentage: float,
        totalSizeInBytes: int,
        createdAt: datetime,
        ioActivity: float,
        activityTrendInfo: any,
        id: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.name = name
        self.provisionType = provisionType
        self.systemId = systemId
        self.system = system
        self.utilizedSizeInBytes = utilizedSizeInBytes
        self.utilizedPercentage = utilizedPercentage
        self.totalSizeInBytes = totalSizeInBytes
        self.createdAt = createdAt
        self.ioActivity = ioActivity
        if activityTrendInfo != None:
            self.activityTrendInfo = [
                CloneActivityTrendDetail(**acttrenddetail) for acttrenddetail in activityTrendInfo
            ]
        else:
            self.activityTrendInfo = None
        self.id = id
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


# Dataclass definition of response body for API /api/v1/clones-activity-trend
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ClonesActivityTrend:
    """
    Dataclass definition of response body for API /api/v1/clones-activity-trend
    This API fetches all the volumes activity for the specific customer
    Content of response body or variables in dataclass:
    items - Gives details about clone activity. This parameter is list[CloneActivity] where the list parameters are defined in another Dataclass CloneActivity.
    count - Default value for pageLimit is 10 and maximum "pageLimit" value is 1000 . Number of data points fetched per API call
    offset - Default value for pageOffset is 0. Determines from which offset data should be read.
    total - Specifies the total number of items
    """

    items: list[CloneActivity]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[CloneActivity], count: int, offset: int, total: int):
        self.items = [CloneActivity(**clone_activity_details) for clone_activity_details in items]
        self.count = count
        self.offset = offset
        self.total = total
