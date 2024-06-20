"""
Test Case ID C57482143
Test Description :- To verify customer is able to view details of snapshots Usage for the specific time intervals
"""

# Standard libraries
import json
import logging
from pathlib import Path
import pandas as pd
from pytest import mark, fixture
from random import randint


# Internal libraries
from lib.dscc.data_panorama.consumption.api.snapshots_api import SnapshotsInfo
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from lib.dscc.data_panorama.consumption.models.snapshots import SnapshotUsageTrend, TotalSnapshotsUsage

# Tests
from tests.e2e.data_panorama.panorama_context import Context
from tests.steps.data_panorama.panaroma_common_steps import Granularity, PanaromaCommonSteps, write_to_json


logger = logging.getLogger()


@fixture(scope="session")
def context():
    yield Context()


@mark.validated
@mark.order(3010)
def test_snapshot_tc2_C57482143(context: context):
    """
    Test Description:
        TC2 - Verify Customer able to view overall snapshots usage data for the specific time intervals
    Test ID: C57482143
    curl cmd:
        curl --location 'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/snapshots-usage-trend?start-time=2023-05-02T16%3A05%3A00Z&end-time=2023-08-16T16%3A05%3A00Z' --header {TOKEN}
    """
    logging.Logger("TestCase Started")
    logger.info("PQA Testing -> Consumption -> Snapshots -> T31996043")
    logger.info("TC2, Jira ID: 	C57482143")
    logger.info("Running pre-requisite: Array configuration")

    """
    Prepare the arrays for test by creating required data.
        Test Description:
        To verify customer is able to view details of overall snapshots usage data for the specific time intervals
        
    Automation blocks:
        Test case verifies customer is able to view snapshot usage  for specific interval of time
        Verification is done  hourly, daily and weekly granularity  
        startTime:  Define the start time for filtering.
        endTime:  Define the end time for filtering.
    """
    logger.info("Start of test case")
    logger.info("Running pre-requisite: Array configuration")

    # Object creation
    pcs_obj = PanaromaCommonSteps(context=context)
    array_obj = ArrayConfigParser(context=context)
    url = context.cluster.panorama_url
    api_header = context.api_header
    snapshot_obj = SnapshotsInfo(url=url, api_header=api_header)

    # Test case execution
    logger.info("\n Test case execution - started")

    granularity_list = [randint(1, 7), randint(8, 180), randint(190, 360)]
    granularity_list = [
        {"days": randint(190, 200), "granularity": Granularity.weekly},
        {"days": randint(8, 180), "granularity": Granularity.daily},
        {"days": randint(1, 7), "granularity": Granularity.hourly},
    ]

    for granularity in granularity_list:
        granul = granularity["granularity"].value
        etime = pcs_obj.get_last_collection_end_time()
        time_interval = pcs_obj.get_timeinterval(granul, etime)

        start_date = time_interval["starttime"].replace("T", " ").replace("Z", "")
        end_date = time_interval["endtime"].replace("T", " ").replace("Z", "")

        logger.info(f"\n Start date - {start_date} \n End date {end_date} \n Granularity - {granul}")

        # Expected Mock /data from array
        array_snapshot_usage_trend: SnapshotUsageTrend = array_obj.get_snapshots_usage_trend(
            startTime=start_date, endTime=end_date, granularity=granul
        )

        logger.info(
            f"\n Expected Snap usage trend for granularity value {granul} from Mock data \n {array_snapshot_usage_trend}"
        )
        logging.info("\n Array response: Snap usage trend")
        logging.info(json.dumps(array_snapshot_usage_trend.to_dict(), indent=4))

        write_to_json(
            pd.DataFrame(array_snapshot_usage_trend.items),
            f"{pcs_obj.json_path}/array_snap_usage_trend_{granul}_{Path(__file__).stem}.json",
            sort_by="timeStamp",
        )

        start_date = time_interval["starttime"]
        end_date = time_interval["endtime"]

        # Get API response
        api_snapshot_usage_trend: SnapshotUsageTrend = pcs_obj.get_all_response(
            snapshot_obj.get_snapshots_usage_trend,
            startTime=start_date,
            endTime=end_date,
        )

        logger.info(f"\n Actual Snap usage trend for granularity value {granul} from ETL \n {api_snapshot_usage_trend}")
        logging.info("\n REST API response: Snap usage trend")
        logging.info(json.dumps(api_snapshot_usage_trend.to_dict(), indent=4))

        write_to_json(
            pd.DataFrame(api_snapshot_usage_trend.items),
            f"{pcs_obj.json_path}/api_snap_usage_trend_{granul}_{Path(__file__).stem}.json",
            sort_by="timeStamp",
        )

        # Verification steps

        _verify_snap_usage_trend_graph(
            actual_obj=api_snapshot_usage_trend, expected_obj=array_snapshot_usage_trend, granul=granul
        )

    logger.info("Test case execution - completed")


def _verify_snap_usage_trend_graph(actual_obj: SnapshotUsageTrend, expected_obj: SnapshotUsageTrend, granul: str):
    """This function verifies whether the expected snapshot usage and actual usage trend matches or not

    Args:
        actual_obj (SnapshotUsageTrend): expected snap usage trend object
        expected_obj (SnapshotUsageTrend): actual/RESTAPI snap usage trend object
    """
    params = list(TotalSnapshotsUsage.__annotations__.keys())
    ignore_param = ["id", "type", "generation", "resourceUri", "consoleUri", "name"]

    check_param = [fields for fields in params if fields not in ignore_param]

    logging.info(f"\n Verification starts: Snap usage trend for granuarity ->  '{granul}'")

    assert expected_obj.total == actual_obj.total, "\n Mis-match for total count of Snapshot usage trend"

    for act_usage_item in actual_obj.items:
        match = 0
        for exp_usage_item in expected_obj.items:
            if act_usage_item.timeStamp == exp_usage_item.timeStamp:
                for param in check_param:
                    assert act_usage_item.__getattribute__(param) == exp_usage_item.__getattribute__(
                        param
                    ), f"\n Parameter Values are not matching. REST API/Actual value: {act_usage_item.__getattribute__(param)} and Expected/Array value: {exp_usage_item.__getattribute__(param)}"
                match = 1
            if match:
                break

    assert (
        match == 1
    ), f"\n Actual Data {act_usage_item} in REST API response is not present in Expected data {exp_usage_item}"

    logging.info(f"\n Verification Completed: Snap usage trend for granuarity ->  '{granul}'")
