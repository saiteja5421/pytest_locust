# standard libraries
import logging
from tests.e2e.data_panorama.panorama_context import Context
from lib.dscc.data_panorama.consumption.api.volumes_api import VolumesInfo
from tests.steps.data_panorama.panaroma_common_steps import Granularity, PanaromaCommonSteps, write_to_json
from lib.dscc.data_panorama.consumption.models.volumes import TotalSnapshotsCopies
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from tests.steps.data_panorama.consumption.wastage_steps import WastageVolumes
from tests.steps.data_panorama.common_methods import get_path_params
from pytest import fixture, mark
from pathlib import Path
import pandas as pd

logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING) #To remove unnecessary logs

@fixture(scope="session")
def context():
    yield Context()


@mark.validated
@mark.order(1060)
@mark.parametrize("granularity", [Granularity.hourly, Granularity.daily, Granularity.weekly])

def test_volume_tc12_C57482017(context: context, granularity):
    """
    Test Description:
        TC12 - To verify customer is able to view Snapshot Copies created for a volume within the specified time interval
    Test ID: C57482017
    curl cmd:
        curl --location 'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/volumes-consumption/systems/8fb0584a00ef4710b0d602909cffccbd/volumes/c60cd95ddb9944d7b5def0edbc723484/snapshots?start-time=2023-05-31T00%3A00%3A00Z&end-time=2023-08-16T16%3A05%3A00Z' --header 'Authorization: Bearer {TOKEN}'
    Test parameters:
    List of parameters that needs to be updated before execution.

    volume_uuid     : str       - ID of volume under test.
    url             : str       - REST API url

    NOTE:
    This test will fail some times with weekly granularity

    Failure Case1:
    API: http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/volumes-consumption/systems/b4cbcb993be643cabdff847ba4c31639/volumes/50fabc18c3b2485c948db5c1cba0e457/snapshots?start-time=2022-11-14T00:00:00.000Z&end-time=2023-07-20T16:05:00.000Z&granularity=week

    Above API is one of the case where it will fail, hence attached here for referance
    Need to raise bug for that

    Failure Case2:
    Need to remove below two fields from API output
    "numClones", "cloneSizeInBytes"
    Need to raise a bug for this

    3rd Case:
    in collectionHour granularity date they are taking from snap creation time and hours and min they are taking from collection end time

    Need to get clarity on this

    As per design: Snapshot size cannot be calculated, so size fields are being skipped for now.

    """

    pcs_obj = PanaromaCommonSteps(context=context)

    # Expected object
    acp_obj = ArrayConfigParser(context=context)
    wastage_array_obj = WastageVolumes(url=context.cluster.panorama_url, api_header=context.api_header)
    # Actual Object
    volume_obj = VolumesInfo(context.cluster.panorama_url, context.api_header)

    db_name = acp_obj.steps_obj.golden_db_path
    table = "spark_snap_all_collection"
    params = ["volume_id", "system_id"]
    path_param = get_path_params(db_name=db_name, table=table, params=params)

    # Test case execution
    logger.info("Test case execution - started")

    granul = granularity.value
    # End time is taken based on collection end time so that we can pick right range of data
    etime = pcs_obj.get_last_collection_end_time()
    time_interval = pcs_obj.get_timeinterval(granul, etime)
    start_date = time_interval["starttime"].replace("Z", ".000Z")
    end_date = time_interval["endtime"].replace("Z", ".000Z")
    logger.info(path_param)
    logger.info(f"Granularity -> {granul}")
    logger.info(time_interval)

    api_obj = wastage_array_obj.get_all_response_volume_path_parameter(
        func=volume_obj.get_volume_snapshot_copies,
        system_id=path_param["system_id"],
        volume_uuid=path_param["volume_id"],
        startTime=start_date,
        endTime=end_date,
        granularity=granul,
    )

    write_to_json(
        pd.DataFrame(api_obj.items),
        f"{pcs_obj.json_path}/API_snap_copies_per_volume_{granul}_{Path(__file__).stem}.json",
        sort_by="timeStamp",
    )
    logger.info(api_obj)

    array_obj = acp_obj.get_volume_replication_trend(
        system_id=path_param["system_id"],
        vol_uuid=path_param["volume_id"],
        start_date=start_date.replace("T", " ").replace("Z", ""),
        end_date=end_date.replace("T", " ").replace("Z", ""),
        granularity=granul,
    )
    write_to_json(
        pd.DataFrame(array_obj.items),
        f"{pcs_obj.json_path}/Arr_snap_copies_per_volume_{granul}_{Path(__file__).stem}.json",
        sort_by="timeStamp",
    )
    logger.info(array_obj)
    # Verify test results
    _verify_snap_copies_per_vol(path_param, time_interval, api_obj, array_obj)

    logger.info("Test completed succesfully")


def _verify_snap_copies_per_vol(path_param, time_interval, api_obj, array_obj):
    assert array_obj.total == api_obj.total, f"No of obj does not match"
    params = list(TotalSnapshotsCopies.__dataclass_fields__.keys())
    ignore_param = [
        "id",
        "name",
        "type",
        "resourceUri",
        "consoleUri",
        "generation",
        # "customerId",
        "periodicSnapshotSizeInBytes",
        "adhocSnapshotSizeInBytes",
        # "numClones",
        # "cloneSizeInBytes",
    ]
    check_param = [element for element in params if element not in ignore_param]
    for item in api_obj.items:
        flag = 0
        for array_item in array_obj.items:
            if item.timeStamp == array_item.timeStamp:
                for param in check_param:
                    assert item.__getattribute__(param) == array_item.__getattribute__(
                        param
                    ), f"{param} value is not matching API: {item.__getattribute__(param)} and Actual: {array_item.__getattribute__(param)}"
                flag = 1
                break
        assert flag == 1, f"timestamp data not found in api call {item.timeStamp}"
