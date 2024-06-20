import logging
import sys
import traceback
from locust import HttpUser, between, events
from common import helpers
from common.enums.aws_regions import AwsStorageLocation
from common.enums.azure_locations import AzureLocations
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway import delete_psg
from lib.dscc.backup_recovery.vmware_protection.protection_store import delete_all_protection_stores_from_current_psg
from tests.steps.vmware_steps.hypervisor import (
    get_datastore_id,
    get_hypervisor_hosts,
    get_host_id,
    get_moref,
    get_networks,
    get_vcenter_id_by_name,
)
from tests.vmware.vmware_crud_operations.task import ProtectionStoregateway
import logging
from lib.logger import rp_agent
from locust.runners import WorkerRunner

logger = logging.getLogger(__name__)


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

        test_case_name = "CRUD-WORKFLOW"
        rp_mgr, rp_test_id, rp_logger = rp_agent.create_test_in_report_portal(
            report_portal_dict,
            launch_suffix="CRUD",
            test_name=test_case_name,
            test_description=f"Test: {test_case_name} | No of Users: {user_count} | Run time: {run_time_mins} Minutes",
        )

        logger.debug(f"Number of users are {user_count}")

    except Exception as e:
        logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
        rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
        rp_mgr.finish_launch()
        sys.exit(1)


class LoadUser(HttpUser):
    """locust user class named as loaduser

    Args:
        HttpUser : the base class, indicating that this user will simulate HTTP interactions.
    """

    wait_time = between(2, 4)
    headers = helpers.gen_token()
    proxies = helpers.set_proxy()
    config = helpers.read_config()
    ip_address = config["testInput"]["ip_address_list"]
    nic_ip = config["testInput"]["nic_ip_address_list"]
    # number of users increases cloud_regions need to be added.
    cloud_regions = [
        AzureLocations.AZURE_northeurope, AwsStorageLocation.AWS_AP_NORTHEAST_1, AzureLocations.AZURE_norwayeast, 
        AwsStorageLocation.AWS_EU_WEST_2, AzureLocations.AZURE_eastus
    ]

    tasks = [ProtectionStoregateway]

    def on_start(self):
        logging.info(f"----Step 1----  Staring CRUD workflow for an protection stores gateway -------")
        try:
            self.psg_id = None
            self.psg_name = None
            self.local_protection_store_id = None
            self.local_protection_store_name = None
            self.cloud_protection_store_id = None
            self.cloud_protection_store_name = None
            config = helpers.read_config()
            vcenter_details = config["testInput"]["vcenter_details"]
            vcenter_name = vcenter_details["name"]
            host_name = vcenter_details["host"]
            datastore_name = vcenter_details["datastore"]
            network_name = vcenter_details["network_name"]
            self.vcenter_id = get_vcenter_id_by_name(vcenter_name)
            self.host_id = get_host_id(host_name)
            self.datastore_id = get_datastore_id(datastore_name, vcenter_name)
            self.network_name = get_moref(network_name, get_networks(self.vcenter_id))
            self.subnet_mask = vcenter_details["netmask"]
            self.gateway = vcenter_details["gateway"]
            self.network_type = vcenter_details["network_type"]
            self.dns_ip = vcenter_details["dns_ip"]
        except Exception as e:
            logger.error(f"[on_start] Exception occurred {e}")
            logger.error(traceback.format_exc())
            rp_logger.error(f"[on_test_start] Error while creating prerequsites::{e}")
            rp_mgr.finish_test_step(step_id=rp_test_id, status=rp_agent.ReportPortalStatus.FAILED)
            rp_mgr.finish_launch()
            sys.exit(1)

    def on_stop(self):
        logger.info(f"---- User test completed -------")
        response = delete_all_protection_stores_from_current_psg(self.psg_name)
        logger.info(f"Delete protection store response {response}")
        if self.psg_id:
            delete_psg(self.psg_id)


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
