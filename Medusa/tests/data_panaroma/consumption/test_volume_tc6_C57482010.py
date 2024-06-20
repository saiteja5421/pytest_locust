# Standard libraries
import logging
from pathlib import Path
import random
import datetime
import pandas as pd

from pytest import fixture, mark

from tests.e2e.data_panorama.panorama_context import Context
from lib.dscc.data_panorama.consumption.api.volumes_api import VolumesInfo
from lib.dscc.data_panorama.consumption.models.volumes import TotalVolumesCreated
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser

from tests.steps.data_panorama.panaroma_common_steps import Granularity, PanaromaCommonSteps, write_to_json


logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING) #To remove unnecessary logs

@fixture(scope="session")
def context():
    yield Context()
    # Test Clean up will be added later


# @mark.skip(reason="Blocked by bug DCS-10212")
@mark.validated
@mark.order(1030)
@mark.parametrize("granularity", [Granularity.hourly,Granularity.daily, Granularity.weekly])
def test_volume_tc6_C57482010(context: context, granularity):
    """Volume Creation Trend: The test case validate the details of all the volumes created data for the specific time intervals between array and api calls.

    Sample Test URL : GET /data-observability/v1alpha1/volumes-creation-trend?start-time=2023-04-30T00%3A00%3A00Z&end-time=2023-08-02T16%3A05%3A00Z

    """

    api_pcs_obj = PanaromaCommonSteps(context=context)

    arr_obj: ArrayConfigParser = ArrayConfigParser(context=context)
    granul = granularity.value

    # End time is taken based on collection end time so that we can pick right range of data
    etime = api_pcs_obj.get_last_collection_end_time()
    time_interval = api_pcs_obj.get_timeinterval(granul, etime)
    json_out_file = api_pcs_obj.json_path

    array_obj = arr_vol_creation_trend(json_out_file, arr_obj, granul, time_interval)

    # Fetching values from API Calls
    api_obj = api_vol_creation_trend(context, api_pcs_obj, granul, time_interval)

    # Validation of volumes creation details from array and api calls matches for a specific time interval
    _verify_creation_trend(array_obj, api_obj)

    logger.info("Test completed succesfully")

def api_vol_creation_trend(context, api_pcs_obj: PanaromaCommonSteps, granul, time_interval):
    volumes_info = VolumesInfo(context.cluster.panorama_url, context.api_header)
    api_obj = api_pcs_obj.get_all_response(
        volumes_info.get_volumes_creation_trend,
        startTime=time_interval["starttime"],
        endTime=time_interval["endtime"],
    )

    write_to_json(
        pd.DataFrame(api_obj.items),
        f"{api_pcs_obj.json_path}/api_creation_trend_{granul}_{Path(__file__).stem}.json",
        sort_by="updatedAt",
    )
    
    return api_obj

def arr_vol_creation_trend(json_out_file, arr_obj: ArrayConfigParser, granul, time_interval):
    start_date = time_interval["starttime"].replace("T", " ").replace("Z", "")
    end_date = time_interval["endtime"].replace("T", " ").replace("Z", "")

    logger.info(f"Start date {start_date} -> Granularity {granul}")
    logger.info(f"End date {end_date} -> Granularity {granul}")

    array_obj = arr_obj.get_volumes_creation_trend(start_date=start_date, end_date=end_date, granularity=granul)
    
    write_to_json(
        pd.DataFrame(array_obj.items),
        f"{json_out_file}/arr_creation_trend_{granul}_{Path(__file__).stem}.json",
        sort_by="updatedAt",
    )
    
    return array_obj


def _verify_creation_trend(array_obj, api_obj):
    assert array_obj.total == api_obj.total, "number of objects does not match"
    # params = [param for param in dir(api_obj.items[0]) if param not in dir(TotalVolumesCreated)]
    params = list(TotalVolumesCreated.__dataclass_fields__.keys())
    ignore_param = ["id", "name", "type", "generation", "resourceUri", "consoleUri", "aggrWindowTimestamp"]
    check_param = [element for element in params if element not in ignore_param]
    for item in api_obj.items:
        flag = 0
        for array_item in array_obj.items:
            if item.updatedAt == array_item.updatedAt:
                for param in check_param:
                    assert item.__getattribute__(param) == array_item.__getattribute__(
                        param
                    ), f"Values not matching API: {item.__getattribute__(param)} and Actual: {array_item.__getattribute__(param)}"
                flag = 1
                break
        assert flag == 1, f"timestamp info not found in api call {item.timeStamp}"
