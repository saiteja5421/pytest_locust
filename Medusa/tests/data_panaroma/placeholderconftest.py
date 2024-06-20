import crayons
import logging
import pytest
import sys
import os
from datetime import datetime
from reportportal_client import RPLogger, RPLogHandler
from _pytest.runner import runtestprotocol
from utils.jenkins_helper import update_build_description


def pytest_runtest_protocol(item, nextitem):
    reports = runtestprotocol(item, nextitem=nextitem)
    for report in reports:
        if report.when == "call" and report.outcome == "passed":
            # print('\n%s --- %s' % (item.name, report.outcome))
            print(f"\n{item.name} ---> {crayons.green(report.outcome.upper())}")
        elif report.when == "call" and report.outcome == "failed":
            # print('\n%s --- %s' % (item.name, report.outcome))
            print(f"\n{item.name} ---> {crayons.red(report.outcome.upper())}")
    return True


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

    if "BUILD_URL" in os.environ and "rp_launch_description" in config.inicfg:
        config.inicfg["rp_launch_description"] += f""" Jenkins URL: {os.environ['BUILD_URL']}"""


@pytest.fixture(scope="session", autouse=True)
def update_jenkins_build_description(request):
    """Update Jenkins current job build information to show RP launch URL."""
    try:
        if hasattr(request.node.config, "py_test_service") and "BUILD_URL" in os.environ:
            rp_launch_url = request.node.config.py_test_service.rp.get_launch_ui_url()
            update_build_description(rp_launch_url)
    except:
        pass
