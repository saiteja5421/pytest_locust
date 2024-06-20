import json
import requests
from requests import Response

from lib.common.common import get, post
from lib.common.users.user import ApiHeader


from lib.dscc.data_panorama.inventory_manager.models.inventory_manager import (
    InventoryStorageSystemsSummary,
    InventoryStorageSystemsCostTrend,
    InventoryStorageSystems,
    ArrayDetails,
)

from tests.e2e.data_panorama.panorama_context_models import PanoramaAPI
from tests.e2e.data_panorama.panorama_context import Context
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps
from tests.e2e.data_panorama.panorama_context import Context


class InventoryManager:
    def __init__(self, context: Context, url: str, api_header: ApiHeader):
        """
            __init__: Constructs all the necessary attributes for the InventoryManager object.

            ---------

            Parameters:

            -----------

                url :- url path eg: http://127.0.0.1:5002/api/v1

                type:- str

                api_header :- authentication header

                type:- str
            Global Variables:

        -----------------

            self.url :- Stores the user passed url
            self.auth_header :- Stores the user authentication header
            self.inventory_storage_systems_summary :- Refers to inventory_storage_systems_summary rest endpoint
            self.inventory_storage_systems_cost_trend :- Refers to inventory_storage_systems_cost_trend rest endpoint
            self.inventory_storage_systems :- Refers to inventory_storage_systems rest endpoint
            self.inventory_storage_systems_config :- Refers to inventory_storage_systems_config rest endpoint

        """
        self.url = url
        self.api_header = api_header
        self.inventory_storage_systems_summary = PanoramaAPI.inventory_storage_systems_summary
        self.inventory_storage_systems_cost_trend = PanoramaAPI.inventory_storage_systems_cost_trend
        self.inventory_storage_systems = PanoramaAPI.inventory_storage_systems
        # inventory-storage-systems-config is post call
        self.inventory_storage_systems_config = PanoramaAPI.inventory_storage_systems_config
        self.commn_steps_obj = PanaromaCommonSteps(context=context)

    def get_inventory_storage_systems_summary(self) -> InventoryStorageSystemsSummary:
        """
        Get request API function to fetch inventory summary details based on the location of a particular customer
                API Request URL Reference: /data-observability/v1alpha1/inventory-storage-systems-summary
                If get response returns success (code: 200) then function will return object of InventoryStorageSystemsSummary
        In Case of failure response (apart from  code: 200) it will return the actual response code.

                Function Arguments: None

                Return:
                if status code 200(OK):-
        response = {
                                "numSystems":7,
                                "numLocations":8,
                                "utilizedSizeInBytes":12629,
                                "totalSizeInBytes":62637,
                                "cost":7450,
                                "currency":"USD"
                "id": "inventory summary-1659182400000",
                "name": "inventory summary-1659182400000",
                "type": "inventory summary",
                "generation": 1,
                "resourceUri": "",
                "customerId": "139e891ffc96a0fc0108f189c7aaaaa"
                "consoleUri": ""
                        }
                else response code :- 400/401/500
        """

        path: str = f"{self.inventory_storage_systems_summary}"
        response: Response = get(self.url, path, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return InventoryStorageSystemsSummary(**json.loads(response.text))

    def get_inventory_storage_systems_cost_trend(self, **params) -> InventoryStorageSystemsCostTrend:
        """
            Get request API function to fetch the system level cost information.
            API Request URL Reference: /data-observability/v1alpha1/inventory-storage-systems-cost-trend
            If get response returns success (code: 200) then function will return object of InventoryStorageSystemsCostTrend
        In Case of failure response (apart from  code: 200) it will return the actual response code.

            params can take the following query parameter as input.
        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments:
            **params :- Required params values will be as mentioned below Ex: {startTime="time/date", endTime="time/date", granularity="hourly|weekly|monthly"}
                        - startTime - (Required) Interval start time.
                                                 - "startTime" parameters should be of RFC3339 format (time/date (format: 2020-11-12T11:45:26.371Z))
                        - endTime - (Required) Interval end time.
                                                 - "endTime" parameters should be of RFC3339 format (time/date (format: 2020-11-12T11:45:26.371Z))
                        - limit - (Optional): limit or pageLimit
                                              - Type: int
                                              - Number of records/items fetched in a rest API call
                                              - Default value for pageLimit is 10 and Maximum "pageLimit" value is 1000
                        - offset - (Optional): offset or pageOffset
                                              - Type: int
                                              - The offset/starting index of the item or record to be fetched by the API call
                                              - Default value for pageOffset is 0.

            Return:
                    if status code 200(OK):-
                response = {
                                                "items":[
                                                            {"year":"2022","month":"Jan","cost":948,"currency":"USD","id":"inventory costtrend-1659182400000","name":"inventory costtrend-1659182400000","type":"inventory costtrend","generation":1,"resourceUri":"","customerId":"139e891ffc96a0fc0108f189c7aaaaa","consoleUri": ""},
                                                            {"year":"2022","month":"Feb","cost":4120,"currency":"USD","id":"inventory costtrend-1659182400000","name":"inventory costtrend-1659182400000","type":"inventory costtrend","generation":1,"resourceUri":"","customerId":"139e891ffc96a0fc0108f189c7aaaaa","consoleUri": ""},
                                                            {"year":"2022","month":"Mar","cost":6635,"currency":"USD","id":"inventory costtrend-1659182400000","name":"inventory costtrend-1659182400000","type":"inventory costtrend","generation":1,"resourceUri":"","customerId":"139e891ffc96a0fc0108f189c7aaaaa","consoleUri": ""}
                                                        ],
                            "pageLimit":10,
                            "pageOffset":0,
                            "total":3
                                            }
                    else response code :- 400/401/500
        """

        path: str = f"{self.inventory_storage_systems_cost_trend}"
        params = self.commn_steps_obj.convert_dict_keys_to_kebab_case(params=params)
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return InventoryStorageSystemsCostTrend(**json.loads(response.text))

    def get_inventory_storage_systems(self, **params) -> InventoryStorageSystems:
        """
            Get request API function to fetch the system and array details
            API Request URL Reference: /data-observability/v1alpha1/inventory-storage-systems
            If get response returns success (code: 200) then function will return object of InventoryStorageSystems
        In Case of failure response (apart from  code: 200) it will return the actual response code.

            params can take the following query parameter as input.
        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be as mentioned below Ex: {arrayInfo = true|false, limit = 50, offset = 51}
                - arrayInfo (Optional): Type 'boolean'
                                                                                Default value of "arrayInfo" parameter is false.
                                                                                If "arrayInfo" is passed true, then along with systems information, corresponding array informations also will be fetched and returned along with response.
                - limit (Optional): limit or pageLimit
                                    - Type 'int'
                                    - Number of records/items fetched in a rest API call
                                                                        - Default value for pageLimit is 10.
                                                                        - Maximum "pageLimit" value is 1000
                - offset (Optional): offset or pageOffset
                                    - Type 'int'
                                    - The offset/starting index of the item or record to be fetched by the API call
                                                                        - Default value for pageOffset is 0.

            Return:
                    if status code OK:-
                response = {"items":[
                {"name":"System-41","id":"61a7589f-b639-4b34-937e-6afeab27663e","type":"HPE Alletra 9000","numArrays":4,"postalCode":"95134","city":"San Jose","state":"CA","country":"United States","longitude":"-71.057083","latitude":"42.361145","utilizedSizeInBytes":9681622249984,"totalSizeInBytes":12129545423360,"cost":11187,"currency":"USD","numSnapshots":10,"numClones":43,
                                                                "arrayInfo":[
                                                                                        {"name":"Array-0","id":"deb755d9-ddb2-4aa1-aea2-343a4d779ca4","type":"HPE Alletra 6000","cost":6494,"currency":"USD","monthsToDepreciate":31,"boughtAt":"2022-03-17T00:00:53.388Z","utilizedSizeInBytes":5298974743552,"totalSizeInBytes":15954883847680},
                                                                                        {"name":"Array-1","id":"afd0bb1e-974b-4eb0-8a33-fee90614f961","type":"HPE Alletra 6000","cost":8983,"currency":"USD","monthsToDepreciate":29,"boughtAt":"2021-09-11T09:20:58.906Z","utilizedSizeInBytes":5298974743552,"totalSizeInBytes":15954883847680}
                                                                                        ],
                                "generation":1,"resourceUri":"","customerId":"139e891ffc96a0fc0108f189c7aaaaa","consoleUri": ""},
                                                                {"name":"System-5","id":"fcdf9854-db8e-45d2-9c3a-894ec381e602","type":"HPE Alletra 9000","numArrays":1,"postalCode":"47162","city":"Boston","state":"MA","country":"United States","longitude":"-73.935242","latitude":"40.73061","utilizedSizeInBytes":1404727740160,"totalSizeInBytes":13401685073920,"cost":5989,"currency":"USD","numSnapshots":9,"numClones":45,
                                                                "arrayInfo":[
                                                                                        {"name":"Array-0","id":"c492f7fd-7815-4c78-8225-523182b8f5b6","type":"HPE Alletra 9000","cost":3865,"currency":"USD","monthsToDepreciate":12,"boughtAt":"2022-01-13T12:39:43.691Z","utilizedSizeInBytes":5298974743552,"totalSizeInBytes":15954883847680}],
                                "generation":1,"resourceUri":"","customerId":"139e891ffc96a0fc0108f189c7aaaaa","consoleUri": ""},
                                        ],
                    "pageLimit": 50,"pageOffset": 0,"total": 2
                    }
                else response code :- 400/401/500

            Note: Above sample response is with 'arrayInfo' set to 'true'.
                  If 'arrayInfo' set to 'false' - "array" details won't be present or Null.
                  For DT-2, arrays are grouped under systems.
                  For DT-1, arrays are not grouped under systems. Arrays are displayed as standalone items.
        """

        path: str = f"{self.inventory_storage_systems}"
        params = PanaromaCommonSteps.convert_dict_keys_to_kebab_case(self, params=params)
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return InventoryStorageSystems(**json.loads(response.text))

    def get_inventory_array_details(self, system_uuid: str, **params) -> ArrayDetails:
        """
            Get request API function to fetch array details for specific system ID
            API Request URL Reference: /data-observability/v1alpha1/inventory-storage-systems/{system-uuid}/array-details
            If get response returns success (code: 200) then function will return object of ArrayDetails
        In Case of failure response (apart from  code: 200) it will return the actual response code.

            params can take the following query parameter as input.
        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments:
                    system_uuid: (Required)- Type 'str'
                                         System Id for which the array details to be fetched

            **params :- Required params values will be as mentioned below Ex: {limit = 5, offset = 6}
                    - limit (Optional): limit or pageLimit
                                        - Type 'int'
                                        - Number of records/items fetched in a rest API call
                                        - Default value for pageLimit is 10.
                                                                            - Maximum "pageLimit" value is 1000
                    - offset (Optional): offset or pageOffset
                                        - Type 'int'
                                        - The offset/starting index of the item or record to be fetched by the API call
                                                                            - Default value for pageOffset is 0.

        Return:
                if status code OK:-
                response = {"items":[
                                                        {"name":"Array-0","id":"95d3c1f6-8bae-4fc7-ab81-9b10f0a6aaed","utilizedSizeInBytes":5298974743552,"totalSizeInBytes":15954883847680,"cost":5244,"currency":"USD","monthsToDepreciate":25,"boughtAt":"2022-01-30T13:46:28.475Z","numSnapshots":10,"numClones":43,"type":"inventory arraydetails","generation":1,"resourceUri":"","customerId":"139e891ffc96a0fc0108f189c7aaaaa","consoleUri": ""},
                                                        {"name":"Array-1","id":"03fb28b2-f0c6-4c55-bb2b-20a54998c61a","utilizedSizeInBytes":5298974743552,"totalSizeInBytes":15954883847680,"cost":5244,"currency":"USD","monthsToDepreciate":29,"boughtAt":"2021-10-30T11:17:58.834Z","numSnapshots":25,"numClones":26,"type":"inventory arraydetails","generation":1,"resourceUri":"","customerId":"139e891ffc96a0fc0108f189c7aaaaa","consoleUri": ""}],
                                        "pageLimit":0,"pageOffset":0,"total":2
                    }
                else response code :- 400/401/500

        """
        product_details: str = "product-details"
        params = self.commn_steps_obj.convert_dict_keys_to_kebab_case(params=params)
        path: str = f"{self.inventory_storage_systems}/{system_uuid}/{product_details}"
        response: Response = get(self.url, path, params=params, headers=self.api_header.authentication_header)
        assert response.status_code == 200, f"API call failed with {response.status_code}"
        return ArrayDetails(**json.loads(response.text))

    def post_inventory_storage_systems_config(self, payload: dict = {}):
        """This function request to set the cost and location details for the array
        It gets payload as the input from the user

        Sample POST request body to insert/update the location and cost:
        {
             "costAndLocationInfo": [{
                                        "systemId": "system1",
                                        "costInfo": [{
                                                        "arrayId": "array1",
                                                        "cost": 500,
                                                        "currency": "INR",
                                                        "depreciationStartDate": 1605181526371,
                                                        "monthsToDepreciate": 1
                                                    }],
                                        "locationInfo": {
                                                            "city": "Bangalore",
                                                            "state": "Karnataka",
                                                            "country": "India",
                                                            "postalCode": "560001"
                                                        }
                                    }, {
                                        "systemId": "system2",
                                        "costInfo": [{
                                                        "arrayId": "system2",
                                                        "cost": 600,
                                                        "currency": "INR",
                                                        "depreciationStartDate": 1636717526371,
                                                        "monthsToDepreciate": 2
                                                    }],
                                        "locationInfo": {
                                                            "city": "Bangalore",
                                                            "state": "Karnataka",
                                                        "country": "India",
                                                         "postalcode": "560001"
                                                        }
                                    }]
        }
        """

        if not payload:
            assert Exception("payload data required")

        path: str = f"{self.inventory_storage_systems_config}"
        response: Response = post(
            self.url,
            path=path,
            json_data=json.dumps(payload),
            headers=self.api_header.authentication_header,
        )
        assert response.status_code == 202, f"API call failed with {response.status_code}"
        return response
