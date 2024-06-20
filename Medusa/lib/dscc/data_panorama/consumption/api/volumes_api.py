import json
import requests
from requests import Response
import lib.dscc.data_panorama.data_collector.common.restClient as restClient

from lib.common.common import get
from lib.common.users.user import ApiHeader

# from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps
from tests.e2e.data_panorama.panorama_context import Context

from lib.dscc.data_panorama.consumption.models.volumes import (
    VolumesConsumption,
    VolumesCostTrend,
    VolumesUsageTrend,
    VolumesCreationTrend,
    VolumesActivityTrend,
    VolumeUsageTrend,
    VolumeIoTrend,
    SnapshotCopies,
    CloneCopies,
    VolumeUsage,
)

from tests.e2e.data_panorama.panorama_context_models import PanoramaAPI


class VolumesInfo:
    def __init__(self, url: str, api_header: ApiHeader):
        """
            __init__: Constructs all the necessary attributes for the VolumesInfo object.

            ---------

            Parameters:

            -----------

                url :- url path eg: http://127.0.0.1:5002/api/v1

                type:- str

                auth_header :- authentication header

                type:- str
            Global Variables:

        -----------------

            self.url :- Stores the user passed url
            self.api_header.authentication_header = Stores the user authentication header
            self.volume_consumptions = Refers to Volumes_consumption rest endpoint
            self.volumes_cost_trend = Refers to volumes_cost_trend rest endpoint
            self.volumes_usage_trend = Refers to volumes_usage_trend rest endpoint
            self.volumes_creation_trend = Refers to volumes_creation_trend rest endpoint
            self.volumes_activity_trend = Refers to volumes_activity_trend rest endpoint
            self.volume_usage = Refers to volume_usage rest endpoint
            self.volume_usage_trend = Refers to volume_usage_trend rest endpoint
            self.volume_io_trend = Refers to volume_io_trend rest endpoint
            self.snapshots = Refers to snapshots rest endpoint
            self.clones = Refers to clones rest endpoint
            self.systems = Refers to identifier along with system id
            self.volumes = Refers to identifier along with volume uuid
        """
        self.url = url
        self.api_header = api_header
        self.volumes_consumption = PanoramaAPI.volumes_consumption
        self.volumes_cost_trend = PanoramaAPI.volumes_cost_trend
        self.volumes_usage_trend = "volumes-usage-trend"
        self.volumes_creation_trend = PanoramaAPI.volumes_creation_trend
        self.volumes_activity_trend = PanoramaAPI.volumes_activity_trend
        # Need to pass UUID to get volume usage: /api/v1/volumes-consumption/{volume-uuid}/volume-usage
        self.volume_usage = "volume-usage"
        # Need to pass UUID to get volume usage trend: /api/v1/volumes-consumption/{volume-uuid}/volume-usage-trend
        self.volume_usage_trend = PanoramaAPI.volume_usage_trend
        # Need to pass UUID to get volume IO trend: /api/v1/volumes-consumption/{volume-uuid}/volume-io-trend
        self.volume_io_trend = PanoramaAPI.volume_io_trend
        # Need to pass UUID to get volume replication trend: /api/v1/volumes-consumption/{volume-uuid}/volume-replication-trend
        self.snapshots = PanoramaAPI.snapshots
        self.clones = PanoramaAPI.clones
        self.systems = PanoramaAPI.systems
        self.volumes = PanoramaAPI.application_volumes

        # Create an object of PanaromaCommonSteps to call function "convert_dict_keys_to_kebab_case"
        # self.pcs_obj = PanaromaCommonSteps(context=Context())

    def convert_dict_keys_to_kebab_case(self, params):
        """This function converts keys of the dictionary from Pascal/Camel case to kebab case

        Returns:
            params:  dictionary (keys with kebab case)
        """

        def to_kebab_case(string):
            # Convert the first letter of the string to lowercase
            kebab_string = string[0].lower() + string[1:]
            # Replace any uppercase letters with a hyphen and lowercase letter
            kebab_string = "".join(["-" + i.lower() if i.isupper() else i for i in kebab_string])
            return kebab_string

        kebab_params = {}
        for key, value in params.items():
            kebab_key = to_kebab_case(key)
            kebab_params[kebab_key] = value
        return kebab_params

    def get_volumes_consumption(self) -> VolumesConsumption:
        """
                   This function fetches all the volumes related information
                   The sample response would be like response = {
            "id": "abc",
            "name": "x",
            "type": "a",
            "generation": 1,
            "resourceUri": "url",
            "customerId": "a",
            "consoleUri": ""
            "numVolumes": 10,
            "totalSizeInBytes": 3,
            "utilizedSizeInBytes": 1,
            "cost": 5.2,
            "previousMonthCost": 2.5,
            "previousMonthUtilizedSizeInBytes": 4,
            "currentMonthCost": 4.1,
            "currentMonthUtilizedSizeInBytes": 1.7
        }

        """

        path: str = f"{self.volumes_consumption}"
        response: Response = get(self.url, path, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return VolumesConsumption(**json.loads(response.text))

    def get_volumes_cost_trend(self, **params) -> VolumesCostTrend:
        """
                This function fetches the monthly cost for the volumes created.
                    If get response is success (200) then function will return object of volumescostTrend
                    In Case of failure (apart from 200) it will return the actual response code
        Query parameter should be passed as argument
            startTime(R)
            endTime(R)
            pageLimit(O)
            pageOffset(O)

        Function "convert_dict_keys_to_kebab_case(params)" - converts API query parameters from camel-case(mentioned in test case) to kebab-case format.

        Return:
        if status code OK:-
                response = {
                        "totalVolumesCost": [
                        {"year" : 1987, "month" : 23, "cost" : 100, "currency" : "xyz", "id": "abc",
            "name": "x",
            "type": "a",
            "generation": 1,
            "resourceUri": "url",
            "customerId": "a",
            "consoleUri": ""}
        ],
         "pageLimit":0,"pageOffset":0,"total":2
        }
        else response code :- 400 or 401 or 500
        """
        path: str = f"{self.volumes_cost_trend}"
        kebab_params = self.convert_dict_keys_to_kebab_case(params)
        response: Response = get(self.url, path, params=kebab_params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return VolumesCostTrend(**json.loads(response.text))

    def get_volumes_usage_trend(self, **params) -> VolumesUsageTrend:
        """
                    This function fetches the overall volumes usage data for the specific time intervals
                        If get response is success (200) then function will return object of volumescostTrend
                        In Case of failure (apart from 200) it will return the actual response code
            Query params can take any of the following query parameter
                        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|monthly"
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily
                        - pageLimit - (Optional)- the number of items to be showed in single page
                        - pageOffset- (Optional)- starts displaying from that point

            Function "convert_dict_keys_to_kebab_case(params)" - converts API query parameters from camel-case(mentioned in test case) to kebab-case format.

        Return:
            if status code OK:-
            response = {
                "totalVolumesUsage": [
                {"timeStamp" : "2020-11-11", "totalUsageInBytes" : 100, "id": "abc",
            "name": "x",
            "type": "a",
            "generation": 1,
            "resourceUri": "url",
            "customerId": "a",
            "consoleUri": ""}
            ],
            "pageLimit":0,"pageOffset":0,"total":2,
            }
            else response code :- 400 or 401 or 500
        """
        path: str = f"{self.volumes_usage_trend}"
        kebab_params = self.convert_dict_keys_to_kebab_case(params)
        response: Response = get(self.url, path, params=kebab_params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return VolumesUsageTrend(**json.loads(response.text))

    def get_volumes_creation_trend(self, **params) -> VolumesCreationTrend:
        """
                    This function fetches the volumes created for the specific time intervals
                        If get response is success (200) then function will return object of volumescostTrend
                        In Case of failure (apart from 200) it will return the actual response code
            Query parameters should be passed as arguments - startTime:datetime,endTime:datetime,granularity:str
                        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|monthly"
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily
                        - pageLimit - (Optional)- the number of items to be showed in single page
                        - pageOffset- (Optional)- starts displaying from that point

        Function "convert_dict_keys_to_kebab_case(params)" - converts API query parameters from camel-case(mentioned in test case) to kebab-case format.

        Return:
            if status code OK:-
                Response = {
                    "totalVolumesCreated": [
                    {"timeStamp" : "2020-12-12", "totalVolumeCreated" : 50, "id": "abc",
            "name": "x",
            "type": "a",
            "generation": 1,
            "resourceUri": "url",
            "customerId": "a",
            "consoleUri": ""}
                ],
                "pageLimit":0,"pageOffset":0,"total":2,
             }
            else response code :- 400 or 401 or 500
        """
        path: str = f"{self.volumes_creation_trend}"
        kebab_params = self.convert_dict_keys_to_kebab_case(params)
        response: Response = get(self.url, path, params=kebab_params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return VolumesCreationTrend(**json.loads(response.text))

    def get_volumes_activity_trend(self, **params) -> VolumesActivityTrend:
        """
                    This function fetches all the volumes activity for the specific customer
                        If get response is success (200) then function will return object of volumescostTrend
                        In Case of failure (apart from 200) it will return the actual response code
                        Query parameters should be passed as arguments- provisionType(O):str,minIo(O):float,maxIo(O):float,minVolumeSize(O):int,maxVolumeSize:int,country:str,state:str,city:str,postalCode:str,
                        pageLimit - (Optional)- the number of items to be showed in single page
                        pageOffset- (Optional)- starts displaying from that point

            Function "convert_dict_keys_to_kebab_case(params)" - converts API query parameters from camel-case(mentioned in test case) to kebab-case format.

            The sample response would be like response = {
            "volumeActivityDetails": [
                {"id" : "abc", "name" : "xyz", "provisionType" : "abc", "totalSizeInBytes" : 100, "utilizedSizeInBytes" : 20, "createdAt" : 2021-11-12, "isConnected" : True, "ioActivity" : 23, "array" : "abc", "activityTrendInfo" : [{"timeStamp" : 2021-11-11, "ioActivity" : 30 }],"type": "a",
            "generation": 1,
            "resourceUri": "url",
            "customerId": "a",
            "consoleUri": "" }
          ],
           "pageLimit":0,"pageOffset":0,"total":2,
        }
        """
        path: str = f"{self.volumes_activity_trend}"
        if params["filter"]:
            response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        elif params["sanity"] == True:
            response: Response = restClient.get_all_response(
                params["url"], headers=params["api_header"]._authentication_header, sort_by="name", get_list=False
            )
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return VolumesActivityTrend(**json.loads(response.text))

    def get_volumes_activity_trend_by_size(self, **params) -> VolumesActivityTrend:
        """
                    This function fetches all the volumes activity for the specific customer
                        If get response is success (200) then function will return object of volumescostTrend
                        In Case of failure (apart from 200) it will return the actual response code
                        Query parameters should be passed as arguments- provisionType(O):str,minIo(O):float,maxIo(O):float,minVolumeSize(O):int,maxVolumeSize:int,country:str,state:str,city:str,postalCode:str,
                        pageLimit - (Optional)- the number of items to be showed in single page
                        pageOffset- (Optional)- starts displaying from that point

            Function "convert_dict_keys_to_kebab_case(params)" - converts API query parameters from camel-case(mentioned in test case) to kebab-case format.

            The sample response would be like response = {
            "volumeActivityDetails": [
                {"id" : "abc", "name" : "xyz", "provisionType" : "abc", "totalSizeInBytes" : 100, "utilizedSizeInBytes" : 20, "createdAt" : 2021-11-12, "isConnected" : True, "ioActivity" : 23, "array" : "abc", "activityTrendInfo" : [{"timeStamp" : 2021-11-11, "ioActivity" : 30 }],"type": "a",
            "generation": 1,
            "resourceUri": "url",
            "customerId": "a",
            "consoleUri": "" }
          ],
           "pageLimit":0,"pageOffset":0,"total":2,
        }
        """
        provision_type = params["provisionType"]
        min_size = params["minVolumeSize"]
        max_size = params["maxVolumeSize"]
        path: str = (
            f"{self.volumes_activity_trend}?offset=0&limit=1000&filter=provisionType eq {provision_type} and utilizedSizeInBytes gt {min_size} and utilizedSizeInBytes lt {max_size}"
        )
        print(f"{self.url}/{path}")

        response: Response = get(self.url, path, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return VolumesActivityTrend(**json.loads(response.text))

    def get_volumes_activity_trend_by_io_activity(self, **params) -> VolumesActivityTrend:
        """
                    This function fetches all the volumes activity for the specific customer
                        If get response is success (200) then function will return object of volumescostTrend
                        In Case of failure (apart from 200) it will return the actual response code
                        Query parameters should be passed as filter- filter=provisionType eq {provision_type} and ioActivity gt {min_io} and ioActivity lt {max_io},
                        pageLimit - (Optional)- the number of items to be showed in single page
                        pageOffset- (Optional)- starts displaying from that point



            The sample response would be like response = {
            "volumeActivityDetails": [
                {"id" : "abc", "name" : "xyz", "provisionType" : "abc", "totalSizeInBytes" : 100, "utilizedSizeInBytes" : 20, "createdAt" : 2021-11-12, "isConnected" : True, "ioActivity" : 23, "array" : "abc", "activityTrendInfo" : [{"timeStamp" : 2021-11-11, "ioActivity" : 30 }],"type": "a",
            "generation": 1,
            "resourceUri": "url",
            "customerId": "a",
            "consoleUri": "" }
          ],
           "pageLimit":0,"pageOffset":0,"total":2,
        }
        """
        provision_type = params["provisionType"]
        min_io = params["minIo"]
        max_io = params["maxIo"]
        path: str = (
            f"{self.volumes_activity_trend}?offset=0&limit=1000&filter=provisionType eq {provision_type} and ioActivity gt {min_io} and ioActivity lt {max_io}"
        )
        print(f"{self.url}/{path}")

        response: Response = get(self.url, path, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return VolumesActivityTrend(**json.loads(response.text))

    def get_volume_usage(self, system_id: str, volume_uuid: str) -> VolumeUsage:
        """
                    This function fetches the volumes detail for the individual volumes
                    Path parameter should be passed as arguments- system_id: str, volume_uuid:str
                    'system_id' and 'volume_uuid' are required parameters.
                The sample response would be like response = {
            "createdAt": "12-07-2022",
            "provisionType": "thin",
            "utilizedSizeInBytes": 23,
            "totalSizeInBytes": 34,
            "id": "abc",
            "name": "x",
            "type": "a",
            "generation": 1,
            "resourceUri": "url",
            "customerId": "a",
            "consoleUri": ""
        }

        """
        path: str = (
            f"{self.volumes_consumption}/{self.systems}/{system_id}/{self.volumes}/{volume_uuid}/{self.volume_usage}"
        )
        response: Response = get(self.url, path, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return VolumeUsage(**json.loads(response.text))

    def get_volume_usage_trend(self, **params) -> VolumeUsageTrend:
        """
                    This function fetches the overall individual volume usage data for the specific time intervals
                        If get response is success (200) then function will return object of volumescostTrend
                        In Case of failure (apart from 200) it will return the actual response code
                        Path parameter should be passed as arguments- volume_uuid:str
                        Query params can take any of the following query parameter
                        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|monthly"
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily
                        - pageLimit - (Optional)- the number of items to be showed in single page
                        - pageOffset- (Optional)- starts displaying from that point

        Function "convert_dict_keys_to_kebab_case(params)" - converts API query parameters from camel-case(mentioned in test case) to kebab-case format.

        Return:
            if status code OK:-
                response = {
                "volumeUsageDetails": [
                {"timeStamp" : "2020-11-11 2:43:34", "totalUsageInBytes" : 100, "id": "abc",
            "name": "x",
            "type": "a",
            "generation": 1,
            "resourceUri": "url",
            "customerId": "a",
            "consoleUri": ""}
                ],
                "pageLimit":0,"pageOffset":0,"total":2,
            }
            else response code :- 400 or 401 or 500
        """
        system_id = params["system_id"]
        del params["system_id"]
        volume_uuid = params["volume_uuid"]
        del params["volume_uuid"]
        path: str = (
            f"{self.volumes_consumption}/{self.systems}/{system_id}/{self.volumes}/{volume_uuid}/{self.volume_usage_trend}"
        )
        kebab_params = self.convert_dict_keys_to_kebab_case(params)
        response: Response = get(self.url, path, params=kebab_params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return VolumeUsageTrend(**json.loads(response.text))

    def get_volume_io_trend(self, **params) -> VolumeIoTrend:
        """
                    This function fetches the overall IO activity data for the specific time intervals
                        If get response is success (200) then function will return object of volumescostTrend
                        In Case of failure (apart from 200) it will return the actual response code
                        Path parameter should be passed as arguments- volume_uuid:str
                        Query params can take any of the following query parameter
                        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|monthly"
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily
                        - pageLimit - (Optional)- the number of items to be showed in single page
                        - pageOffset- (Optional)- starts displaying from that point

        Function "convert_dict_keys_to_kebab_case(params)" - converts API query parameters from camel-case(mentioned in test case) to kebab-case format.

        Return:
            if status code OK:
                response = {
                "ioactivityDetails": [
                {"timeStamp" : "2020-11-11 2:43:34", "ioActivity" : 100, "id": "abc",
            "name": "x",
            "type": "a",
            "generation": 1,
            "resourceUri": "url",
            "customerId": "a",
            "consoleUri": ""}
            ],
            "pageLimit":0,"pageOffset":0,"total":2,
            }
            else response code :- 400 or 401 or 500
        """
        system_id = params["system_id"]
        del params["system_id"]
        volume_uuid = params["volume_uuid"]
        del params["volume_uuid"]
        path: str = (
            f"{self.volumes_consumption}/{self.systems}/{system_id}/{self.volumes}/{volume_uuid}/{self.volume_io_trend}"
        )
        kebab_params = self.convert_dict_keys_to_kebab_case(params)
        response: Response = get(self.url, path, params=kebab_params, headers=self.api_header.authentication_header)
        assert (
            response.status_code == 200
        ), f"API call failed with {response.status_code}. full response is {response.text}"
        return VolumeIoTrend(**json.loads(response.text))

    def get_volume_snapshot_copies(self, **params) -> SnapshotCopies:
        """
                    The function fetches the snapshots copies created per volume
                        If get response is success (200) then function will return object of Snapshots
                        In Case of failure (apart from 200) it will return the actual response code
                        Path parameter should be passed as arguments- volume_uuid:str
                        Query params can take any of the following query parameter
                        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|monthly"
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily
                        - pageLimit - (Optional)- the number of items to be showed in single page
                        - pageOffset- (Optional)- starts displaying from that point

        Function "convert_dict_keys_to_kebab_case(params)" - converts API query parameters from camel-case(mentioned in test case) to kebab-case format.

        Return:
            if status code OK:-
                response = {
                "items": [{
                "timeStamp": xx,
                "periodicSnapshotSizeInBytes": "xx",
                "adhocSnapshotSizeInBytes": xx,
                "numPeriodicSnapshots": xx,
                "numAdhocSnapshots": xx,
                "id": "abc",
                "name": "x",
                "type": "a",
                "generation": 1,
                "resourceUri": "url",
                "customerId": "a",
                "consoleUri": ""
                },
            ]},
             "pageLimit":0,"pageOffset":0,"total":2
            }
            else response code :- 400 or 401 or 500
        """
        system_id = params["system_id"]
        del params["system_id"]
        volume_uuid = params["volume_uuid"]
        del params["volume_uuid"]
        path: str = (
            f"{self.volumes_consumption}/{self.systems}/{system_id}/{self.volumes}/{volume_uuid}/{self.snapshots}"
        )
        kebab_params = self.convert_dict_keys_to_kebab_case(params)
        response: Response = get(self.url, path, params=kebab_params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return SnapshotCopies(**json.loads(response.text))

    def get_volume_clone_copies(self, **params) -> CloneCopies:
        """
                    The function fetches the clone copies created per volume
                        If get response is success (200) then function will return object of Clones
                        In Case of failure (apart from 200) it will return the actual response code
                        Path parameter should be passed as arguments- volume_uuid:str
                        Query params can take any of the following query parameter
                        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|monthly"
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily
                        - pageLimit - (Optional)- the number of items to be showed in single page
                        - pageOffset- (Optional)- starts displaying from that point

        Function "convert_dict_keys_to_kebab_case(params)" - converts API query parameters from camel-case(mentioned in test case) to kebab-case format.

        Return:
            if status code OK:-
                response = {
                "items": [{
                "timeStamp": xx,
                "sizeInBytes": "xx",
                "numClones": xx,
                "id": "abc",
                "name": "x",
                "type": "a",
                "generation": 1,
                "resourceUri": "url",
                "customerId": "a",
                "consoleUri": ""
                },
            ]},
             "pageLimit":0,"pageOffset":0,"total":2
            }
            else response code :- 400 or 401 or 500
        """
        system_id = params["system_id"]
        del params["system_id"]
        volume_uuid = params["volume_uuid"]
        del params["volume_uuid"]
        path: str = f"{self.volumes_consumption}/{self.systems}/{system_id}/{self.volumes}/{volume_uuid}/{self.clones}"
        kebab_params = self.convert_dict_keys_to_kebab_case(params)
        response: Response = get(self.url, path, params=kebab_params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return CloneCopies(**json.loads(response.text))
