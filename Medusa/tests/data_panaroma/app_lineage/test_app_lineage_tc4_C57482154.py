# Standard libraries
import json
import logging
from pathlib import Path
import random
import pandas as pd

from pytest import fixture, mark

from tests.e2e.data_panorama.panorama_context import Context
from lib.dscc.data_panorama.app_lineage.api.app_lineage_api import AppLineageInfo
from lib.dscc.data_panorama.app_lineage.models.app_lineage import (
    ApplicationList,
    ClonesDetail,
    SnapshotsDetail,
    VolumesDetail,
)
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from tests.steps.data_panorama.consumption.wastage_steps import WastageVolumes
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, write_to_json
from tests.steps.data_panorama.app_lineage.app_lineage_steps import (
    verify_snap_details,
    verify_clone_details,
)

logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING)
logging.getLogger("faker").setLevel(logging.WARNING)


@fixture(scope="session")
def context():
    yield Context()
    # Test Clean up will be added later

# @mark.skip(reason="REST API Changes/design changes")
@mark.validated
@mark.order(1020)
def test_app_lineage_tc4_C57482154(context: context):
    """
    Verify customer able to see snapshot and clone details
    Pre-requisites:
    Create 10 volumes and tag 7 of them to different applications(Outlook, AWS, Oracle)
    Create 5 snapshots on 5 volumes and 15 snapshots on remaining volume
    Create 5 clones on 5 volumes and 15 clones on remaining volume

    """

    # pcs_obj = PanaromaCommonSteps(context=context)
    pcs_obj : PanaromaCommonSteps = PanaromaCommonSteps(context=context)
    acp_obj : ArrayConfigParser = ArrayConfigParser(context=context)
    api_header = context.api_header
    url = context.cluster.url

    wastage_array_obj = WastageVolumes(url=url, api_header=api_header)
    # Collecting Expected data

    # List of application list from mock data and Select random app for verification
    expected_app_obj: ApplicationList = acp_obj.get_applications()
    appindex = random.randint(0, expected_app_obj.total)

    # volume details for perticulat application from mock data and Selecting Random volume
    app_id = expected_app_obj.items[appindex].id
    system_id = expected_app_obj.items[appindex].systemId

    expected_vol_obj = acp_obj.get_application_volumes_detail(app_id=app_id,system_id=system_id)

    if expected_vol_obj.total < 0:
        assert "No Volumes present"
    else:
        api_clone_df_list = []
        arr_clone_df_list = []

        api_clone_list = []
        arr_clone_list = []
        for volindex in range(expected_vol_obj.total):
            sys_id = expected_vol_obj.items[volindex].systemId
            vol_id = expected_vol_obj.items[volindex].id
            app_vol_info = AppLineageInfo(context.cluster.panorama_url, context.api_header)

            # Expected Data
            # List of snapshots for perticular volume id from mock data

            # _snap_lineage(context, pcs_obj, acp_obj, app_id, sys_id, vol_id)

            # List of clones for perticular volume id from mock data
            
            # snap_list = 
            expected_snap_obj: SnapshotsDetail = acp_obj.get_app_vol_snap_list(sys_id=sys_id, vol_uuid=vol_id)
            
            for snap in expected_snap_obj.items:
                print(snap.id)

                actual_clone_obj: ClonesDetail = pcs_obj.get_all_response(
                    app_vol_info.get_application_clones_detail, system_id=sys_id,
                    snapshot_id=snap.id
                )
                logging.info(json.dumps(actual_clone_obj.to_dict(), indent=4))
                if actual_clone_obj.items != []:
                    api_clone_df_list.append(pd.DataFrame(actual_clone_obj.items))
                    api_clone_list.append(actual_clone_obj)

                expected_clone_obj: ClonesDetail = acp_obj.get_app_vol_clone_list(sys_id=sys_id, snap_id=snap.id)

                if expected_clone_obj.items != []:
                    arr_clone_df_list.append(pd.DataFrame(expected_clone_obj.items))
                    arr_clone_list.append(expected_clone_obj)
                
        clone_df= pd.concat(api_clone_df_list)
        write_to_json(
            clone_df,
            f"{pcs_obj.json_path}/api_clone_details_app_{app_id}_{Path(__file__).stem}.json",
            sort_by="name",
        )
        arr_clone_df= pd.concat(arr_clone_df_list)
        write_to_json(
            arr_clone_df,
            f"{pcs_obj.json_path}/arr_clone_details_app_{app_id}_{Path(__file__).stem}.json",
            sort_by="name",
        )

        for i in range(len(api_clone_list)):
            verify_clone_details(expected_clone_obj=arr_clone_list[i], actual_clone_obj=api_clone_list[i])

        