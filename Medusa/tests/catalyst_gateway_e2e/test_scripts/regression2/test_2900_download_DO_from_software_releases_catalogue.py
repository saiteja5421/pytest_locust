"""
    TestRail ID C57582065: Download DO from software-release API/Catalogue.
"""

import logging
from pytest import mark, fixture
from tests.catalyst_gateway_e2e.test_context import Context

from tests.steps.vm_protection.vcenter_steps import (
    download_DO_from_software_catalogue,
    validate_downloaded_DO,
    perform_DO_cleanup,
)

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context(skip_inventory_exception=True)
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_DO_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@mark.order(2900)
def test_download_DO_from_software_releases_api(context):
    """
    TestRail ID C57582065: Download DO from software-release API/Catalogue
    Test case to download latest DO from software-release API and validate whether successfully downloaded or not.
    Args:
        context (Context): Context Object
    """
    download_DO_from_software_catalogue(context)
    validate_downloaded_DO(context)
