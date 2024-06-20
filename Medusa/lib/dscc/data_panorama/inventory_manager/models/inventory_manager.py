from datetime import datetime
from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class InventoryStorageSystemsSummary:
    """
    Dataclass definition of response body for API /data-observability/v1alpha1/inventory-storage-systems-summary.
    This API fetches the inventory summary details based on the location of a particular customer.
    Content of response body or variables in dataclass:
    numSystems - Gives the number of systems
    numLocations - Gives the number of locations where the systems are present
    utilizedSizeInBytes - Gives the overall Space utilized by their systems
    totalSizeInBytes - Gives the overall Total space of their systems
    cost - Gives the overall cost of their systems per month
    currency - Denotes the currency
    id - unique id required as per rest API
    name - name required as per rest API
    type - type required as per rest API
    generation - generation required as per rest API, by default value will be 1.
    resourceUri -  request URL or blank
    customerId - customer ID
    consoleUri - console URL or blank
    """

    numSystems: int
    numLocations: int
    utilizedSizeInBytes: int
    totalSizeInBytes: int
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
        numSystems: int,
        numLocations: int,
        utilizedSizeInBytes: int,
        totalSizeInBytes: int,
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
        self.numSystems = numSystems
        self.numLocations = numLocations
        self.utilizedSizeInBytes = utilizedSizeInBytes
        self.totalSizeInBytes = totalSizeInBytes
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
class SystemsCost:
    """
    Dataclass definition of response body for API /data-observability/v1alpha1/inventory-storage-systems-cost-trend.
    This API fetches the system level cost information.
    This is Dataclass definition of one of the parameter "list of [SystemsCost]" of another Dataclass InventoryStorageSystemsCostTrend
    Content of response body or variables in dataclass:
    month - Specifies the month for which system cost is displayed.
    year - Specifies the year for which system cost is displayed.
    cost - Gives the overall cost of the systems for that particular month.
    currency - Denotes the currency.
    id - unique id required as per rest API
    name - name required as per rest API
    type - type required as per rest API
    generation - generation required as per rest API, by default value will be 1.
    resourceUri -  request URL or blank
    customerId - customer ID
    consoleUri - console URL or blank
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
class InventoryStorageSystemsCostTrend:
    """
    Dataclass definition of response body for API /data-observability/v1alpha1/inventory-storage-systems-cost-trend
    This API fetches the the system level cost information
    Content of response body or variables in dataclass:
    items - Gives the overall monthly systems cost. This parameter is list[SystemsCost] where the list of parameters are defined in another Dataclass MonthlySystemsCost
    count - Specifies the number of items or records to be fetched by the API call
    offset - Specifies the offset/starting index of the item or record to be fetched by the API call
    total - Specifies the total number of items or records
    """

    items: list[SystemsCost]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[SystemsCost], count: int, offset: int, total: int):
        self.items = [SystemsCost(**syscost_items) for syscost_items in items]
        self.count = count
        self.offset = offset
        self.total = total


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Array:

    """
    Dataclass definition of response body for API /data-observability/v1alpha1/inventory-storage-systems
    This API fetches the system and array details.
    This is Dataclass definition of one of the parameter "list of [Array]" of another Dataclass System
    Content of response body or variables in dataclass:
    name - Gives the array name
    id - Gives the array ID
    type - Gives the array type
    cost - Gives the overall cost of the array
    purchaseCost - Purchase cost of the array
    currency - Denotes the currency.
    monthsToDepreciate - Specifies the depreciation duration in months
    boughtAt - Specifies the purchase date
    utilizedSizeInBytes - Gives the overall Space utilized by the array
    totalSizeInBytes - Gives the Total space of the array
    """

    name: str
    id: str
    type: str
    cost: float
    purchaseCost: float
    currency: str
    monthsToDepreciate: int
    boughtAt: datetime
    utilizedSizeInBytes: int
    totalSizeInBytes: int

    def __init__(
        self,
        name: str,
        id: str,
        type: str,
        cost: float,
        purchaseCost: float,
        currency: str,
        monthsToDepreciate: int,
        boughtAt: datetime,
        utilizedSizeInBytes: int,
        totalSizeInBytes: int,
    ):
        self.name = name
        self.id = id
        self.type = type
        self.cost = cost
        self.purchaseCost = purchaseCost
        self.currency = currency
        self.monthsToDepreciate = monthsToDepreciate
        self.boughtAt = boughtAt
        self.utilizedSizeInBytes = utilizedSizeInBytes
        self.totalSizeInBytes = totalSizeInBytes


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class System:
    """
        Dataclass definition of response body for API /data-observability/v1alpha1/inventory-storage-systems
        This API fetches the system and array details.
        This is Dataclass definition of one of the parameter "list of [System]" of another Dataclass InventoryStorageSystems
        Content of response body or variables in dataclass:
        name - Gives the system name
        id - Gives the system ID
        type - Gives the system type
        numArrays - Gives the number of arrays under a system
        pincode - Gives the pincode information where the system is present.
        city - Gives the city information where the system is present.
        state - Gives the state information where the system is present.
        country - Gives the country information where the system is present.
        latitude - Gives the latitude information where the system is present.
        longitude - Gives the longitude information where the system is present.
        utilizedSizeInBytes - Gives the overall Space utilized by their systems
        totalSizeInBytes - Gives the overall Total space of their systems
        cost - Gives the overall cost of the system
    purchaseCost - Purchase cost of the system
        currency - Denotes the currency.
        monthsToDepreciate - Specifies the depreciation duration in months
        boughtAt - Specifies the purchase date
    numVolumes - Specifies the array's volumes count
        numSnapshots - specifies the array's snapshots count
        numClones - specifies the array's clones count
        arrayInfo - Gives the array details. This parameter is list[Array] where the list of parameters are defined in another Dataclass Array
                                if arrayInfo is false return none or else return array details.
        generation - generation required as per rest API, by default value will be 1.
        resourceUri -  request URL or blank
        customerId - customer ID
        consoleUri - console URL or blank
    """

    name: str
    id: str
    type: str
    numArrays: int
    postalCode: str
    city: str
    state: str
    country: str
    latitude: str
    longitude: str
    utilizedSizeInBytes: int
    totalSizeInBytes: int
    utilizedPercentage: int
    cost: float
    purchaseCost: float
    currency: str
    monthsToDepreciate: int
    boughtAt: datetime
    numVolumes: int
    numSnapshots: int
    numClones: int
    arrayInfo: any
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        name: str,
        id: str,
        type: str,
        numArrays: int,
        postalCode: str,
        city: str,
        state: str,
        country: str,
        latitude: str,
        longitude: str,
        utilizedSizeInBytes: int,
        totalSizeInBytes: int,
        utilizedPercentage: int,
        cost: float,
        purchaseCost: float,
        currency: str,
        monthsToDepreciate: int,
        boughtAt: datetime,
        numVolumes: int,
        numSnapshots: int,
        numClones: int,
        arrayInfo: any,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.name = name
        self.id = id
        self.type = type
        self.numArrays = numArrays
        self.postalCode = postalCode
        self.city = city
        self.state = state
        self.country = country
        self.latitude = latitude
        self.longitude = longitude
        self.utilizedSizeInBytes = utilizedSizeInBytes
        self.totalSizeInBytes = totalSizeInBytes
        self.utilizedPercentage = utilizedPercentage
        self.cost = cost
        self.purchaseCost = purchaseCost
        self.currency = currency
        self.monthsToDepreciate = monthsToDepreciate
        self.boughtAt = boughtAt
        self.numVolumes = numVolumes
        self.numSnapshots = numSnapshots
        self.numClones = numClones
        if arrayInfo != None:
            self.arrayInfo = [Array(**array_details) for array_details in arrayInfo]
        else:
            self.arrayInfo = []
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class InventoryStorageSystems:
    """
    Dataclass definition of response body for API /data-observability/v1alpha1/inventory-storage-systems
    This API fetches the system and array details
    Content of response body or variables in dataclass:
    items - Gives the system details. This parameter is list[System] where the list of parameters are defined in another Dataclass System
    count - Specifies the number of items or records to be fetched by the API call
    offset - Specifies the offset/starting index of the item or record to be fetched by the API call
    total - Specifies the total number of items or records
    """

    items: list[System]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[System], count: int, offset: int, total: int):
        self.items = [System(**system_details) for system_details in items]
        self.count = count
        self.offset = offset
        self.total = total


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SubscriptionInfo:
    """
    Dataclass definition of response body for API /data-observability/v1alpha1/inventory-storage-systems/{system-uuid}/product-details
    This API fetches array details for specific system ID
    This is Dataclass definition of one of the parameter "list of [SubscriptionInfo]" of another Dataclass ProductInfo
    Content of response body or variables in dataclass:
    key - Gives the subscription key info
    type - Gives the subscription type info
    tier - Gives the subscription tier info
    startedAt - Gives the subscription start date
    endsAt - Gives the subscription end date
    quantity - Gives the subscription quantity
    availableQuantity - Gives the subscription available quantity
    """

    key: str
    type: str
    tier: str
    startedAt: datetime
    endsAt: datetime
    quantity: str
    availableQuantity: str

    def __init__(
        self,
        key: str,
        type: str,
        tier: str,
        startedAt: datetime,
        endsAt: datetime,
        quantity: str,
        availableQuantity: str,
    ):
        self.key = key
        self.type = type
        self.tier = tier
        self.startedAt = startedAt
        self.endsAt = endsAt
        self.quantity = quantity
        self.availableQuantity = availableQuantity


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class supportCaseInfo:
    productNumber: str
    serialNumber: str
    numPendingCases: int
    numResolvedCases: datetime
    timeStamp: str

    def __init__(
        self, productNumber: str, serialNumber: str, numPendingCases: int, numResolvedCases: datetime, timeStamp: str
    ):
        self.productNumber = productNumber
        self.serialNumber = serialNumber
        self.numPendingCases = numPendingCases
        self.numResolvedCases = numResolvedCases
        self.timeStamp = timeStamp


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class warrantyInfo:
    productNumber: str
    serialNumber: str
    startedAt: datetime
    endsAt: datetime
    status: bool

    def __init__(self, productNumber: str, serialNumber: str, startedAt: datetime, endsAt: datetime, status: bool):
        self.productNumber = productNumber
        self.serialNumber = serialNumber
        self.startedAt = startedAt
        self.endsAt = endsAt
        self.status = status


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProductInfo:
    """
    Dataclass definition of response body for API /data-observability/v1alpha1/inventory-storage-systems/{system-uuid}/product-details
    This API fetches array details for specific system ID
    This is Dataclass definition of one of the parameter "list of [ProductInfo]" of another Dataclass ArrayDetails
    Content of response body or variables in dataclass:
    name - Gives the array name
    id - Gives the array ID
    serialNumber - Product serial number
    deviceType - Product device type
    warrantyInfo - Warranty information of the devices
    subscriptionInfo - Subscriptions information of each device. This parameter is list [SubscriptionInfo] where the list of parameters are defined in another Dataclass SubscriptionInfo
    supportCaseInfo - Provides number of open and closed support cases information about the array
    type - type required as per rest API
    generation - generation required as per rest API, by default value will be 1.
    resourceUri -  request URL or blank
    customerId - customer ID
    consoleUri - console URL or blank
    """

    name: str
    id: str
    serialNumber: str
    deviceType: str
    warrantyInfo: dict
    subscriptionInfo: list[SubscriptionInfo]
    supportCaseInfo: supportCaseInfo
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        name: str,
        id: str,
        serialNumber: str,
        deviceType: str,
        warrantyInfo: warrantyInfo,
        subscriptionInfo: list[SubscriptionInfo],
        supportCaseInfo: supportCaseInfo,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.name = name
        self.id = id
        self.serialNumber = serialNumber
        self.deviceType = deviceType
        self.warrantyInfo = warrantyInfo
        self.subscriptionInfo = [SubscriptionInfo(**subs_info) for subs_info in subscriptionInfo]
        self.supportCaseInfo = supportCaseInfo
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ArrayDetails:
    """
    Dataclass definition of response body for API /data-observability/v1alpha1/inventory-storage-systems/{system-uuid}/product-details
    This API fetches array details for specific system ID
    Content of response body or variables in dataclass:
    items - Gives the array details. This parameter is list[ProductInfo] where the list of parameters are defined in another Dataclass ProductInfo
    count - Specifies the number of items or records to be fetched by the API call
    offset - Specifies the offset/starting index of the item or record to be fetched by the API call
    total - Specifies the total number of items or records
    """

    items: list[ProductInfo]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[ProductInfo], count: int, offset: int, total: int):
        self.items = [ProductInfo(**array_details) for array_details in items]
        self.count = count
        self.offset = offset
        self.total = total
