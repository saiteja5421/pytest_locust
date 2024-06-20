# Standard libraries
import datetime
import logging
import random
import pandas as pd
from pathlib import Path
from random import randint
from pytest import fixture, mark

from tests.e2e.data_panorama.panorama_context import Context
from lib.dscc.data_panorama.consumption.api.volumes_api import VolumesInfo
from lib.dscc.data_panorama.consumption.models.volumes import TotalVolumesUsage
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser


from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, Granularity, write_to_json

logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING) #To remove unnecessary logs

@fixture(scope="session")
def context():
    yield Context()
    # Test Clean up will be added later


@mark.validated
@mark.order(1025)
def test_volume_tc5_C57482009(context: context):
    """The test case validate the details of all the volumes usage data for the specific time intervals between array and api calls.
    Sample test URL : GET /data-observability/v1alpha1/volumes-usage-trend?start-time=2023-04-09T00%3A00%3A00Z&end-time=2023-08-02T16%3A05%3A00Z


    """

    time_period = [random.randint(1, 7), random.randint(8, 180), random.randint(190, 360)]
    granularity_list = [randint(1, 7), randint(8, 180), randint(190, 360)]
    granularity_list = [
        {"days": randint(8, 180), "granularity": Granularity.daily},  # granularity will be daily
        {"days": randint(190, 200), "granularity": Granularity.weekly},  # Granularity will be weekly
        {"days": randint(1, 7), "granularity": Granularity.hourly},  # Granularity will be hourly
    ]
    aobj = ArrayConfigParser(context=context)
    obj = PanaromaCommonSteps(context=context)

    for granularity in granularity_list:
        granul = granularity["granularity"].value
        etime = obj.get_last_collection_end_time()
        time_interval = obj.get_timeinterval(granul, etime)
        start_date = time_interval["starttime"].replace("T", " ").replace("Z", "")
        end_date = time_interval["endtime"].replace("T", " ").replace("Z", "")
        array_obj = aobj.get_volumes_usage_trend(
            start_date=start_date,
            end_date=end_date,
            granularity=granul,
        )
        print(f"Start date {start_date} -> Granularity {granul}")
        print(f"End date {end_date} -> Granularity {granul}")

        write_to_json(
            pd.DataFrame(array_obj.items),
            f"{obj.json_path}/arr_{granul}_{Path(__file__).stem}.json",
            sort_by="timeStamp",
        )

        # Fetching values from API Calls
        volumes_info = VolumesInfo(context.cluster.panorama_url, context.api_header)
        api_obj = obj.get_all_response(
            volumes_info.get_volumes_usage_trend, startTime=time_interval["starttime"], endTime=time_interval["endtime"]
        )

        write_to_json(
            pd.DataFrame(api_obj.items),
            f"{obj.json_path}/api_{granul}_{Path(__file__).stem}.json",
            sort_by="timeStamp",
        )

        # print("api_info =", api_obj)

        # Match the length of the API response and Expected data
        # print("time period completed", period)
        assert array_obj.total == api_obj.total, "number of objects does not match"
        params = list(TotalVolumesUsage.__dataclass_fields__.keys())
        # params = [param for param in dir(api_obj.items[0]) if param not in dir(TotalVolumesUsage)]
        # print("params=", params)
        ignore_param = ["id", "name", "type", "resourceUri", "consoleUri"]
        check_param = [element for element in params if element not in ignore_param]

        for item in api_obj.items:
            flag = 0
            for array_item in array_obj.items:
                if item.timeStamp == array_item.timeStamp:
                    for param in check_param:
                        assert item.__getattribute__(param) == array_item.__getattribute__(
                            param
                        ), f"Values not matching API: {item.__getattribute__(param)} and Actual: {array_item.__getattribute__(param)}"
                    flag = 1
                    break
            assert flag == 1, f"timestamp info not found in api call {item.timeStamp}"
        # print("time period completed", period)
        logger.info("Test completed succesfully")
