
import random
import pandas as pd
import sqlalchemy
from lib.dscc.data_panorama.app_lineage.models.app_lineage import (
    Application,
    ApplicationClonesInfo,
    ApplicationList,
    ApplicationSnapshotsInfo,
    ApplicationVolumesInfo,
    VolumesDetail,
    ClonesDetail,
    SnapshotsDetail,
)
from lib.dscc.data_panorama.app_lineage.api.app_lineage_api import AppLineageInfo


class AppLineageFunc:
    """
    Class for AppLineageFunc used to host App lineage library functions.
    functions present:
        verify_app_info(): validates whether the actual and expected application details matches or not
        verify_volume_snap_clone_for_app(): validates whether the actual and expected volume details for the specific application  matches or not
        verify_snap_details() : validates whether the actual and expected snapshot details for the specific volume id for that application matches or not
        verify_clone_details() :validates whether the actual and expected snapshot details for the specific volume id for that application matches or not
    """

    def __init__(self, url: str) -> None:
        """
         __init__: Constructs all the necessary attributes for the AppLineageFunc object.

         -----------
         Parameters:
         -----------
             url :- url  of type string and its the url path eg: http://127.0.0.1:5002/api/v1
             type:- str
        -----------------
                     Arguments:
                     -----------------
         self.url :- Stores the user passed url
         self.applineagemanager = Object of AppLineageInfo class
        """

        self.url = url
        self.applineagemanager = AppLineageInfo(self.url)


def verify_app_info(expected_app_obj: ApplicationList, actual_app_obj: ApplicationList):
    """
    This function validates whether the actual and expected application details tagged with volumes for that application matches or not

    The function accept 2 parameters of type class ApplicationList
    expected_app_obj: this is expected output(data from array captured from array consumption library)
    actual_app_obj: this is output from REST API url(/data-observability/v1alpha1/applications)

    """
    # Get list of keys/all fields  from Application object
    params = list(Application.__dataclass_fields__.keys())

    # create list of param to ignore while doing verification of test
    ignore_param = ["type", "generation", "resourceUri", "consoleUri"]

    # create final list of param need to verified
    check_param = [element for element in params if element not in ignore_param]

    assert expected_app_obj.total == actual_app_obj.total, f"Application count mismatch"

    for act_app in actual_app_obj.items:
        match_flag: bool = False
        for exp_app in expected_app_obj.items:
            if act_app.id == exp_app.id:
                for param in check_param:
                    assert act_app.__getattribute__(param) == exp_app.__getattribute__(
                        param
                    ), f"\n Parameter {param} -Values not matching. \n REST API: {act_app.__getattribute__(param)} and Expected: {exp_app.__getattribute__(param)}"
                match_flag = True
            if match_flag:
                break

    assert (
        match_flag == True
    ), f"Application Data mismatch  Actual application  ID : {act_app.id}  Expected application ID : {exp_app.id}"


def verify_volume_details(expected_vol_obj: VolumesDetail, actual_vol_obj: VolumesDetail):
    """This function validates whether the actual and expected volume details for the specific application id matches or not

    The function accept 2 parameters of type class VolumesDetail
    expected_snap_obj: this is expected output(data from array captured from array consumption library)
    actual_snap_obj: this is output from REST API url(/data-observability/v1alpha1/applications/{app-id}/volumes)

    """
    assert expected_vol_obj.total == actual_vol_obj.total, "volume count mismatch"

    params = list(ApplicationVolumesInfo.__dataclass_fields__.keys())

    ignore_param = ["type", "resourceUri", "consoleUri", "generation"]

    check_param = [element for element in params if element not in ignore_param]

    for act_app in actual_vol_obj.items:
        flag = 0
        for exp_app in expected_vol_obj.items:
            if act_app.id == exp_app.id:
                for param in check_param:
                    assert act_app.__getattribute__(param) == exp_app.__getattribute__(
                        param
                    ), f"Parameter {param} - Values not matching  REST API: {act_app.__getattribute__(param)} and Expected: {exp_app.__getattribute__(param)} . volume name is {exp_app.name} . system name is {act_app.system}"
                flag = 1
            if flag:
                break
    assert flag == 1, f"Volume data mismatch : Actual volume ID : {act_app.id}  and  Expected volume ID : {exp_app.id}"


def verify_snap_details(expected_snap_obj: SnapshotsDetail, actual_snap_obj: SnapshotsDetail):
    """This function validates whether the actual and expected snapshot details for the specific volume id for that application matches or not

    The function accept 2 parameters of type class SnapshotsDetail
    expected_snap_obj: this is expected output(data from array captured from array consumption library)
    actual_snap_obj: this is output from REST API url(/data-observability/v1alpha1/volumes/{volume-uuid}/snapshots)"""
    # Get list of keys/all fields  from Application object
    params = list(ApplicationSnapshotsInfo.__dataclass_fields__.keys())

    # create list of param to ignore while doing verification of test
    ignore_param = ["type", "generation", "resourceUri", "consoleUri","totalSizeInBytes","expiresAt"] # expiresAt for snap may be 2038 due to no expiry date so ignoring it

    # create final list of param need to verified
    check_param = [element for element in params if element not in ignore_param]

    assert expected_snap_obj.total == actual_snap_obj.total, "Snap count for volume mis-match"
    match_flag: bool = False
    for act_snap in actual_snap_obj.items:
        match_flag: bool = False
        for exp_snap in expected_snap_obj.items:
            if act_snap.id == exp_snap.id:
                for param in check_param:
                    assert act_snap.__getattribute__(param) == exp_snap.__getattribute__(
                        param
                    ), f"\n Parameter {param} - Values not matching REST API: {act_snap.__getattribute__(param)} and Expected: {exp_snap.__getattribute__(param)}"
                match_flag = True
            if match_flag:
                break
    # assert match_flag == True, f"\n Snapshot data mismatch : Actual snapshot ID : {act_snap.id}  and  Expected snapshot ID : {exp_snap.id}"


def verify_clone_details(expected_clone_obj: ClonesDetail, actual_clone_obj: ClonesDetail):
    """This function validates whether the actual and expected clone details for the specific volume id for that application matches or not

    The function accept 2 parameters of type class CloneDetail
    expected_clone_obj: this is expected output(data from array captured from array consumption library)
    actual_clone_obj: this is output from REST API url(/data-observability/v1alpha1/volumes/{volume-uuid}/clones)
    """
    # Get list of keys/all fields  from Application object
    params = list(ApplicationClonesInfo.__dataclass_fields__.keys())

    # create list of param to ignore while doing verification of test
    ignore_param = ["type", "generation", "resourceUri", "consoleUri"]

    # create final list of param need to verified
    check_param = [element for element in params if element not in ignore_param]

    assert expected_clone_obj.total == actual_clone_obj.total, "Clone count for volume mis-match"

    for act_clone in actual_clone_obj.items:
        match_flag: bool = False
        for exp_clone in expected_clone_obj.items:
            if act_clone.id == exp_clone.id:
                for param in check_param:
                    assert act_clone.__getattribute__(param) == exp_clone.__getattribute__(
                        param
                    ), f"\n Parameter {param} - Values not matching REST API: {act_clone.__getattribute__(param)} and Expected: {exp_clone.__getattribute__(param)}"
                match_flag = True
            if match_flag:
                break
    assert match_flag == 1, f"\n Clone data mismatch : Actual clone ID : {act_clone.id}  and  Expected clone ID : {exp_clone.id}"



def get_volume_not_tagged_with_application(db_name: str) -> str :
    """This function retuns a volume id which is not tagged with any application

    Args:
        db_name (str): path for database

    Returns:
        str: volume id
    """
    engine = sqlalchemy.create_engine("sqlite:///%s" % db_name, execution_options={"sqlite_raw_colnames": True})
    conn = engine.connect()

    collection_df = pd.read_sql_table("collections_info", con=conn)
    coll_list = collection_df["collection_name"].unique()
    latest_collection = coll_list[-1]

    vol_dt1_df = pd.read_sql_table("dt1_collections_volumes", con=conn)
    latest_collection_vol_dt1_df = vol_dt1_df[vol_dt1_df["collection_name"] == latest_collection]

    vol_dt2_df = pd.read_sql_table("dt2_collections_volumes", con=conn)
    latest_collection_vol_dt2_df = vol_dt2_df[vol_dt2_df["collection_name"] == latest_collection]

    latest_collection_vol_dt1_df = latest_collection_vol_dt1_df[["volume_id", "app_id"]]
    latest_collection_vol_dt2_df = latest_collection_vol_dt2_df[["volume_id", "app_id"]]

    latest_collection_vol_dt1_no_app = latest_collection_vol_dt1_df.loc[
        (latest_collection_vol_dt1_df["app_id"].isnull()) | (latest_collection_vol_dt1_df["app_id"] == "0")
    ]

    latest_collection_vol_dt2_no_app = latest_collection_vol_dt2_df.loc[
        (latest_collection_vol_dt2_df["app_id"].isnull()) | (latest_collection_vol_dt2_df["app_id"] == "0")
    ]
    all_volumes_tagged_without_app = pd.concat([latest_collection_vol_dt1_no_app, latest_collection_vol_dt2_no_app]).reset_index(
        drop=True
    )

    random_index = random.randint(0, all_volumes_tagged_without_app.shape[0] - 1)

    return all_volumes_tagged_without_app.iloc[random_index]["volume_id"]
