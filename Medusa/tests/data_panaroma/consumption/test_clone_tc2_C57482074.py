# Standard libraries
import logging
import time
from pytest import mark, fixture

# Internal libraries
from lib.dscc.data_panorama.consumption.models.clones import ClonesActivityTrend

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
    # Test Clean up will be added later


@mark.order(2010)
@mark.skip("This test case is not applicable for automation")
def test_clone_tc2_C57482074(context=context):
    """
    The test case validate the mounted clones count between array and api calls.

    Test parameters:
    data_set  : dict  - dictionary of array used for execution and corresponding configuration
    actual_mounted_clones: int - Integer to count mounted clones

    """
    # Test Parameters:
    actual_mounted_clones: int = 0
    # To DO: Configuration details:
    data_set = {"s012": [[0, 1, 0, 0, 0, 6, 3, 1]], "pqa-2-sys": [[0, 0, 2, 10, 0, 4, 1, 2]]}
    logger.info("Running pre-requisite: Array configuration")
    array_obj = PanaromaCommonSteps(context=context)

    # Function call to add/modify JSON files
    array_obj.mock_json_data_generate()
    time.sleep(300)

    array_config = ArrayConfigParser(context=context)
    array_clone_activity = array_obj.get_all_response(array_config.get_clones_activity_trend)
    for item in array_clone_activity.items:
        if item.isConnected == True:
            actual_mounted_clones += 1

    # Fetching values from API Calls
    api_info = WastageVolumes()
    api_mounted_clones_list = api_info.get_mounted_clones()
    api_mounted_clones = len(api_mounted_clones_list)

    # Verification steps - Validation of count of mounted clones between array and api calls
    assert (
        api_mounted_clones == actual_mounted_clones
    ), f"Mounted clone count created - {actual_mounted_clones} and mounted clone count returned by API - {api_mounted_clones} does not match"
    logger.info("Test case execution - completed")
    logger.info("Test completed succesfully")
    """
    obj.create_config(array_data_set=data_set,pre_clean_up=True)
    obj.trigger_data_collection()
    # sleep for 5 minutes. To allow data collection and computation 
    time.sleep(300)
    aobj = ArrayConfigParser(context=context)
    array_obj = aobj.get_clones_activity_trend()

    mounted_count: int = 0
    clone_activity_list = []

    if type(array_obj)is tuple:
        clone_activity_list = list(array_obj)       
    else:
        clone_activity_list.append(array_obj) 

    
    for volume in array_obj:
        for actual_val in volume.cloneActivityDetails:
            if actual_val.connected == True:
                mounted_count=mounted_count+1
    print("mounted_count")
    
	#Fetching values from API Calls
    api_mount = []
    api_info = WastageVolumes()
    api_mount = api_info.get_mounted_clones()
    api_mount_count = len(api_mount)
    
    # Validation of count of mounted clones between array and api calls
    assert api_mount_count == mounted_count, "mounted clone count created and mounted clone count returned by API does not match"
    """
