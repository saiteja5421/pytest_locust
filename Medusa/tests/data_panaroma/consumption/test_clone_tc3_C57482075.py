# Standard libraries
import logging
import time
from pytest import mark, fixture

# Common Steps
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from tests.steps.data_panorama.consumption.wastage_steps import WastageVolumes

# Common Tests
from tests.e2e.data_panorama.panorama_context import Context


logger = logging.getLogger()


@fixture(scope="session")
def context():
    yield Context()
    # Test Clean up will be added latertest_clone_tc2_C57482074


@mark.order(2015)
@mark.skip("This test case is not applicable for automation")
def test_clone_tc3_C57482075(context=context):
    """
    The test case validate the unmounted clones count between array and api calls.

    Test parameters:List of parameters that needs to be updated before execution.
    data_set  : dict  - dictionary of array used for execution and corresponding configuration
    actual_non_mounted_clones: int - Integer to count unmounted clones
    """
    # Test Parameters:
    actual_non_mounted_clones: int = 0

    # To DO: Configuration details:
    data_set = {"s012": [[0, 1, 0, 0, 0, 6, 3, 1]], "pqa-2-sys": [[0, 0, 2, 10, 0, 4, 1, 2]]}
    logger.info("Running pre-requisite: Array configuration")

    # Function call to add/modify JSON files
    array_obj = PanaromaCommonSteps(context=context)
    array_obj.mock_json_data_generate()
    time.sleep(300)
    array_config = ArrayConfigParser(context=context)

    # Test case execution
    logger.info("Test case execution - started")
    array_clone_activity = array_obj.get_all_response(array_config.get_clones_activity_trend)
    for item in array_clone_activity.items:
        if item.isConnected == False:
            actual_non_mounted_clones += 1

    # Fetching values from API Calls
    api_info = WastageVolumes()
    api_non_mounted_clones_list = api_info.get_non_mounted_clones()
    api_non_mounted_clones = len(api_non_mounted_clones_list)

    # Verification steps - Validation of count of mounted clones between array and api calls
    assert (
        api_non_mounted_clones == actual_non_mounted_clones
    ), f"Mounted clone count created - {actual_non_mounted_clones} and mounted clone count returned by API - {api_non_mounted_clones} does not match"
    logger.info("Test case execution - completed")
    logger.info("Test completed succesfully")

    """
    # To DO: Configuration details:
    data_set = {
        "s012": [
            [0, 1, 0, 0, 0, 6, 3, 1]
        ],
        "pqa-2-sys": [
            [0, 0, 2, 10, 0, 4, 1, 2]
        ]
    }
    obj = PanaromaCommonSteps(context=context)
    obj.create_config(array_data_set=data_set,pre_clean_up=True)
    obj.trigger_data_collection()
    # sleep for 5 minutes. To allow data collection and computation 
    time.sleep(300)
    aobj = ArrayConfigParser(context=context)
    array_obj = aobj.get_clones_activity_trend()

    unmounted_count: int = 0
    clone_activity_list = []

    if type(array_obj)is tuple:
        clone_activity_list = list(array_obj)       
    else:
        clone_activity_list.append(array_obj) 

    
    for volume in array_obj:
        for actual_val in volume.cloneActivityDetails:
            if actual_val.connected == False:
                unmounted_count=unmounted_count+1
    print("unmounted_count")
    
#Fetching values from API Calls
    api_unmount = []
    api_info = WastageVolumes()
    api_unmount = api_info.get_non_mounted_clones()
    api_unmount_count = len(api_unmount)
    
    ## Validation of count of unmounted clones between array and api calls
    assert api_unmount_count == unmounted_count, "unmounted clones count created and unmounted clones count returned by API does not match"
    """
