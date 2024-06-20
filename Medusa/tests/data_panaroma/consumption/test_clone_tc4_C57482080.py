# Standard libraries
import logging
from pathlib import Path
from random import randint
import time
import pandas as pd
from pytest import mark, fixture

# Internal libraries
from lib.dscc.data_panorama.consumption.api.clones_api import ClonesInfo
from lib.dscc.data_panorama.consumption.models.clones import ClonesCostTrend, MonthlyVolumesCost

# Common Steps
from tests.steps.data_panorama.panaroma_common_steps import Granularity, PanaromaCommonSteps, write_to_json
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser

# Common Tests
from tests.e2e.data_panorama.panorama_context import Context


logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING) #To remove unnecessary logs

@fixture(scope="session")
def context():
    test_context = Context()
    yield test_context


@mark.order(2020)
@mark.validated
def test_clone_tc4_C57482080(context: Context):
    """
    Test Description:
        TC4 - To verify customer is able to view details of clones cost per month
    Test ID: C57482080
    curl cmd:
        curl --location 'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/clones-cost-trend?start-time=2023-08-01T00%3A00%3A00Z&end-time=2023-08-02T16%3A05%3A00Z' --header {TOKEN}
    Automation blocks:
        1. Create mock data based out of data_set
        2. For each of period in time_period whole test is executed to validate all granularity
        3. get_all_response function gathers all array and API clone cost data
        4. Array object data against API object data validation
    Test parameters:
    List of parameters that needs to be updated before execution.
    data_set        : dict  - dictionary of array used for execution and corresponding configuration
    url             : str   - REST API url
    """
    logger.info("Start of test case")
    logger.info("PQA Testing -> Consumption -> volumes -> TC4_C57482080")

    # This test case no need granularity . Giving weekly granularity just to fetch larger start and end time
    granularity = (Granularity.weekly).value
    logger.info(granularity)

    # System configuration - Preconditions
    logger.info("Running pre-requisite: Array configuration")
    """
    Function call to add/modify JSON files
    Needs to be revisited once function is available
    """
    pcs_obj = PanaromaCommonSteps(context=context)
    array_obj = ArrayConfigParser(context=context)
    clone_obj = ClonesInfo(url=context.cluster.panorama_url, api_header=context.api_header)
    logger.info("Array configuration - completed")
    etime = pcs_obj.get_last_collection_end_time()
    time_interval = pcs_obj.get_timeinterval(granularity, etime)
    start_date = time_interval["starttime"].replace("T", " ").replace("Z", "")
    end_date = time_interval["endtime"].replace("T", " ").replace("Z", "")
    logger.info(time_interval)
    # start_date = get_first_date_month(start_date)
    # end_date = get_last_date_month(end_date)
    logger.info(start_date)
    logger.info(end_date)

    # Test case execution
    logger.info("Test case execution - started")

    # Get Array data
    array_clone_usage_cost = array_obj.get_clones_cost_trend(start_date=start_date, end_date=end_date)
    write_to_json(
        df=pd.DataFrame(array_clone_usage_cost.items),
        path=f"{pcs_obj.json_path}/arr_{Path(__file__).stem}.json",
        sort_by=["year", "month"],
    )

    # Get API response
    api_clone_usage_cost: ClonesCostTrend = pcs_obj.get_all_response(
        clone_obj.get_clones_cost_trend, startTime=time_interval["starttime"], endTime=time_interval["endtime"]
    )
    write_to_json(
        df=pd.DataFrame(api_clone_usage_cost.items),
        path=f"{pcs_obj.json_path}/api_{Path(__file__).stem}.json",
        sort_by=["year", "month"],
    )

    # Verification steps
    _verify_clone_cost_trend(granularity, array_clone_usage_cost, api_clone_usage_cost)
    logger.info("Test case execution - completed")




def _verify_clone_cost_trend(granularity, array_clone_usage_cost, api_clone_usage_cost):
    params = list(MonthlyVolumesCost.__dataclass_fields__.keys())
    ignore_param = ["id", "name", "type", "generation", "resourceUri", "consoleUri"]
    check_param = [element for element in params if element not in ignore_param]
    assert (
        array_clone_usage_cost.total == api_clone_usage_cost.total
    ), f"Number of records present in API response is not matching with expected data for {granularity} granularity"
    for item in array_clone_usage_cost.items:
        for record in api_clone_usage_cost.items:
            if item.__getattribute__("month") == record.__getattribute__("month") and item.__getattribute__(
                "year"
            ) == record.__getattribute__("year"):
                for param in check_param:
                    if param == "cost":
                        assert abs(round(record.__getattribute__(param)) - round(item.__getattribute__(param))) <= 1, f"Values not matching API: {record.__getattribute__(param)} and Actual: {item.__getattribute__(param)}" 
                        #Allowing the mismatch to be there for +-1 due to end & beginning of month cost mismatch
                    else:
                        assert item.__getattribute__(param) == record.__getattribute__(
                            param
                        ), f"{param} value not matching. API value: {record.__getattribute__(param)} and Array value: {item.__getattribute__(param)}"
