import json
import logging
from pyVim.connect import vim, SmartConnect, Disconnect
from time import sleep

from utils.timeout_manager import TimeoutManager
from lib.common.enums.vm_power_option import VmPowerOption

logger = logging.getLogger()


DETAILS = {
    "vm_name": [],
    "datastore": [],
    "power_status": [],
    "ip_address": [],
    "mac_address": [],
    "connected_status": [],
}


def sizeof_fmt(num):
    """
    Returns the human readable version of a file size
    :param num:
    :return:
    """
    for item in ["bytes", "KB", "MB", "GB"]:
        if num < 1024.0:
            return "%3.1f%s" % (num, item)
        num /= 1024.0
    return "%3.1f%s" % (num, "TB")


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


def get_datastores(content, for_vm=""):
    ds_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datastore], True)
    datastores = list(ds_view.view)
    for ds in datastores:
        print_datastore_info(ds, vm_name=for_vm)
    ds_view.Destroy()
    return datastores


def get_datastore_by_name(content, datastore_name):
    datastore = None
    ds_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datastore], True)
    datastores = list(ds_view.view)
    for ds in datastores:
        if ds.name == datastore_name:
            datastore = ds
            break
    ds_view.Destroy()
    return datastore


def print_datastore_info(ds_obj, vm_name=""):
    summary = ds_obj.summary
    ds_capacity = summary.capacity
    ds_freespace = summary.freeSpace
    ds_uncommitted = summary.uncommitted if summary.uncommitted else 0
    ds_provisioned = ds_capacity - ds_freespace + ds_uncommitted
    ds_overp = ds_provisioned - ds_capacity
    ds_overp_pct = (ds_overp * 100) / ds_capacity if ds_capacity else 0
    for item in ds_obj.vm:
        if item.name == vm_name:
            print("")
            print(f"Name                  : {summary.name}")
            print(f"URL                   : {summary.url}")
            print(f"Capacity              : {sizeof_fmt(ds_capacity)} GB")
            print(f"Free Space            : {sizeof_fmt(ds_freespace)} GB")
            print(f"Uncommitted           : {sizeof_fmt(ds_uncommitted)} GB")
            print(f"Provisioned           : {sizeof_fmt(ds_provisioned)} GB")
            if ds_overp > 0:
                print(f"Over-provisioned  : {sizeof_fmt(ds_overp)} GB / {ds_overp_pct} %")
            print(f"Hosts                 : {len(ds_obj.host)}")
            print(f"Virtual Machines      : {len(ds_obj.vm)}")
            print(f"Virtual Machine Name  : {item.name}")
            DETAILS["vm_name"].append(item.name)
            DETAILS["datastore"].append(summary.name)


def get_vm_hosts(content):
    print("Getting all ESX hosts ...")
    host_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
    hosts = list(host_view.view)
    host_view.Destroy()
    return hosts


def get_vms(content):
    logging.info("Getting VM details from the vCenter")
    vm_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    views = [vm for vm in vm_view.view]
    vm_view.Destroy()
    return views


def get_cluster_compute_resources(content):
    logging.info("Getting all ClusterComputeResource ...")
    cluster_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.ClusterComputeResource], True)
    views = [cluster for cluster in cluster_view.view]
    cluster_view.Destroy()
    return views


def get_drs_status(cluster):
    return cluster.configuration.drsConfig.enabled if cluster else None


def get_ha_status(cluster):
    return cluster.configuration.dasConfig.enabled if cluster else None


def set_drs_status(cluster, status: bool):
    cluster_spec = vim.cluster.ConfigSpecEx()
    drs_info = vim.cluster.DrsConfigInfo()
    drs_info.enabled = status
    cluster_spec.drsConfig = drs_info
    task = cluster.ReconfigureComputeResource_Task(cluster_spec, True)
    wait_for_task(task)


def set_ha_status(cluster, status: bool):
    cluster_spec = vim.cluster.ConfigSpecEx()
    das_info = vim.cluster.DasConfigInfo()
    das_info.enabled = status
    cluster_spec.dasConfig = das_info
    task = cluster.ReconfigureComputeResource_Task(cluster_spec, True)
    wait_for_task(task)


def get_hosts_portgroups(hosts):
    print("Collecting portgroups on all hosts. This may take a while ...")
    host_pg_dict = {}
    for host in hosts:
        pgs = host.config.network.portgroup
        host_pg_dict[host] = pgs
        print("\tHost {} done.".format(host.name))
    print("\tPortgroup collection complete.")
    return host_pg_dict


def print_vminfo(vm):
    vm_power_state = vm.runtime.powerState
    print("Found VM:", vm.name + "(" + vm_power_state + ")")
    # print("Found IP:", vm.summary.guest.ipAddress)
    DETAILS["power_status"].append(vm_power_state)
    for nic in vm.guest.net:
        DETAILS["ip_address"].append(nic.ipAddress)
        DETAILS["mac_address"].append(nic.macAddress)
        DETAILS["connected_status"].append(nic.connected)
        print(
            f"\nIP Address: {nic.ipAddress}\n",
            f"MAC Address: {nic.macAddress}\n",
            f"Connected Status: {nic.connected}",
            "\n",
        )


def show_summary():
    json_object = json.dumps(DETAILS, indent=4)
    return json_object


def get_vm_details_in_a_vcenter(vm_name, host, username, password):
    """
    By default, the vcenter details are read from
    `variables.ini` file like the IP of vCenter, username, password,
    and the VM name to be searched for.

    The user has an option to override these by sending the vCenter details
    as a parameterized form.
        get_vm_details_in_a_vcenter(vm_name="my-personal-vm")
    or
        get_vm_details_in_a_vcenter(
            host="1.2.4.5",
            username="something@vsphere.local,
            password="s3cr3T",
            vm_name="my vm"
        )
    """
    si = generate_SmartConnect(host, username, password)
    content = si.RetrieveContent()
    hosts = get_vm_hosts(content)
    get_hosts_portgroups(hosts)
    get_datastores(content, for_vm=vm_name)
    vms = get_vms(content)
    for vm in vms:
        if vm_name in vm.name:
            print_vminfo(vm)
            break
    # print(f"\n\nSummary: {show_summary()}")
    return show_summary()


def wait_for_task(task, timeout=TimeoutManager.standard_task_timeout, sleep_interval=5):
    timeout = TimeoutManager.standard_task_timeout
    """Waits for a vCenter task to finish"""
    while timeout > 0:
        if task.info.state == "success":
            return task.info.state
        if task.info.state == "error":
            raise AssertionError(f"Failed to complete task, error = {task.info.error}")
        sleep(sleep_interval)
        timeout -= sleep_interval


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


def get_host_power_status(content, host_name):
    """
    Get Host power state
    Possible values (poweredOn, poweredOff, suspended)
    """
    host = get_obj(content, [vim.HostSystem], host_name)
    return host.runtime.powerState if host else None


def reboot_host(service_instance, host_name, force=True):
    """
    Reboot ESX Host
    force = True -> Flag to specify whether or not the host should be rebooted
    regardless of whether it is in maintenance mode.
    """
    content = service_instance.RetrieveContent()
    host = get_obj(content, [vim.HostSystem], host_name)
    task = host.RebootHost_Task(force)
    task_status = wait_for_task(task)
    assert task_status == "success"


def disconnect_host(service_instance, host_name):
    """
    Disconnect ESX Host.
    Args:
        host_name(str): ESX host name
    """
    content = service_instance.RetrieveContent()
    host = get_obj(content, [vim.HostSystem], host_name)
    task = host.DisconnectHost_Task()
    task_status = wait_for_task(task)
    assert task_status == "success"


def reconnect_host(service_instance, host_name):
    """
    Reconnect ESX Host.
    Args:
        host_name(str): ESX host name
    """
    content = service_instance.RetrieveContent()
    host = get_obj(content, [vim.HostSystem], host_name)
    task = host.ReconnectHost_Task()
    task_status = wait_for_task(task)
    assert task_status == "success"


def get_vm_power_status(service_instance, vm_name):
    """
    Get VM power state
    Possible values (poweredOn, poweredOff, suspended)
    """
    content = service_instance.RetrieveContent()
    vm = get_obj(content, [vim.VirtualMachine], vm_name)
    return vm.runtime.powerState if vm else None


def get_vm_host(service_instance, vm_name):
    """
    Get VM host
    """
    content = service_instance.RetrieveContent()
    vm = get_obj(content, [vim.VirtualMachine], vm_name)
    return vm.runtime.host.name if vm else None


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


def reboot_vm(service_instance, vm_name):
    """
    Reboot the VM
    """
    content = service_instance.RetrieveContent()
    vm = get_obj(content, [vim.VirtualMachine], vm_name)
    if vm.runtime.powerState != "poweredOff":
        vm.RebootGuest()


def power_on_vm(service_instance, vm_name):
    """
    Power ON the VM
    Returns: success, Raise Assertion error in case of failure
    """
    content = service_instance.RetrieveContent()
    vm = get_obj(content, [vim.VirtualMachine], vm_name)
    return wait_for_task(vm.PowerOn())


def get_vm(content, vm_name):
    template = get_obj(content, [vim.VirtualMachine], vm_name)
    return template


def get_datastore_object_with_name(content, datastore_name):
    datastore_obj = get_obj(content, [vim.Datastore], datastore_name)
    return datastore_obj._moId


def clone_vm(content, vm_name, template, cluster, power_status):
    datastore = get_obj(content, [vim.Datastore], template.datastore[0].info.name)
    datacenter = get_obj(content, [vim.Datacenter], "Datacenter")
    relospec = vim.vm.RelocateSpec()
    relospec.datastore = datastore
    relospec.pool = cluster.resourcePool
    clonespec = vim.vm.CloneSpec()
    clonespec.location = relospec
    clonespec.powerOn = power_status

    task = template.Clone(folder=datacenter.vmFolder, name=vm_name, spec=clonespec)
    return wait_for_task(task)


def destroy_vm(service_instance, vm_name):
    """
    Delete the VM
    Returns: success, Raise Assertion error in case of failure
    """
    content = service_instance.RetrieveContent()
    vm = get_obj(content, [vim.VirtualMachine], vm_name)
    return wait_for_task(vm.Destroy_Task())


def get_tasks(service_instane, begin_time, end_time):
    """
    Returns vCenter tasks which are matched with given query
    """
    content = service_instane.RetrieveContent()
    task_manager = content.taskManager
    spec_by_time = vim.TaskFilterSpec.ByTime(beginTime=begin_time, endTime=end_time, timeType="startedTime")
    tasks = task_manager.CreateCollectorForTasks(vim.TaskFilterSpec(time=spec_by_time))
    tasks.ResetCollector()
    try:
        # pyvmomi experiancing failure while processing ContentLibraryItem related tasks
        # Open issue: https://github.com/vmware/pyvmomi/issues/872
        # For now logging exception. If needed lets have vSphere REST API call to process tasks
        tasks.ReadPreviousTasks(999)
        return tasks.ReadNextTasks(999)
    except Exception as e:
        logging.getLogger().debug(f"Error has occured while reading tasks: {e}")


def disconnect_vcenter(service_instance):
    """Disconnect vCenter session"""
    Disconnect(service_instance)
    logging.getLogger().debug("Disconnected vCenter session")


def wait_until_vm_gets_powered_off(service_instance, vm_name, timeout, sleep_interval=30):
    wait_time = timeout
    while timeout > 0:
        status = get_vm_power_status(service_instance, vm_name)
        if status is None:
            logger.info(f"{vm_name} virtual machine not found in the vCenter")
            return False
        if status == VmPowerOption.off.value:
            logger.info(f"VM: {vm_name} is in {VmPowerOption.off.value} state")
            return True
        logger.info(f"{vm_name} is in {status} state - sleeping for {sleep_interval} seconds")
        sleep(sleep_interval)
        timeout -= sleep_interval
    if timeout == 0:
        logger.error(
            f"[Times up] Failed to get the VM: {vm_name} {VmPowerOption.off.value} state with in {wait_time/ 60:1f} minutes"
        )
        return False
