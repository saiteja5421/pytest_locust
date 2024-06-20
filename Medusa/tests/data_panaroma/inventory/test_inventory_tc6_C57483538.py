"""
Test Case ID C57483538
Test Description - TC6:- Verify Customer able to view array details of a system
"""

# Standard libraries
import logging
import time

from pytest import fixture, mark
from tests.e2e.data_panorama.panorama_context import Context
from lib.dscc.data_panorama.inventory_manager.api.inventory_manager_api import InventoryManager
from lib.dscc.data_panorama.inventory_manager.models.inventory_manager import (
    SubscriptionInfo,
    ProductInfo,
)

# from tests.steps.data_panorama.inventory_manager.inventory_manager_steps import InventoryManagerFunc
# from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from tests.steps.data_panorama.common_methods import get_path_params_by_type

logger = logging.getLogger()


@fixture(scope="session")
def context():
    yield Context()


def get_all_response_inventoryproductdetails(func, system_uuid, **params):
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
    # total = func(system_uuid).total
    result = func(system_uuid=system_uuid)
    total = result.total
    limit = 0
    offset = 0
    dataclass_type = type(result)
    if total != 0:
        if limit != 0:
            rem_items = limit
        else:
            rem_items = total

        # Decide number of function calls required to get the complete set of data keeping 1000 as the maximum value of limit/pagelimit
        params = {}
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
            response_list.append(func(system_uuid=system_uuid))
            # rem_items = rem_items - limit
            offset += limit

        # Get list of parameters present as part of items dictionary
        # Get the variables of class ProductInfo to build dictionary
        # response_params = [
        #    param for param in dir(response_list[0].items[0]) if param not in dir(type(response_list[0].items[0]))
        # ]
        response_params = list(ProductInfo.__dataclass_fields__.keys())
        # Get the variables of class SubscriptionInfo to build dictionary
        # vars = [
        #   vars
        #    for vars in dir(response_list[0].items[0].subscriptionInfo[0])
        #    if vars not in dir(type(response_list[0].items[0].subscriptionInfo[0]))
        # ]
        vars = list(SubscriptionInfo.__dataclass_fields__keys())

        items = []
        for item in response_list:
            for val in item.items:
                temp_dict = {}
                for param in response_params:
                    if param != "subscriptionInfo":
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
        # response_obj = type(response_list[0])(**response_dict)
        response_obj = dataclass_type(**response_dict)
        return response_obj


@mark.skip
@mark.order(4030)
def test_inventory_tc6_C57483538(context: context):
    logger.info("Start of test case")
    logger.info("PQA Testing -> Inventory -> TC6_C57483538")

    """
    To verify Customer is able to view array details of a system 
       
    Test parameters:
    List of parameters that needs to be updated before execution.
    data_set        : dict      - dictionary of array used for execution and corresponding configuration
    array_obj_list  : list      - list to hold objects returned from ArrayConfigParser method
    url             : str       - REST API url
    limit           : int       - number of volumes to be showed in single page
    offset          : int       - page offset
    
    """

    """
    TO-DO : Expected data or Knowme
    """
    # Function call to add/modify JSON files
    # tc_inventory_storage_systems_exp = get_inventory_storage_systems(arrayInfo = tp_arrayinfo)

    # Create an instance of Panaroma Common Steps class
    # tc_pcs = PanaromaCommonSteps(context=context)
    # To-Do: Function needs to be revisited, Need details of arguments to be passed

    # Create an instance of Array Config Parser class
    tc_acs = ArrayConfigParser(context=context)

    """
    API call to get the actual values
    """

    inventory_systems = InventoryManager(context, context.cluster.panorama_url, context.api_header)
    db_name = "/workspaces/qa_automation/Medusa/tests/e2e/data_panorama/mock_data_generate/golden_db/ccs_pqa/mock_30_days.sqlite"
    # db_name = "/workspaces/qa_automation/Medusa/tests/data_panaroma/test.sqlite"
    type = "inventory"
    path_param = get_path_params_by_type(db_name=db_name, type=type)
    print("PATH PARAMS:", path_param)
    # Fetching sysytem ID details from common function path -tests.steps.data_panorama.inventory_manager.inventory_manager_steps import InventoryManagerFunc
    # To-DO: Change this to system id list from generator script once info available
    system_ids_app_list = [path_param["storagesysid"]]

    # system_ids_app_list = system_info.get_systemids()

    # Validation of all array details for all system IDs
    for sys_id in system_ids_app_list:
        tc_inventory_product_details_expected = get_all_response_inventoryproductdetails(
            tc_acs.get_inventory_product_details, system_uuid=sys_id
        )
        api_inventory_product_details = get_all_response_inventoryproductdetails(
            inventory_systems.get_inventory_array_details, system_uuid=sys_id
        )

        """
        Verification steps
        """
        # Get the variables of class System for comparison
        # params = [param for param in dir(api_inventory_product_details.items[0]) if param not in dir(ProductInfo)]
        params = list(ProductInfo.__dataclass_fields__keys())
        ignore_param = ["type", "generation", "resourceUri", "consoleUri"]
        check_param = [element for element in params if element not in ignore_param]

        # Get the variables of class ArrayCost for comparison
        # vars = [
        #    param
        #    for param in dir(api_inventory_product_details.items[0].subscriptionInfo[0])
        #    if param not in dir(SubscriptionInfo)
        # ]
        vars = list(SubscriptionInfo.__dataclass_fields__keys())

        # Compare value of each items/variables
        # assert len(api_inventory_product_details.items) == len(tc_inventory_product_details_expected.items), f"Numbers of records in API response and Expected data doesn't match"
        assert (
            api_inventory_product_details.total == tc_inventory_product_details_expected.total
        ), f"Numbers of records in API response and Expected data doesn't match"

        for api_items in api_inventory_product_details.items:
            product_match = 0
            for exp_items in tc_inventory_product_details_expected.items:
                if api_items.id == exp_items.id:
                    for param in check_param:
                        if param != "subscriptionInfo":
                            assert api_items.__getattribute__(param) == exp_items.__getattribute__(
                                param
                            ), f"Device parameter {param} of API: {api_items.__getattribute__(param)} and Expected Data: {exp_items.__getattribute__(param)} doesn't match"
                        else:
                            assert len(api_items.__getattribute__(param)) == len(
                                exp_items.__getattribute__(param)
                            ), f"Number of subscriptions for device with ID {api_items.id} doesn't match"
                            for api_arrayitems in api_items.__getattribute__(param):
                                subscription_match = 0
                                for exp_arrayitems in exp_items.__getattribute__(param):
                                    if api_arrayitems.key == exp_arrayitems.key:
                                        for var in vars:
                                            assert api_arrayitems.__getattribute__(
                                                var
                                            ) == exp_arrayitems.__getattribute__(
                                                var
                                            ), f"subscription details parameter {var} of API: {api_arrayitems.__getattribute__(var)} and Expected data: {exp_arrayitems.__getattribute__(var)} doesn't match"
                                        subscription_match = 1
                                        break
                                assert (
                                    subscription_match == 1
                                ), f"Subscription: With key {api_arrayitems.key} in API response not present in Expected data"
                    product_match = 1
                    break
            assert product_match == 1, f"Device: With ID {api_items.id} in API response not present in Expected data"

    logger.info("Test completed succesfully")
