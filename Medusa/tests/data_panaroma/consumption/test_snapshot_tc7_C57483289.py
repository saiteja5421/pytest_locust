# standard libraries
import json
import logging
from pathlib import Path
import pandas as pd
from pytest import mark, fixture

# Internal libraries

from lib.dscc.data_panorama.consumption.api.snapshots_api import SnapshotsInfo
from lib.dscc.data_panorama.consumption.models.snapshots import Snapshots, SnapshotsDetail

# Common steps
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, write_to_json
from tests.e2e.data_panorama.panorama_context import Context
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser


logger = logging.getLogger()


@fixture(scope="session")
def context():
    yield Context()


@mark.validated
@mark.order(3035)
def test_snapshot_tc7_C57483289(context: Context):
    """
    To verify customer is able to view details of Snapshots
    Automation blocks:
        1. Create mock data based out of data_set
        2. Collect array and API snapshot creation data
        3. Validation of Array object data against API object data
    """
    logger.info("Start of test case")
    logger.info("PQA Testing -> Consumption -> snapshots -> TC7_C57483289")

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

    # Expected Mock /data from array

    array_snapshots: Snapshots = array_obj.get_snapshot_details()

    logger.info(f"\n Expected Snaphots from Mock data \n {array_snapshots}")
    logging.info("\n Array response: Snaphots")
    logging.info(json.dumps(array_snapshots.to_dict(), indent=4))

    write_to_json(
        pd.DataFrame(array_snapshots.items),
        f"{pcs_obj.json_path}/array_snaphots_{Path(__file__).stem}.json",
        sort_by="name",
    )

    # Get API response
    api_snapshots: Snapshots = pcs_obj.get_all_response(func=snapshot_obj.get_snapshots_details)
    logger.info(f"\n Actual Snaphots  from REST API \n {api_snapshots}")
    logging.info("\n REST API response: Snaphots ")
    logging.info(json.dumps(api_snapshots.to_dict(), indent=4))

    write_to_json(
        pd.DataFrame(api_snapshots.items),
        f"{pcs_obj.json_path}/api_snaphots_{Path(__file__).stem}.json",
        sort_by="name",
    )

    # Verification steps

    _verify_snapshot_details(actual_obj=array_snapshots, expected_obj=api_snapshots)

    logger.info("Test case execution - completed")


def _verify_snapshot_details(actual_obj: Snapshots, expected_obj: Snapshots):
    """This function verifies whether the expected snapshots and actual snapshots matches or not

    Args:
        actual_obj (Snapshots): expected snaphots object
        expected_obj (Snapshots): actual/RESTAPI snapshots  object
    """
    params = list(SnapshotsDetail.__annotations__.keys())
    ignore_param = ["id", "type", "generation", "resourceUri", "consoleUri"]

    check_param = [fields for fields in params if fields not in ignore_param]

    logging.info("\n Verification starts: Snaphots ")

    assert expected_obj.total == actual_obj.total, "\n Mis-match for total count of Snapshots"

    for act_snap in actual_obj.items:
        match = 0
        for exp_snap in expected_obj.items:
            if act_snap.name == exp_snap.name:
                for param in check_param:
                    assert act_snap.__getattribute__(param) == exp_snap.__getattribute__(
                        param
                    ), f"\n  Parameter {param} - Values are not matching. REST API/Actual value: {act_snap.__getattribute__(param)} and Expected/Array value: {exp_snap.__getattribute__(param)}"
                match = 1
            if match:
                break

    assert (
        match == 1
    ), f"\n Actual Data {act_snap.name} in REST API response is not present in Expected data {exp_snap.name}"

    logging.info("\n Verification completed: Snaphots")
