import requests
from requests import Response, codes
import json
from lib.common.common import get
from lib.common.users.user import ApiHeader

# For post, patch, delete
from lib.dscc.data_panorama.consumption.models.snapshots import (
    SnapshotConsumption,
    SnapshotCostTrend,
    SnapshotUsageTrend,
    SnapshotCreationTrend,
    SnapshotAgeTrend,
    SnapshotRetentionTrend,
    Snapshots,
)
from tests.e2e.data_panorama.panorama_context_models import PanoramaAPI
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps


class SnapshotsInfo:
    def __init__(self, url: str, api_header: ApiHeader):
        """
         __init__: Constructs all the necessary attributes for the SnapshotsInfo object.
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
            self.snapshots_consumption = Refers to snapshot consumption rest endpoint
            self.snapshots_cost_trend = Refers to snapshot cost trend rest endpoint
            self.snapshots_usage_trend = Refers to snapshot usage trend rest endpoint
            self.snapshots_creation_trend = Refers to snapshot creation trend rest endpoint
            self.snapshots_age_trend = Refers to snapshot age trend rest endpoint
            self.snapshots_retention_trend = Refers to snapshot retention trend rest endpoint
        """
        self.url = url
        self.api_header = api_header
        self.snapshots_consumption = PanoramaAPI.snapshots_consumption
        self.snapshots_cost_trend = PanoramaAPI.snapshots_cost_trend
        self.snapshots_usage_trend = PanoramaAPI.snapshots_usage_trend
        self.snapshots_creation_trend = PanoramaAPI.snapshots_creation_trend
        self.snapshots_age_trend = PanoramaAPI.snapshots_age_trend
        self.snapshots_retention_trend = PanoramaAPI.snapshots_retention_trend
        self.snapshots_details = PanoramaAPI.snapshots_details

    def get_snapshot_consumption(self) -> SnapshotConsumption:
        """
        GET request to fetch all the snapshots related information for a specific customer id
        API Request URL reference: /data-observability/v1alpha1/snapshots-consumption
        Returns response as SnapshotConsumption Dataclass object defined for API 'snapshots-consumption'

        Return:
                response = {
                                "numSnapshots":xx,
                                "totalSizeInBytes":xx,
                                "cost": xx,
                                "previousMonthCost": xx,
                                "currentMonthCost": xx
                            }
        """
        path: str = f"{self.snapshots_consumption}"
        response: Response = get(self.url, path, headers=self.api_header.authentication_header)
        assert response.status_code == codes.ok, f"API call failed with {response.status_code}"
        return SnapshotConsumption(**json.loads(response.text))

    def get_snapshots_cost_trend(self, **params) -> SnapshotCostTrend:
        """
        GET request to fetch the monthly cost for the snapshots created
        API Request URL reference: /data-observability/v1alpha1/snapshots-cost-trend
        Returns response as SnapshotCostTrend Dataclass object defined for API 'snapshots-cost-trend'
        Arguments
            : startTime (R)	time/date parameters should be of RFC3339 time format
            : endTime (R)	time/date parameters should be of RFC3339 time format
            : limit & offset are optional parameters. Default value for pageLimit is 10 and pageOffset is 0. Maximum "pageLimit" value is 1000

        Return:
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
        """
        path: str = f"{self.snapshots_cost_trend}"
        params = PanaromaCommonSteps.convert_dict_keys_to_kebab_case(self, params=params)
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == codes.ok, f"API call failed with {response.status_code}"
        return SnapshotCostTrend(**json.loads(response.text))

    def get_snapshots_usage_trend(self, **params) -> SnapshotUsageTrend:
        """
        GET request to fetch the overall snapshots usage data for the specific time intervals
        API Request URL reference: /data-observability/v1alpha1/snapshots-usage-trend
        Returns response as SnapshotAgeTrend Dataclass object defined for API  'snapshots-usage-trend'
        Params can take the following query parameter as input.
        During the function call dictionary of the below parameters have to be defined and passed to params
        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|monthly"

                - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format.If difference between startTime and endTime is less than or equal to 7 days → collectionHour granularity. If difference between startTime and endTime is greater than 6 months → week granularity
                - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format. If difference between startTime and endTime is greater than 7 days and less than or equal to 6 months → day granularity
                - granularity - (Optional) Allowed values for "granularity" parameter are collection Hour, day and week. If passed as empty, then the granularity is calculated based on the below conditions. Default value will be daily
                - limit & offset are optional parameters. Default value for pageLimit is 10 and pageOffset is 0. Maximum "pageLimit" value is 1000
        Return:
                response = {
                                "items": [{
                                    "timeStamp": xx
                                    "totalUsageInBytes": xx
                                }],
                            "pageLimit": xx,
                            "pageOffset": xx,
                            "total": xx,
                            }
        """
        path: str = f"{self.snapshots_usage_trend}"
        params = PanaromaCommonSteps.convert_dict_keys_to_kebab_case(self, params=params)
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == codes.ok, f"API call failed with {response.status_code}"
        return SnapshotUsageTrend(**json.loads(response.text))

    def get_snapshots_creation_trend(self, **params) -> SnapshotCreationTrend:
        """
        GET request to fetch the snapshots created for the specific time intervals
        API Request URL reference: /data-observability/v1alpha1/snapshots-creation-trend
        Returns response as SnapshotCreationTrend Dataclass object defined for API  'snapshots-creation-trend'

        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|monthly"

                - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily
                - limit & offset are optional parameters. Default value for pageLimit is 10 and pageOffset is 0. Maximum "pageLimit" value is 1000
        Return:
                response = {
                                "items": [{
                                    "timeStamp": xx
                                    "numAdhocSnapshots": xx
                                    "numPeriodicSnapshots": xx
                                }],
                                "pageLimit": xx,
                                "pageOffset": xx,
                                "total": xx,
                            }
        """
        path: str = f"{self.snapshots_creation_trend}"
        params = PanaromaCommonSteps.convert_dict_keys_to_kebab_case(self, params=params)
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == codes.ok, f"API call failed with {response.status_code}"
        return SnapshotCreationTrend(**json.loads(response.text))

    def get_snapshots_age_trend(self, **params) -> SnapshotAgeTrend:
        """
        GET request to fetch the snapshots age size related information for the specific time intervals
        API Request URL reference: /data-observability/v1alpha1/snapshots-age-trend
        Returns response as SnapshotAgeTrend Dataclass object defined for API  'snapshots-age-trend'

        Arguments
            - limit & offset are optional parameters. Default value for pageLimit is 10 and pageOffset is 0. Maximum "pageLimit" value is 1000

        Return:
                response =
                            {
                                "items": [{
                                    "age": "xx-xx",
                                    "bucket": xx,
                                    "sizeInfo": [{
                                        "numSnapshots": xx,
                                    }]
                                }],
                                "pageLimit": xx,
                                "pageOffset": xx,
                                "total": xx,
                            }
        """
        path: str = f"{self.snapshots_age_trend}"
        params = PanaromaCommonSteps.convert_dict_keys_to_kebab_case(self,params=params)
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == codes.ok, f"API call failed with {response.status_code}"
        return SnapshotAgeTrend(**json.loads(response.text))

    def get_snapshots_retention_trend(self, **params) -> SnapshotRetentionTrend:
        """
        GET request to fetch the snapshots retention related information for the specific time intervals
        API Request URL reference: /data-observability/v1alpha1/snapshots-retention-trend
        Returns response as SnapshotRetentionTrend Dataclass object defined for API 'snapshots-retention-trend'

        Arguments
            - limit & offset are optional parameters. Default value for pageLimit is 10 and pageOffset is 0. Maximum "pageLimit" value is 1000

        Return:
                response = {
                                "items": [{
                                    "range": "xx-yy",
                                    "numPeriodicSnapshots": xx,
                                    "numAdhocSnapshots": xx,
                                }],
                                "pageLimit": xx,
                                "pageOffset": xx,
                                "total": xx,
                            }
        """
        path: str = f"{self.snapshots_retention_trend}"
        params = PanaromaCommonSteps.convert_dict_keys_to_kebab_case(self, params=params)
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == codes.ok, f"API call failed with {response.status_code}"
        return SnapshotRetentionTrend(**json.loads(response.text))

    def get_snapshots_details(self, **params) -> Snapshots:
        """
        GET request to fetch the snapshots related information .
        If get response is success  then function will return object of Snapshots
        In Case of failure it will return the actual response code
        API Request URL reference: /data-observability/v1alpha1/snapshots
        Returns response as Snapshotdetails Dataclass object defined for API 'snapshots'

        Arguments
            - filter (O) is optional parameter
            The filter query parameter is used to filter the set of resources returned in the response. The returned set of resources must match the criteria in the filter query parameter.
            A comparison compares a property name to a literal. The comparisons supported are the following:
            “eq” : Is a property equal to value. Valid for number, boolean and string properties.
            “ne” : Is a property not equal to value. Valid for number, boolean and string properties.
            “gt” : Is a property greater than a value. Valid for number or string timestamp properties.
            “lt” : Is a property less than a value. Valid for number or string timestamp properties
            Filters are supported on following attributes:
            createdAt (Supported filters: eq, gt, lt), volumeSizeInBytes (Supported filters: eq, gt, lt), aggregateSizeInBytes (Supported filters: eq, gt, lt), isAdhoc (Supported filters: eq, ne), retainedUntil (Supported filters: eq, gt, lt)

            Searching is supported on following attributes:
            name (Supported filters: contains, not contains),volumeName (Supported filters: contains, not contains),system (Supported filters: contains, not contains)

            - sort(O) The sort query parameter supports a comma separated list of properties to sort by, followed by a direction indicator ("asc" or "desc"). If no direction indicator is specified the default order is ascending.
            Sorts are supported on following attributes:
            name, createdAt, volumeName, aggregateSizeInBytes, volumeSizeInBytes
            - limit & offset are optional parameters. Default value for pageLimit is 10 and pageOffset is 0. Maximum "pageLimit" value is 1000

        Return:
                response = {
                                "items": [{
                                    "name": "xx",
                                    "aggregateSizeInBytes": xx,
                                    "volumeName": "xx",
                                    "volumeSizeInBytes": xx,
                                    "createdAt": xx,
                                    "system": xx,
                                    "systemId": xx,
                                    "retainedUntil": xx,
                                    "isAdhoc": xx,
                            }],
                                "offset":xx,
                                "count":xx ,
                                "total": xx
                            }
        """
        # Get filter and sort query parameter
        filter = self.get_filter(params)
        sort = self.get_sort_string(params)
        # constructing url with filter and sort parameter
        path: str = f"{self.snapshots_details}?sort={sort}&filter={filter}&"
        params = PanaromaCommonSteps.convert_dict_keys_to_kebab_case(self, params=params)
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == codes.ok, f"API call failed with {response.status_code}"
        return Snapshots(**json.loads(response.text))

    def get_sort_string(self, params):
        if "sort" not in params:
            # default value if no sort parameter  metioned
            sort = ""
        else:
            # sort parameter passed as parameter
            sort = params["sort"]
            # Need to remove as its passed in url path and get_all_response will send other parameter via test case
            params.pop("sort")
        return sort

    def get_filter(self, params):
        if "filter" not in params:
            # default value if no sort parameter  metioned
            filter = ""
        else:
            # sort parameter passed as parameter
            filter = params["filter"]
            # Need to remove as its passed in url path and get_all_response will send other parameter via test case
            params.pop("filter")
        return filter
