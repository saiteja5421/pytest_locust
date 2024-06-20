import logging
from lib.dscc.backup_recovery.common.enums.vm_power_option import VmPowerOption
from lib.dscc.backup_recovery.vmware_protection.vcenter import (
    generate_SmartConnect,
    get_vms,
    power_off_vm,
    destroy_vm,
    get_vm_power_status,
)

logger = logging.getLogger(__name__)


class VMwareSteps:
    def __init__(self, vcenter, username, password):
        self.si = generate_SmartConnect(vcenter, username, password)
        self.si_content = self.si.RetrieveContent()
        self.timeStart = self.get_login_time()

    def get_login_time(self):
        return self.si.content.sessionManager.currentSession.loginTime

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
