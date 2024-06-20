# Standard libraries
import logging
import time
import json
from pathlib import Path
from random import uniform
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
@mark.order(2030)
def test_clone_tc6_C57482082(context: Context):
    """
    Test Description:
        To verify customer is able to view clone activity details of all Thin provisioned type based on the IO range
    Automation blocks:
        1. Create mock data based out of data_set
        2. Calculate min and max IO
        3. get_all_response function gathers all array and API clone activity data based on min and max IO
        4. Array object data against API object data validation
    Test parameters:
    data_set        : dict  - dictionary of array used for execution and corresponding configuration
    url             : str   - REST API url
    provision_type   : str   - clone provisioning type(Thin)
    min_io          : float   - minimum IO range to filter clones
    max_io          : float   - maximum IO range to filter clones
    min_max_list      : list  - Holds complete list of IO activity
    """
    logger.info("Start of test case")
    logger.info("PQA Testing -> Consumption -> clones -> TC6_C57482082")

    provision_type: str = "Thin"
    min_max_list = []

    # System configuration - Preconditions
    logger.info("Running pre-requisite: Array configuration")

    pcs_obj = PanaromaCommonSteps(context=context)

    array_obj = ArrayConfigParser(context=context)
    clone_obj = ClonesInfo(url=context.cluster.panorama_url, api_header=context.api_header)
    logger.info("Array configuration complete")

    # Test case execution
    logger.info("Test case execution - started")
    temp_dict, minmax_calculate = array_obj.get_clones_activity_trend_by_io(provisionType=provision_type)
    for index, record in minmax_calculate.iterrows():
        min_max_list.append(record["avg_iops"])
    min_max_list.sort()
    min_io = round(uniform(0, min_max_list[int(len(min_max_list) / 2) - 1]), 2)
    max_io = round(uniform(min_max_list[int(len(min_max_list) / 2) - 1], min_max_list[-1]), 2)
    print(f"minio {min_io} and maxio {max_io}")

    # Get Array clone activity data
    array_clone_activity_trend, temp_dict = array_obj.get_clones_activity_trend_by_io(
        provisionType=provision_type, minio=min_io, maxio=max_io
    )
    write_to_json(
        df=pd.DataFrame(array_clone_activity_trend.items),
        path=f"{pcs_obj.json_path}/arr_{Path(__file__).stem}.json",
        sort_by="id",
    )

    # Get API clone activity response
    api_clone_activity_trend, api_clone_activity_trend_dict = pcs_obj.get_all_response_cloneactivity(
        clone_obj.get_clones_activity_trend,
        filter=f"filter=provisionType eq {provision_type} and ioActivity gt {min_io} and ioActivity lt {max_io}",
    )
    write_to_json(
        df=pd.DataFrame(api_clone_activity_trend.items),
        path=f"{pcs_obj.json_path}/api_{Path(__file__).stem}.json",
        sort_by="id",
    )

    # Verification steps
    # Get  the items/variables of the class for comparision

    params = list(CloneActivity.__dataclass_fields__.keys())
    ignore_param = ["type", "generation", "resourceUri", "consoleUri"]
    check_param = [element for element in params if element not in ignore_param]

    # Match the length of API response and Expected data

    assert (
        array_clone_activity_trend.total == api_clone_activity_trend.total
    ), f"Number of records in the API response and Expected data doesn't match"

    # Compare value of each items/variables
    for item in api_clone_activity_trend.items:
        assert (
            item.provisionType == provision_type and min_io <= item.ioActivity < max_io
        ), "API data has volume which isn't thin or IO-activity value falling outside minIO-maxIO range"
        match_flag: bool = False
        for record in array_clone_activity_trend.items:
            if record.id == item.id:
                for param in check_param:
                    if param != "activityTrendInfo":
                        if param in ["ioActivity","utilizedPercentage"]:
                            assert int(record.__getattribute__(param)) == int(
                                item.__getattribute__(param)
                            ), f"ioActivity value is not matching. API: {item.__getattribute__(param)} and Array: {record.__getattribute__(param)}"
                        else:
                            assert record.__getattribute__(param) == item.__getattribute__(
                                param
                            ), f"API {param} value is not matching with array value. API: {item.__getattribute__(param)} and Array: {record.__getattribute__(param)}"
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
    logger.info("Test Completed Successfully")
