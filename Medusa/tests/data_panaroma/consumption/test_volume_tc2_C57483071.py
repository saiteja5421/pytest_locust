"""
Test Case ID C57483071
Test Description - TC2:- To verify customer is able to view activity details of all Thick provision volumes based on size range
"""

# Standard libraries
from datetime import datetime
import logging
import time
import random
from pathlib import Path
import pandas as pd
from pandas.testing import assert_frame_equal
from pytest import mark, fixture
import os

# Internal libraries
from lib.dscc.data_panorama.consumption.api.volumes_api import VolumesInfo
from lib.dscc.data_panorama.consumption.models.volumes import VolumeActivity, ActivityTrendDetail, VolumesActivityTrend

# Steps
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser

# Tests
from tests.e2e.data_panorama.panorama_context import Context

logger = logging.getLogger()


@fixture(scope="session")
def context():
    test_context = Context()
    yield test_context


@mark.validated
# @mark.skip("Blocked by activity trend bug: DCS-10955")
@mark.order(1010)
def test_volume_tc2_C57483071(context: context):
    """
    Test Description:
        TC2 - To verify customer is able to view activity details of all Thick provision volumes based on size range
    Test ID: C57483071
    curl cmd:
        curl --location 'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/volumes-activity-trend?limit=1000&filter=provisionType%20eq%20Thick%20and%20utilizedSizeInBytes%20gt%20206233323%20and%20utilizedSizeInBytes%20lt%201600529378' --header {TOKEN}
    """
    logger.info("Start of test case")
    logger.info("PQA Testing -> Consumption -> Volumes -> TC2_C57483071")
    """
    Define the volume provision type of which volume activity trend to be fetched
    Test case provides details of all those Thick provision volumes where utilized space size is within the defined range.
    """
    tp_provisiontype: str = "Thick"
    logger.info("Running pre-requisite: Array configuration")
    tc_pcs = PanaromaCommonSteps(context=context)
    arr_spark = ArrayConfigParser(context=context)

    """
    Define the filter parameters used in test case to be passed as arguments in API call
    tp_minvolsize:int - Define the filtering range -> Starting utilized size value
    tp_maxvolsize:int - Define the filtering range -> Ending utilized size value
    tp_minvolsize and tp_maxvolsize are the random values set based on the utilizedSize values from the data generator response
    """
    minmax_calculate = arr_spark.get_volumes_activity_trend_by_size(provisionType=tp_provisiontype)
    minmaxlist = []
    for record in minmax_calculate.items:
        minmaxlist.append(record.utilizedSizeInBytes)
    minmaxlist.sort()
    median = minmaxlist[int(len(minmaxlist) / 2) - 1]
    tp_minvolsize: int = round(random.randint(0, median))
    tp_maxvolsize: int = round(random.randint(median, minmaxlist[-1]))

    """
    Expected Data from data generator for verification:
    get_all_response -> Function to calculate and trigger multiple API/Array calls based on limit and offset. 
                        Collected response will be unified into single dictionary and converted to corresponding Class object.
    get_volumes_activity_trend:-> Function returns the data related to volume activity for verification with API response.
                                  This is the expected data of the test case against which actual values will be compared.
    """
    tc_vol_activity_trend_expected = arr_spark.get_volumes_activity_trend_by_size(
        provisionType=tp_provisiontype,
        minVolumeSize=tp_minvolsize,
        maxVolumeSize=tp_maxvolsize,
    )
    print(tc_vol_activity_trend_expected)
    df = pd.DataFrame(tc_vol_activity_trend_expected.items).sort_values(by=["id"])
    df.to_json(f"{tc_pcs.json_path}/arr_{Path(__file__).stem}.json", orient="records")

    """
    API call to get the actual values
    get_all_response -> Function to calculate and trigger multiple API/Array calls based on limit and offset. 
                        Collected response will be unified into single dictionary and converted to corresponding Class object.
    get_volumes_activity_trend:-> API call to get volume activity.
    
    """
    volumes_activity = VolumesInfo(context.cluster.url, api_header=context.api_header)
    api_vol_activity_trend = tc_pcs.get_all_response_volactivity(
        volumes_activity.get_volumes_activity_trend,
        filter=f"provisionType eq {tp_provisiontype} and utilizedSizeInBytes gt {tp_minvolsize} and utilizedSizeInBytes lt {tp_maxvolsize}"
        # provisionType=tp_provisiontype,
        # minVolumeSize=tp_minvolsize,
        # maxVolumeSize=tp_maxvolsize,
    )
    print(api_vol_activity_trend)
    api_df = pd.DataFrame(api_vol_activity_trend.items).sort_values(by=["id"])
    api_df.to_json(f"{tc_pcs.json_path}/api_{Path(__file__).stem}.json", orient="records")

    """
    Verification steps
    """

    # Get the items/variables of the class for comparision
    params = list(VolumeActivity.__dataclass_fields__.keys())
    ignore_param = ["type", "generation", "resourceUri", "consoleUri"]
    check_param = [element for element in params if element not in ignore_param]

    # Match the length of API response and Expected data
    assert len(tc_vol_activity_trend_expected.items) == len(
        api_vol_activity_trend.items
    ), f"Number of records in the API response and Expected data doesn't match"
    assert (
        tc_vol_activity_trend_expected.total == api_vol_activity_trend.total
    ), f"Number of records in the API response and Expected data doesn't match"

    # Compare value of each items/variables
    for item in api_vol_activity_trend.items:
        assert (
            item.provisionType == tp_provisiontype and tp_minvolsize < item.utilizedSizeInBytes < tp_maxvolsize
        ), "API data has volume which isn't thick or IO-activity value falling outside minIO-maxIO range"
        match_flag: bool = False
        for record in tc_vol_activity_trend_expected.items:
            if record.id == item.id:
                for param in check_param:
                    if param != "activityTrendInfo":
                        if param in ["ioActivity","utilizedPercentage"]:
                            assert int(record.__getattribute__(param)) == int(
                                item.__getattribute__(param)
                            ), f"Values not matching. \n API: {item.__getattribute__(param)} and Expected: {record.__getattribute__(param)}"
                        else:
                            assert record.__getattribute__(param) == item.__getattribute__(
                                param
                            ), f"Values not matching. \n API: {item.__getattribute__(param)} and Expected: {record.__getattribute__(param)}"
                    else:
                        assert len(record.activityTrendInfo) == len(
                            item.activityTrendInfo
                        ), "Activity trend timestamps in API and Expected data aren't matching"
                        api_activity_trend_info = pd.DataFrame(item.activityTrendInfo)
                        arr_activity_trend_info = pd.DataFrame(record.activityTrendInfo)
                        api_activity_trend_info["ioActivity"] = api_activity_trend_info["ioActivity"].astype("int64")
                        arr_activity_trend_info["ioActivity"] = arr_activity_trend_info["ioActivity"].astype("int64")
                        assert_frame_equal(api_activity_trend_info, arr_activity_trend_info)
                match_flag = True
            if match_flag:
                break
        assert match_flag == True, f"{item} in API response is not present in Expected data"
    logger.info("Test completed successfully")
