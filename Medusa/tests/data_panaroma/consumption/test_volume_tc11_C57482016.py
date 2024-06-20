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
@mark.order(1055)
@mark.parametrize("granularity", [Granularity.weekly, Granularity.daily])
def test_volume_tc11_C57482016(context: context, granularity):
    """
    Test Description:
        TC11 - To verify customer is able to view IO activity of a particular volume for specific time interval

    Test ID: C57482016
    curl cmd:
        curl -v -X GET 'http://CCS_DEV_URL/data-observability/v1alpha1/volumes-consumption/systems/<system-id>/volumes/<volume-id>/volume-io-trend?offset=0&limit=1000&granularity=day&start-time=2023-06-01T16%3A00%3A00Z&end-time=2023-07-02T16%3A00%3A00Z' --header 'Authorization: Bearer TOKEN' | jq .

    """
    logger.info("Start of test case")
    logger.info("PQA Testing -> Consumption -> Volumes -> TC11_C57482016")
    """
    Define the filter parameters used in test case to be passed in API call
    Test case provides particular volume IO activity details for the specific time intervals.
    Verification is done for time 3 intervals which will address hourly, daily and weekly granularity
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
    wastage_array_obj = WastageVolumes(url=url, api_header=api_header)
    api_volumes_info = wastage_array_obj.volume_info

    # Variables definition to get System id and Volume id
    db_name = panorama_step.golden_db_path
    consumption_type = "volumes"

    # Test case execution
    logger.info("Test case execution - started")
    # less than 7 days it is hourly, 8 to 180 days it is daily, greater than 180 days it is weekly

    etime = panorama_step.get_last_collection_end_time()
    time_interval = panorama_step.get_timeinterval(granul, etime)
    start_date = time_interval["starttime"].replace("T", " ").replace("Z", "")
    end_date = time_interval["endtime"].replace("T", " ").replace("Z", "")

    # To do section - To get particular volume id and system id
    path_params = get_path_params_by_type(db_name=db_name, type=consumption_type)
    logger.info(f"Start date - {start_date} : End date {end_date} : Granularity - {granul}")

    """
    volume_uuid = _get_volume_uuid(panorama_step, start_date, end_date)
    # volume_uuid = "4c8d6c31-8a0b-9941-93a8-1403b1559147"
    """

    vol_id = path_params["volumeId"]
    sys_id = path_params["storagesysid"]
    logger.info(f"Volume id  - {vol_id} : System id {sys_id} : Granularity - {granul}")

    array_volume_io_trend = mock_array_obj.get_volume_io_trend(
        system_id=sys_id,
        vol_uuid=vol_id,
        start_date=start_date,
        end_date=end_date,
        granularity=granul,
    )
    logger.info(f"Expected IO trend from Mock data {array_volume_io_trend}")
    logging.info("Array response: Volume IO activity trend")
    logging.info(json.dumps(array_volume_io_trend.to_dict(), indent=4))
    print(
        f"volume id {path_params['volumeId']} - io activity trend - granularity {granul} - start_date {start_date} and end date is {end_date}"
    )

    # uncomment below line during debug.
    write_to_json(
        pd.DataFrame(array_volume_io_trend.items),
        f"{panorama_step.json_path}/array_io_trend_{granul}_{Path(__file__).stem}.json",
        sort_by="timeStamp",
    )

    logger.info(f"Get Actual volume trend from API")

    """
    Sample API
    curl -v -X GET 'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/volumes-consumption/systems/<system-id>/volumes/<volume-id>/volume-io-trend?offset=0&limit=1000&granularity=day&start-time=2023-06-01T16%3A00%3A00Z&end-time=2023-07-02T16%3A00%3A00Z' --header 'Authorization: Bearer <token>' | jq .
    """
    api_volume_io_trend = api_volumes_info.get_volume_io_trend(
        system_id=path_params["storagesysid"],
        volume_uuid=path_params["volumeId"],
        startTime=time_interval["starttime"],
        endTime=time_interval["endtime"],
        granularity=granul,
        limit=1000,
    )
    logger.info(f"Actual IO trend for volume {path_params['volumeId']} from {start_date} to {end_date}")
    # file.write(json.dumps(api_volume_io_trend))
    # verification
    logger.info(f"Granularity is {granul} - Volume uuid is {path_params['volumeId']}")
    logging.info("API response: Volume IO activity trend")
    logging.info(json.dumps(api_volume_io_trend.to_dict(), indent=4))
    # uncomment below line during debug.

    write_to_json(
        pd.DataFrame(api_volume_io_trend.items),
        f"{panorama_step.json_path}/api_io_trend_{granul}_{Path(__file__).stem}.json",
        sort_by="timeStamp",
    )
    _verify_volume_io_trend(path_params["volumeId"], array_volume_io_trend, api_volume_io_trend, granul)

    logger.info(f"Granularity {granul} validation succeeded")


def _verify_volume_io_trend(volume_uuid, array_volume_io_trend, api_volume_io_trend, granularity: str):
    # List of response from expected API and actual API is compared
    match_count = 0
    for api_io_trend in api_volume_io_trend.items:
        for array_io_trend in array_volume_io_trend.items:
            # Compare upto hour - as minute differences are there .
            api_time = datetime.datetime.strptime(api_io_trend.timeStamp, "%Y-%m-%dT%H:%M:%SZ")
            arr_time = datetime.datetime.strptime(array_io_trend.timeStamp, "%Y-%m-%dT%H:%M:%SZ")
            if api_time == arr_time:
                # Only customerId ,timestamp and ioActivity need to be compared
                api_io_trend.customerId == array_io_trend.customerId, f"Customer Id doesn't match for volume {volume_uuid}"
                assert (
                    api_io_trend.timeStamp == array_io_trend.timeStamp
                ), f"timestamp not matching for volume {volume_uuid} in granularity {granularity}"
                # round the ioActivity as decimal digits are different for API and array response
                assert round(api_io_trend.ioActivity) == round(
                    array_io_trend.ioActivity
                ), f"ioActivity is not matching for volume {volume_uuid} for the time {api_io_trend.timeStamp} with granularity {granularity}"
                match_count = match_count + 1

    assert (
        array_volume_io_trend.total == api_volume_io_trend.total
    ), f"Total Volume io trend count mis-match for volume with uuid {volume_uuid}. Array volume trend count {array_volume_io_trend.total} . Api volume trend count {api_volume_io_trend.total}. Granularity level is {granularity} "

    assert match_count == api_volume_io_trend.total, f"Some data are mismatching. Check the json file "


def _get_volume_uuid(panorama_step, start_date, end_date):
    """Get volume uuid in a given time range if present. If not present get any random volume uuid which exists.

    Args:
        panorama_step (_type_): _description_
        start_date (datetime): start date
        end_date (datetime): end date

    Returns:
        str: volume uuid
    """
    all_vol_uuid_in_time_range = panorama_step.spark_get_sample_vol_io_trend_within_timerange(
        start_date=start_date, end_date=end_date
    )
    if all_vol_uuid_in_time_range["data"]:
        volume_uuid = all_vol_uuid_in_time_range["data"][0]["id"]
    else:
        sample_data = panorama_step.spark_get_sample_vol_io_trend()
        volume_uuid = sample_data["data"][0]["id"]
    return volume_uuid
