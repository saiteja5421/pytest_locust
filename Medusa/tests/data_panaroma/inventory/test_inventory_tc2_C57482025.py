"""
Test Case ID C57482025
Test Description - TC2:- Verify Customer able to view monthly cost information of their systems
"""

# Standard libraries
from datetime import datetime
import logging
from pathlib import Path
import time
import pandas as pd
from pytest import mark, fixture

# Internal libraries
from lib.dscc.data_panorama.inventory_manager.api.inventory_manager_api import InventoryManager

# Steps
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, write_to_json
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser

# Tests
from tests.e2e.data_panorama.panorama_context import Context

logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING) #To remove unnecessary logs

@fixture(scope="session")
def context():
    test_context = Context()
    yield test_context


@mark.order(4010)
@mark.validated
def test_inventory_tc2_C57482025(context: context):
    """
    Test Case ID C57482025
    Test Description - TC2:- Verify Customer able to view monthly cost information of their systems

    curl --location 'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/inventory-storage-systems-cost-trend? \
    start-time=2022-04-25T06%3A41%3A00.000Z&end-time=2023-08-10T06%3A41%3A00.000Z' \
    --header 'Authorization: Bearer token
    """
    logger.info("Start of test case")
    logger.info("PQA Testing -> Inventory -> TC2_C57482025")

    # Create an instance of Panaroma Common Steps class
    tc_pcs = PanaromaCommonSteps(context=context)

    """
    Define the path and filter parameters used in test case to be passed in API call
    Test case provides the overall system level cost information for the specified time intervals.
    tp_starttime: datetime - Define the start time for filtering.
    tp_endtime: datetime - Define the end time for filtering.
    starttime and endtime are set using the function "calculate_timeinterval"
    """
    time_interval = tc_pcs.calculate_timeinterval(months=12)
    tp_starttime: datetime = time_interval["starttime"]
    tp_endtime: datetime = time_interval["endtime"]

    # Create an instance of Array Config Parser class
    tc_acs = ArrayConfigParser(context=context)
    # tc_inventory_cost_trend_expected = tc_pcs.get_all_response(tc_acs.get_inventory_storage_system_cost_trend, start_date=tp_starttime.replace("T", " ").replace(".000Z",""), end_date=tp_endtime.replace("T", " ").replace(".000Z",""), limit=15)

    arr_resp = tc_acs.get_inventory_storage_system_cost_trend()

    write_to_json(
        pd.DataFrame(arr_resp.items),
        f"{tc_acs.steps_obj.json_path}/array_inv_cost_{Path(__file__).stem}.json",
        sort_by="month",
    )

    # API call to get the actual values
    inventory_cost = InventoryManager(context, context.cluster.panorama_url, context.api_header)
    api_inventory_cost_trend = tc_pcs.get_all_response(
        inventory_cost.get_inventory_storage_systems_cost_trend, startTime=tp_starttime, endTime=tp_endtime, limit=15
    )

    write_to_json(
        pd.DataFrame(api_inventory_cost_trend.items),
        f"{tc_acs.steps_obj.json_path}/api_inv_cost_{Path(__file__).stem}.json",
        sort_by="month",
    )

    """
    Verification steps
    """
    # Assert if the total number of items in API response and Array config data doesn't match
    assert api_inventory_cost_trend.total == len(
        arr_resp.items
    ), f"Numbers of records in API response and Expected data doesn't match"

    """
    Iterate through each item of Array config data (mock data) and API response.
    Compare based on the month and year.
    If it matches(equal), then compare Cost, Currency and Customer ID values of both Array config data (mock data) and API response for that particular item.
    Flag "match_found" will help to capture those records present in one data set(Mock/API) and not in another data set(API/Mock).
    """
    for api_item in api_inventory_cost_trend.items:
        match_found = 0
        for array_item in arr_resp.items:
            if api_item.month == array_item.month and api_item.year == array_item.year:
                assert (round(api_item.cost), api_item.currency, api_item.customerId) == (
                    round(array_item.cost),
                    array_item.currency,
                    array_item.customerId,
                ), f"API response value and Expected data value doesn't match"
                match_found = 1
                break
        assert match_found == 1, f"Record {api_item} in API response not present in Expected data"
    logger.info("Test completed successfully")
