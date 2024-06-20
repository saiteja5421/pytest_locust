# Standard libraries
import logging


from pytest import fixture, mark

from tests.e2e.data_panorama.panorama_context import Context
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser

from tests.steps.data_panorama.consumption.wastage_steps import WastageVolumes

from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps


logger = logging.getLogger()


@fixture(scope="session")
def context():
    yield Context()
    # Test Clean up will be added later


@mark.order(1115)
@mark.skip("This test case is not applicable for automation")
def test_volume_tc23_C57482023(context=context):
    """
    The test case validate the mounted and unmounted volumes count between array and api calls.

    Test parameters:List of parameters that needs to be updated before execution.

        vol_activity_list  : list  - list to hold objects returned from ArrayConfigParser methods
    mounted_count: int - Integer to count mounted volumes
    non_mounted_count: int - Integer to count unmounted volumes

    """

    # Define data set for mock generator
    # To-Do: Function needs to be revisited, Need details of arguments to be passed

    obj = PanaromaCommonSteps(context=context)
    obj.mock_json_data_generate()

    aobj = ArrayConfigParser(context=context)
    # array_obj = aobj.get_volumes_activity_trend()

    # Mounted  and unmounted volumes in a_6k_obj and a_9k_obj
    mounted_count: int = 0
    non_mounted_count: int = 0

    tc_vol_activity_trend_expected = obj.get_all_response_volactivity(aobj.get_volumes_activity_trend)
    for record in tc_vol_activity_trend_expected.items:
        if record.isConnected == True:
            mounted_count = mounted_count + 1
        else:
            non_mounted_count = non_mounted_count + 1

    # Fetching values from API Calls

    api_mount = []
    api_non_mount = []
    api_info = WastageVolumes()
    api_mount = api_info.get_mounted_volumes()
    api_mount_count = len(api_mount)
    api_non_mount = api_info.get_non_mounted_volumes()
    api_non_mount_count = len(api_non_mount)

    # Validation of count of mounted and unmounted volumes from array and api calls

    assert (
        api_mount_count == mounted_count
    ), "mounted volumes count created and mounted volumes count returned by API does not match"
    assert (
        api_non_mount_count == non_mounted_count
    ), "unmounted volumes count created and unmounted volumes count returned by API does not match"
