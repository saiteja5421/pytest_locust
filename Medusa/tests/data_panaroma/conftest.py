from datetime import datetime
import logging
import os
from pathlib import Path
import sys
import pytest
import sqlalchemy
from tests.e2e.data_panorama.mock_data_generate.spark_tables.aggregated_tables import create_spark_tables

from tests.e2e.data_panorama.panorama_context import Context
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps
from reportportal_client import RPLogger, RPLogHandler


@pytest.fixture(scope="session", autouse=True)
def create_aggregated_db():
    test_context = Context()
    # mock_data_generate/golden_db/ccs_pqa/mock_aggregated_db.sqlite
    FILE_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
    out_db_name = f"{FILE_PATH}/../../{test_context.golden_db_path}"
    engine = sqlalchemy.create_engine("sqlite:///%s" % out_db_name, execution_options={"sqlite_raw_colnames": True})
    conn = engine.connect()

    input_db_name = f"{FILE_PATH}/../../{test_context.input_golden_db_path}"
    input_engine = sqlalchemy.create_engine(
        "sqlite:///%s" % input_db_name, execution_options={"sqlite_raw_colnames": True}
    )
    input_conn = input_engine.connect()
    # Spark tables are required to create expected API response.
    create_spark_tables(out_db_name=out_db_name, db_name=test_context.input_golden_db_path)


@pytest.fixture(scope="session", autouse=True)
def logger(request):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Create a handler for Report Portal if the service has been
    # configured and started.
    if hasattr(request.node.config, "py_test_service"):
        # Import Report Portal logger and handler to the test module.
        logging.setLoggerClass(RPLogger)
        rp_handler = RPLogHandler()

        # Add additional handlers if it is necessary
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)
    else:
        rp_handler = logging.StreamHandler(sys.stdout)

    # Set INFO level for Report Portal handler.
    rp_handler.setLevel(logging.INFO)
    return logger


def pytest_configure(config):
    """
    pyTest hook method - This is used here to add additional attribute 'Launch Time'
    and updating Jenkins build URL to the launch desctiption.
    """
    if "rp_launch_attributes" in config.inicfg:
        config.inicfg["rp_launch_attributes"] += f""" 'Launch Time:{datetime.now().strftime("%d/%m/%YT%H.%M.%S")}'"""
