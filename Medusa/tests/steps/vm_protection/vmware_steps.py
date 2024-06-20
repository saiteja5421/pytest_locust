import logging
import time
from waiting import wait, TimeoutExpired
from typing import List
from lib.platform.vmware.vcenter_details import (
    destroy_vm,
    generate_SmartConnect,
    get_cluster_compute_resources,
    get_datastore_object_with_name,
    get_drs_status,
    set_drs_status,
    disconnect_vcenter,
    disconnect_host,
    get_host_power_status,
    get_vms,
    power_off_vm,
    power_on_vm,
    get_vm_host,
    get_vm_power_status,
    reboot_host,
    reconnect_host,
    get_ha_status,
    set_ha_status,
    get_vm_hosts,
    get_vm,
    clone_vm,
    get_tasks,
)
from lib.common.enums.vm_power_option import VmPowerOption
from datetime import timedelta
from utils.timeout_manager import TimeoutManager

logger = logging.getLogger()


class VMwareSteps:
    def __init__(self, vcenter, username, password):
        self.si = generate_SmartConnect(vcenter, username, password)
        self.si_content = self.si.RetrieveContent()
        self.timeStart = self.get_login_time()

    def get_cluster_drs_status(self):
        logger.info("Getting cluster information")
        clusters = get_cluster_compute_resources(self.si_content)

        # Assumption: there is only one cluster in test environment
        drs_status = get_drs_status(clusters[0])
        logger.info(f"DRS status: {drs_status} on {clusters[0].name}")
        return drs_status

    def get_cluster_ha_status(self):
        logger.info("Getting cluster information")
        clusters = get_cluster_compute_resources(self.si_content)

        # Assumption: there is only one cluster in test environment
        ha_status = get_ha_status(clusters[0])
        logger.info(f"HA status: {ha_status} on {clusters[0].name}")
        return ha_status

    def set_cluster_drs_status(self, status):
        drs_status = self.get_cluster_drs_status()
        if drs_status == status:
            logger.info("No need to change DRS")
            return

        logger.info("Getting cluster information")
        clusters = get_cluster_compute_resources(self.si_content)

        # Assumption: there is only one cluster in test environment
        logger.info(f"Setting DRS: {status} on {clusters[0].name}")
        set_drs_status(clusters[0], status)
        logger.info(f"DRS changed to: {status} on {clusters[0].name}")

    def set_cluster_ha_status(self, status):
        ha_status = self.get_cluster_ha_status()
        if ha_status == status:
            logger.info("No need to change HA")
            return

        logger.info("Getting cluster information")
        clusters = get_cluster_compute_resources(self.si_content)

        # Assumption: there is only one cluster in test environment
        logger.info(f"Setting HA: {status} on {clusters[0].name}")
        set_ha_status(clusters[0], status)

        try:
            wait(
                lambda: self.get_cluster_ha_status() == status,
                timeout_seconds=TimeoutManager.standard_task_timeout,
                sleep_seconds=5,
            )
        except TimeoutExpired:
            pass
        logger.info(f"HA changed to: {status} on {clusters[0].name}")

    def reboot_host_and_wait(self, host_name):
        logger.info(f"Rebooting host: {host_name}")
        reboot_host(self.si, host_name)
        logger.info(f"Waiting for power status: {VmPowerOption.unknown.value} on {host_name}")
        self.wait_for_host_power_status(host_name, VmPowerOption.unknown)
        logger.info(f"Waiting for power status: {VmPowerOption.on.value} on {host_name}")
        self.wait_for_host_power_status(host_name, VmPowerOption.on)

    def disconnect_host_and_wait(self, host_name):
        logger.info(f"Disconnect host: {host_name}")
        disconnect_host(self.si, host_name)
        logger.info(f"Disconnected host : {host_name} , and sleeping for 10 mins reflect on the vcenter")
        time.sleep(10 * 60)

    def reconnect_host_and_wait(self, host_name):
        logger.info(f"Reconnecting host: {host_name}")
        reconnect_host(self.si, host_name)
        logger.info(f"Reconnected host : {host_name} , and sleeping for 10 mins reflect on the vcenter")
        time.sleep(10 * 60)

    def wait_for_host_power_status(self, host_name, power_option: VmPowerOption):
        def _return_condition():
            result = get_host_power_status(self.si_content, host_name) == power_option.value
            return result

        try:
            wait(
                _return_condition,
                timeout_seconds=TimeoutManager.standard_task_timeout,
                sleep_seconds=30,
            )
        except TimeoutExpired:
            raise AssertionError(f"Host {host_name} is still powered off")
        logger.info(f"Host {host_name} status: {power_option}")

    def get_all_vms(self, power_option=VmPowerOption.on, host_name=None, memory_reserved=0):
        logger.info(f"Getting all vms with power: {power_option.on.value}")
        vms_list_all = get_vms(self.si_content)
        _vms_list_found = []
        for vm in vms_list_all:
            _host_query = True
            _memory_query = True
            _power_query = True
            if power_option:
                _power_query = vm.runtime.powerState == power_option.value
            if host_name:
                _host_query = vm.runtime.host.name == host_name
            if memory_reserved:
                _memory_query = vm.config.memoryAllocation.reservation > memory_reserved * 1024
            if _power_query and _host_query and _memory_query:
                _vms_list_found.append(vm.name)

        logger.info(f"Host {host_name} poweredOn vms list: {_vms_list_found}")
        return _vms_list_found

    def set_vms_power(self, vms: List, power_option: VmPowerOption):
        for vm in vms:
            vm_power_status = get_vm_power_status(self.si, vm)
            if power_option.value == vm_power_status:
                continue

            logger.info(f"Setting vm: {vm} to power: {power_option.on.value}")
            if power_option == VmPowerOption.on:
                power_on_vm(self.si, vm)
            elif power_option == VmPowerOption.off:
                power_off_vm(self.si, vm)
            logger.info(f"Vm: {vm} power set to: {power_option.on.value}")

    def shutdown_all_psgw_vms(self):
        # DO has 16 GB reserved
        psgw_list = self.get_all_vms(VmPowerOption.on, memory_reserved=18)
        for psgw_vm in psgw_list:
            # skip Do Not Delete protection store gateways
            if "DND" in psgw_vm:
                logger.info(f"Skipping PSGW shutdown for Do Not Delete: {psgw_vm}")
                continue
            logger.info(f"Setting psgw vm: {psgw_vm} to power: {VmPowerOption.off.value}")
            power_off_vm(self.si, psgw_vm)
            logger.info(f"PSGW vm: {psgw_vm} power set to: {VmPowerOption.off.value}")

    def get_vm_host(self, vm_name):
        logger.info(f"Getting vm: {vm_name} host")
        return get_vm_host(self.si, vm_name)

    def get_all_hosts(self, power_option: VmPowerOption):
        hosts = get_vm_hosts(self.si_content)

        _hosts_list = []
        for host in hosts:
            if get_host_power_status(self.si_content, host.name) == power_option.value:
                _hosts_list.append(host)

        return _hosts_list

    def search_vm(self, vm_name):
        logger.info(f"Searching for {vm_name} in the vCenter...")
        vm_list = get_vms(self.si_content)
        logger.info(f"Got vm list from the vCenter: {vm_list}")
        return vm_name in [vm.name for vm in vm_list]

    def delete_vm(self, vm_name):
        logger.info(f"Deleting vm: {vm_name}")
        vm_power_status = get_vm_power_status(self.si, vm_name)
        logger.info(f"VM {vm_name} power status: {vm_power_status}")
        if vm_power_status == VmPowerOption.on.value:
            power_off_vm(self.si, vm_name)
            logger.info(f"VM {vm_name} power status: {get_vm_power_status(self.si, vm_name)}")
        if vm_power_status:
            status = destroy_vm(self.si, vm_name)
            if status == "success":
                logger.info(f"Deleted vm: {vm_name}")
            else:
                logger.info(f"Failed - Delete vm: {vm_name}")
        else:
            status = "vm not exists"
        return status

    def create_vm_from_template(self, template_name, vm_name, power_status=False):
        logger.info("Getting cluster information")
        logger.info(f"content: {self.si_content}")
        clusters = get_cluster_compute_resources(self.si_content)
        logger.info(f"Clusters list from the vCenter: {clusters}")

        logger.info("Getting template information")
        template_info = get_vm(self.si_content, template_name)

        logger.info("Clonning template to vm")
        status = clone_vm(self.si_content, vm_name, template_info, clusters[0], power_status)
        assert status, f"Failed - vm {vm_name} clone from template {template_name}"
        logger.info(f"VM {vm_name} cloned from template {template_name}")

    def get_datastore_obj_with_name(self, datastore_name):
        datastore_obj = get_datastore_object_with_name(self.si_content, datastore_name)
        return datastore_obj

    def get_datastore_id(self, vm_name):
        logger.info(f"Getting datastore id from vm {vm_name}")
        vm = get_vm(self.si_content, vm_name)
        datastore_id = vm.datastore[0]._moId
        return datastore_id

    def get_login_time(self):
        return self.si.content.sessionManager.currentSession.loginTime

    def get_tasks(self):
        _timeStart = self.timeStart + timedelta(days=-1)
        _timeEnd = self.timeStart + timedelta(days=1)
        tasks = get_tasks(self.si, begin_time=_timeStart, end_time=_timeEnd)
        return tasks

    def wait_for_task(self, task_id):
        def _get_tasks():
            tasks = self.get_tasks()
            try:
                task = next(filter(lambda task: task.key == task_id, tasks))
            except StopIteration:
                return
            if task.state == "success":
                return (True, True)
            elif task.state == "error":
                return (False, task.error.msg)

        try:
            status = wait(_get_tasks, timeout_seconds=900, sleep_seconds=15)
            return status
        except TimeoutExpired:
            raise Exception("Failed to add Datastore - TIMEOUT")

    def get_vm_ip_by_name(self, vm_name):
        vms_list_all = get_vms(self.si_content)
        return next(filter(lambda x: x.name == vm_name, vms_list_all)).guest.ipAddress

    def __del__(self):
        disconnect_vcenter(self.si)
