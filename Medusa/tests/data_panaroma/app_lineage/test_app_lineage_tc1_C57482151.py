# Standard libraries
import logging
import json
from pathlib import Path
import pandas as pd
from pytest import fixture, mark

from lib.dscc.data_panorama.app_lineage.models.app_lineage import ApplicationList

from tests.e2e.data_panorama.panorama_context import Context
from lib.dscc.data_panorama.app_lineage.api.app_lineage_api import AppLineageInfo
from tests.steps.data_panorama.app_lineage.app_lineage_steps import verify_app_info


from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, write_to_json
from pytest_testrail.plugin import pytestrail

logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING)
logging.getLogger("faker").setLevel(logging.WARNING)


@fixture(scope="session")
def context():
    yield Context()


# @mark.skip(reason="DCS-10998")
@mark.validated
@mark.order(5005)
@pytestrail.case("C57482151")
def test_app_lineage_tc1_C57482151(context: context):
    """
    To verify customer is able to see all applications listed under consumption/applications tab

    Test parameters:
    List of parameters that needs to be updated before execution.
    url: str       - REST API url

    Pre-requisites:
    Create 10 volumes and tag 7 of them to different applications(Outlook, AWS, Oracle)
    """

    pcs_obj = PanaromaCommonSteps(context=context)
    acp_obj = ArrayConfigParser(context=context)
    api_header = context.api_header
    url = context.cluster.url
    app_lineage_obj = AppLineageInfo(url=url, api_header=api_header)
    # Step1: Click on the view button of consumption tile and navigate to Applications tab

    # Expected Data - Mock/Actual

    expected_app_obj: ApplicationList = acp_obj.get_applications()
    logger.info(f"Expected output  : {expected_app_obj}")
    logger.info(f"\n Expected application list from Mock data {expected_app_obj}")
    logging.info("\n Array response: application list from Mock data")
    logging.info(json.dumps(expected_app_obj.to_dict(), indent=4))
    write_to_json(
        pd.DataFrame(expected_app_obj.items),
        f"{pcs_obj.json_path}/array_application_list_{Path(__file__).stem}.json",
        sort_by="id",
    )

    # REST CALL - actual data

    actual_app_obj: ApplicationList = pcs_obj.get_all_response(app_lineage_obj.get_applications)

    logger.info(f"Actual  output  : {actual_app_obj}")
    logger.info(f"\n Actual application list from ETL {actual_app_obj}")
    logging.info("\n REST API response: application list from ETL")
    logging.info(json.dumps(actual_app_obj.to_dict(), indent=4))
    write_to_json(
        pd.DataFrame(actual_app_obj.items),
        f"{pcs_obj.json_path}/api_application_list_{Path(__file__).stem}.json",
        sort_by="id",
    )

    # verify actual with expected

    verify_app_info(expected_app_obj=expected_app_obj, actual_app_obj=actual_app_obj)
