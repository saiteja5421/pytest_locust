# standard libraries
import json
import logging
import datetime
from datetime import datetime, timedelta
from random import randint
from pathlib import Path
import pandas as pd
import random
from tests.e2e.data_panorama.panorama_context import Context
from lib.dscc.data_panorama.consumption.api.volumes_api import VolumesInfo
from tests.steps.data_panorama.panaroma_common_steps import Granularity, PanaromaCommonSteps, write_to_json
from lib.dscc.data_panorama.consumption.models.volumes import TotalClonesCopies
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from tests.steps.data_panorama.consumption.wastage_steps import WastageVolumes
from tests.steps.data_panorama.common_methods import get_path_params
from pytest import fixture, mark


logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING)
 

@fixture(scope="session")
def context():
    yield Context()


@mark.validated
@mark.order(1075)
@mark.parametrize("granularity", [Granularity.hourly, Granularity.daily, Granularity.weekly])
# @mark.parametrize("granularity", [Granularity.hourly])
def test_volume_tc15_C57483828(context: context, granularity):
    """
    Test Description:
        TC15 - To verify customer is able to view Clones Copies created for a volume within the specified time interval
        Known Issue: If the clone creation time matches with the collection start time, then the clones are still being missed.

    Test ID: C57483828
    curl cmd:
        curl --location 'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/volumes-consumption/systems/8fb0584a00ef4710b0d602909cffccbd/volumes/da7131fa468748959616b0dcf5a239ca/clones?start-time=2023-05-31T00%3A00%3A00Z&end-time=2023-08-16T16%3A05%3A00Z' --header 'Authorization: Bearer {TOKEN}'
    Test parameters:
        List of parameters that needs to be updated before execution.

        volume_uuid     : str       - ID of volume under test.
        url             : str       - REST API url
    """
    logger.info("Running pre-requisite: Array configuration")

    pcs_obj = PanaromaCommonSteps(context=context)

    # Expected object
    acp_obj = ArrayConfigParser(context=context)
    wastage_array_obj = WastageVolumes(url=context.cluster.panorama_url, api_header=context.api_header)
    # Actual Object
    volume_obj = VolumesInfo(context.cluster.panorama_url, context.api_header)

    db_name = acp_obj.steps_obj.golden_db_path
    table = "spark_clone_all_collection"
    params = ["cloneparentid", "storagesysid", "clonecreationtime"]
    path_param = get_path_params(db_name=db_name, table=table, params=params)
    print("path_params=", path_param)

    # Test case execution
    logger.info("Test case execution - started")

    granul = granularity.value
    logger.info(f"Granularity -> {granul}")
    # etime = pcs_obj.get_last_collection_end_time()
    
    etime=path_param["clonecreationtime"].to_pydatetime() + timedelta(days=2) 
    #This logic is to filter the dates based on clone creation time for the chosen volume
    time_interval = pcs_obj.get_timeinterval(granul, etime)

    start_date = time_interval["starttime"]
    end_date = time_interval["endtime"]
    array_obj = acp_obj.get_volume_replication_clone_trend(
        system_id=path_param["storagesysid"],
        vol_uuid=path_param["cloneparentid"],
        start_date=start_date.replace("T", " ").replace("Z", ""),
        end_date=end_date.replace("T", " ").replace("Z", ""),
        granularity=granul,
    )

    logger.info(json.dumps(array_obj.to_dict(), indent=4))
    write_to_json(
        pd.DataFrame(array_obj.items),
        f"{pcs_obj.json_path}/arr_{granul}_{Path(__file__).stem}.json",
        sort_by="timeStamp",
    )

    # Get API response
    api_obj = wastage_array_obj.get_all_response_volume_path_parameter(
        func=volume_obj.get_volume_clone_copies,
        system_id=path_param["storagesysid"],
        volume_uuid=path_param["cloneparentid"],
        startTime=start_date,
        endTime=end_date,
        granularity=granul,
    )

    logger.info(json.dumps(api_obj.to_dict(), indent=4))
    write_to_json(
        pd.DataFrame(api_obj.items),
        f"{pcs_obj.json_path}/api_{granul}_{Path(__file__).stem}.json",
        sort_by="timeStamp",
    )

    # Verify results
    _verify_clone_copies_per_vol(array_obj, api_obj)

    logger.info("Test completed succesfully")


def _verify_clone_copies_per_vol(array_obj, api_obj):
    assert array_obj.total == api_obj.total, "number of objects does not match"
    params = list(TotalClonesCopies.__dataclass_fields__.keys())
    ignore_param = ["id", "name", "type", "resourceUri", "consoleUri", "generation", "customerId"]
    check_param = [element for element in params if element not in ignore_param]
    # params = [param for param in dir(api_obj.items[0]) if param not in dir(TotalClonesCopies)]
    for item in api_obj.items:
        flag = 0
        for array_item in array_obj.items:
            if item.timeStamp == array_item.timeStamp:
                for param in check_param:
                    assert item.__getattribute__(param) == array_item.__getattribute__(
                        param
                    ), f"Values not matching API: {item.__getattribute__(param)} and Actual: {array_item.__getattribute__(param)}"
                flag = 1
                # if flag == 1:
                break
        assert flag == 1, f"timestamp data not found in api call {item.timeStamp}"
