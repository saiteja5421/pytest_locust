# Standard libraries

import json
import logging
from pathlib import Path
import pandas as pd

from pytest import fixture, mark
from pytest_testrail.plugin import pytestrail
from tests.e2e.data_panorama.panorama_context import Context
from lib.dscc.data_panorama.app_lineage.models.app_lineage import VolumesDetail
from lib.dscc.data_panorama.app_lineage.models.app_lineage import ApplicationList
from lib.dscc.data_panorama.app_lineage.api.app_lineage_api import AppLineageInfo
from tests.steps.data_panorama.app_lineage.app_lineage_steps import (
    get_volume_not_tagged_with_application,
    verify_volume_details,
)
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, write_to_json


logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING)
logging.getLogger("faker").setLevel(logging.WARNING)

@fixture(scope="session")
def context():
    yield Context()


# @mark.skip(reason="DCS-11675")
@mark.validated
@mark.order(5010)
@pytestrail.case("C57482152")
def test_app_lineage_tc2_C57482152(context: context):
    """
    To verify customer is able to see volume details corresponding to an application
    API :   'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/systems/{system-id}/applications/{id}/volumes'
    Test parameters:
    List of parameters that needs to be updated before execution.
    id              : str       - app id
    system_id       : str       - system id

    Pre-requisites:
    Create 10 volumes and tag 7 of them to different applications(Outlook, AWS, Oracle)
    Create 5 snapshots on 5 volumes and 15 snapshots on remaining volume
    Create 5 clones on 5 volumes and 15 clones on remaining volume

    """

    pcs_obj = PanaromaCommonSteps(context=context)
    acp_obj = ArrayConfigParser(context=context)
    db_name = pcs_obj.input_golden_db_path

    logger.info(f"Test execution started")

    # Get app_id:
    expected_app_obj: ApplicationList = acp_obj.get_applications()
    if expected_app_obj.total < 0:
        assert "No Applications present"
    else:
        api_vol_list = []
        for appindex in range(expected_app_obj.total):
            app_id = expected_app_obj.items[appindex].id
            app_name = expected_app_obj.items[appindex].name
            system_id = expected_app_obj.items[appindex].systemId
            sys_name = expected_app_obj.items[appindex].system

            logger.info(f"Application ID : {app_id} and system ID : {system_id}")
            logging.info(f"\n Application ID : '{app_id}' and system ID : '{system_id}'")

            # Get volume list for specific application id - Expected Data

            array_obj: VolumesDetail = acp_obj.get_application_volumes_detail(app_id=app_id, system_id=system_id)

            logger.info(f"Expected output  : {array_obj}")
            logger.info(f"\n Expected Volume list from Mock data {array_obj}")
            logging.info("\n Array response: Volume list from Mock data")
            logging.info(json.dumps(array_obj.to_dict(), indent=4))

            write_to_json(
                pd.DataFrame(array_obj.items),
                f"{pcs_obj.json_path}/array_volume_details_appid{app_id}_{Path(__file__).stem}.json",
                sort_by="name",
            )

            # REST CALL - actual data
            app_vol_info = AppLineageInfo(context.cluster.panorama_url, context.api_header)

            api_obj: VolumesDetail = pcs_obj.get_all_response(
                func=app_vol_info.get_application_volumes_detail, app_id=app_id, system_id=system_id
            )

            logger.info(f"Actual output  : {api_obj}")
            logger.info(f"\n Actual/REST API Volume list {api_obj}")
            logging.info("\n REST API response: Volume list ")
            logging.info(json.dumps(api_obj.to_dict(), indent=4))

            write_to_json(
                pd.DataFrame(api_obj.items),
                f"{pcs_obj.json_path}/api_volume_details_appid{app_id}_{Path(__file__).stem}.json",
                sort_by="name",
            )

            for item in api_obj.items:
                api_vol_list.append(item.id)

            # Verification steps

            logger.info(f"\nVerification of expected and actual output for app {app_name} in the system {sys_name}")

            verify_volume_details(expected_vol_obj=array_obj, actual_vol_obj=api_obj)

    # verify volume which not tagged with application is displayed on Applineage tile
    logger.info(f"\n verify that volume not tagged with application is not displayed on Applineage tile")
    volume_with_no_app = get_volume_not_tagged_with_application(db_name=db_name)

    assert (
        volume_with_no_app not in api_vol_list
    ), f"\n Verification failed: Volume '{volume_with_no_app}' is present in the list of volumes tagged with application."

    logger.info(f"Test execution completed")
