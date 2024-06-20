# Standard libraries
import logging
from pathlib import Path
import time
from random import randint
import pandas as pd
from pytest import mark, fixture
import json

# Internal libraries
from lib.dscc.data_panorama.consumption.api.clones_api import ClonesInfo
from lib.dscc.data_panorama.consumption.models.clones import ClonesCreationTrend, TotalClonesCreated

# Common Steps
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, Granularity, write_to_json
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser

# Common Tests
from tests.e2e.data_panorama.panorama_context import Context


logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING) #To remove unnecessary logs

@fixture(scope="session")
def context():
    test_context = Context()
    yield test_context


@mark.order(2050)
@mark.validated
@mark.parametrize("granularity", [Granularity.daily, Granularity.weekly, Granularity.hourly])
def test_clone_tc10_C57482083(context: context, granularity):
    """
    Test Description:
        TC10 - To verify customer is able to view details of clones created for the specific time intervals
    Test ID: C57482083
    curl cmd:
        curl --location 'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/clones-creation-trend?limit=1000&start-time=2023-08-09T16:05:00Z&end-time=2023-08-16T16:05:00Z' --header {TOKEN}'
    Automation blocks:
        1. Create mock data based out of data_set
        2. For each of period in time_period, whole test is executed to validate all granularity
        3. get_all_response function gathers all array and API clone creation data
        4. Array object data against API object data validation
    """
    logger.info("Start of test case")
    logger.info("PQA Testing -> Consumption -> Clones -> TC10_C57482083")

    granularity = granularity.value
    logger.info(granularity)
    logger.info("Running pre-requisite: Array configuration")
    """
    Function call to add/modify JSON files
    Needs to be revisited once function is available
    """
    api_obj = PanaromaCommonSteps(context=context)
    array_obj = ArrayConfigParser(context=context)
    clone_obj = ClonesInfo(context.cluster.panorama_url, context.api_header)
    logger.info("Array configuration - completed")

    # Calculate start and end date
    etime = api_obj.get_last_collection_end_time()
    time_interval = api_obj.get_timeinterval(granularity, etime)
    start_date = time_interval["starttime"].replace("T", " ").replace("Z", "")
    end_date = time_interval["endtime"].replace("T", " ").replace("Z", "")
    logger.info(time_interval)
    

    # Test case execution
    logger.info("Test case execution - started")
    logger.debug(start_date)
    logger.debug(end_date)
    logger.debug(granularity)

    # Get Array data
    json_path = api_obj.json_path
    array_clone_creation_trend = ARRAY_CLONE_CREATION_TREND(granularity, json_path, array_obj, start_date, end_date)

    # Get API response
    api_clone_creation_trend = API_CLONE_CREATION_TREND(granularity, api_obj, clone_obj, time_interval)

    # Verification steps
    VERIFY_CLONE_CREATION_TREND(granularity, array_clone_creation_trend, api_clone_creation_trend)
    logger.info(f"Clone creation {granularity} Trend  from {start_date} to {end_date} - completed successfully")

def ARRAY_CLONE_CREATION_TREND(granularity, json_path, array_obj: ArrayConfigParser, start_date, end_date):
    array_clone_creation_trend: ClonesCreationTrend = array_obj.get_clones_creation_trend(
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
    )
    logger.info("Array Response")
    logger.info(json.dumps(array_clone_creation_trend.to_dict(), indent=4))
    
    write_to_json(
        df=pd.DataFrame(array_clone_creation_trend.items),
        path=f"{json_path}/arr_{granularity}_{Path(__file__).stem}.json",
        sort_by="updatedAt",
    )
    
    return array_clone_creation_trend

def API_CLONE_CREATION_TREND(granularity, pcs_obj, clone_obj, time_interval):
    api_clone_creation_trend: ClonesCreationTrend = pcs_obj.get_all_response(
        clone_obj.get_clones_creation_trend, startTime=time_interval["starttime"], endTime=time_interval["endtime"]
    )
    logger.info(api_clone_creation_trend)
    logger.info("API Response")
    logger.info(json.dumps(api_clone_creation_trend.to_dict(), indent=4))
    write_to_json(
        df=pd.DataFrame(api_clone_creation_trend.items),
        path=f"{pcs_obj.json_path}/api_{granularity}_{Path(__file__).stem}.json",
        sort_by="updatedAt",
    )
    
    return api_clone_creation_trend


def VERIFY_CLONE_CREATION_TREND(granularity, array_clone_creation_trend, api_clone_creation_trend):
    params = list(TotalClonesCreated.__dataclass_fields__.keys())
    ignore_param = ["id", "name", "type", "generation", "resourceUri", "consoleUri"]
    check_param = [element for element in params if element not in ignore_param]
    assert (
        array_clone_creation_trend.total == api_clone_creation_trend.total
    ), f"Number of records present in API response is not matching with expected data for {granularity} granularity"
    for arr in array_clone_creation_trend.items:
        for api in api_clone_creation_trend.items:
            if arr.updatedAt == api.updatedAt:
                for param in check_param:
                    assert arr.__getattribute__(param) == api.__getattribute__(
                        param
                    ), f"{param} value not matching. API value: {api.__getattribute__(param)} and Array value: {arr.__getattribute__(param)}"
