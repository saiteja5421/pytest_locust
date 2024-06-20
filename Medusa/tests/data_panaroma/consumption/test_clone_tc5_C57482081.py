# Standard libraries
import logging
from random import randint
import time
from pytest import mark, fixture
import json

import pandas as pd
from pandas.testing import assert_frame_equal
from pathlib import Path

# Internal libraries
from lib.dscc.data_panorama.consumption.api.clones_api import ClonesInfo
from lib.dscc.data_panorama.consumption.models.clones import ClonesUsageTrend
from lib.dscc.data_panorama.consumption.models.volumes import TotalVolumeUsage

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


@mark.validated
@mark.order(2025)
@mark.parametrize("granularity", [Granularity.daily, Granularity.weekly, Granularity.hourly])
def test_clone_tc5_C57482081(context: context, granularity):
    """
    Test Description:
        TC5 - To verify customer is able to view details of overall clones usage data for the specific time intervals
    Test ID: C57482081
    curl cmd:
        curl --location 'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/clones-usage-trend?start-time=2023-05-02T16%3A05%3A00Z&end-time=2023-08-16T16%3A05%3A00Z' --header {TOKEN}
    Automation blocks:
        1. Create mock data based out of data_set
        2. For each of period in time_period whole test is executed to validate all granularity
        3. get_all_response function gathers all array and API clone usage data
        4. Array object data against API object data validation
    """
    logger.info("Start of test case")
    logger.info("PQA Testing -> Consumption -> Clones -> TC5_C57482081")

    logger.info("Running pre-requisite: Array configuration")
    """
    Function call to add/modify JSON files
    Needs to be revisited once function is available
    """
    granularity = granularity.value
    logger.info(granularity)
    pcs_obj = PanaromaCommonSteps(context=context)
    array_obj = ArrayConfigParser(context=context)
    clone_obj = ClonesInfo(context.cluster.panorama_url, context.api_header)
    logger.info("Array configuration - completed")
    etime = pcs_obj.get_last_collection_end_time()
    time_interval = pcs_obj.get_timeinterval(granularity, etime)
    start_date = time_interval["starttime"].replace("T", " ").replace("Z", "")
    end_date = time_interval["endtime"].replace("T", " ").replace("Z", "")
    logger.info(time_interval)
    logger.info(start_date)
    logger.info(end_date)

    # Test case execution
    logger.info("Test case execution - started")

    # Get Array clone usage data
    array_clone_usage_trend: ClonesUsageTrend = array_obj.get_clones_usage_trend(
        start_date=start_date, end_date=end_date, granularity=granularity
    )
    write_to_json(
        df=pd.DataFrame(array_clone_usage_trend.items),
        path=f"{pcs_obj.json_path}/arr_{granularity}_{Path(__file__).stem}.json",
        sort_by="timeStamp",
    )

    # Get API clone usage response
    api_clone_usage_trend: ClonesUsageTrend = pcs_obj.get_all_response(
        clone_obj.get_clones_usage_trend, startTime=time_interval["starttime"], endTime=time_interval["endtime"]
    )
    write_to_json(
        df=pd.DataFrame(api_clone_usage_trend.items),
        path=f"{pcs_obj.json_path}/api_{granularity}_{Path(__file__).stem}.json",
        sort_by="timeStamp",
    )

    # Verification steps
    _verify_clone_usage_trend(array_clone_usage_trend, api_clone_usage_trend)
    logger.info("Test case execution - completed")


def _verify_clone_usage_trend(array_clone_usage_trend, api_clone_usage_trend):
    """
    Verification steps

    # Check timestamp returned by API response is within the specified time range
    for item in api_clones_usage_trend.totalClonesUsage:
        assert tp_starttime < item.timeStamp < tp_endtime, "API has clone data outside the specified time interval"

    # Compare value of each items/variables
    for item in api_clones_usage_trend.totalClonesUsage:
        tot_clone_usage =0
        for device in tc_clones_usage_trend_explist:
            for actual_val in device.totalClonesUsage:
                if actual_val.timeStamp == item.timeStamp:
                    tot_clone_usage += actual_val.totalCloneUsage
                    tc_clones_usage_trend_explen -= 1
        assert item.totalCloneUsage == tot_clone_usage, f"Clone usage doesn't match at time {item.timeStamp}"
    assert tc_clones_usage_trend_explen == 0, "Data mismatch. More timestamp instances present in Expected data from array than API Response"
    logger.info("Test completed succesfully")
    """
    logger.info("Inside verification steps")
    params = list(TotalVolumeUsage.__dataclass_fields__.keys())
    ignore_param = ["id", "name", "type", "resourceUri", "consoleUri", "systemName"]
    check_param = [element for element in params if element not in ignore_param]
    assert (
        array_clone_usage_trend.total == api_clone_usage_trend.total
    ), "Number of records in the API response and Expected data doesn't match"
    for item in api_clone_usage_trend.items:
        for record in array_clone_usage_trend.items:
            if item.timeStamp == record.timeStamp:
                for param in check_param:
                    assert item.__getattribute__(param) == record.__getattribute__(
                        param
                    ), f"{param} value not matching. API value: {item.__getattribute__(param)} Array value: {record.__getattribute__(param)}"
    logger.info("Verification completed successfully")
