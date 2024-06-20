"""
Test Case ID C57482145
Test Description :- To verify customer is able to view details of snapshots retention
"""

# Standard libraries
import logging
from pytest import mark, fixture
import json
from pathlib import Path
import pandas as pd


from random import randint
from datetime import datetime

# Internal libraries
from lib.dscc.data_panorama.consumption.api.snapshots_api import SnapshotsInfo
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from lib.dscc.data_panorama.consumption.models.snapshots import SnapshotRetentionTrend, SnapshotRetention

# Tests
from tests.e2e.data_panorama.panorama_context import Context
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, write_to_json

logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING)
logging.getLogger("faker").setLevel(logging.WARNING)


@fixture(scope="session")
def context():
    yield Context()


@mark.validated
@mark.order(3020)
def test_snapshot_tc4_C57482145(context: context):
    """
    Test Description:
        To verify customer is able to view details snapshots retention related information for the specific time intervals
    Automation blocks:
        1. Create mock data based out of data_set
        2. get_all_response function gathers all array and API snapshot retention data
        3. Array object data against API object data validation
    """

    logger.info("Start of test case")
    logger.info("Running pre-requisite: Array configuration")

    # Object creation

    pcs_obj = PanaromaCommonSteps(context=context)
    acp_obj = ArrayConfigParser(context=context)
    url = context.cluster.panorama_url
    api_header = context.api_header
    snapshot_obj = SnapshotsInfo(url=url, api_header=api_header)

    # Test case execution
    logger.info("\n Test case execution - started")

    # Expected Mock /data from array
    array_snapshot_retention_trend: SnapshotRetentionTrend = acp_obj.get_snapshots_retention_trend()

    logger.info(f"\n Expected Snap Retention trend with Mock data \n {array_snapshot_retention_trend}")
    logging.info("\n Array response: Snap retention trend")
    logging.info(json.dumps(array_snapshot_retention_trend.to_dict(), indent=4))

    # Get API response
    api_snapshot_retention_trend: SnapshotRetentionTrend = pcs_obj.get_all_response(
        snapshot_obj.get_snapshots_retention_trend
    )
    write_to_json(
        pd.DataFrame(array_snapshot_retention_trend.items),
        f"{pcs_obj.json_path}/array_snap_retention_trend_{Path(__file__).stem}.json",
        sort_by="range",
    )

    # Get API response
    api_snapshot_retention_trend: SnapshotRetentionTrend = snapshot_obj.get_snapshots_retention_trend()

    logger.info(f"\n Actual Snap Retention trend with values from ETL \n {api_snapshot_retention_trend}")
    logging.info("\n REST API response: Snap retention trend")
    logging.info(json.dumps(api_snapshot_retention_trend.to_dict(), indent=4))

    write_to_json(
        pd.DataFrame(api_snapshot_retention_trend.items),
        f"{pcs_obj.json_path}/api_snap_retention_trend_{Path(__file__).stem}.json",
        sort_by="range",
    )
    # Verification steps

    _verify_snap_retention_graph(actual_obj=api_snapshot_retention_trend, expected_obj=array_snapshot_retention_trend)

    logger.info("Test case execution - completed")


def _verify_snap_retention_graph(actual_obj: SnapshotRetentionTrend, expected_obj: SnapshotRetentionTrend):
    """This function verifies whether the expected snapshot retention and actual snap retetion trend matches or not
    Args:
        actual_obj (SnapshotRetentionTrend): expected snap retention trend object
        expected_obj (SnapshotRetentionTrend): actual/RESTAPI snap retention trend object
    """
    params = list(SnapshotRetention.__annotations__.keys())
    ignore_param = ["id", "type", "generation", "resourceUri", "consoleUri", "name"]

    check_param = [fields for fields in params if fields not in ignore_param]

    logging.info("\n Verification starts: Snap retention trend")

    assert expected_obj.total == actual_obj.total, "\n Mis-match for total count of Snapshot retention trend"

    for act_retention_item in actual_obj.items:
        match = 0
        for exp_retention_item in expected_obj.items:
            if act_retention_item.range == exp_retention_item.range:
                for param in check_param:
                    assert act_retention_item.__getattribute__(param) == exp_retention_item.__getattribute__(
                        param
                    ), f"\nParameter {param} Values are not matching.\n REST API/Actual value: {act_retention_item.__getattribute__(param)} and Expected/Array value: {exp_retention_item.__getattribute__(param)}"
                match = 1
            if match:
                break

    assert (
        match == 1
    ), f"\n Actual Data {act_retention_item.range} in REST API response is not present in Expected data {exp_retention_item.range}"

    logging.info("\n Verification completed: Snap retention trend")
