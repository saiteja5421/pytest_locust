# Standard libraries
import json
import logging
from pathlib import Path
import pandas as pd
from pytest import mark, fixture
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Internal libraries
from lib.dscc.data_panorama.consumption.api.snapshots_api import SnapshotsInfo
from lib.dscc.data_panorama.consumption.models.snapshots import MonthlySnapshotsCost, SnapshotCostTrend

# Common Steps
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, write_to_json
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser

# Common Tests
from tests.e2e.data_panorama.panorama_context import Context


logger = logging.getLogger()


@fixture(scope="session")
def context():
    yield Context()


@mark.validated
@mark.order(3030)
def test_snapshot_tc6_C57482147(context: Context):
    """
    Test Description:
        To verify customer is able to view details of Snapshots cost per month
    Automation blocks:
        1. Create mock data based out of data_set
        2. For each of period in time_period whole test is executed to validate all granularity
        3. get_all_response function gathers all array and API Snapshot cost data
        4. Array object data against API object data validation
    """

    logger.info("Start of test case")
    logger.info("Running pre-requisite: Array configuration")

    # Object creation

    pcs_obj = PanaromaCommonSteps(context=context)
    acp_obj = ArrayConfigParser(context=context)
    url = context.cluster.panorama_url
    api_header = context.api_header
    snapshot_obj = SnapshotsInfo(url=url, api_header=api_header)

    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    start_date = (end_date.replace(day=1) - relativedelta(months=5)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    # Test case execution
    logger.info("\n Test case execution - started")

    array_snapshot_cost_trend: SnapshotCostTrend = acp_obj.get_snapshots_cost_trend(
        start_date=start_date, end_date=end_date
    )

    logger.info(f"\n Expected Snap cost trend with Mock data \n {array_snapshot_cost_trend}")
    logging.info("\n Array response: Snap cost trend")
    logging.info(json.dumps(array_snapshot_cost_trend.to_dict(), indent=4))
    write_to_json(
        pd.DataFrame(array_snapshot_cost_trend.items),
        f"{pcs_obj.json_path}/array_snap_cost_trend_{Path(__file__).stem}.json",
        sort_by="month",
    )

    # Get API response
    api_snapshot_cost_trend: SnapshotCostTrend = pcs_obj.get_all_response(
        snapshot_obj.get_snapshots_cost_trend,
        startTime=start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        endTime=end_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    )
    logger.info(f"\n REST API Snap cost trend data \n {api_snapshot_cost_trend}")
    logging.info("\n REST API response: Snap cost trend")
    logging.info(json.dumps(api_snapshot_cost_trend.to_dict(), indent=4))
    write_to_json(
        pd.DataFrame(api_snapshot_cost_trend.items),
        f"{pcs_obj.json_path}/api_snap_cost_trend_{Path(__file__).stem}.json",
        sort_by="month",
    )
    # Verification steps
    _verify_snap_cost_graph(actual_obj=api_snapshot_cost_trend, expected_obj=array_snapshot_cost_trend)

    logger.info("Test case execution - completed")


def _verify_snap_cost_graph(actual_obj: SnapshotCostTrend, expected_obj: SnapshotCostTrend):
    """This function verifies whether the expected snapshot cost and actual snap cost trend matches or not
    Args:
        actual_obj (SnapshotCostTrend): actual/RESTAPI snaphot cost trend object
        expected_obj (SnapshotCostTrend): expected snapshot cost trend object
    """
    params = list(MonthlySnapshotsCost.__annotations__.keys())
    ignore_param = ["id", "type", "generation", "resourceUri", "consoleUri", "name"]

    check_param = [fields for fields in params if fields not in ignore_param]

    logging.info("\n Verification starts: Snapshot cost trend")

    assert expected_obj.total == actual_obj.total, "\n Mis-match for total count of Snapshot cost trend"

    for act_cost_item in actual_obj.items:
        match = 0
        for exp_cost_item in expected_obj.items:
            if act_cost_item.year == exp_cost_item.year and act_cost_item.month == exp_cost_item.month:
                for param in check_param:
                    if param == "cost":
                        diff = act_cost_item.__getattribute__(param) - exp_cost_item.__getattribute__(param)
                        assert (
                            diff <= 0.10
                        ), f"\nParameter {param} Values are not matching.\n REST API/Actual value: {act_cost_item.__getattribute__(param)} and Expected/Array value: {exp_cost_item.__getattribute__(param)}"

                    else:
                        assert act_cost_item.__getattribute__(param) == exp_cost_item.__getattribute__(
                            param
                        ), f"\nParameter {param} Values are not matching.\n REST API/Actual value: {act_cost_item.__getattribute__(param)} and Expected/Array value: {exp_cost_item.__getattribute__(param)}"
                match = 1
            if match:
                break

    assert (
        match == 1
    ), f"\n Actual Data {act_cost_item.range} in REST API response is not present in Expected data {exp_cost_item.range}"

    logging.info("\n Verification completed: Snapshot cost trend")
