import sys
import os
import time
from datetime import datetime
import traceback
import uuid
from locust import HttpUser, between, events
from common import helpers
from tests.vmware.backup_restore.task import BackupTasks
from lib.dscc.backup_recovery.vmware_protection import (
    protection_policy,
    protection_job,
    protection_store,
)
from lib.dscc.backup_recovery.vmware_protection.virtual_machines import virtual_machines
from lib.dscc.backup_recovery.vmware_protection.backups import delete_all_backups_from_vm
from lib.dscc.backup_recovery.vmware_protection.vmware import VMwareSteps
from tests.steps.vmware_steps import hypervisor
from lib.dscc.backup_recovery.vmware_protection.vcenter import refresh_vcenter

VCENTER_NAME = os.environ.get("VCENTER_NAME")
VCENTER_USERNAME = os.environ.get("VCENTER_USERNAME")
VCENTER_PASSWORD = os.environ.get("VCENTER_PASSWORD")

import logging

from lib.logger import rp_agent
from locust.runners import WorkerRunner

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins

# Get tiny vm name here
logger = logging.getLogger(__name__)
BACKUP_VM_LIST = []


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    try:
        logging.info("---- Start Load Test -----------")
        logging.info("On test start: Add Report portal start launch ")
        report_portal_dict = helpers.get_report_portal_info()
        user_count = environment.parsed_options.num_users
        run_time_mins = environment.parsed_options.run_time / 60
        global rp_mgr
        global rp_test_id
        global rp_logger

        test_case_name = "LOCAL BACKUP"
        rp_mgr, rp_test_id, rp_logger = rp_agent.create_test_in_report_portal(
            report_portal_dict,
            launch_suffix="BACKUP_RESTORE",
            test_name=test_case_name,
            test_description=f"Test: {test_case_name} | No of Users: {user_count} | Run time: {run_time_mins} Minutes",
        )

        logger.debug(f"Number of users are {user_count}")
        config = helpers.read_config()
        global PSGW_NAME
        PSGW_NAME =  os.environ.get("PSGW_NAME")
        global BACKUP_VM_LIST
        BACKUP_VM_LIST = config["testInput"]["backup_vm_list"]
        if "SCINT" in PSGW_NAME:
            BACKUP_VM_LIST = [vm+"_scint" for vm in BACKUP_VM_LIST]

        # Create protection store
        protection_store.create_protection_store(psgw_name=PSGW_NAME, type="ON_PREMISES")
        protection_store.create_protection_store(psgw_name=PSGW_NAME, type="CLOUD")

    except Exception as e:
        logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
        rp_mgr.finish_launch()
        sys.exit(1)


class LoadUser(HttpUser):
    wait_time = between(120, 180)
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    tasks = [BackupTasks]

    def on_start(self):
        try:
            # Get VM from the list
            if BACKUP_VM_LIST:
                self.vm_name = BACKUP_VM_LIST.pop()
            self.protection_policy_name = "PSR_Protection_Policy_" + str(uuid.uuid4())
            logger.info("Testcase started")

            # Get protection store
            onprem_protection_store_id_list = []
            cloud_protection_store_id_list = []
            (
                onprem_protection_store_id_list,
                cloud_protection_store_id_list,
            ) = protection_store.get_on_premises_and_cloud_protection_store(psgw_name=PSGW_NAME)

            # Create protection policy
            response_data = protection_policy.create_protection_policy(
                self.protection_policy_name,
                "YEARS",
                1,
                1,
                "WEEKLY",
                1,
                onprem_protection_store_id_list,
                cloud_protection_store_id_list,
            )
            self.protection_policy_id = response_data["id"]
            logger.info(f"Protection policy id {self.protection_policy_id}")

            # Get protection policy
            protection_template = protection_policy.get_protection_policy_by_id(self.protection_policy_id)

            asset_type = "hybrid-cloud/virtual-machine"
            backup_granularity_type: str = "VMWARE_CBT"
            schedule_id_list = []
            for protection in protection_template["protections"]:
                if "Array_Snapshot" in protection["schedules"][0]["name"]:
                    snapshot_id = protection["id"]
                    snapshot_schedule_id = protection["schedules"][0]["scheduleId"]
                elif "On-Premises" in protection["schedules"][0]["name"]:
                    local_backup_id = protection["id"]
                    local_backup_schedule_id = protection["schedules"][0]["scheduleId"]
                elif "HPE_Cloud" in protection["schedules"][0]["name"]:
                    cloud_backup_id = protection["id"]
                    cloud_backup_schedule_id = protection["schedules"][0]["scheduleId"]
            schedule_id_list.append(snapshot_schedule_id)
            schedule_id_list.append(local_backup_schedule_id)
            schedule_id_list.append(cloud_backup_schedule_id)

            # Assign protection policy
            self.virtual_machine_id = virtual_machines.get_vm_id_by_name(self.vm_name)
            logger.info(f"Virtual machine {self.virtual_machine_id}")
            self.protection_job_id = protection_job.assign_protection_policy(
                asset_name=self.vm_name,
                asset_type=asset_type,
                asset_id=self.virtual_machine_id,
                template_id=self.protection_policy_id,
                snapshot_id=snapshot_id,
                local_backup_id=local_backup_id,
                cloud_backup_id=cloud_backup_id,
                backup_granularity_type=backup_granularity_type,
                schedule_id_list=schedule_id_list,
            )

            # Get protection job id
            logger.info(f"Protection job id is {self.protection_job_id}")

            logger.info(f"Wait for the Initial Snapshot schedule to be completed")
            time.sleep(120)

        except Exception as e:
            logger.error(f"[on_start] Exception occurred {e}")
            logger.error(traceback.format_exc())
            rp_logger.error("[on_start] Exception occurred {e}")
            rp_logger.error(traceback.format_exc())
            rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
            rp_mgr.finish_launch()
            sys.exit(1)

    def on_stop(self):
        logger.info(f"---- User test completed -------")

        vcenter_id = hypervisor.get_vcenter_id_by_name(VCENTER_NAME)
        refresh_vcenter(vcenter_id=vcenter_id)
        time.sleep(60)

        # Deleting all backups from tinyvm
        virtual_machine_id = virtual_machines.get_vm_id_by_name(self.vm_name)
        delete_all_backups_from_vm(virtual_machine_id)
        
        # Delete backups from restored vm with vmname suffixed with "_restored"
        restore_vm_name = self.vm_name + "_restored"
        vcenter = VMwareSteps(VCENTER_NAME, VCENTER_USERNAME, VCENTER_PASSWORD)
        if vcenter.search_vm(restore_vm_name):
            logger.info(f"Restore VM {restore_vm_name} found successful after restore")
            # Delete backups from restored vm with vm_name suffixed with "_restored"
            restore_vm_id = virtual_machines.get_vm_id_by_name(restore_vm_name)
            delete_all_backups_from_vm(restore_vm_id)        
            # Delete restored vm from vcenter  
            vcenter.delete_vm(restore_vm_name)
            logger.info("Restored VM deleted successfully")

        # Unprotect protection job
        response = protection_job.unprotect_job(self.protection_job_id)

        # Delete protection policy
        response = protection_policy.delete_protection_policy_by_id(self.protection_policy_id)
        logger.info(f"Protection policy deletion response {response}")

        # Delete local and cloud protection store
        response = protection_store.delete_all_protection_stores_from_current_psg(PSGW_NAME,force=True)
        logger.info(f"Delete protection store response {response}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("Testcase stopped")


@events.request.add_listener
def record_in_report_portal(
    request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs
):
    rp_agent.log_request_stats_in_reportportal(rp_logger, request_type, name, response_time, exception, start_time, url)


@events.quitting.add_listener
def do_checks(environment, **_kw):
    if isinstance(environment.runner, WorkerRunner):
        return

    RP_TEST_STATUS = rp_agent.ReportPortalStatus.PASSED
    logger = rp_agent.set_logger(rp_logger)
    rp_agent.log_stats_summary(environment, logger)

    stats_total = environment.runner.stats.total
    fail_ratio = stats_total.fail_ratio

    check_fail_ratio = 0.01
    logger.info(f"Total number of requests {stats_total.num_requests}")
    if stats_total.num_requests == 0:
        logger.error(f"TEST FAILED: Since no requests occurred")
        RP_TEST_STATUS = rp_agent.ReportPortalStatus.FAILED
        environment.process_exit_code = 3
    else:
        if fail_ratio > check_fail_ratio:
            logger.error(
                f"CHECK FAILED: fail ratio was {(fail_ratio*100):.2f}% (threshold {(check_fail_ratio*100):.2f}%)"
            )
            RP_TEST_STATUS = rp_agent.ReportPortalStatus.FAILED
            environment.process_exit_code = 3
        else:
            logger.info(
                f"CHECK SUCCESSFUL: fail ratio was {(fail_ratio*100):.2f}% (threshold {(check_fail_ratio*100):.2f}%)"
            )

    if rp_mgr:
        rp_mgr.finish_test_step(step_id=rp_test_id, status=RP_TEST_STATUS)
        rp_mgr.finish_launch()
