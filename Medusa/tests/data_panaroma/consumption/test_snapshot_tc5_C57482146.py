"""
Test Case ID C57482146
Test Description :- To verify customer is able to view details of snapshots creation
"""

# Standard libraries
import json
import logging
import pandas as pd
from pytest import mark, fixture
from random import randint
from pathlib import Path

# Internal libraries
from lib.dscc.data_panorama.consumption.api.snapshots_api import SnapshotsInfo
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from lib.dscc.data_panorama.consumption.models.snapshots import SnapshotCreationTrend, TotalSnapshotsCreated

# Tests
from tests.e2e.data_panorama.panorama_context import Context
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from tests.steps.data_panorama.panaroma_common_steps import Granularity, PanaromaCommonSteps, write_to_json

logger = logging.getLogger()


@fixture(scope="session")
def context():
    yield Context()


@mark.validated
@mark.order(3025)
def test_snapshot_tc5_C57482146(context: context):
    """
    Test Description:
        To verify customer is able to view details of Snapshots created for the specific time intervals
    Automation blocks:
        1. Create mock data based out of data_set
        2. For each of period in time_period, whole test is executed to validate all granularity
        3. Collect array and API snapshot creation data
        4. Array object data against API object data validation

    """
    logger.info("Start of test case")
    logger.info("Running pre-requisite: Array configuration")

    # Object creation
    api_obj = PanaromaCommonSteps(context=context)
    array_obj = ArrayConfigParser(context=context)
    url = context.cluster.panorama_url
    api_header = context.api_header
    snapshot_obj = SnapshotsInfo(url=url, api_header=api_header)

    # Test case execution
    logger.info("\n Test case execution - started")
    granularity_list = [
        {"days": randint(190, 200), "granularity": Granularity.weekly},
        {"days": randint(8, 180), "granularity": Granularity.daily},
        {"days": randint(1, 7), "granularity": Granularity.hourly},
    ]
    # Testing for hourly, daily and weekly granularity
    for granularity in granularity_list:
        granul = granularity["granularity"].value
        etime = api_obj.get_last_collection_end_time()
        time_interval = api_obj.get_timeinterval(granul, etime)

        start_date = time_interval["starttime"].replace("T", " ").replace("Z", "")
        end_date = time_interval["endtime"].replace("T", " ").replace("Z", "")

        logger.info(f"\nStart date - {start_date} \n End date {end_date} \n Granularity - {granul}")

        # Expected Mock /data from array
        array_snapshot_creation_trend: SnapshotCreationTrend = array_obj.get_snapshots_creation_trend(
            startTime=start_date, endTime=end_date, granularity=granul
        )

        logger.info(
            f"\n Expected Snap creation trend for granularity value {granul} from Mock data \n {array_snapshot_creation_trend}"
        )
        logging.info("\n Array response: Snap creation trend")
        logging.info(json.dumps(array_snapshot_creation_trend.to_dict(), indent=4))

        write_to_json(
            pd.DataFrame(array_snapshot_creation_trend.items),
            f"{api_obj.json_path}/array_snap_creation_trend_{granul}_{Path(__file__).stem}.json",
            sort_by="updatedAt",
        )

        start_date = time_interval["starttime"]
        end_date = time_interval["endtime"]

        # Get API response
        api_snapshot_creation_trend: SnapshotCreationTrend = api_obj.get_all_response(
            snapshot_obj.get_snapshots_creation_trend,
            startTime=start_date,
            endTime=end_date,
        )

        logger.info(
            f"\n Actual Snap creation trend for granularity value {granul} from ETL \n {api_snapshot_creation_trend}"
        )
        logging.info("\n REST API response: Snap creation trend")
        logging.info(json.dumps(api_snapshot_creation_trend.to_dict(), indent=4))

        write_to_json(
            pd.DataFrame(api_snapshot_creation_trend.items),
            f"{api_obj.json_path}/api_snap_creation_trend_{granul}_{Path(__file__).stem}.json",
            sort_by="updatedAt",
        )

        # Verification steps

        _verify_snap_creation_trend_graph(
            actual_obj=api_snapshot_creation_trend, expected_obj=array_snapshot_creation_trend, granul=granul
        )

    logger.info("Test case execution - completed")


def _verify_snap_creation_trend_graph(
    actual_obj: SnapshotCreationTrend, expected_obj: SnapshotCreationTrend, granul: str
):
    """This function verifies whether the expected snapshot creation and actual creation trend matches or not

    Args:
        actual_obj (SnapshotCreationTrend): expected snap creation trend object
        expected_obj (SnapshotCreationTrend): actual/RESTAPI snap creation trend object
    """
    params = list(TotalSnapshotsCreated.__annotations__.keys())
    ignore_param = ["id", "type", "generation", "resourceUri", "consoleUri", "name", "aggrWindowTimestamp"]

    check_param = [fields for fields in params if fields not in ignore_param]

    logging.info(f"\n Verification started for Snap creation trend : granularity {granul}")

    assert expected_obj.total == actual_obj.total, "\n Mis-match for total count of Snapshot creation trend"

    for act_creation_item in actual_obj.items:
        match = 0
        for exp_creation_item in expected_obj.items:
            if act_creation_item.updatedAt == exp_creation_item.updatedAt:
                for param in check_param:
                    assert act_creation_item.__getattribute__(param) == exp_creation_item.__getattribute__(
                        param
                    ), f"{param} Values are not matching. REST API/Actual value: {act_creation_item.__getattribute__(param)} and Expected/Array value: {exp_creation_item.__getattribute__(param)}"
                match = 1
            if match:
                break

    assert (
        match == 1
    ), f" Actual Data {act_creation_item} in REST API response is not present in Expected data {exp_creation_item}"

    logging.info(f"\n Verification completed for Snap creation trend:  granularity {granul} ")
