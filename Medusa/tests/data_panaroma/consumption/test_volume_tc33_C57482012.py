# standard libraries
import logging
import datetime
from dateutil.relativedelta import relativedelta, MO
from random import randint
import random
from tests.e2e.data_panorama.panorama_context import Context
from lib.dscc.data_panorama.consumption.api.volumes_api import VolumesInfo
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, write_to_json
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from pytest import fixture, mark
import pandas as pd
from pathlib import Path
from lib.dscc.data_panorama.consumption.models.volumes import MonthlyVolumesCost

logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING) #To remove unnecessary logs

@fixture(scope="session")
def context():
    test_context = Context()
    yield test_context


@mark.validated
@mark.order(1060)
def test_volume_tc33_C57482012(context: context):
    """TC8 - To verify customer is able to view volume usage cost for time interval (6 months)"""
    logger.info("Start of test case")
    logger.info("PQA Testing -> Consumption -> volumes -> TC33_C57482012")
    logger.info("TC33, Jira ID: C57482012")
    """ 
    Define the path and filter parameters used in test case to be passed in API call
    Test case verifies customer is able to view volume usage of particular volume for specific interval of time
    Test Description:
        TC8 - To verify customer is able to view volume usage cost for time interval (1year)
     
    Verification is done 2 intervals for one year and 4 months which will address weekly and daily granularity.  
    volume_uuid: str - Volume ID for which IO activity details are required.
    startTime:  Define the start time for filtering.
    endTime:  Define the end time for filtering.
    """
    # time_period = [random.randint(1, 7), random.randint(8, 180), random.randint(190, 360)]
    obj = PanaromaCommonSteps(context=context)

    aobj = ArrayConfigParser(context=context)

    volume_obj = VolumesInfo(context.cluster.panorama_url, context.api_header)
    c_time = datetime.datetime.now()
    e_time = c_time - relativedelta(years=0, months=0, days=1, hours=0, minutes=0)
    s_time = e_time - relativedelta(years=0, months=6, days=0, hours=0, minutes=0)
    tp_starttime = s_time.strftime("%Y-%m-%d %H:%M:%S").replace(" ", "T") + ".000Z"
    tp_endtime = e_time.strftime("%Y-%m-%d %H:%M:%S").replace(" ", "T") + ".000Z"

    # Get Array data

    array_volume_cost_trend = obj.get_all_response(
        aobj.get_volumes_cost_trend,
        start_date=tp_starttime.replace(".000Z", ""),
        end_date=tp_endtime.replace(".000Z", ""),
    )

    write_to_json(
        pd.DataFrame(array_volume_cost_trend.items),
        f"{obj.json_path}/ARRAY_volume_cost_trend_{Path(__file__).stem}.json",
        sort_by="month",
    )
    # Get API response

    api_volume_cost_trend = obj.get_all_response(
        func=volume_obj.get_volumes_cost_trend,
        startTime=tp_starttime,
        endTime=tp_endtime,
    )

    write_to_json(
        pd.DataFrame(api_volume_cost_trend.items),
        f"{obj.json_path}/API_volume_cost_trend_{Path(__file__).stem}.json",
        sort_by="month",
    )
    # verification 1

    assert array_volume_cost_trend.total == api_volume_cost_trend.total, "Total Volume cost trend count mis-match"
    params = list(MonthlyVolumesCost.__dataclass_fields__.keys())
    ignore_param = [
        "id",
        "name",
        "type",
        "resourceUri",
        "consoleUri",
        "generation",
    ]
    check_param = [element for element in params if element not in ignore_param]
    # params = [param for param in dir(api_obj.items[0]) if param not in dir(TotalClonesCopies)]
    for item in api_volume_cost_trend.items:
        flag = 0
        for array_item in array_volume_cost_trend.items:
            if item.month == array_item.month:
                for param in check_param:
                    if param == "cost":
                        assert abs(round(item.__getattribute__(param)) - round(array_item.__getattribute__(param))) <= 1, f"Values not matching API: {item.__getattribute__(param)} and Actual: {array_item.__getattribute__(param)}" #Allowing the mismatch to be there for +-1 due to end & beginning of month cost mismatch
                    else:
                        assert item.__getattribute__(param) == array_item.__getattribute__(
                            param
                        ), f"Values not matching API: {item.__getattribute__(param)} and Actual: {array_item.__getattribute__(param)}"
                flag = 1
                break
        assert flag == 1, f"month data not found in api call {item.month}"

    logger.info("Test completed succesfully")
