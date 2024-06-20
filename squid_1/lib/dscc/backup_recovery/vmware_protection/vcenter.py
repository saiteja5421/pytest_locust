import json
import logging
import time
from tests.vmware.vmware_config import Paths

import requests
from common import helpers
from pyVim.connect import vim, SmartConnect

logger = logging.getLogger(__name__)
headers = helpers.gen_token()
proxies = helpers.set_proxy()


def power_off_vm(service_instance, vm_name):
    """
    Power OFF the VM
    Returns: success, Raise Assertion error in case of failure
    """
    content = service_instance.RetrieveContent()
    vm = get_obj(content, [vim.VirtualMachine], vm_name)
    status = "success"
    if vm.runtime.powerState != "poweredOff":
        status = wait_for_task(vm.PowerOff())
    return status


def destroy_vm(service_instance, vm_name):
    """
    Delete the VM
    Returns: success, Raise Assertion error in case of failure
    """
    content = service_instance.RetrieveContent()
    vm = get_obj(content, [vim.VirtualMachine], vm_name)
    return wait_for_task(vm.Destroy_Task())


def wait_for_task(task, timeout=1500, sleep_interval=5):
    """Waits for a vCenter task to finish"""
    while timeout > 0:
        if task.info.state == "success":
            return task.info.state
        if task.info.state == "error":
            raise AssertionError(f"Failed to complete task, error = {task.info.error}")
        time.sleep(sleep_interval)
        timeout -= sleep_interval


def get_vms(content):
    logging.info("Getting VM details from the vCenter")
    vm_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    views = [vm for vm in vm_view.view]
    vm_view.Destroy()
    return views


def get_vm_power_status(service_instance, vm_name):
    """
    Get VM power state
    Possible values (poweredOn, poweredOff, suspended)
    """
    content = service_instance.RetrieveContent()
    vm = get_obj(content, [vim.VirtualMachine], vm_name)
    return vm.runtime.powerState if vm else None


def get_obj(content, vimtype, name):
    """
    Get vCenter object.
    content: SI content
    vimtype: vim ManagedEntity. E.g. vim.VirtualMachine, vim.HostSystem, vim.Datastore, vim.Datacenter
    name: Name of the object looking for

    Returns: Matched object or None
    """
    vm = content.viewManager
    for c in vm.CreateContainerView(content.rootFolder, vimtype, True).view:
        if c.name.startswith(name):
            return c
    return None


def generate_SmartConnect(host, username, password):
    logging.getLogger().debug(f"Connecting to vCenter '{host}'")
    try:
        return SmartConnect(
            host=host,
            user=username,
            pwd=password,
            port=int("443"),
            disableSslCertValidation=True,
        )
    except Exception as e:
        logging.getLogger().exception("Failed to connect to the vCenter", e)


def refresh_vcenter(vcenter_id):
    url = f"{helpers.get_locust_host()}{Paths.vcenter}/{vcenter_id}/refresh"
    payload = {"fullRefresh": True}
    response = requests.request(
        "POST", url, headers=headers.authentication_header, data=json.dumps(payload)
    )
    logger.info(response)
