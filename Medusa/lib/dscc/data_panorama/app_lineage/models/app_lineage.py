from datetime import datetime
from dataclasses import dataclass

from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Application:
    """
    The below dataclass is to get the available applications list
        The request URL /data-observability/v1alpha1/applications
    This is a part of dataclass "items"
    Dataclass "Application" has variables below:
        name : name is of string type and it will be endpointname-collectiontime
        id : id is of string type and it is same as name field
        numVolumes is of integer type and it stores volume count for that perticular application
        numSnapshots is of integer type and it stores snapshots count for that volume
        numClones is of integer type and it stores clones count for that volume
        system is str type and it stores system's name
        systemId is str type and it stores Id of system
        type : type is of string type and it is api endpoint
        generation : generation is of int and default value is 1
        resourceUri : resourceUri is of type string  It shows the REST API call
        customerId : str.  It is the customer id for which the application list is retieved
        consoleUri : consoleUri of type string, mandatory field and it will empty for release 1
    """

    name: str
    id: str
    numVolumes: int
    numSnapshots: int
    numClones: int
    system: str
    systemId: str
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        name: str,
        id: str,
        numVolumes: int,
        numSnapshots: int,
        numClones: int,
        system: str,
        systemId: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.name = name
        self.id = id
        self.numVolumes = numVolumes
        self.numSnapshots = numSnapshots
        self.numClones = numClones
        self.system = system
        self.systemId = systemId
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ApplicationList:
    """
    The below dataclass is to fetch all the available applications list
        The request URL is /data-observability/v1alpha1/applications
    This dataclass "ApplicationList" has variable below:
        items : This is list of type class Application which are tagged with volumes
        count : Count is of type integer. This is optional parameter and represents number of records requested as part of API call. Default value for pageLimit is 10. Max limit is 1000.
        offset : Offset is of type int. This is optional parameter. It repesents the starting address of first record. Default value for pageOffset is 0
        total : total is of type int and represents total number of records present( in backend DB)
    """

    items: list[Application]
    count: int
    offset: int
    total = int

    def __init__(self, items: list[Application], count: int, offset: int, total: int):
        self.items = [Application(**app) for app in items]
        self.count = count
        self.offset = offset
        self.total = total


# 2 Below section covers Data models for API /data-observability/v1alpha1/applications/{id}/volumes


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ApplicationVolumesInfo:
    """
    The below dataclass is to get list of volume details for the specific application
        The request URL is /data-observability/v1alpha1/applications/{id}/volumes
    This is a part of dataclass "VolumesDetail"
    Dataclass "ApplicationVolumesInfo" has variables below:
        name is of string type and it stores application name
        id is of string type and it stores application id
        numSnapshots is of integer type and it stores snapshots count for that volume
        numClones is of integer type and it stores clones count for that volume
        utilizedSizeInBytes is of int and it stores total size used
        totalSizeInBytes is of int and it stores total size
        system is of type string and it stores system details
        systemID : systemID of type string and its gives system ID
        country is of type string and it stores country details
        state is of type string and it stores state details
        city is of type string and it stores city details
        postalCode is of type string and it stores postal details
        type : type is of string type and it is api endpoint
        generation : generation is of int and default value is 1
        resourceUri : resourceUri is of type string  It shows the REST API call
        customerId : str.  It is the customer id for which the application list is retieved
        consoleUri : consoleUri of type string, mandatory field and it will empty for release 1.
    """

    name: str
    id: str
    numSnapshots: int
    numClones: int
    utilizedSizeInBytes: int
    totalSizeInBytes: int
    system: str
    systemId: str
    country: str
    state: str
    city: str
    postalCode: str
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        name: str,
        id: str,
        numSnapshots: int,
        numClones: int,
        utilizedSizeInBytes: int,
        totalSizeInBytes: int,
        system: str,
        systemId: str,
        country: str,
        state: str,
        city: str,
        postalCode: str,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.name = name
        self.id = id
        self.numSnapshots = numSnapshots
        self.numClones = numClones
        self.utilizedSizeInBytes = utilizedSizeInBytes
        self.totalSizeInBytes = totalSizeInBytes
        self.system = system
        self.systemId = systemId
        self.country = country
        self.state = state
        self.city = city
        self.postalCode = postalCode
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VolumesDetail:
    """
    The below dataclass is to get list of volume details for the specific application
        The request URL is /data-observability/v1alpha1/applications/{id}/volumes
    This is a part of dataclass "ApplicationVolumesInfo"
    Dataclass "VolumesDetail" has variables below:
        items: items is of list type and it stores details of volume (name, id, numSnapshots, numClones etc)
        count : Count is of type integer. This is optional parameter and represents number of records requested as part of API call. Default value for pageLimit is 10. Max limit is 1000.
        offset : Offset is of type int. This is optional parameter. It repesents the starting address of first record. Default value for pageOffset is 0
        total : total is of type int and represents total number of records present( in backend DB)
    """

    items: list[ApplicationVolumesInfo]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[ApplicationVolumesInfo], count: int, offset: int, total: int):
        self.items = [ApplicationVolumesInfo(**appsnapsinfo) for appsnapsinfo in items]
        self.count = count
        self.offset = offset
        self.total = total


# 3 Below section covers Data Models for API /data-observability/v1alpha1/systems/{system-id}/volumes/{volume-id}/snapshots


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ApplicationSnapshotsInfo:
    """
    The below dataclass is to get list of snapshot details for the specific volume tagged to application
        The request URL is /data-observability/v1alpha1/systems/{system-id}/volumes/{volume-id}/snapshots
    This is a part of dataclass "ApplicationSnapshotDetails"
    Dataclass "ApplicationSnapshotsInfo" has variables below:
        name is of string type and it stores volume name
        id is of string type and it stores volume id
        totalSizeInBytes is of integer type and it stores total size of snapshots in bytes
        createdAt is of datetime type and it stores snapshot creation date
        expiresAt is of datetime type and it stores snapshot expiry date
        type : type is of string type and it is api endpoint
        generation : generation is of int and default value is 1
        resourceUri : resourceUri is of type string  It shows the REST API call
        customerId : str.  It is the customer id for which the application list is retieved
        consoleUri : consoleUri of type string, mandatory field and it will empty for release 1
    """

    name: str
    id: str
    totalSizeInBytes: int
    createdAt: datetime
    expiresAt: datetime
    numClones: int
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        name: str,
        id: str,
        totalSizeInBytes: int,
        createdAt: datetime,
        expiresAt: datetime,
        numClones: int,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.name = name
        self.id = id
        self.totalSizeInBytes = totalSizeInBytes
        self.createdAt = createdAt
        self.expiresAt = expiresAt
        self.numClones = numClones
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SnapshotsDetail:
    """
    The below dataclass is to get list of snapshot details for the specific volume for an application
        The request URL is /data-observability/v1alpha1/systems/{system-id}/volumes/{volume-id}/snapshots
    This is a part of dataclass "ApplicationSnapshotsInfo"
    Dataclass "SnapshotsDetail" has variables below:
        items is of list type and it stores details of snapshots
        count : Count is of type integer. This is optional parameter and represents number of records requested as part of API call. Default value for pageLimit is 10. Max limit is 1000.
        offset : Offset is of type int. This is optional parameter. It repesents the starting address of first record. Default value for pageOffset is 0
        total : total is of type int and represents total number of records present( in backend DB)

    """

    items: list[ApplicationSnapshotsInfo]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[ApplicationSnapshotsInfo], count: int, offset: int, total: int):
        self.items = [ApplicationSnapshotsInfo(**appsnapsinfo) for appsnapsinfo in items]
        self.count = count
        self.offset = offset
        self.total = total


# 4 Below section covers Data Models for API /data-observability/v1alpha1/systems/{system-id}/volumes/{volume-id}/clones


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ApplicationClonesInfo:
    """
    The below dataclass is to get list of clone details for the specific volume for an application
        The request URL is /data-observability/v1alpha1/systems/{system-id}/volumes/{volume-id}/clones
    This is a part of dataclass "ApplicationClonesDetails"
    Dataclass "ApplicationClonesInfo" has variables below:
        name is of string type and it stores volume name
        id is of string type and it stores volume id
        utilizedSizeInBytes is of integer type and it stores utilized size for clones in bytes
        createdAt is of datetime type and it stores clone creation date
        totalSizeInBytes is of integer type and it stores total size for clones in bytes
        type : type is of string type and it is api endpoint
        generation : generation is of int and default value is 1
        resourceUri : resourceUri is of type string  It shows the REST API call
        customerId : str.  It is the customer id for which the application list is retieved
        consoleUri : consoleUri of type string, mandatory field and it will empty for release 1
    """

    name: str
    id: str
    utilizedSizeInBytes: int
    totalSizeInBytes: int
    createdAt: datetime
    numSnapshots: int
    type: str
    generation: int
    resourceUri: str
    customerId: str
    consoleUri: str

    def __init__(
        self,
        name: str,
        id: str,
        utilizedSizeInBytes: int,
        totalSizeInBytes: int,
        createdAt: datetime,
        numSnapshots: int,
        type: str,
        generation: int,
        resourceUri: str,
        customerId: str,
        consoleUri: str,
    ):
        self.name = name
        self.id = id
        self.utilizedSizeInBytes = utilizedSizeInBytes
        self.totalSizeInBytes = totalSizeInBytes
        self.createdAt = createdAt
        self.numSnapshots = numSnapshots
        self.type = type
        self.generation = generation
        self.resourceUri = resourceUri
        self.customerId = customerId
        self.consoleUri = consoleUri


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ClonesDetail:
    """
    The below dataclass is to get list of clone details for the specific volume for an application
        The request URL is /data-observability/v1alpha1/systems/{system-id}/volumes/{volume-id}/clones
    This is a part of dataclass "ApplicationClonesInfo"
    Dataclass "ClonesDetail" has variables below:
        items is of list type and it stores details of clones for specific volume
        count : Count is of type integer. This is optional parameter and represents number of records requested as part of API call. Default value for pageLimit is 10. Max limit is 1000.
        offset : Offset is of type int. This is optional parameter. It repesents the starting address of first record. Default value for pageOffset is 0
        total : total is of type int and represents total number of records present( in backend DB)

    """

    items: list[ApplicationClonesInfo]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[ApplicationClonesInfo], count: int, offset: int, total: int):
        self.items = [ApplicationClonesInfo(**appclonesinfo) for appclonesinfo in items]
        self.count = count
        self.offset = offset
        self.total = total
