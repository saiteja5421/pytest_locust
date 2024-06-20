"""
Test Case ID C57482144
Test Description :- To verify customer is able to view details of snapshots age
"""

# Standard libraries
import json
import logging
from pathlib import Path
import pandas as pd
from pytest import mark, fixture
import time
from random import randint


# Internal libraries
from lib.dscc.data_panorama.consumption.api.snapshots_api import SnapshotsInfo
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from lib.dscc.data_panorama.consumption.models.snapshots import SnapshotAge, SnapshotAgeTrend, SnapshotSize

# Tests
from tests.e2e.data_panorama.panorama_context import Context
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, write_to_json

logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING)
logging.getLogger("faker").setLevel(logging.WARNING)


@fixture(scope="session")
def context():
    test_context = Context()
    yield test_context


@mark.validated
@mark.order(3015)
def test_snapshot_tc3_C57482144(context: context):
    logger.info("Start of test case")

    """
    Test Description:
        To verify customer is able to view details of snapshots Age 
    Automation blocks:
        1. Create mock data based out of data_set
        2. get_all_response function gathers all array and API snapshot age data
        3. Array object data against API object data validation
    """

    logger.info("Running pre-requisite: Array configuration")

    # Variables
    pcs_obj = PanaromaCommonSteps(context=context)
    array_obj = ArrayConfigParser(context=context)
    url = context.cluster.panorama_url
    snapshot_obj = SnapshotsInfo(url=url, api_header=context.api_header)
    logger.info("Array configuration - completed")

    # Test case execution
    logger.info("Test case execution - started")

    # Get Array data
    array_snapshot_age_trend: SnapshotAgeTrend = array_obj.get_snapshots_age_trend()
    logger.info(f"\n Expected Snaphots from Mock data \n {array_snapshot_age_trend}")
    logging.info("\n Array response: Snaphots age trend")
    logging.info(json.dumps(array_snapshot_age_trend.to_dict(), indent=4))
    write_to_json(
        pd.DataFrame(array_snapshot_age_trend.items),
        f"{pcs_obj.json_path}/array_snaphots_{Path(__file__).stem}.json",
        sort_by="age",
    )

    # Get API response
    api_snapshot_age_trend: SnapshotAgeTrend = snapshot_obj.get_snapshots_age_trend()

    logger.info(f"\n Actual Snaphots  from REST API \n {api_snapshot_age_trend}")
    logging.info("\n REST API response: Snaphots age Trend ")
    logging.info(json.dumps(api_snapshot_age_trend.to_dict(), indent=4))

    write_to_json(
        pd.DataFrame(api_snapshot_age_trend.items),
        f"{pcs_obj.json_path}/api_snaphots_{Path(__file__).stem}.json",
        sort_by="age",
    )

    verify_snapshot_age_trend(
        api_snapshot_age_trend=api_snapshot_age_trend, array_snapshot_age_trend=array_snapshot_age_trend
    )

    logger.info("Test completed succesfully")


def verify_snapshot_age_trend(array_snapshot_age_trend: SnapshotAgeTrend, api_snapshot_age_trend: SnapshotAgeTrend):

    params = list(SnapshotAge.__dataclass_fields__.keys())
    subparm = list(SnapshotSize.__dataclass_fields__.keys())
    # create list of param to ignore while doing verification of test
    ignore_param = ["name", "id", "type", "generation", "resourceUri", "consoleUri"]

    # create final list of param need to verified
    check_param = [element for element in params if element not in ignore_param]

    assert array_snapshot_age_trend.total == api_snapshot_age_trend.total, f"Snapshot age trend graph count mismatch"

    for act_app in api_snapshot_age_trend.items:
        match_flag: bool = False
        for exp_app in array_snapshot_age_trend.items:
            if act_app.age == exp_app.age:
                for param in check_param:
                    if param != "sizeInfo":
                        assert act_app.__getattribute__(param) == exp_app.__getattribute__(
                            param
                        ), f"\n Parameter {param} -Values not matching. \n REST API: {act_app.__getattribute__(param)} and Expected: {exp_app.__getattribute__(param)}"
                    else:
                        assert len(act_app.sizeInfo) == len(
                            exp_app.sizeInfo
                        ), "length of sub buckets are not matching in Snapshot trend Graph"
                        for i in range(len(act_app.sizeInfo)):
                            assert getattr(act_app.sizeInfo[i], subparm[0]) == getattr(
                                exp_app.sizeInfo[i], subparm[0]
                            ), f"\n Num of snapcounts in sub buckets are not matching "
                match_flag = True
            if match_flag:
                break
    assert match_flag == True, f"\n Snapshot Age trend is not matching"
