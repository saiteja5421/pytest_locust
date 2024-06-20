"""
Test Case ID C57482015
Test Description - TC10:- To verify customer is able to view activity details of all Thin provision volumes based on size range
"""

# Standard libraries
from datetime import datetime
import logging
import time
import random
import pandas as pd
from pandas.testing import assert_frame_equal
from pathlib import Path
from pytest import mark, fixture

# Internal libraries
from lib.dscc.data_panorama.consumption.api.volumes_api import VolumesInfo
from lib.dscc.data_panorama.consumption.models.volumes import VolumeActivity

# Steps
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, write_to_json
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser

# Tests
from tests.e2e.data_panorama.panorama_context import Context

logger = logging.getLogger()


@fixture(scope="session")
def context():
    test_context = Context()
    yield test_context


@mark.validated
@mark.order(1050)
def test_volume_tc10_C57482015(context: context):
    """
    Test Description:
        TC10 - To verify customer is able to view activity details of all Thin provision volumes based on size range
    Test ID: C57482081
    curl cmd:
        curl --location 'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/volumes-activity-trend?limit=1000&filter=provisionType%20eq%20Thin%20and%20utilizedSizeInBytes%20gt%20206233323%20and%20utilizedSizeInBytes%20lt%201600529378' --header {TOKEN}
    """
    logger.info("Start of test case")
    logger.info("PQA Testing -> Consumption -> Volumes -> TC10_C57482015")
    """
    Define the volume provision type of which volume activity trend to be fetched
    Test case provides details of all those Thick provision volumes where utilized space size is within the defined range.
    """
    tp_provisiontype: str = "Thin"

    """
    Preconditions:
    Prepare the required data for test case execution.
    data_set:-> Define configuration parameters.
    mock_json_data_generate:-> Function to generate data as per the data_set.
    sleep for 5 minutes. To allow data collection and computation
    """
    logger.info("Running pre-requisite: Array configuration")
    tc_pcs = PanaromaCommonSteps(context=context)

    tc_acs: ArrayConfigParser = ArrayConfigParser(context=context)

    """
    Define the filter parameters used in test case to be passed as arguments in API call
    tp_minvolsize:int - Define the filtering range -> Starting utilized size value
    tp_maxvolsize:int - Define the filtering range -> Ending utilized size value
    tp_minvolsize and tp_maxvolsize are the random values set based on the utilizedSize values from the data generator response
    """
    minmax_calculate = tc_acs.get_volumes_activity_trend_by_size(provisionType=tp_provisiontype)
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
        tc_vol_activity_trend_expected = tc_acs.get_volumes_activity_trend_by_size(
            provisionType=tp_provisiontype,
            minVolumeSize=tp_minvolsize,
            maxVolumeSize=tp_maxvolsize,
        )
        # Record Array (expected API) response in json
        write_to_json(
            df=pd.DataFrame(tc_vol_activity_trend_expected.items),
            path=f"{tc_pcs.json_path}/arr_{Path(__file__).stem}.json",
            sort_by="id",
        )

        """
        API call to get the actual values
        get_all_response -> Function to calculate and trigger multiple API/Array calls based on limit and offset. 
                            Collected response will be unified into single dictionary and converted to corresponding Class object.
        get_volumes_activity_trend:-> API call to get volume activity.

        curl call:
        curl -X GET 'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/volumes-activity-trend?offset=0&limit=1000&provisionType=Thin&min-volume-size=2147483648&max-volume-size=2234534545' --header 'Authorization: Bearer <token>'
        
        """

        volumes_activity = VolumesInfo(context.cluster.panorama_url, context.api_header)
        api_vol_activity_trend = tc_pcs.get_all_response_volactivity(
            volumes_activity.get_volumes_activity_trend_by_size,
            provisionType=tp_provisiontype,
            minVolumeSize=tp_minvolsize,
            maxVolumeSize=tp_maxvolsize,
        )
        # Record API response as json file to compare manually if doubtful
        write_to_json(
            df=pd.DataFrame(api_vol_activity_trend.items),
            path=f"{tc_pcs.json_path}/api_{Path(__file__).stem}.json",
            sort_by="id",
        )

        """
        Verification steps
        """

        # Get the items/variables of the class for comparision
        # params = [param for param in dir(api_vol_activity_trend.items[0]) if param not in dir(VolumeActivity)]
        params = list(VolumeActivity.__dataclass_fields__.keys())
        ignore_param = ["type", "generation", "resourceUri", "consoleUri"]
        check_param = [element for element in params if element not in ignore_param]

        # Match the length of API response and Expected data
        # assert len(tc_vol_activity_trend_expected.items) == len(api_vol_activity_trend.items), f"Number of records in the API response and Expected data doesn't match"
        assert (
            tc_vol_activity_trend_expected.total == api_vol_activity_trend.total
        ), f"Number of records in the API response and Expected data doesn't match"

        # Compare value of each items/variables
        _verify_activity_trend(
            tp_provisiontype,
            tp_minvolsize,
            tp_maxvolsize,
            tc_vol_activity_trend_expected,
            api_vol_activity_trend,
            check_param,
        )


def _verify_activity_trend(
    tp_provisiontype, tp_minvolsize, tp_maxvolsize, tc_vol_activity_trend_expected, api_vol_activity_trend, check_param
):
    for item in api_vol_activity_trend.items:
        assert (
            item.provisionType == tp_provisiontype and tp_minvolsize < item.utilizedSizeInBytes < tp_maxvolsize
        ), "API data has volume which isn't thick or volume size falling outside minvolsize-maxvolsize range"
        match_flag: bool = False
        for record in tc_vol_activity_trend_expected.items:
            if record.id == item.id:
                for param in check_param:
                    if param != "activityTrendInfo":
                        if param in  ["ioActivity","utilizedPercentage"]:
                            assert round(record.__getattribute__(param)) == round(
                                item.__getattribute__(param)
                            ), f"iOActivity values not matching. \n API: {item.__getattribute__(param)} and Expected: {record.__getattribute__(param)}"
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
                        try:
                            assert_frame_equal(api_activity_trend_info, arr_activity_trend_info)
                        except:
                            raise Exception("activityTrendInfo values not matching")
                match_flag = True
            if match_flag:
                break
        assert match_flag == True, f"{item} in API response is not present in Expected data"
    logger.info("Test completed successfully")
