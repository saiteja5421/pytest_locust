"""
Test Case ID C57483070
Test Description - TC1:- To verify customer is able to view activity details of all Thick provision volumes based on the IO range
"""

# Standard libraries
from datetime import datetime
import logging
import time
import random
from pytest import mark, fixture
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
from tests.steps.data_panorama.common_methods import get_path_params_by_type

# Tests
from tests.e2e.data_panorama.panorama_context import Context

logger = logging.getLogger()


@fixture(scope="session")
def context():
    test_context = Context()
    yield test_context


@mark.validated
@mark.order(1005)
def test_volume_tc1_C57483070(context: context):
    """
    Test Description:
        TC1 - To verify customer is able to view activity details of all Thick provision volumes based on the IO range
    Test ID: C57483070
    curl cmd:
        curl --location 'http://CCS_DEV_URL/data-observability/v1alpha1/volumes-activity-trend?offset=0 limit=1000&filter=provisionType%20eq%20Thick' --header 'Authorization: Bearer TOKEN
    """
    logger.info("Test Case Starts")
    logger.info("PQA Testing -> Consumption -> Volumes -> TC1_C57483070")
    """
    Define the volume provision type of which volume activity trend to be fetched.
    Test case provides details of all those Thick provision volumes where IOActivity is within the defined range.
    """
    tc_acs = ArrayConfigParser(context=context)
    tc_pcs = PanaromaCommonSteps(context=context)
    tp_provisiontype: str = "Thick"

    """
    Define the filter parameters used in test case to be passed as arguments in API call
    tp_minio:float - Define the filtering range -> Starting IO value
    tp_maxio:float - Define the filtering range -> Ending IO value
    tp_minio and tp_maxio are the random values set based on the IOActivity values from the data generator response
    """

    temp, minmax_calculate = tc_acs.get_volumes_activity_trend_by_io(provisionType=tp_provisiontype)

    minmaxlist = []
    for record in minmax_calculate.iterrows():
        minmaxlist.append(record[1]["avgiops"])
    minmaxlist.sort()
    median = minmaxlist[int(len(minmaxlist) / 2) - 1]
    tp_minio: int = round(random.randint(0, median))
    tp_maxio: int = round(random.randint(median, minmaxlist[-1]))

    """
    Expected Data from data generator for verification:
    get_all_response -> Function to calculate and trigger multiple API/Array calls based on limit and offset. 
                        Collected response will be unified into single dictionary and converted to corresponding Class object.
    get_volumes_activity_trend:-> Function returns the data related to volume activity for verification with API response.
                                  This is the expected data of the test case against which actual values will be compared.
    """

    tc_vol_activity_trend_expected, temp_activity_trend = tc_acs.get_volumes_activity_trend_by_io(
        provisionType=tp_provisiontype, minIo=tp_minio, maxIo=tp_maxio
    )
    print(tc_vol_activity_trend_expected)
    write_to_json(
        df=pd.DataFrame(tc_vol_activity_trend_expected.items),
        path=f"{tc_pcs.json_path}/arr_{Path(__file__).stem}.json",
        sort_by="id",
    )

    """
    API call to get the actual values:
    get_all_response -> Function to calculate and trigger multiple API/Array calls based on limit and offset. 
                        Collected response will be unified into single dictionary and converted to corresponding Class object.
    get_volumes_activity_trend:-> API call to get volume activity.
    """
    volumes_activity = VolumesInfo(url=context.cluster.panorama_url, api_header=context.api_header)
    api_vol_activity_trend = tc_pcs.get_all_response_volactivity(
        volumes_activity.get_volumes_activity_trend_by_io_activity,
        provisionType=tp_provisiontype,
        minIo=tp_minio,
        maxIo=tp_maxio,
    )

    write_to_json(
        df=pd.DataFrame(api_vol_activity_trend.items),
        path=f"{tc_pcs.json_path}/api_{Path(__file__).stem}.json",
        sort_by="id",
    )

    """
    Verification steps
    """
    # Get the items/variables of the class for comparision
    params = list(VolumeActivity.__dataclass_fields__.keys())
    ignore_param = ["type", "generation", "resourceUri", "consoleUri", "name", "system"]
    check_param = [element for element in params if element not in ignore_param]

    # Match the length of API response and Expected data
    assert len(tc_vol_activity_trend_expected.items) == len(
        api_vol_activity_trend.items
    ), f"Number of records in the API response and Expected data doesn't match"
    assert (
        tc_vol_activity_trend_expected.total == api_vol_activity_trend.total
    ), f"Number of records in the API response and Expected data doesn't match"

    # Compare value of each items/variables
    _verify_activity_trend_by_io(
        tp_provisiontype,
        tp_minio,
        tp_maxio,
        tc_vol_activity_trend_expected,
        api_vol_activity_trend,
        check_param,
    )


def _verify_activity_trend_by_io(
    tp_provisiontype, tp_minio, tp_maxio, tc_vol_activity_trend_expected, api_vol_activity_trend, check_param
):
    for item in api_vol_activity_trend.items:
        assert (
            item.provisionType == tp_provisiontype and tp_minio <= item.ioActivity < tp_maxio
        ), "API data has volume which isn't thick or IO-activity value falling outside minIO-maxIO range"
        match_flag: bool = False
        for record in tc_vol_activity_trend_expected.items:
            if record.id == item.id:
                for param in check_param:
                    if param != "activityTrendInfo":
                        if param in ["ioActivity","utilizedPercentage"]: # decimal may not match so convert to int 
                            assert int(record.__getattribute__(param)) == int(
                                item.__getattribute__(param)
                            ), f"Values not matching. \n API: {item.__getattribute__(param)} and Expected: {record.__getattribute__(param)}"
                        else:
                            assert record.__getattribute__(param) == item.__getattribute__(
                                param
                            ), f"Values not matching for {param}. \n API: {item.__getattribute__(param)} and Expected: {record.__getattribute__(param)}"
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
