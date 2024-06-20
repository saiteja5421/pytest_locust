# Standard libraries
import logging
import time
import json
from pathlib import Path
import pandas as pd
from pytest import fixture, mark
from tests.e2e.data_panorama.panorama_context import Context
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, write_to_json

from lib.dscc.data_panorama.inventory_manager.api.inventory_manager_api import InventoryManager
from lib.dscc.data_panorama.inventory_manager.models.inventory_manager import InventoryStorageSystemsSummary

logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING) #To remove unnecessary logs

@fixture(scope="session")
def context():
    yield Context()


@mark.validated
@mark.order(4005)
def test_inventory_tc1_C57482024(context: context):
    """
    To verify Customer able to view their inventory summary details based on location
    """
    logger.info("Start of test case")
    logger.info("PQA Testing -> Inventory -> TC1_C57482024")

    # To get inventory summary details data from array
    aobj = ArrayConfigParser(context=context)
    panorama_step = PanaromaCommonSteps(context=context)
    actual_obj = aobj.get_inventory_storage_system_summary()
    logger.info("Array Response")
    logger.info(json.dumps(actual_obj.to_dict(), indent=4))
    write_to_json(
        pd.DataFrame(actual_obj.to_dict(), index=[0]),
        f"{panorama_step.json_path}/arr_{Path(__file__).stem}.json",
        sort_by="customerId",
    )

    # Fetching data from API Calls
    inventory_info = InventoryManager(context, context.cluster.panorama_url, context.api_header)
    api_obj = inventory_info.get_inventory_storage_systems_summary()
    logger.info("API Response")
    logger.info(json.dumps(api_obj.to_dict(), indent=4))
    write_to_json(
        pd.DataFrame(api_obj.to_dict(), index=[0]),
        f"{panorama_step.json_path}/api_{Path(__file__).stem}.json",
        sort_by="customerId",
    )

    # To validate inventory summary details from array and api calls
    # Build list of parameters of data class InventoryStorageSystemsSummary
    params = list(InventoryStorageSystemsSummary.__dataclass_fields__.keys())
    # Define list of common parameters for which verification need to be skipped
    ignore_param = ["id", "name", "type", "generation", "resourceUri", "consoleUri"]
    # Build list of final parameters to be used for verification
    check_param = [element for element in params if element not in ignore_param]

    """
    Compare each paramter returned from Array config data (mock data) and API response
    """
    for param in check_param:
        if param == "cost":
            assert int(api_obj.__getattribute__(param)) == int(
                actual_obj.__getattribute__(param)
            ), f"{param} value not matching ---> API value: {api_obj.__getattribute__(param)} and Actual value: {actual_obj.__getattribute__(param)}"
        else:
            assert api_obj.__getattribute__(param) == actual_obj.__getattribute__(
                param
            ), f"{param} value not matching ---> API value: {api_obj.__getattribute__(param)} and Actual value: {actual_obj.__getattribute__(param)}"

    logger.info("Test completed successfully")
