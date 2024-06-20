import json
import requests
from requests import Response

from lib.common.common import get
from lib.common.users.user import ApiHeader

from lib.dscc.data_panorama.consumption.models.clones import (
    ClonesConsumption,
    ClonesCostTrend,
    ClonesIoTrend,
    ClonesUsageTrend,
    ClonesCreationTrend,
    ClonesActivityTrend,
)

from tests.e2e.data_panorama.panorama_context_models import PanoramaAPI


class ClonesInfo:
    def __init__(self, url: str, api_header: ApiHeader):
        """
         __init__: Constructs all the necessary attributes for the ClonesInfo object.
        ---------
        Parameters:
        -----------
            url :- url path eg: http://127.0.0.1:5002/api/v1
                type:- str
        -----------------
        Global Variables:
        -----------------
            self.url :- Stores the user passed url
            self.auth_header = Stores the user authentication header
            self.clones_consumption = Refers to clones_consumption rest endpoint
            self.clones_cost_trend = Refers to clones_cost_trend rest endpoint
            self.clones_usage_trend = Refers to clones_usage_trend rest endpoint
            self.clones_creation_trend = Refers to clones_creation_trend rest endpoint
            self.clones_activity_trend = Refers to clones_activity_trend rest endpoint
        """
        self.url = url
        self.api_header = api_header
        self.clones_consumption = PanoramaAPI.clones_consumption
        self.clone_io_trend = PanoramaAPI.clone_io_trend
        self.clones_cost_trend = PanoramaAPI.clones_cost_trend
        self.clones_usage_trend = PanoramaAPI.clones_usage_trend
        self.clones_creation_trend = PanoramaAPI.clones_creation_trend
        self.clones_activity_trend = PanoramaAPI.clones_activity_trend

    def convert_params_to_kebab_case(self, params):
        """
        This function converts keys of the dictionary from Pascal/Camel case to kebab case
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

    def get_clones_consumption(self) -> ClonesConsumption:
        """
        GET request API function to fetch all the clones related information for a specific customer id
        API Request URL reference: /api/v1/clones-consumption
        Returns response as ClonesConsumption Dataclass object defined for API '/api/v1/clones-consumption'
        Return:
            if status code 200:-
                response = {
                    "numClones":xx,
                    "totalSizeInBytes":xx,
                    "utilizedSizeInBytes": xx,
                    "cost": xx,
                    "previousMonthTotalCost": xx,
                    "previousMonthUtilizedSpace": xx,
                    "currentMonthTotalCost": xx,
                    "currentMonthUtilizedSpace": xx,
                }
            else response code :- 400/401/500
        Status code definition:
            200	OK
            400	BAD Request
            401	Unauthorized
            500	Internal Server Error
        """
        path: str = f"{self.clones_consumption}"
        response: Response = get(self.url, path, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return ClonesConsumption(**json.loads(response.text))

    def get_clones_cost_trend(self, **params) -> ClonesCostTrend:
        """
        GET request API function to fetch the monthly cost for the clones created
        API Request URL reference: /api/v1/clones-cost-trend
        Arguments
            **params :- Required params values will be as mentioned below Ex: {startTime="time/date", endTime="time/date", granularity="hourly|weekly|monthly"}
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - limit & offset are optional parameters. Default value for pageLimit is 10 and pageOffset is 0. Maximum "pageLimit" value is 1000
        Returns reponse as ClonesConsumption Dataclass object defined for API '/api/v1/clones-cost-trend'
        Return:
            if status code 200:-
                response = {
                        "items": [{
                            "year": "xx",
                            "month": "xx",
                            "cost": xx
                            "currency": xx
                        }],
                        "pageLimit": xx,
                        "pageOffset": xx,
                        "total": xx,
                    }
            else response code :- 400/401/500
        Status code definition:
            200	OK
            400	BAD Request
            401	Unauthorized
            500	Internal Server Error
        """
        path: str = f"{self.clones_cost_trend}"
        params = self.convert_params_to_kebab_case(params)
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return ClonesCostTrend(**json.loads(response.text))

    def get_clones_usage_trend(self, **params) -> ClonesUsageTrend:
        """
        GET request API function to fetch the overall clones usage data for the specific time intervals
        API Request URL reference: /api/v1/clones-usage-trend
        If get response returns success (code: 200) then function will return object of ClonesUsageTrend
            In Case of failure response (apart from  code: 200) it will return the actual response code
                params can take the following query parameter as input.
        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be as mentioned below Ex: {startTime="time/date", endTime="time/date", granularity="hourly|weekly|monthly"}
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily
                        - limit & offset are optional parameters. Default value for pageLimit is 10 and pageOffset is 0. Maximum "pageLimit" value is 1000

        Return:
            if status code 200:-
                response = {
                    "items": [{
                        "timeStamp": xx
                        "totalUsageInBytes": xx
                    }],
                    "pageLimit": xx,
                    "pageOffset": xx,
                    "total": xx,
                }
            else response code :- 400/401/500
        Status code definition:
            200	OK
            400	BAD Request
            401	Unauthorized
            500	Internal Server Error
        """
        path: str = f"{self.clones_usage_trend}"
        params = self.convert_params_to_kebab_case(params)
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return ClonesUsageTrend(**json.loads(response.text))

    def get_clones_creation_trend(self, **params) -> ClonesCreationTrend:
        """
        GET request API function to fetch the clones created for the specific time intervals
        API Request URL reference: /api/v1/clones-creation-trend
        If get response returns success (code: 200) then function will return object of ClonesCreationTrend
            In Case of failure response (apart from  code: 200) it will return the actual response code
                params can take the following query parameter as input.
        During the function call dictionary of the below parameters have to be defined and passed to params

         Arguments
            **params :- Required params values will be as mentioned below Ex: {startTime="time/date", endTime="time/date", granularity="hourly|weekly|monthly"}
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily
                        - limit & offset are optional parameters. Default value for pageLimit is 10 and pageOffset is 0. Maximum "pageLimit" value is 1000

        Return:
            if status code 200:-
                response = {
                    "items": [{
                        "timeStamp": xx
                        "numClones": xx
                    }],
                    "pageLimit": xx,
                    "pageOffset": xx,
                    "total": xx,
                }
            else response code :- 400/401/500
        Status code definition:
            200	OK
            400	BAD Request
            401	Unauthorized
            500	Internal Server Error
        """
        params["limit"] = 1000 if "limit" not in params else params["limit"]
        path: str = f"{self.clones_creation_trend}"
        params = self.convert_params_to_kebab_case(params)
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return ClonesCreationTrend(**json.loads(response.text))

    def get_clones_activity_trend(self, **params) -> ClonesActivityTrend:
        """
        GET request API function to fetch the all the clones activity for the specific customer.
        API Request URL reference: /api/v1/clones-activity-trend
        If get response returns success (code: 200) then function will return object of ClonesActivityTrend
            In Case of failure response (apart from  code: 200) it will return the actual response code
                params can take the following query parameter as input.
        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be as mentioned below Ex: {provisionType="Thin|Thick", minIo="str", maxIo="str", minCloneSize="int", maxCloneSize="int"}
                - provisionType - (Optional)
                - minIo - (Optional)
                - maxIo - (Optional)
                - minCloneSize - (Optional)
                - maxCloneSize - (Optional)
                - limit & offset are optional parameters. Default value for pageLimit is 10 and pageOffset is 0. Maximum "pageLimit" value is 1000

        Return:
            if status code 200:-
                    response = {
                        "items": [{
                            "name": "xx",
                            "provisionType": "xx",
                            "utilizedSizeInBytes": xx,
                            "totalSizeInBytes": xx,
                            "createdAt": xx,
                            "isConnected": xx,
                            "ioActivity": xx
                        }]
                    }
            else response code :- 400/401/500
        Status code definition:
            200	OK
            400	BAD Request
            401	Unauthorized
            500	Internal Server Error
        """

        path: str = f"{self.clones_activity_trend}"
        params = self.convert_params_to_kebab_case(params)
        response: Response = get(self.url, path, params=params["filter"], headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return ClonesActivityTrend(**json.loads(response.text)), json.loads(response.text)

    def get_clones_io_trend(self, **params) -> ClonesIoTrend:
        """
                    This function fetches the overall IO activity data for the specific time intervals
                        If get response is success (200) then function will return object of ClonesIoTrend
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
        clone_id = params["clone_id"]
        del params["clone_id"]

        # data - observability / v1alpha1 / systems
        path: str = f"systems/{system_id}/clones/{clone_id}/{self.clone_io_trend}"
        kebab_params = self.convert_params_to_kebab_case(params)
        response: Response = get(self.url, path, params=kebab_params, headers=self.api_header.authentication_header)
        assert (
            response.status_code == 200
        ), f"API call failed with {response.status_code}. full response is {response.text}"
        return ClonesIoTrend(**json.loads(response.text))
