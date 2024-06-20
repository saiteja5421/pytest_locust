# Standard libraries
import logging
import random
import json

import pandas as pd
from pandas.testing import assert_frame_equal
from pathlib import Path
from pytest import fixture, mark

from tests.e2e.data_panorama.panorama_context import Context
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from lib.dscc.data_panorama.consumption.api.volumes_api import VolumesInfo
from lib.dscc.data_panorama.consumption.models.volumes import VolumeUsage

from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, write_to_json

from tests.steps.data_panorama.common_methods import get_path_params_by_type

logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING) #To remove unnecessary logs

@fixture(scope="session")
def context():
    yield Context()


@mark.validated
@mark.order(1020)
def test_volume_tc4_C57482008(context: context):
    """
    The test case validate the volume usage for given volume
    Test sample url: /data-observability/v1alpha1/volumes-consumption/systems/5CSC73PAC4/volumes/8fc40390bdb3485897f201574d9b20c8/volume-usage

    """
    arr_conf_parser = ArrayConfigParser(context=context)

    # db_name = "/workspaces/qa_automation/Medusa/tests/e2e/data_panorama/mock_data_generate/golden_db/ccs_pqa/mock_3days.sqlite"
    db_name = arr_conf_parser.steps_obj.golden_db_path

    consumption_type = "volumes"

    path_param = get_path_params_by_type(db_name=db_name, type=consumption_type)

    actual_obj = arr_conf_parser.get_volume_usage_trend(
        storagesysid=path_param["storagesysid"], vol_uuid=path_param["volumeId"]
    )
    logger.info("Array Response")
    logger.info(json.dumps(actual_obj.to_dict(), indent=4))

    write_to_json(
        pd.DataFrame([actual_obj.to_dict()]),
        f"{arr_conf_parser.steps_obj.json_path}/arr_{Path(__file__).stem}.json",
        sort_by="createdAt",
    )

    volumes_info = VolumesInfo(context.cluster.panorama_url, context.api_header)
    api_obj = volumes_info.get_volume_usage(system_id=path_param["storagesysid"], volume_uuid=path_param["volumeId"])
    logger.info("API Response")
    logger.info(json.dumps(api_obj.to_dict(), indent=4))

    write_to_json(
        pd.DataFrame([api_obj.to_dict()]),
        f"{arr_conf_parser.steps_obj.json_path}/api_{Path(__file__).stem}.json",
        sort_by="createdAt",
    )

    # Validation of volume details from array and api calls

    # params = [param for param in dir(api_obj) if param not in dir(VolumeUsage)]
    params = list(VolumeUsage.__dataclass_fields__.keys())
    ignore_param = ["id", "resourceUri", "consoleUri", "name"]
    check_param = [element for element in params if element not in ignore_param]

    for param in check_param:
        # print("param=", param)
        assert api_obj.__getattribute__(param) == actual_obj.__getattribute__(
            param
        ), f"Values not matching API: {api_obj.__getattribute__(param)} and Actual: {actual_obj.__getattribute__(param)}"
    logger.info("Test completed succesfully")
