# To verify customer is able to view IO activity of a particular volume for specific time interval
# Standard libraries
import datetime
import json
import logging
from math import ceil
from pathlib import Path
from random import randint
import time
import pandas as pd
from pytest import mark, fixture
from lib.dscc.data_panorama.consumption.api.clones_api import ClonesInfo

# Internal libraries
from lib.dscc.data_panorama.consumption.api.volumes_api import VolumesInfo
from lib.dscc.data_panorama.consumption.models.volumes import TotalIOActivity

# Steps
from tests.steps.data_panorama.panaroma_common_steps import Granularity, PanaromaCommonSteps, write_to_json
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from tests.steps.data_panorama.consumption.wastage_steps import WastageVolumes
from tests.steps.data_panorama.common_methods import get_path_params_by_type

# Tests
from tests.e2e.data_panorama.panorama_context import Context

logger = logging.getLogger()


@fixture(scope="session")
def context():
    test_context = Context()
    yield test_context


"""
As per the latest ETL changes collectionHour granularity will return day granularity results. Hence we no more need to execute this testcase with collectionHour granularity for volume and clone io trend. 
Please refer DCS-12688 for more details.
"""


@mark.validated
@mark.order(2055)
@mark.parametrize(
    "granularity",
    [Granularity.weekly, Granularity.daily],
)
def test_clone_tc14_C57572063(context: context, granularity):
    """
    Test Description:
        TC14 - To verify customer is able to view IO activity of a particular clone for specific time interval with granularity speicified.

    Test ID: C57572063
    curl cmd:
        curl -v -X GET 'http://CCS_DEV_URL/data-observability/v1alpha1/systems/{id}/clones/{id}/clone-io-trend?offset=0&limit=1000&granularity=day&start-time=2023-06-01T16%3A00%3A00Z&end-time=2023-07-02T16%3A00%3A00Z' --header 'Authorization: Bearer TOKEN' | jq .
                ''
    """
    logger.info("Start of test case")
    logger.info("PQA Testing -> Consumption -> Clones -> TC11_C57572063")
    """
    Define the filter parameters used in test case to be passed in API call
    Test case provides particular Clones IO activity details for the specific time intervals.
    Verification is done for time 3 intervals which will address CollectionHour, daily and weekly granularity
    volume_uuid: str - Volume ID for which IO activity details are required.
    startTime:  Define the start time for filtering. (collection end time will be used for  both start_time and end_time)
    endTime:  Define the end time for filtering.
    Note: End time will be excluded. It means if we give exact end time it won't be taken. Less than the end time will be taken. 
    """
    # Define the path and filter parameters used in test case to be passed in API call

    logger.info("Prerequisiste: Mock data should be uploaded")
    granul = granularity.value

    panorama_step = PanaromaCommonSteps(context=context)

    # Expected object
    mock_array_obj = ArrayConfigParser(context=context)
    url = context.cluster.url
    api_header = context.api_header
    clone_obj = ClonesInfo(url, api_header)

    # Variables definition to get System id and Volume id
    db_name = panorama_step.golden_db_path

    # Test case execution
    logger.info("Test case execution - started")
    # less than 7 days it is hourly, 8 to 180 days it is daily, greater than 180 days it is weekly

    etime = panorama_step.get_last_collection_end_time()
    time_interval = panorama_step.get_timeinterval(granul, etime)
    start_date = time_interval["starttime"].replace("T", " ").replace("Z", "")
    end_date = time_interval["endtime"].replace("T", " ").replace("Z", "")

    logger.info(f"Start date - {start_date} : End date {end_date} : Granularity - {granul}")
    # To do section - To get particular clone id and it's corresponding system id from database
    consumption_type = "clones"
    path_params = get_path_params_by_type(db_name=db_name, type=consumption_type)

    sys_id = path_params["system_id"]
    clone_id = path_params["cloneid"]
    arr_clone_io_trend = mock_array_obj.get_clone_io_trend(
        system_id=sys_id,
        vol_uuid=clone_id,
        start_date=start_date,
        end_date=end_date,
        granularity=granul,
    )
    logger.info(f"Expected IO trend from Mock data {arr_clone_io_trend}")
    logging.info("Array response: Volume IO activity trend")
    logging.info(json.dumps(arr_clone_io_trend.to_dict(), indent=4))
    logging.info(
        f"System id - {sys_id} - Clone id {clone_id} - io activity trend - granularity {granul} - start_date {start_date} and end date is {end_date}"
    )

    # uncomment below line during debug.
    write_to_json(
        pd.DataFrame(arr_clone_io_trend.items),
        f"{panorama_step.json_path}/array_io_trend_{granul}_{Path(__file__).stem}.json",
        sort_by="timeStamp",
    )

    logger.info(f"Get Actual Clone IO trend from API")

    """
    Sample API
    curl -v -X GET 'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/volumes-consumption/systems/<system-id>/volumes/<volume-id>/volume-io-trend?offset=0&limit=1000&granularity=day&start-time=2023-06-01T16%3A00%3A00Z&end-time=2023-07-02T16%3A00%3A00Z' --header 'Authorization: Bearer <token>' | jq .
    """
    api_clone_io_trend = clone_obj.get_clones_io_trend(
        system_id=sys_id,
        clone_id=clone_id,
        startTime=time_interval["starttime"],
        endTime=time_interval["endtime"],
        limit=1000,
        granularity=granul,
    )
    logger.info(f"Actual IO trend for volume {clone_id} from {start_date} to {end_date}")
    # verification
    logger.info(f"Granularity is {granul} - clone uuid is {clone_id}")
    logging.info("API response: Clones IO activity trend")
    logging.info(json.dumps(api_clone_io_trend.to_dict(), indent=4))

    write_to_json(
        pd.DataFrame(api_clone_io_trend.items),
        f"{panorama_step.json_path}/api_io_trend_{granul}_{Path(__file__).stem}.json",
        sort_by="timeStamp",
    )
    _verify_clones_io_trend(clone_id, arr_clone_io_trend, api_clone_io_trend, granul)

    logger.info(f"Granularity {granul} validation succeeded")


def _verify_clones_io_trend(clone_id, arr_clone_io_trend, api_clone_io_trend, granularity: str):
    # List of response from expected API and actual API is compared
    match_count = 0
    for api_io_trend in api_clone_io_trend.items:
        for array_io_trend in arr_clone_io_trend.items:
            # Compare upto hour - as minute differences are there .
            api_time = datetime.datetime.strptime(api_io_trend.timeStamp, "%Y-%m-%dT%H:%M:%SZ")
            arr_time = datetime.datetime.strptime(array_io_trend.timeStamp, "%Y-%m-%dT%H:%M:%SZ")
            if api_time == arr_time:
                # Only customerId ,timestamp and ioActivity need to be compared
                api_io_trend.customerId == array_io_trend.customerId, f"Customer Id doesn't match for volume {clone_id}"
                assert (
                    api_io_trend.timeStamp == array_io_trend.timeStamp
                ), f"timestamp not matching for volume {clone_id} in granularity {granularity}"
                # round the ioActivity as decimal digits are different for API and array response
                assert round(api_io_trend.ioActivity) == round(
                    array_io_trend.ioActivity
                ), f"ioActivity is not matching for volume {clone_id} for the time {api_io_trend.timeStamp} with granularity {granularity}"
                match_count = match_count + 1

    assert (
        arr_clone_io_trend.total == api_clone_io_trend.total
    ), f"Total Volume io trend count mis-match for volume with uuid {clone_id}. Array volume trend count {arr_clone_io_trend.total} . Api volume trend count {api_clone_io_trend.total}. Granularity level is {granularity} "

    assert match_count == api_clone_io_trend.total, f"Some data are mismatching. Check the json file "
