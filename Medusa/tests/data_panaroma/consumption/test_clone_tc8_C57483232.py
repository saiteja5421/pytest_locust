# Standard libraries
import logging
import time
import json
from pathlib import Path
from random import randint
import pandas as pd
from pytest import mark, fixture

# Internal libraries
from lib.dscc.data_panorama.consumption.api.clones_api import ClonesInfo
from lib.dscc.data_panorama.consumption.models.clones import ClonesActivityTrend, CloneActivity

# Common steps
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, write_to_json

# Common tests
from tests.e2e.data_panorama.panorama_context import Context

logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING) #To remove unnecessary logs


@fixture(scope="session")
def context():
    test_context = Context()
    yield test_context


@mark.validated
@mark.order(2040)
def test_clone_tc23_C57483232(context: Context):
    """
    Test Description:
        To verify customer is able to view clone activity details of all Thin provisioned type based on the clone size
    Automation blocks:
        1. Create mock data based out of data_set
        2. Calculate min and max clone size
        3. get_all_response function gathers all array and API clone activity data based on min and max IO
        4. Array object data against API object data validation
    Test parameters:
    data_set        : dict  - dictionary of array used for execution and corresponding configuration
    url             : str   - REST API url
    provision_type   : str   - clone provisioning type(Thin)
    min_clone_size    : int   - minimum used clone size to filter clones
    max_clone_size    : int   - maximum used clone size to filter clones
    minmaxlist      : list  - Holds complete list of clones used size
    """
    logger.info("Start of test case")
    logger.info("PQA Testing -> Consumption -> clones -> TC23_C57483232")

    provision_type: str = "Thin"
    minmaxlist = []

    # System configuration - Preconditions
    logger.info("Running pre-requisite: Array configuration")

    pcs_obj = PanaromaCommonSteps(context=context)

    array_obj = ArrayConfigParser(context=context)
    clone_obj = ClonesInfo(url=context.cluster.panorama_url, api_header=context.api_header)
    logger.info("Array configuration complete")

    # Test case execution
    logger.info("Test case execution - started")
    temp_dict, minmax_calculate = array_obj.get_clones_activity_trend_by_size(provisionType=provision_type)
    for record in minmax_calculate.iterrows():
        minmaxlist.append(record[1]["cloneusedsize"])
    minmaxlist.sort()
    min_clone_size = randint(0, minmaxlist[int(len(minmaxlist) / 2) - 1])
    max_clone_size = randint(minmaxlist[int(len(minmaxlist) / 2) - 1], minmaxlist[-1])
    print(f"min_clone_size {min_clone_size} and max_clone_size {max_clone_size}")

    # Get Array data
    array_clone_activity_trend, array_clone_activity_trend_dict = array_obj.get_clones_activity_trend_by_size(
        provisionType=provision_type, minCloneSize=min_clone_size, maxCloneSize=max_clone_size
    )

    write_to_json(
        df=pd.DataFrame(array_clone_activity_trend.items),
        path=f"{pcs_obj.json_path}/arr_{Path(__file__).stem}.json",
        sort_by="id",
    )

    # Get API response
    api_clone_activity_trend, api_clone_activity_trend_dict = pcs_obj.get_all_response_cloneactivity(
        clone_obj.get_clones_activity_trend,
        filter=f"filter=provisionType eq {provision_type} and utilizedSizeInBytes gt {min_clone_size} and utilizedSizeInBytes lt {max_clone_size}&limit=1000",
    )

    write_to_json(
        df=pd.DataFrame(api_clone_activity_trend.items),
        path=f"{pcs_obj.json_path}/api_{Path(__file__).stem}.json",
        sort_by="id",
    )

    # Verification steps
    # Get the items/variables of the class for comparision

    params = list(CloneActivity.__dataclass_fields__.keys())
    ignore_param = ["type", "generation", "resourceUri", "consoleUri"]
    check_param = [element for element in params if element not in ignore_param]

    # Match the length of API response and Expected data

    assert (
        array_clone_activity_trend.total == api_clone_activity_trend.total
    ), f"Number of records in the API response and Expected data doesn't match"
    print(
        f"Total records found as per input (Clone size {min_clone_size} - {max_clone_size} and {provision_type}): Array: {array_clone_activity_trend.total} API: {api_clone_activity_trend.total}"
    )

    # Compare value of each items/variables
    for item in api_clone_activity_trend.items:
        assert (
            item.provisionType == provision_type and min_clone_size <= item.utilizedSizeInBytes < max_clone_size
        ), "API data has volume which isn't thin or volume size falling outside minvolsize-maxvolsize range"
        match_flag: bool = False
        for record in array_clone_activity_trend.items:
            if record.id == item.id:
                for param in check_param:
                    if param != "activityTrendInfo":
                        if param in ["ioActivity","utilizedPercentage"]:
                            assert int(record.__getattribute__(param)) == int(
                                item.__getattribute__(param)
                            ), f"API {param} value is not matching with array response. API: {item.__getattribute__(param)} and Expected: {record.__getattribute__(param)}"
                        else:
                            assert record.__getattribute__(param) == item.__getattribute__(
                                param
                            ), f"API {param} value is not matching with array response. API: {item.__getattribute__(param)} and Expected: {record.__getattribute__(param)}"
                    else:
                        assert len(record.activityTrendInfo) == len(
                            item.activityTrendInfo
                        ), "Number of records in the API response Activity trend not matching Expected data"
                        for api_item in item.activityTrendInfo:
                            activity_trend_match = False
                            for array_item in record.activityTrendInfo:
                                if api_item.timeStamp == array_item.timeStamp:
                                    assert round(api_item.ioActivity) == round(
                                        array_item.ioActivity
                                    ), f"API ioactivity of {item.name} not matching with array data. Activity trend info from API: {api_item} Expected data: {array_item}"
                                    activity_trend_match = True
                            assert (
                                activity_trend_match == True
                            ), f"API output not found in Expected data list. API item: {api_item} Expected data: {array_item}"
                match_flag = True
            if match_flag:
                break
        assert match_flag == True, f"{item} in API response is not present in Expected data"
    print("Test Completed Successfully")
    logger.info("Test completed successfully")
