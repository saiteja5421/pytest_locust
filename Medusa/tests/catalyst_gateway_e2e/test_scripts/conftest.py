import logging
import time
import pytest
from requests import codes
from lib.common.enums import vcenter_state
from waiting import wait, TimeoutExpired
from lib.dscc.backup_recovery.protection_policies.api.protection_templates import ProtectionTemplate

from lib.dscc.backup_recovery.vmware_protection.common.custom_error_helper import (
    VcenterNotFoundError,
)
from lib.platform.vmware.vcenter_details import get_vms
from tests.steps.vm_protection.psgw_steps import cleanup_psgw_vm
from lib.common.config.config_manager import ConfigManager
from tests.steps.vm_protection.vcenter_steps import (
    create_vm_and_refresh_vcenter_inventory,
    refresh_vcenter_inventory,
    unregister_vcenter,
    add_vcenter,
    wait_for_vcenter_state,
)
from lib.common.enums.vcenter_state import VcenterState
from datetime import datetime, timedelta
from tests.steps.vm_protection.vmware_steps import VMwareSteps
from tests.catalyst_gateway_e2e.test_context import Context

logger = logging.getLogger()


@pytest.fixture(scope="module")
def vm_deploy(context):
    # check if context is passing to test as a tuple() or tuple(tupple())
    for ctx in context if isinstance(context, tuple) else [context]:
        ctx = ctx[0] if isinstance(ctx, tuple) else ctx
        create_vm_and_refresh_vcenter_inventory(ctx)


@pytest.fixture(scope="module")
def deploy_multiple_vm_large_data(context):
    for vm in context.large_size_data_vm_name_list:
        context.vm_name = vm
        create_vm_and_refresh_vcenter_inventory(context, large_vm=True)


@pytest.fixture(scope="module")
def shutdown_all_psgw(context):
    for ctx in context if isinstance(context, tuple) else [context]:
        ctx = ctx[0] if isinstance(ctx, tuple) else ctx
        vcenter_control = VMwareSteps(ctx.vcenter["ip"], ctx.vcenter["username"], ctx.vcenter["password"])
        vcenter_control.shutdown_all_psgw_vms()


@pytest.fixture(scope="session", autouse=True)
def clean_start_reregister_vcenters():
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
def check_data_orchestrator_health(clean_start_reregister_vcenters):
    context = Context(skip_inventory_exception=True)
    response = context.ope.get_ope(context.ope_id)
    assert response.status_code == codes.ok, f"response failed with {response.status_code}, {response.text}"
    try:
        wait(
            lambda: context.ope.get_ope(context.ope_id).json()["state"] == "OK"
            and context.ope.get_ope(context.ope_id).json()["status"] == "OK"
            and context.ope.get_ope(context.ope_id).json()["connectionState"] == "CONNECTED",
            sleep_seconds=300,
        )
        ope_name = context.ope.get_ope(context.ope_id).json()["displayName"]
        logger.info(f"Data Orchestrator {ope_name} is healthy.")
    except TimeoutExpired:
        logger.error(
            f"Data Orchestrator is not healthy. Data Orchestrator details: {context.ope.get_ope(context.ope_id).json()}"
        )
        pytest.exit("Data Orchestrator is not healthy. Terminating pytest...")


@pytest.fixture(scope="session", autouse=True)
def clean_start_delete_psgw(clean_start_reregister_vcenters):
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


@pytest.fixture(scope="session", autouse=True)
def clean_start_remove_stale_vms():
    config = ConfigManager.get_config()
    vcenters = [config_section for config_section in config if "VCENTER" in config_section]
    for vcenter in vcenters:
        context = Context(vcenter, skip_inventory_exception=True)
        tiny_vm_prefix = f"_{context.vm_template_name}_"
        vmware = VMwareSteps(
            context.vcenter["ip"],
            context.vcenter["username"],
            context.vcenter["password"],
        )
        vms = get_vms(vmware.si_content)
        large_vm_list = context.large_size_data_vm_name_list
        for vm in vms:
            if (tiny_vm_prefix in vm.name) or (vm.name in large_vm_list):
                logger.info(f"Deleting stale vm {vm.name} from vCenter {context.vcenter_name} as part of clean start.")
                vmware.delete_vm(vm.name)


@pytest.fixture(scope="session", autouse=True)
def clean_all_stale_protection_policies():
    context = Context()
    protection_template = ProtectionTemplate(context.user)
    resp = protection_template.get_protection_templates()
    policies = resp.json().get("items")
    for pol in policies:
        policy_name = pol["name"]
        if policy_name.startswith(context.test_data["policy_name"]):
            policy_id = pol["id"]
            logger.info(f"Deleting protection policy name : {policy_name}, id: {policy_id}")
            protection_template.delete_protection_template(policy_id)
            logger.info(f"successfully deleted protection policy name : {policy_name}, id: {policy_id}")
