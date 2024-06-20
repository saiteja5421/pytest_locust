"""
Test Case ID C57482002
Test Description - TC4:- Verify Customer able to add cost/location information of arrays
"""

# Internal libraries
from lib.dscc.data_panorama.inventory_manager.models.inventory_manager import InventoryStorageSystems
from lib.dscc.data_panorama.inventory_manager.api.inventory_manager_api import InventoryManager
from tests.steps.data_panorama.inventory_manager.inventory_manager_steps import InventoryManagerFunc
from pytest import mark, fixture
from datetime import datetime
import logging
import time

# Steps
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps

# Tests
from tests.e2e.data_panorama.panorama_context import Context

"""
--------------------------------------------------------------------------------------------------------------------------------
Note: Before executing the test case define the payload as appropriately
1) data_location - Case1: Adding only location details to a system
2) data_cost - Case2: Adding only cost details to an array
3) data_costlocation - Case3: Adding both location details of a system and cost details of arrays belonging to that system
--------------------------------------------------------------------------------------------------------------------------------
"""

"""
Case1: Adding only location details to the system
Input dictionary (data_location) to be passed as payload for the post call to update system location details
Create a payload with both the below mentioned conditions.
	a) create a new location and assign it to the system 
			- have location details such that customer doesn't have any systems in that location.
	b) from the existing location assign it to the system 
			- have location details such that customer already have systems in that location
Sample input format (data_location) mentioned below, edit as necessary before test.
"""
data_location = {
    "costAndLocationInfo": [
        {
            "systemId": "system1",
            "locationInfo": {"city": "Bangalore", "state": "Karnataka", "country": "India", "postalCode": "560001"},
        },
        {
            "systemId": "system2",
            "locationInfo": {"city": "Bangalore", "state": "Karnataka", "country": "India", "postalCode": "560001"},
        },
    ]
}

"""
Case2: Adding only cost details to an array
Input dictionary (data_cost) to be passed as payload for the post call to update array cost details
Create a payload with all the mandatory parameters
Sample input format (data_cost) mentioned below, edit as necessary before test.
"""
data_cost = {
    "costAndLocationInfo": [
        {
            "systemId": "system1",
            "costInfo": [
                {
                    "arrayId": "array1",
                    "cost": 500,
                    "currencyType": "INR",
                    "depreciationStartDate": 1605181526371,
                    "monthsToDepreciate": 1,
                },
                {
                    "arrayId": "array2",
                    "cost": 500,
                    "currencyType": "INR",
                    "depreciationStartDate": 1605181526371,
                    "monthsToDepreciate": 1,
                },
            ],
        },
        {
            "systemId": "system2",
            "costInfo": [
                {
                    "arrayId": "system2",
                    "cost": 600,
                    "currencyType": "INR",
                    "depreciationStartDate": 1636717526371,
                    "monthsToDepreciate": 2,
                }
            ],
        },
    ]
}

"""
Case3: Adding both location details of a system and cost details of arrays belonging to that system.
Input dictionary (data_costlocation) to be passed as payload for the post call to update system location and array cost details.
Create a payload to update location and cost at the same time with all the below mentioned conditions.
For location,
	a) create a new location and assign it to the system 
			- have location details such that customer doesn't have any systems in that location.
	b) from the existing location assign it to the system 
			- have location details such that customer already have systems in that location
For cost,
	a) add cost details to an array - define all the mandatory parameters
Sample input format (data_costlocation) mentioned below, edit as necessary before test.
"""
data_costlocation = {
    "costAndLocationInfo": [
        {
            "systemId": "61a7589f-b639-4b34-937e-6afeab27663e",
            "costInfo": [
                {
                    "arrayId": "array1",
                    "cost": 500,
                    "currencyType": "INR",
                    "depreciationStartDate": 1605181526371,
                    "monthsToDepreciate": 1,
                },
                {
                    "arrayId": "array2",
                    "cost": 700,
                    "currencyType": "INR",
                    "depreciationStartDate": 1605181526371,
                    "monthsToDepreciate": 1,
                },
            ],
            "locationInfo": {"city": "Bangalore", "state": "Karnataka", "country": "India", "postalCode": "560001"},
        },
        {
            "systemId": "system2",
            "costInfo": [
                {
                    "arrayId": "array3",
                    "cost": 600,
                    "currencyType": "INR",
                    "depreciationStartDate": 1636717526371,
                    "monthsToDepreciate": 2,
                }
            ],
            "locationInfo": {"city": "Pune", "state": "Mumbai", "country": "Bharath", "postalCode": "460001"},
        },
    ]
}

"""
----------------------------------------------------------------------------------------------------------------------------------------------------
Below are the functions defined to retrieve specific values from the input data/payload used in post call for verification after successful update
Functions:
a) get_expected_systemid() - Function to retrieve system IDs from input data/payload
b) get_expected_arrayidlist_for_system() - Function to retrieve array IDs associated with a system from input data/payload
c) get_expected_system_location() - Function to retrieve location details of a system
d) get_expected_array_cost() - Function to retrieve cost details of an array
---------------------------------------------------------------------------------------------------------------------------------------------------
"""


def get_expected_systemid(datainput: dict) -> list:
    """
        Function to retrieve system IDs from input data/payload
        Arguments:
                          datainput - datainput/payload as a argument in post call
    Return argument:
              List of system IDs (list[system_id])
    """
    system_id = []
    for item in datainput["costAndLocationInfo"]:
        system_id.append(item["systemId"])
    return system_id


def get_expected_arrayidlist_for_system(datainput: dict, system_id: str) -> list:
    """
        Function to retrieve array IDs associated with a system from input data/payload
        Arguments:
                          datainput - datainput/payload as a argument in post call
              system_id - system id to which arrays are associated
    Return argument:
              List of array IDs of a system (list[arrayidlist])
    """
    arrayidlist = []
    for count in range(len(datainput["costAndLocationInfo"])):
        if datainput["costAndLocationInfo"][count]["systemId"] == system_id:
            for item in datainput["costAndLocationInfo"][count]["costInfo"]:
                arrayidlist.append(item["arrayId"])
    return arrayidlist


def get_expected_system_location(datainput: dict, system_id: str) -> dict:
    """
        Function to retrieve location details of a system
        Arguments:
                          datainput - datainput/payload as a argument in post call
              system_id - system id for which location details are required
    Return argument:
              Dictionary of location details related to a system (dict{expected_sysloc})
    """
    expected_sysloc = {}
    vars = ["city", "postalCode", "state", "country"]
    for count in range(len(datainput["costAndLocationInfo"])):
        if datainput["costAndLocationInfo"][count]["systemId"] == system_id:
            for var in vars:
                expected_sysloc[var] = datainput["costAndLocationInfo"][count]["locationInfo"][var]
    return expected_sysloc


def get_expected_array_cost(datainput: dict, system_id: str, array_id: str) -> dict:
    """
        Function to retrieve cost details of an array
        Arguments:
                          datainput - datainput/payload as a argument in post call
              system_id - system id to which arrays are associated
              array_id - array id for which cost details are required
    Return argument:
              Dictionary of location details related to a system (dict{expected_arraycost})
    """
    expected_arraycost = {}
    for count in range(len(datainput["costAndLocationInfo"])):
        if datainput["costAndLocationInfo"][count]["systemId"] == system_id:
            for val in range(len(datainput["costAndLocationInfo"][count]["costInfo"])):
                if datainput["costAndLocationInfo"][count]["costInfo"][val]["arrayId"] == array_id:
                    params = ["cost", "currencyType", "depreciationStartDate", "monthsToDepreciate"]
                    for param in params:
                        expected_arraycost[param] = datainput["costAndLocationInfo"][count]["costInfo"][val][param]
    return expected_arraycost


logger = logging.getLogger()


@fixture(scope="session")
def context():
    test_context = Context()
    yield test_context


@mark.order(4020)
@mark.skip("This test case is not applicable for automation")
def test_inventory_tc4_C57482002(context: context):
    logger.info("Start of test case")
    logger.info("PQA Testing -> Inventory -> TC4_C57482002")

    url = context.cluster.url
    Inventory_manager = InventoryManager(url=url, api_header=context.api_header)
    Inventory_func = InventoryManagerFunc(url=url, api_header=context.api_header)

    """
	------------------------------------------------------------------------------------------------------------------------------
	Case1: Adding location details to the system
	a) create a new location and assign it to the system
	b) from the existing location assign it to the system
	------------------------------------------------------------------------------------------------------------------------------
	"""
    # Get all the system IDs for which location has to be added from input data
    system_ids = get_expected_systemid(datainput=data_location)

    # check whether the location details of those system are blank
    for sys_id in system_ids:
        system_location = Inventory_func.get_actual_system_location(sys_id)
        for var in system_location:
            assert system_location[var] == "", f"System location details should be empty to proceed with test case."

    # Post call to add system location details
    api_response_location = Inventory_manager.post_inventory_storage_systems_config(data_location)
    # If post call response is successful, trigger a collection and verify location are updated successfully for the systems under test.
    if api_response_location == "OK":
        # trigger a collection before verification
        tc_pcs = PanaromaCommonSteps(context=context)
        tc_pcs.trigger_data_collection
        time.sleep(300)
        for sys_id in system_ids:
            expected_system_location = get_expected_system_location(datainput=data_location, system_id=sys_id)
            api_system_location = Inventory_func.get_actual_system_location(system_id=sys_id)
            assert (
                expected_system_location == api_system_location
            ), f"Location update for system with id: {sys_id} unsuccessful."
    logger.info("Case1 of Test completed succesfully")

    """
	------------------------------------------------------------------------------------------------------------------------------
	Case2: Adding cost details to an array
	------------------------------------------------------------------------------------------------------------------------------
	"""
    # Get all the array IDs associated with a system for which cost details has to be added from input data and check whether the cost details of those arrays are blank
    system_ids = get_expected_systemid(datainput=data_cost)
    for sys_id in system_ids:
        array_ids = get_expected_arrayidlist_for_system(datainput=data_cost, system_id=sys_id)
        for array_id in array_ids:
            array_cost = Inventory_func.get_actual_array_cost(system_id=sys_id, array_id=array_id)
            for costparam in array_cost:
                assert array_cost[costparam] == "", f"Array cost details should be empty to proceed with test case."

    # Post call to add array cost details
    api_response_cost = Inventory_manager.post_inventory_storage_systems_config(data_cost)
    # If post call response is successful, trigger a collection and verify cost details are updated successfully for the array under test.
    if api_response_cost == "OK":
        # trigger a collection before verification
        tc_pcs = PanaromaCommonSteps(context=context)
        tc_pcs.trigger_data_collection
        time.sleep(300)
        for sys_id in system_ids:
            array_ids = get_expected_arrayidlist_for_system(datainput=data_cost, system_id=sys_id)
            for array_id in array_ids:
                expected_array_cost = get_expected_array_cost(datainput=data_cost, system_id=sys_id, array_id=array_id)
                api_array_cost = Inventory_func.get_actual_array_cost(system_id=sys_id, array_id=array_id)
                assert expected_array_cost == api_array_cost, f"Cost update for array with id: {array_id} unsuccessful."
    logger.info("Case2 of Test completed succesfully")

    """
	------------------------------------------------------------------------------------------------------------------------------
	Case3: Adding location details of a system and cost details of array belonging to that system.
	a) create a new location and assign it to the system
	b) from the existing location assign it to the system
	c) add cost details to array
	------------------------------------------------------------------------------------------------------------------------------
	"""
    system_ids = get_expected_systemid(datainput=data_costlocation)
    for sys_id in system_ids:
        system_location = Inventory_func.get_actual_system_location(sys_id)
        for var in system_location:
            assert system_location[var] == "", f"System location details should be empty to proceed with test case."
            array_ids = get_expected_arrayidlist_for_system(datainput=data_costlocation, system_id=sys_id)
            for array_id in array_ids:
                array_cost = Inventory_func.get_actual_array_cost(system_id=sys_id, array_id=array_id)
                for costparam in array_cost:
                    assert array_cost[costparam] == "", f"Array cost details should be empty to proceed with test case."

    # Post call to add array cost details
    api_response_costlocation = Inventory_manager.post_inventory_storage_systems_config(data_costlocation)
    # If post call response is successful, trigger a collection and verify location and cost details are updated successfully for the systems/arrays under test.
    if api_response_costlocation == "OK":
        # trigger a collection before verification
        tc_pcs = PanaromaCommonSteps(context=context)
        tc_pcs.trigger_data_collection
        time.sleep(300)
        for sys_id in system_ids:
            expected_system_location = get_expected_system_location(datainput=data_costlocation, system_id=sys_id)
            api_system_location = Inventory_func.get_actual_system_location(system_id=sys_id)
            assert (
                expected_system_location == api_system_location
            ), f"Location update for system with id: {sys_id} unsuccessful."
            array_ids = get_expected_arrayidlist_for_system(datainput=data_costlocation, system_id=sys_id)
            for array_id in array_ids:
                expected_array_cost = get_expected_array_cost(
                    datainput=data_costlocation, system_id=sys_id, array_id=array_id
                )
                api_array_cost = Inventory_func.get_actual_array_cost(system_id=sys_id, array_id=array_id)
                assert expected_array_cost == api_array_cost, f"Cost update for array with id: {array_id} unsuccessful."
    logger.info("Case3 of Test completed succesfully")
