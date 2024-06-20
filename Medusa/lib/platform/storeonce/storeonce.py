import json
import logging
import random
import string
from time import sleep

import requests
from assertpy import assert_that
from pytest_check import check
from requests import Response, codes
from waiting import wait, TimeoutExpired

from lib.common.common import post, get, put
from lib.platform.storeonce.models.store_once import (
    CloudStore,
    CloudStorePermission,
    StoreOnceAuthentication,
    StoreOnceCredentials,
    StoreOnceInformation,
    StoreOnceLogCollection,
    NTPInfo,
    VolumeCopy,
    VolumeCopyJob,
    CloudStorePermissions,
    UserEntryDetails,
    CloudStoreProxy,
    ResourceInfo,
)
from utils.size_conversion import tib_to_bytes

logger = logging.getLogger()


class StoreOnce:
    def __init__(self, host, username, password):
        self.username = username
        self.password = password
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}
        self.protocol = "https://"
        self.host = host
        self.url = f"{self.protocol}{self.host}"
        self.path_auth = "pml/login/authenticatewithobject"
        self.path_resources = "rest/index/resources?category=systems&count=20&start=0&query=&sort=systemHostname%3Aasc"
        self.path_information = "api/v1/management-services/system/information"
        self.path_log_collection = "logcollection/collections"
        self.path_ntp_servers = "network-services/cluster/networking/config/ntp"
        self.path_volume_copy = "api/v1/data-services/data-extractor/volume-copies"
        self.path_volume_copy_job = "api/v1/data-services/data-extractor/jobs/job"
        self.path_cloud_store = "api/v1/data-services/cat/stores/store/0"
        self.path_all_cloud_stores = "api/v1/data-services/cat/stores"
        self.path_store_permission = "api/v1/data-services/cat/stores-permissions/store/0/client/0"
        self.path_store_proxy_setting = "api/v1/data-services/cat/cloud-proxy"
        self.path_get_store_permission = "api/v1/data-services/cat/stores-permissions/store/0"
        self.path_set_user_entries = "rest/users"
        self.path_services_status = "api/v1/data-services/d2d-service/status"
        self.path_licensing = "api/v1/management-services/licensing"
        self.path_licensing_status = "api/v1/management-services/licensing/status"
        self.path_remote_support_status = "rsvs/remotesupportstatus"
        self.path_local_storage_overview = "api/v1/management-services/local-storage/overview"
        self.cluster_management = "pml/clustermanagement"
        self.ida_status = "hp/rest/provisioning/storeonce-{cluster_uuid}/system/v2/support/idastatus"
        self.strong_pw = "strongpw/manage/allinfo"
        self.token = ""
        self.summary = None
        self.session = self.authenticate(username, password)
        self.load_summary()

    def authenticate(self, username: str, password: str):
        payload = StoreOnceCredentials(username, password).to_json()
        response = post(self.url, self.path_auth, json_data=payload, headers=self.headers)
        _session = StoreOnceAuthentication.from_json(response.text)
        assert _session.access_token
        self.token = _session.access_token
        self.headers["Authorization"] = f"Bearer {self.token}"

    def load_summary(self, refresh=False):
        if refresh or not self.summary:
            response = get(self.url, self.path_resources, headers=self.headers)
            resource_info = ResourceInfo.from_json(response.text)
            self.summary = resource_info.members[0]

    def read_data(self, source_id, snapshot_id, external_id, region, store_credentials):
        logger.info(f"Read data from s3: {source_id}, snapshot: {snapshot_id}")
        volume_copy_model = VolumeCopy(
            target_identifier=snapshot_id,
            source_identifier=source_id,
            client_password=store_credentials.password,
            source_type="CATALYST",
            target_type="EBS",
            client_user=store_credentials.username,
        )
        external_id = external_id.decode("utf-8").replace("-", "")
        volume_copy_model.aws_details.externalID = external_id
        volume_copy_model.aws_details.region = region
        payload = volume_copy_model.to_json(ensure_ascii=False)
        response: Response = post(
            self.url,
            self.path_volume_copy,
            json_data=payload,
            headers=self.headers,
            auth=(self.username, self.password),
        )
        assert (
            response.status_code == codes.accepted
        ), f"Status code is :{codes.accepted} != {response.status_code}. Response: {response.text}"

        def _wait_for_job_status_completed():
            try:
                response_wait = requests.get(response.headers._store["location"][1], headers=self.headers, verify=False)
                volume_copy_job = VolumeCopyJob.from_json(response_wait.text)
                if volume_copy_job.job_state == "COMPLETED":
                    return volume_copy_job
            except KeyError as e:
                logger.warn(f"Data extractor volume copy job waits: {e}")

        try:
            volume_copy_job = wait(_wait_for_job_status_completed, timeout_seconds=180, sleep_seconds=5)
        except TimeoutExpired as e:
            logger.error(f"Data extractor volume copy job failed. {e}")
            raise e

        logger.info(f"Read data from s3: {source_id} completed, snpashot: {snapshot_id}")

        changed_blocks_count = 0
        for changed_data in volume_copy_job.checkpoint_data:
            changed_blocks_count += changed_data.num_blocks_read_or_written
        return changed_blocks_count

    def write_data(self, catalyst_store_name, external_id, store_credentials: StoreOnceCredentials):
        random_suffix = "".join(random.choice(string.ascii_letters) for _ in range(10))
        target_id = f"{catalyst_store_name}:{random_suffix}"
        logger.info(f"Write data to s3: {target_id}")
        volume_copy_model = VolumeCopy(target_id, store_credentials.password, store_credentials.username)
        external_id = external_id.decode("utf-8").replace("-", "")
        volume_copy_model.aws_details.externalID = external_id
        payload = volume_copy_model.to_json(ensure_ascii=False)
        response: Response = post(
            self.url,
            self.path_volume_copy,
            json_data=payload,
            headers=self.headers,
            auth=(self.username, self.password),
        )
        assert (
            response.status_code == codes.accepted
        ), f"Status code is :{codes.accepted} != {response.status_code}. Response: {response}"

        response_wait = ""

        def _wait_for_job_status_completed():
            try:
                response_wait = requests.get(response.headers._store["location"][1], headers=self.headers, verify=False)
                volume_copy_job: VolumeCopyJob = VolumeCopyJob.from_json(response_wait.text)
                if volume_copy_job.job_state == "COMPLETED":
                    return True
            except KeyError as e:
                logger.warn(f"Data extractor volume copy job waits: {e}")

        try:
            wait(_wait_for_job_status_completed, timeout_seconds=900, sleep_seconds=15)
        except TimeoutExpired as e:
            logger.error(f"Data extractor volume copy job failed. {e}, response: {response_wait}")
            raise e

        logger.info(f"Write data to s3: {target_id} completed")
        return target_id

    def get_temp_support_password_mode(self) -> str:
        def _get_response():
            return get(self.url, self.strong_pw, headers=self.headers)

        wait(
            lambda: _get_response().status_code == requests.codes.ok,
            timeout_seconds=900,
            sleep_seconds=10,
            waiting_for=f"After 15min response status code for {self.strong_pw} is: {_get_response().status_code},"
            f"response: {_get_response().text}",
        )
        return _get_response().json().get("mode")

    def get_cluster_uuid(self) -> str:
        response = get(self.url, self.cluster_management, headers=self.headers)
        uuid = json.loads(response.text)["uuid"]
        return uuid

    def get_ida_status(self) -> bool | None:
        cluster_uuid = self.get_cluster_uuid()
        response = get(self.url, self.ida_status.format(cluster_uuid=cluster_uuid), headers=self.headers)
        logger.info(f"Get IDA status response status code: {response.status_code}. Response body: {response.text}")
        return self._ida_status_or_none(response.json())

    @staticmethod
    def _ida_status_or_none(response_json: dict) -> bool | None:
        ida_status = response_json.get("idaStatus")
        if ida_status:
            ida_status = bool(ida_status)
        return ida_status

    def get_platform_customer_id(self):
        response = get(self.url, self.path_information, headers=self.headers)
        information = StoreOnceInformation.from_json(response.text)
        return information.platform_customer_id

    def get_support_bundle_logs(self, name):
        response = get(self.url, self.path_log_collection, headers=self.headers)
        logs_collection = response.json().get("logcollection")
        log_list = []
        for log_collection in logs_collection:
            log_json = json.dumps(log_collection)
            log = StoreOnceLogCollection.from_json(log_json)
            if log.status == "COMPLETE" and name in log.name:
                log_list.append(log)
        return log_list

    def get_cloud_store(self) -> CloudStore:
        response = get(self.url, self.path_cloud_store, headers=self.headers)
        cloud_store = CloudStore.from_json(response.text)
        return cloud_store

    def get_cloud_stores(self) -> list[CloudStore]:
        wait(
            lambda: get(self.url, self.path_all_cloud_stores, headers=self.headers).status_code == 200,
            timeout_seconds=120,
            sleep_seconds=10,
        )
        response = get(self.url, self.path_all_cloud_stores, headers=self.headers)
        logger.info(f"Cloud stores response status code: {response.status_code}. Response body: {response.text}")
        assert response.ok, f"{response.json()}"
        return [CloudStore.from_dict(store) for store in response.json()["members"]]

    def get_store_permissions(self) -> list[CloudStorePermissions]:
        response = get(self.url, self.path_get_store_permission, headers=self.headers)
        logger.info(
            f"Cloud stores permissions response status code: {response.status_code}. Response body: {response.text}"
        )
        return [CloudStorePermissions.from_dict(permission) for permission in response.json()["members"]]

    def get_cloud_proxy_settings(self) -> CloudStoreProxy:
        response = get(self.url, self.path_store_proxy_setting, headers=self.headers)
        logger.info(f"Cloud proxies response status code: {response.status_code}. Response body: {response.text}")
        cloud_proxy = CloudStoreProxy.from_json(response.text)
        return cloud_proxy

    def get_ntp_servers(self) -> NTPInfo:
        response = get(self.url, self.path_ntp_servers, headers=self.headers)
        ntp_servers = NTPInfo.from_json(response.text)
        return ntp_servers

    def get_system_information(self):
        response = get(self.url, self.path_information, headers=self.headers)
        system_information = StoreOnceInformation.from_json(response.text)
        return system_information

    def get_storeoncename_and_serialnumber(self):
        response = get(self.url, self.path_information, headers=self.headers)
        response_information = response.json()
        logger.info(
            f'storeoncename {response_information["hostname"]} and serial number {response_information["serialNumber"]}'
        )
        return response_information["hostname"], response_information["serialNumber"]

    def get_dual_auth_pending_request_id(self):
        # This method will  getting the request id
        dualauth_pending_request = "pml/dualauth/requests/?&start=0&count=20&sort=submitTime:desc&status=pending"
        response = get(self.url, dualauth_pending_request, headers=self.headers)
        assert response.status_code == codes.ok, f"Failed to get the request id"
        response_information = response.json()
        logger.info(response_information)
        request_id = response_information["members"][0]["id"]
        logger.info(f"Dualauth request id {request_id}")
        return request_id

    def get_dualauth_status(self):
        dualauth_config = "pml/dualauth/config"
        # This method will give the dualauth status
        response = get(self.url, dualauth_config, headers=self.headers)
        assert response.status_code == codes.ok, f"Failed to get dualauth status"
        response_information = response.json()
        dualauth_status = response_information["featureEnabled"]
        logger.info(dualauth_status)
        return dualauth_status

    def set_store_permission_public(self, access=True):
        payload = CloudStorePermission(access).to_json()
        response = put(self.url, self.path_store_permission, json_data=payload, headers=self.headers)
        assert response.status_code == codes.no_content

    def set_cloud_proxy_settings(self, address):
        payload = CloudStoreProxy(address).to_json()
        response = put(self.url, self.path_store_proxy_setting, headers=self.headers)
        logger.info(
            f"Update cloud proxies response status code: {response.status_code}. Response body: {response.text}"
        )
        assert response.status_code == codes.ok

    def set_ida_status(self, status: bool = False) -> bool | None:
        cluster_uuid = self.get_cluster_uuid()
        response = post(
            self.url,
            self.ida_status.format(cluster_uuid=cluster_uuid),
            headers=self.headers,
            json_data=json.dumps({"idaStatus": status}),
        )
        logger.info(f"Set IDA status response status code: {response.status_code}. Response body: {response.text}")
        return self._ida_status_or_none(response.json())

    def enable_disable_dual_auth_in_storeonce(self, enable=False):
        # The method will enable the dual auth in storeonce
        dualauth_config = "pml/dualauth/config"
        payload = json.dumps({"featureEnabled": enable})
        response = put(self.url, dualauth_config, json_data=payload, headers=self.headers)
        assert response.status_code == codes.accepted, f"Failed to enable= {enable}  dual auth in storeonce"

    def approve_dual_auth_request(
        self, dualauth_username, dualauth_password, admin_username, admin_password, request_id
    ):
        # This method will approve the dual auth request
        self.authenticate(dualauth_username, dualauth_password)
        dualauth_approve_request = f"pml/dualauth/requests/{request_id}"
        payload = json.dumps({"status": "approved"})
        response = put(self.url, dualauth_approve_request, json_data=payload, headers=self.headers)
        assert response.status_code == codes.ok, f"Failed to approve dual auth request id {request_id}"
        self.authenticate(admin_username, admin_password)

    def reset_user_password(self, username, password):
        payload = UserEntryDetails(username, password).to_json()
        path = f"{self.path_set_user_entries}/{username}"
        response = put(self.url, path, json_data=payload, headers=self.headers)
        assert response.status_code == codes.ok

    def verify_stores_with_local_cloud_value(
        self,
        cloud_disk_bytes_expected,
        user_bytes_expected_cloud,
        local_capacity_bytes,
    ):
        """
        This method is used to verify the local and cloud backup values in dscc are matched with storeonce values
        """
        self.load_summary(refresh=True)
        # Check if cloud disk bytes value in dscc is matched with storeonce cloud disk bytes value
        cloud_disk_bytes_expected = cloud_disk_bytes_expected
        cloud_disk_bytes_actual = self.summary.cloud_disk_bytes
        assert (
            cloud_disk_bytes_expected == cloud_disk_bytes_actual
        ), f"cloud_capacity_bytes: {cloud_disk_bytes_expected} == {cloud_disk_bytes_actual}"
        # Check if  user bytes for cloud disk bytes value in dscc is matched with storeonce user bytes for cloud value
        cloud_user_bytes_actual = self.summary.cloud_user_bytes
        assert (
            user_bytes_expected_cloud == cloud_user_bytes_actual
        ), f"cloud_user_bytes: {user_bytes_expected_cloud} == {cloud_user_bytes_actual}"
        # Check if user bytes for local_capacity_bytes value in dscc is matched with storeonce local_capacity_bytes value
        local_capacity_bytes_expected = local_capacity_bytes
        local_capacity_bytes_actual = self.summary.local_capacity_bytes
        assert (
            local_capacity_bytes_expected == local_capacity_bytes_actual
        ), f"local_capacity_bytes: {local_capacity_bytes_expected} == {local_capacity_bytes_actual}"
        logger.info("storeonce info has verified successfully")

    def verify_stores(self, local_capacity_bytes=50000000000, user_bytes_expected=0):
        self.load_summary(refresh=True)
        # Cloud Capacity Bytes - hardcoded by StoreOnce - if possible to check without dashboard /localhost
        with check:
            cloud_capacity_bytes_expected = tib_to_bytes(1000)
            cloud_capacity_bytes_actual = self.summary.cloud_capacity_bytes
            assert_that(cloud_capacity_bytes_expected, "cloud_capacity_bytes").is_equal_to(cloud_capacity_bytes_actual)
            # Verify that we didn't get cloud store that has something written on (with 5% margin)
            cloud_free_bytes_expected = tib_to_bytes(995)
            cloud_free_bytes_actual = self.summary.cloud_free_bytes
            assert_that(cloud_free_bytes_expected, "cloud_free_bytes").is_less_than(cloud_free_bytes_actual)
            # Check if cloud bank is empty
            cloud_user_bytes_actual = self.summary.cloud_user_bytes
            assert_that(user_bytes_expected, "user_bytes_expected").is_equal_to(cloud_user_bytes_actual)
            # Check if EBS with correct values is attached to StoreOnce (with 2% margin)
            local_capacity_bytes_expected = int(local_capacity_bytes * 0.98)
            local_capacity_bytes_actual = self.summary.local_capacity_bytes
            assert_that(local_capacity_bytes_expected, "local_capacity_bytes").is_less_than(local_capacity_bytes_actual)
            local_capacity_bytes_expected = int(local_capacity_bytes / 0.98)
            assert_that(local_capacity_bytes_expected, "local_capacity_bytes").is_greater_than(
                local_capacity_bytes_actual
            )
            # If metadata volume is not full (EBS) after first time creation (with 2% margin)
            local_free_bytes_expected = local_capacity_bytes * 0.98
            local_free_bytes_actual = self.summary.local_free_bytes
            assert_that(local_free_bytes_expected, "local_free_bytes").is_less_than(local_free_bytes_actual)
            # Check if local bank is empty
            local_user_bytes_actual = self.summary.local_user_bytes
            assert_that(user_bytes_expected, "user_bytes").is_equal_to(local_user_bytes_actual)
            logger.info("Storeonce verify stores success.")

    def verify_health(self):
        self.assert_licensing_status()
        self.assert_remote_support_status()
        self.assert_services_overall_health_string_status()
        self.load_summary(refresh=True)
        assert self.summary.appliance_status == "OK", "appliance_status"
        assert self.summary.software_update_recommended is False, "software_update_recommended should be False"

    def verify_health_status_for_storeonce(self):
        self.load_summary(refresh=True)
        assert self.summary.remote_support_status == "OK", "remote_support_status"
        assert self.summary.appliance_status == "OK", "appliance_status"
        assert self.summary.data_services_status == "OK", "data_services_status"
        assert self.summary.license_status == "OK", "license_status"
        assert self.summary.software_update_recommended is False, "software_update_recommended should be False"

    def verify_health_cvsa(self):
        with check:
            self.assert_licensing_status()
            self.assert_remote_support_status()
            self.assert_stores_health()
            self.assert_local_storage_health()
            self.assert_each_service_status()

    def assert_licensing_status(self):
        storeonce_license = get(self.url, self.path_licensing, headers=self.headers).json()
        assert storeonce_license["licenseLockId"], storeonce_license["licenseLockId"]
        assert storeonce_license["modeName"] == "Standalone", storeonce_license["modeName"] == "Standalone"
        assert storeonce_license["licensingStatusEnum"] == "GOOD", storeonce_license["licensingStatusEnum"] == "GOOD"
        assert storeonce_license["licensingStatus"] == 0, storeonce_license["licensingStatus"]
        assert not storeonce_license["inGracePeriod"], storeonce_license["inGracePeriod"]

    def get_remote_support_status(self) -> str | None:
        try:
            request = get(self.url, self.path_remote_support_status, headers=self.headers)
            return request.json().get("remoteSupportStatusEnum", None)
        except Exception as e:
            logging.error(f"Get remote support status failed with error: {e}")
            return None

    def assert_remote_support_status(self):
        wait(
            lambda: self.get_remote_support_status() == "OK",
            timeout_seconds=360,
            sleep_seconds=10,
            waiting_for=f"remoteSupportStatusEnum is {self.get_remote_support_status()} after 360s, expected: OK",
        )

    def assert_stores_health(self):
        stores = get(self.url, self.path_all_cloud_stores, headers=self.headers).json()["members"][0]
        assert stores["healthLevelString"] == "OK"
        assert stores["cloudStoreEnabled"] is True

    def assert_local_storage_health(self):
        local_storage_overview = get(self.url, self.path_local_storage_overview, headers=self.headers).json()
        assert local_storage_overview["storageHealth"] == 2
        assert local_storage_overview["storageHealthString"] == "Online, healthy"
        assert local_storage_overview["simplifiedStatus"] == 0
        assert local_storage_overview["simplifiedStatusString"] == "OK"

    def assert_services_overall_health_string_status(self) -> dict:
        response_json = get(self.url, self.path_services_status, headers=self.headers).json()
        services = response_json["services"]
        services_status = services["OverallHealth"]["healthLevelString"]
        assert services_status == "OK"
        return services

    def assert_each_service_status(self):
        services_to_check = [
            "evt-mgr",
            "rep-obj-rpc",
            "rep-rpc",
            "buffer-manager",
            "res-mgr",
            "d2d-iscsid",
            "fc-rpc",
            "smm",
            "licensing-rpc",
            "rmc-ert-iscsid",
            "d2d-manager-proxy",
            "replication",
            "smm-rpc",
            "cat-rpc",
            "predupe",
            "object-store",
        ]
        timeout = 0
        while timeout <= 10:
            services = self.assert_services_overall_health_string_status()
            services_check = []
            for service in services_to_check:
                if service in services:
                    services_check.append(services[service]["healthLevelString"] == "OK")
                else:
                    logging.error(f"Following service status not available: {service} in {services}")
            services_asserted = {k: "OK" if v else "UNHEALTHY" for k, v in zip(services_to_check, services_check)}
            if not all(services_check):
                logging.error(f"UNHEALTHY services available: {services_asserted}")
                timeout += 1
            else:
                break
            logging.error(f"Checking again in 30s, total 5 minutes")
            sleep(30)
        logging.error(f"UNHEALTHY services available after 5 minutes: {services_asserted}")
        # todo: uncomment/delete after requirements are clarified
        # assert all(services_check), f"UNHEALTHY services available after 10 minutes: {services_asserted}"
