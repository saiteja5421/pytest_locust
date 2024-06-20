import time
import pytest
from requests import codes
import logging
from tests.steps.vm_protection.psgw_steps import cleanup_psgw_vm
from tests.steps.vm_protection.vcenter_steps import (
    refresh_vcenter_inventory,
    unregister_vcenter,
    add_vcenter,
    create_vm_and_refresh_vcenter_inventory,
)
from datetime import datetime, timedelta
from lib.common.config.config_manager import ConfigManager
from tests.catalyst_gateway_e2e.test_context import Context
from lib.common.enums.vcenter_state import VcenterState

logger = logging.getLogger()


@pytest.fixture(scope="session", autouse=True)
def clean_start_reregister_vcenters_sanity():
    config = ConfigManager.get_config()
    vcenters = [config_section for config_section in config if "VCENTER" in config_section]
    for vcenter in vcenters:
        context = Context(vcenter, skip_inventory_exception=True)
        if context.config[vcenter]["ip"] not in context.excluded_vcenters:
            vcenter_registered = context.hypervisor_manager.check_vcenter_already_registered(context.vcenter_name)
            if vcenter_registered:
                # checking vcenter last refreshed time is grater than 5 mins.
                vcenter_info = context.hypervisor_manager.get_vcenter_by_name(context.vcenter_name)
                if vcenter_info["state"] == VcenterState.OK.value:
                    vcenter_last_refreshed = datetime.strptime(vcenter_info["lastRefreshed"], "%Y-%m-%dT%H:%M:%S.%fZ")
                    vcenter_refresh_time_diff = datetime.now() - vcenter_last_refreshed
                    logger.info(f"vcenter last refresh ago : {vcenter_refresh_time_diff}")
                    if vcenter_refresh_time_diff > timedelta(minutes=5):
                        logger.info("vcenter refresh time is grater than 5 minutes.So,Refreshing vcenter")
                        refresh_vcenter_inventory(context, vcenter_info.get("id"))
                else:
                    unregister_vcenter(context, force=True)
                    # Adding some wait time to get dependent services settled with unregister operation.
                    time.sleep(120)
                    add_vcenter(context, extended_timeout=True)
            else:
                logger.info(f"Registering vcenter: {context.vcenter_name} ")
                add_vcenter(context, extended_timeout=True)


@pytest.fixture(scope="session", autouse=True)
def clean_start_delete_psgw(clean_start_reregister_vcenters_sanity):
    context = Context()
    atlas = context.catalyst_gateway
    response = atlas.get_catalyst_gateways()
    assert response.status_code == codes.ok, f"response failed with {response.status_code}, {response.text}"

    items = response.json().get("items")
    for item in items:
        if context.psgw_name.split("_")[0] in item["name"]:
            _psgw_name, _, _vcenter_name = atlas.get_catalyst_gateway_details(context.user, item)
            current_vcenter = _vcenter_name == context.vcenter_name
            if current_vcenter:
                context.psgw_name = _psgw_name
                cleanup_psgw_vm(context)


@pytest.fixture(scope="module")
def vm_deploy(context):
    # check if context is passing to test as a tuple() or tuple(tupple())
    for ctx in context if isinstance(context, tuple) else [context]:
        ctx = ctx[0] if isinstance(ctx, tuple) else ctx
        create_vm_and_refresh_vcenter_inventory(ctx)


# def pytest_sessionstart(session):
#     session.results = dict()


# @pytest.hookimpl(tryfirst=True, hookwrapper=True)
# def pytest_runtest_makereport(item, call):
#     outcome = yield
#     result = outcome.get_result()

#     if result.when == 'call':
#         item.session.results[item] = result


# def pytest_sessionfinish(session, exitstatus):
#     context = Context()
#     if exitstatus == 0:
#         # logger.info(f"\n{'Teardown Start'.center(40, '*')}")
#         perform_cleanup(context, clean_vm=True)
#         logger.info(f"\n{'Teardown Complete'.center(40, '*')}")
#     else:
#         logger.info("Skipping teardown because all the test cases are not passed.")
