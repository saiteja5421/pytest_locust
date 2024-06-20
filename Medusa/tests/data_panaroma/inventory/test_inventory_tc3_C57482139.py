"""
Test Case ID C57482139
Test Description - TC3:- Verify Customer able to view their systems and arrays details
"""

# Standard libraries
from datetime import datetime
import logging
import time
from pytest import mark, fixture

# Internal libraries
from lib.dscc.data_panorama.inventory_manager.api.inventory_manager_api import InventoryManager
from lib.dscc.data_panorama.inventory_manager.models.inventory_manager import System, Array

# Steps
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser

# Tests
from tests.e2e.data_panorama.panorama_context import Context

logger = logging.getLogger()


@fixture(scope="session")
def context():
    test_context = Context()
    yield test_context


def get_all_response_inventorysystem(func, limit=0, offset=0, **params):
    """
    Function to calculate and trigger multiple API/Array calls based on limit and offset where response will have list within list.
    Collected response will be unified into single dictionary and converted to corresponding Class object.
    Arguments:
        func        (R) - Variable to recieve array or API methods and reused
        limit: int  (O) - Limit =0, means retreive all the records. Value passed to limit, means retreive number of records equal to value passed.
        offset: int (O) - Default value of pageOffset is 0. Determines from which offset the data should be read from table.
        params:     (O) - set of query parameters required for func()

    """
    response_list = []
    items = []

    # Get total items using default api call
    result = func(**params)
    total = result.total
    dataclass_type = type(result)
    if total != 0:
        if limit != 0:
            rem_items = limit
        else:
            rem_items = total

        # Decide number of function calls required to get the complete set of data keeping 1000 as the maximum value of limit/pagelimit
        while rem_items:
            if rem_items > 1000:
                limit = 1000
                rem_items = rem_items - limit
            elif rem_items < 10:
                limit = 10
                rem_items = 0
            else:
                limit = rem_items
                rem_items = rem_items - limit
            params["limit"] = limit
            params["offset"] = offset
            response_list.append(func(**params))
            offset += limit

        # Get list of parameters present as part of items dictionary
        # Get the variables of class VolumeActivity to build dictionary
        # response_params = [param for param in dir(response_list[0].items[0]) if param not in dir(type(response_list[0].items[0]))]
        response_params = list(System.__dataclass_fields__.keys())
        # Get the variables of class ActivityTrendDetail to build dictionary
        # vars = [vars for vars in dir(response_list[0].items[0].arrayInfo[0]) if vars not in dir(type(response_list[0].items[0].arrayInfo[0]))]
        vars = list(Array.__dataclass_fields__.keys())

        items = []
        for item in response_list:
            for val in item.items:
                temp_dict = {}
                for param in response_params:
                    if param != "arrayInfo":
                        temp_dict[param] = val.__getattribute__(param)
                    else:
                        activity_list = []
                        for iter in val.__getattribute__(param):
                            activity_dict = {}
                            for var in vars:
                                activity_dict[var] = iter.__getattribute__(var)
                            activity_list.append(activity_dict)
                        temp_dict[param] = activity_list
                items.append(temp_dict)

    # Compose dictionary by combining multiple response object
    response_dict = {"items": items, "count": 10, "offset": 0, "total": total}

    # Convert the dictionary to object using models and return the object.
    response_obj = dataclass_type(**response_dict)
    return response_obj


@mark.skip(reason="Blocked - Require new mock data")
@mark.order(4015)
def test_inventory_tc3_C57482139(context: context):
    logger.info("Start of test case")
    logger.info("PQA Testing -> Inventory -> TC3_C57482139")
    """
    Define the path and filter parameters used in test case to be passed in API call
    Test case provides the system and array details of the customer.
    Parameters:
                - arrayInfo (Optional): Type 'boolean'
										Default value of "arrayInfo" parameter is false. 
										If "arrayInfo" is passed true, then along with systems information, corresponding array informations also will be fetched and returned along with response.
                - limit (Optional): Type 'int'
									Default value for pageLimit is 10.
									Maximum "pageLimit" value is 1000
                - offset (Optional): Type 'int'
									 Default value for pageOffset is 0.
    """
    tp_arrayinfo: bool = True

    # Create an instance of Array Config Parser class
    tc_acs = ArrayConfigParser(context=context)
    tc_inventory_storage_systems_expected = tc_acs.get_inventory_storage_systems(arrayInfo=tp_arrayinfo)
    print(tc_inventory_storage_systems_expected)

    # API call to get the actual values
    inventory_systems = InventoryManager(
        context=context, url=context.cluster.panorama_url, api_header=context.api_header
    )
    api_inventory_storage_systems = get_all_response_inventorysystem(
        inventory_systems.get_inventory_storage_systems, arrayInfo=tp_arrayinfo
    )
    # api_inventory_storage_systems = get_all_response_inventorysystem(inventory_systems.get_inventory_storage_systems)

    """
    Verification steps
    """
    # Build list of parameters of data class System
    # params = [param for param in dir(api_inventory_storage_systems.items[0]) if param not in dir(System)]
    params = list(System.__dataclass_fields__.keys())
    # Define list of common parameters for which verification need to be skipped
    ignore_param = [
        "generation",
        "resourceUri",
        "consoleUri",
    ]
    # Build list of final parameters to be used for verification
    check_param = [element for element in params if element not in ignore_param]

    # Get the variables of class ArrayCost for comparison
    # vars = [param for param in dir(api_inventory_storage_systems.items[0].arrayInfo[0]) if param not in dir(Array)]
    vars = list(Array.__dataclass_fields__.keys())

    # Compare value of each items/variables
    # Assert if the total number of items in API response and Array config data doesn't match
    assert (
        api_inventory_storage_systems.total == tc_inventory_storage_systems_expected.total
    ), f"Numbers of records in API response and Expected data doesn't match"

    """
    Iterate through each item of Array config data (mock data) and API response.
    Compare based on the ID value.
    If it matches, then compare remaining paramteres (expect common fields) values of both Array config data (mock data) and API response for that particular item.
    Flag "system_match" will help to capture those records present in one data set(Mock/API) and not in another data set(API/Mock).
    During verification if the parameter to compare is "arrayinfo" which is again a list of parameters, loop through each parameters with the list(reference 'else' block)
    Flag "array_match" will help to capture those records of 'arrayinfo' present in one data set(Mock/API) and not in another data set(API/Mock).
    """

    for api_item in api_inventory_storage_systems.items:
        system_match = 0
        for array_item in tc_inventory_storage_systems_expected.items:
            if api_item.id == array_item.id:
                for param in check_param:
                    if param != "arrayInfo":
                        assert api_item.__getattribute__(param) == array_item.__getattribute__(
                            param
                        ), f"System details parameter {param} of API: {api_item.__getattribute__(param)} and Expected Data: {array_item.__getattribute__(param)} doesn't match"
                    else:
                        assert len(api_item.__getattribute__(param)) == len(
                            array_item.__getattribute__(param)
                        ), f"Number of Arrays for system with ID {api_item.id} doesn't match"
                        for api_arrayitem in api_item.__getattribute__(param):
                            array_match = 0
                            for expected_arrayitem in array_item.__getattribute__(param):
                                if api_arrayitem.id == expected_arrayitem.id:
                                    for var in vars:
                                        assert api_arrayitem.__getattribute__(
                                            var
                                        ) == expected_arrayitem.__getattribute__(
                                            var
                                        ), f"Array details parameter {var} of API: {api_arrayitem.__getattribute__(var)} and Expected data: {expected_arrayitem.__getattribute__(var)} doesn't match"
                                    array_match = 1
                                    break
                            assert (
                                array_match == 1
                            ), f"Array: With ID {api_arrayitem.id} in API response not present in Expected data"
                system_match = 1
                break
        assert system_match == 1, f"System: With ID {api_item.id} in API response not present in Expected data"
    logger.info("Test completed successfully")
