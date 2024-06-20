"""
Test Case ID C57482067
Test Description - TC1:- To verify customer is able to view details of clones consumption
"""

# Standard libraries
import json
import logging
from pathlib import Path
import time
import pandas as pd
from pytest import mark, fixture

# Internal libraries
from lib.dscc.data_panorama.consumption.api.clones_api import ClonesInfo
from lib.dscc.data_panorama.consumption.models.clones import ClonesConsumption

# Steps
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, write_to_json
from tests.steps.data_panorama.consumption.array_consumption_steps import (
    ArrayConfigParser,
)

# Tests
from tests.e2e.data_panorama.panorama_context import Context

logger = logging.getLogger()


@fixture(scope="session")
def context():
    test_context = Context()
    yield test_context


# @mark.skip(reason="Blocked by cost design changes")
@mark.order(2005)
@mark.validated
def test_clone_tc1_C57482067(context: context):
    """
    Test Description:
        This test verifies the Clone consumption API response and compare it with Mock(array) response.
    Test ID: C57482067
    curl cmd:
        curl --location 'http://CCS_DEV_URL/data-observability/v1alpha1/clones-consumption' --header 'Authorization: Bearer TOKEN
    """
    logger.info("Start of test case")
    logger.info("PQA Testing -> Consumption -> Clones -> TC1_C57482067")
    """
    This test verifies the Clone consumption API response and compare it with Mock(array) response.
    Preconditions:
    Prepare the arrays for test by creating required data.
    get_clones_consumption:- Function returns the data related to clones consumption for verification with API response.
                                 This is the expected data of the test case against which actual values will be compared.
    """

    logger.info("Running pre-requisite: Array configuration")

    tc_acs: ArrayConfigParser = ArrayConfigParser(context=context)
    tc_clones_consumption_exp = tc_acs.get_clones_consumption()
    logger.info("Array response: Clones Consumption")
    logger.info(tc_clones_consumption_exp)
    write_to_json(
        df=pd.DataFrame([tc_clones_consumption_exp.to_dict()]),
        path=f"{tc_acs.steps_obj.json_path}/arr_{Path(__file__).stem}.json",
        sort_by="id",
    )

    """
    API call to get the actual values
    """
    clone_obj = ClonesInfo(url=context.cluster.panorama_url, api_header=context.api_header)

    """
    curl --location 'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/clones-consumption' --header 'Authorization: Bearer <Token>
    """
    api_clones_consumption = clone_obj.get_clones_consumption()

    logger.info("Array response: Volume IO activity trend")
    logger.info(api_clones_consumption)
    write_to_json(
        df=pd.DataFrame([api_clones_consumption.to_dict()]),
        path=f"{tc_acs.steps_obj.json_path}/api_{Path(__file__).stem}.json",
        sort_by="id",
    )

    # Verification steps
    params = [param for param in dir(api_clones_consumption) if param not in dir(type(api_clones_consumption))]
    ignore_param = ["id", "name", "generation", "resourceUri", "consoleUri"]
    check_param = [element for element in params if element not in ignore_param]

    for param in check_param:
        if param == "cost" or param == "currentMonthCost" or param == "previousMonthCost":
            assert round(api_clones_consumption.__getattribute__(param)) == round(
                tc_clones_consumption_exp.__getattribute__(param)
            ), f"Values not matching API: {api_clones_consumption.__getattribute__(param)} and Actual: {tc_clones_consumption_exp.__getattribute__(param)}"
        else:
            assert api_clones_consumption.__getattribute__(param) == tc_clones_consumption_exp.__getattribute__(
                param
            ), f"Values not matching API: {api_clones_consumption.__getattribute__(param)} and Actual: {tc_clones_consumption_exp.__getattribute__(param)}"
    print("Test Completed succesfully")
    logger.info("Test completed succesfully")
