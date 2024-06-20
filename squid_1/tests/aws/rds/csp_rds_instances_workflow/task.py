from locust import SequentialTaskSet, tag, task
from lib.dscc.backup_recovery.aws_protection.rds.models.csp_rds_instance import (
    CSPRDSInstance,
    CSPRDSInstanceList,
)
from tests.aws.config import RDSPaths
from requests import codes
from common import helpers
import logging
from tenacity import retry, wait_exponential, stop_after_attempt
import random

# Below import is needed for locust-grafana integration, do not remove
import locust_plugins

logger = logging.getLogger(__name__)

v1_beta_1_api, _ = helpers.get_v1_beta_api_prefix()


class CSPRDSInstanceTasks(SequentialTaskSet):
    """CSP RDS instance jobs will be done like list csp rds instances
    and details csp rds instances and refresh csp rds instance simultaneously"""

    def on_start(self):
        self.csp_rds_instances: CSPRDSInstanceList = None
        self.rds_instance: CSPRDSInstance = None

    @tag("rds_instance")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def list_csp_rds_instances(self):
        """List CSP RDS instances simultaneously"""
        # /backup-recovery/v1beta1/csp-rds-instances
        with self.client.get(
            f"{RDSPaths.CSP_RDS_INSTANCES}",
            proxies=self.user.proxies,
            headers=self.user.headers.authentication_header,
            catch_response=True,
            name="List CSP RDS Instances",
        ) as response:
            logger.info(f"List CSP RDS instances returned code {response.status_code}\n Response :{response.text}")
            if response.status_code == codes.ok:
                self.csp_rds_instances = CSPRDSInstanceList.from_json(response.text)
                logger.info(f"CSP RDS Instances {self.csp_rds_instances}")
                if self.csp_rds_instances.total == 0:
                    logger.warning("CSP RDS instances list is empty")
            else:
                response.failure(
                    f"Failed to get csp RDS instances list->Response code {response.status_code}\n Response text {response.text}"
                )

    @tag("rds_instance")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def get_csp_rds_instance_details(self):
        """List a CSP RDS instance details simultaneously"""

        # /backup-recovery/v1beta1/csp-rds-instances/{id}
        if self.csp_rds_instances:
            self.rds_instance = random.choice(self.csp_rds_instances.items)
            with self.client.get(
                f"{RDSPaths.CSP_RDS_INSTANCES}/{self.rds_instance.id}",
                proxies=self.user.proxies,
                headers=self.user.headers.authentication_header,
                catch_response=True,
                name="GET CSP RDS Instance details",
            ) as response:
                logger.info(
                    f"Response {RDSPaths.CSP_RDS_INSTANCES}/{self.rds_instance.id}: {response.status_code}"
                )
                logger.info(
                    f"Response text for {RDSPaths.CSP_RDS_INSTANCES}/{self.rds_instance.id}: {response.text}"
                )
                if response.status_code != codes.ok:
                    response.failure(
                        f"Failed to get RDS instance details->{response.status_code}\n Response text {response.text}"
                    )
        else:
            raise Exception("No CSP RDS instances available")

    @tag("rds_instance")
    @task
    @retry(
        wait=wait_exponential(multiplier=10, min=4, max=30),
        stop=stop_after_attempt(10),
        before_sleep=helpers.custom_before_sleep,
        retry_error_callback=helpers.raise_retries_exceeded_exception,
    )
    def refresh_csp_rds_instance(self):
        """Perform refresh of CSP RDS instance"""
        # /backup-recovery/v1beta1/csp-rds-instances/{id}/refresh
        if self.csp_rds_instances:
            try:
                with self.client.post(
                    f"{self.rds_instance.resource_uri}/refresh",
                    headers=self.user.headers.authentication_header,
                    proxies=self.user.proxies,
                    catch_response=True,
                    name="Refresh CSP RDS Instance",
                ) as response:
                    try:
                        logger.info(
                            f"Refreshing csp rds instance {self.rds_instance.id}->Response code {response.status_code}"
                        )
                        logger.info(
                            f"Refreshing csp rds instance {self.rds_instance.id}->Response text {response.text}"
                        )

                        if response.status_code == codes.accepted:
                            logger.info(f"Response Headers = {response.headers}")
                            task_uri = response.headers["location"]
                            task_status = helpers.wait_for_task(task_uri=task_uri, api_header=self.user.headers)
                            if task_status == helpers.TaskStatus.success:
                                logger.info("Refresh csp rds instance success")
                            elif task_status == helpers.TaskStatus.timeout:
                                raise Exception("Refresh csp rds instance failed with timeout error")
                            elif task_status == helpers.TaskStatus.failure:
                                raise Exception("Refresh csp rds instance failed with status'FAILED' error")
                            else:
                                raise Exception("Refresh csp rds instance failed with unknown error")
                        else:
                            logger.info(
                                f"Refresh CSP RDS instance {self.rds_instance.id}->Response code {response.status_code}"
                            )
                            logger.info(
                                f"Refresh CSP RDS instance {self.rds_instance.id}->Response text {response.text}"
                            )

                            response.failure(
                                f"Refresh CSP RDS instance {self.rds_instance.id}->Response code is {response.status_code}\n Response text {response.text}"
                            )
                    except Exception as e:
                        response.failure(f"Exception during refresh csp rds instance {e}")
                        raise
            except Exception as e:
                helpers.custom_locust_response(self.user.environment, name="refresh_csp_rds_instance", exception=e)
        else:
            raise Exception("No CSP RDS instances available")

    @tag("rds_instance")
    @task
    def on_completion(self):
        self.interrupt()
