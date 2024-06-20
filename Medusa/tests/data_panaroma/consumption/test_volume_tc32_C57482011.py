# standard libraries
import logging
import datetime
from random import randint
import random
import json
import pandas as pd
from pandas.testing import assert_frame_equal
from pathlib import Path
import time
from pytest import fixture, mark

from tests.e2e.data_panorama.panorama_context import Context
from lib.dscc.data_panorama.consumption.api.volumes_api import VolumesInfo
from tests.steps.data_panorama.panaroma_common_steps import Granularity, PanaromaCommonSteps, write_to_json
from lib.dscc.data_panorama.consumption.models.volumes import VolumeUsageTrend, TotalVolumeUsage
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from tests.steps.data_panorama.consumption.wastage_steps import WastageVolumes
from tests.steps.data_panorama.common_methods import get_path_params_by_type

logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING) #To remove unnecessary logs

@fixture(scope="session")
def context():
    yield Context()


@mark.validated
@mark.order(10250)
@mark.parametrize("granularity", [Granularity.daily, Granularity.weekly, Granularity.hourly])
def test_volume_tc32_C57482011(context: context, granularity):
    """To verify customer is able to view volume usage of particular volume for specific interval of time"""
    logger.info("Start of test case")
    logger.info("PQA Testing -> Consumption -> volumes -> TC32_C57482011")
    logger.info("TC32, Jira ID: C57482011")

    """ 
    Define the path and filter parameters used in test case to be passed in API call
    Test case verifies customer is able to view volume usage of particular volume for specific interval of time
    Test Description:
        To verify customer is able to view volume usage of particular volume for specific interval of time
     
    Verification is done for time 3 intervals which will address hourly, daily and weekly granularity  
    system_id: str - Storagesysid fro which IO activity details are required.
    volume_uuid: str - Volume ID for which IO activity details are required.
    startTime:  Define the start time for filtering.
    endTime:  Define the end time for filtering.
    """
    granularity = granularity.value
    logger.info(granularity)
    # Expected object
    pcs_obj = PanaromaCommonSteps(context=context)
    acp_obj = ArrayConfigParser(context=context)
    wastage_array_obj = WastageVolumes(url=context.cluster.panorama_url, api_header=context.api_header)
    # Actual Object
    volume_obj = VolumesInfo(context.cluster.panorama_url, context.api_header)
    etime = pcs_obj.get_last_collection_end_time()
    time_interval = pcs_obj.get_timeinterval(granularity, etime)
    start_date = time_interval["starttime"].replace("T", " ").replace("Z", "")
    end_date = time_interval["endtime"].replace("T", " ").replace("Z", "")
    logger.info(time_interval)
    logger.info(start_date)
    logger.info(end_date)

    # To do section - To get particular volume id and system id
    db_name = acp_obj.steps_obj.golden_db_path
    consumption_type = "volumes"
    path_params = get_path_params_by_type(db_name=db_name, type=consumption_type)
    logger.info(path_params)

    # Test case execution
    logger.info("Test case execution - started")

    # Get Array data
    array_volume_usage_trend = acp_obj.get_volume_time_stamp_usage_trend(
        system_id=path_params["storagesysid"],
        vol_uuid=path_params["volumeId"],
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
    )
    logger.info(array_volume_usage_trend.total)
    write_to_json(
        df=pd.DataFrame(array_volume_usage_trend.items),
        path=f"{pcs_obj.json_path}/arr_{granularity}_{Path(__file__).stem}.json",
        sort_by="timeStamp",
    )

    api_volume_usage_trend = wastage_array_obj.get_all_response_volume_path_parameter(
        func=volume_obj.get_volume_usage_trend,
        system_id=path_params["storagesysid"],
        volume_uuid=path_params["volumeId"],
        startTime=time_interval["starttime"],
        endTime=time_interval["endtime"],
    )
    logger.info(api_volume_usage_trend.total)
    write_to_json(
        df=pd.DataFrame(api_volume_usage_trend.items),
        path=f"{pcs_obj.json_path}/api_{granularity}_{Path(__file__).stem}.json",
        sort_by="timeStamp",
    )
    # Verification steps
    _verify_vol_usage_trend(array_volume_usage_trend, api_volume_usage_trend)

    logger.info("Test case execution - completed")


def _verify_vol_usage_trend(array_volume_usage_trend, api_volume_usage_trend):
    assert (
        array_volume_usage_trend.total == api_volume_usage_trend.total
    ), f"Total Volume Usage count is not matching. API: {api_volume_usage_trend.total} and {array_volume_usage_trend.total}"
    params = list(TotalVolumeUsage.__dataclass_fields__.keys())
    ignore_param = ["id", "name", "resourceUri", "consoleUri"]
    check_param = [element for element in params if element not in ignore_param]

    for act_vol in array_volume_usage_trend.items:
        timestampflag = False
        for exp_vol in api_volume_usage_trend.items:
            if act_vol.timeStamp == exp_vol.timeStamp:
                for param in check_param:
                    assert act_vol.__getattribute__(param) == exp_vol.__getattribute__(
                        param
                    ), f"{param} value is not matching. API: {act_vol.__getattribute__(param)} and Actual: {exp_vol.__getattribute__(param)}"
                    timestampflag = True
                break
        assert timestampflag == True, f"timeStamp not found in api call {act_vol.timeStamp}"
