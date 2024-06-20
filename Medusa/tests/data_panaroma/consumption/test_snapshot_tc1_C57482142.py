"""
Test Case ID C57482142
Test Description :- To verify customer is able to view details of snapshots consumption 
"""

# Standard libraries
import logging
from pathlib import Path
import pandas as pd
from pytest import mark, fixture


# Internal libraries
from lib.dscc.data_panorama.consumption.api.snapshots_api import SnapshotsInfo
from lib.dscc.data_panorama.consumption.models.snapshots import SnapshotConsumption
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser

# Tests
from tests.e2e.data_panorama.panorama_context import Context
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, write_to_json

logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING) #To remove unnecessary logs

@fixture(scope="session")
def context():
    yield Context()


@mark.validated
@mark.order(3005)
def test_snapshot_tc1_C57482142(context: context):
    """
    This test case validates the details of all the snapshots consumption related information like numSnapshots,totalSizeInBytes,Cost,previousMonthCost,currentMonthCost between array and api calls.
    Preconditions:
    Prepare the arrays for test by creating required data.
    data_set:- Define configuration parameters for each array under test.
    create_config:- Function configures the array as per the data_set.
    trigger_data_collection:- Function triggers the data collection.
    sleep for 5 minutes. To allow data collection and computation
    get_snapshot_consumption:- Function returns the data related to snapshot consumption for verification with API response.
                                 This is the expected data of the test case against which actual values will be compared.

    """
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
    array_snapshot_consumption: SnapshotConsumption = acp_obj.get_snapshot_consumption()

    logger.info(f"\n Expected Snap consumption with Mock data \n {array_snapshot_consumption}")
    logging.info("\n Array response: Snap consumption")

    write_to_json(
        pd.DataFrame([array_snapshot_consumption.to_dict()]),
        f"{pcs_obj.json_path}/array_snap_consumption_{Path(__file__).stem}.json",
        sort_by="id",
    )

    # Get API response
    api_snapshot_consumption: SnapshotConsumption = snapshot_obj.get_snapshot_consumption()
    logger.info(f"\n REST API Snap consumption\n {api_snapshot_consumption}")
    logging.info("\n REST API response: Snap consumption")

    write_to_json(
        pd.DataFrame([api_snapshot_consumption.to_dict()]),
        f"{pcs_obj.json_path}/api_snap_consumption_{Path(__file__).stem}.json",
        sort_by="id",
    )

    # Verification steps

    _verify_snap_consumption(actual_obj=api_snapshot_consumption, expected_obj=array_snapshot_consumption)

    logger.info("Test case execution - completed")


def _verify_snap_consumption(actual_obj: SnapshotConsumption, expected_obj: SnapshotConsumption):
    """This function verifies whether the expected snapshot consumption and actual snap consumption matches or not
    Args:
        actual_obj (SnapshotConsumption): expected snap consumption object
        expected_obj (SnapshotConsumption): actual/RESTAPI snap consumption object
    """
    params = list(SnapshotConsumption.__annotations__.keys())
    ignore_param = ["id", "type", "generation", "resourceUri", "consoleUri", "name"]

    check_param = [fields for fields in params if fields not in ignore_param]

    logging.info("\n Verification starts: Snapshot consumption ")

    for param in check_param:
        if param == "cost" or param == "currentMonthCost" or param == "previousMonthCost":
            diff = actual_obj.__getattribute__(param) - expected_obj.__getattribute__(param)
            assert (
                diff <= 0.10
            ), f"\nParameter {param} Values are not matching.\n REST API/Actual value: {actual_obj.__getattribute__(param)} and Expected/Array value: {expected_obj.__getattribute__(param)}"

        else:
            assert actual_obj.__getattribute__(param) == expected_obj.__getattribute__(
                param
            ), f"\nParameter {param} Values are not matching.\n REST API/Actual value: {actual_obj.__getattribute__(param)} and Expected/Array value: {expected_obj.__getattribute__(param)}"

    logging.info("\n Verification completed: Snaphot consumption ")
