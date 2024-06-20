"""
    No of simultaneous users from  customer account  access data panorama customer facing RestAPI ,   measure response time
    Note : dataset created by datageneration tool in array
"""

from datetime import datetime, timedelta
from enum import Enum
from http.client import HTTPConnection
from locust import SequentialTaskSet, tag, task
from requests import codes
from tests.datapanorama import datapanorama_paths
from common import helpers

import logging


logger = logging.getLogger(__name__)
HTTPConnection.debuglevel = 1
logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True


class Granularity(Enum):
    daily = "day"
    hourly = "collectionHour"


class RestApiResponseTime(SequentialTaskSet):
    proxies = helpers.set_proxy(no_proxy=True)

    today_time = datetime.now()
    endtime = today_time.isoformat(timespec="milliseconds") + "Z"
    starttime = datetime.now() - timedelta(days=30)
    starttime = starttime.isoformat(timespec="milliseconds") + "Z"
    granularity = "day"
    snapstarttime = datetime.now() - timedelta(days=1)
    snapstarttime = snapstarttime.isoformat(timespec="milliseconds") + "Z"

    def on_start(self):
        self.headers = self.user.headers
        self.proxies = self.user.proxies

    @tag("tested")
    @task
    def get_volume_consumption_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_VOLUMES_SUMMARY}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_VOLUMES_SUMMARY} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_VOLUMES_SUMMARY} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_volume_cost_trend_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_VOLUMES_COST_TREND}?granularity={self.granularity}&start-time={self.starttime}&end-time={self.endtime}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_VOLUMES_COST_TREND} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_VOLUMES_COST_TREND} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("rework")
    @task
    def get_volume_usage_trend_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_VOLUMES_SUMMARY}/systems/{system_id}/volumes/{volume_id}/volume-usage-trend?granularity={Granularity.hourly.value}&start-time={self.starttime}&end-time={self.endtime}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_VOLUMES_USAGE_TREND} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_VOLUMES_USAGE_TREND} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_volume_creation_trend_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_VOLUMES_CREATION_TREND}?granularity={self.granularity}&start-time={self.starttime}&end-time={self.endtime}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_VOLUMES_CREATION_TREND} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_VOLUMES_CREATION_TREND} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    # {"error":"An internal server error occurred","errorCode":500}
    @tag("testing.failed")
    @task
    def get_volume_activity_trend_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_VOLUMES_ACTIVITY_TREND}?granularity={self.granularity}&start-time={self.starttime}&end-time={self.endtime}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_VOLUMES_ACTIVITY_TREND} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_VOLUMES_ACTIVITY_TREND} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_snapshots_summary_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_SNAPSHOTS_SUMMARY}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_SNAPSHOTS_SUMMARY} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_SNAPSHOTS_SUMMARY} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_snapshots_cost_trend_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_SNAPSHOTS_COST_TREND}?granularity={self.granularity}&start-time={self.starttime}&end-time={self.endtime}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_SNAPSHOTS_COST_TREND} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_SNAPSHOTS_COST_TREND} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_snapshots_usage_trend_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_SNAPSHOTS_USAGE_TREND}?granularity={self.granularity}&start-time={self.starttime}&end-time={self.endtime}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_SNAPSHOTS_USAGE_TREND} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_SNAPSHOTS_USAGE_TREND} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_snapshots_creation_trend_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_SNAPSHOTS_CREATION_TREND}?granularity={self.granularity}&start-time={self.starttime}&end-time={self.endtime}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_SNAPSHOTS_CREATION_TREND} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_SNAPSHOTS_CREATION_TREND} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_snapshots_age_trend_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_SNAPSHOTS_AGE_TREND}?granularity={self.granularity}&start-time={self.starttime}&end-time={self.endtime}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_SNAPSHOTS_AGE_TREND} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_SNAPSHOTS_AGE_TREND} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_snapshots_retention_trend_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_SNAPSHOTS_RETENTION}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_SNAPSHOTS_RETENTION} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_SNAPSHOTS_RETENTION} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(f"response is {response.text}")

    @tag("tested")
    @task
    def get_snapshots_total_api(self):
        # Note: In UI, only the snapshots created at a day is filtered so using the same here in testing
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_SNAPSHOTS_TOTAL}?offset=0&limit=10&filter=createdAt%20ge%20{self.snapstarttime}%20and%20createdAt%20lt%20{self.endtime}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_SNAPSHOTS_TOTAL} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_SNAPSHOTS_TOTAL} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_clones_summary_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_CLONES_SUMMARY}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_CLONES_SUMMARY} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_CLONES_SUMMARY} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_clones_cost_trend_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_CLONES_COST_TREND}?granularity={self.granularity}&start-time={self.starttime}&end-time={self.endtime}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_CLONES_COST_TREND} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_CLONES_COST_TREND} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_clones_usage_trend_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_CLONES_USAGE_TREND}?granularity={self.granularity}&start-time={self.starttime}&end-time={self.endtime}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_CLONES_USAGE_TREND} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_CLONES_USAGE_TREND} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_clones_creation_trend_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_CLONES_CREATION_TREND}?granularity={self.granularity}&start-time={self.starttime}&end-time={self.endtime}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_CLONES_CREATION_TREND} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_CLONES_CREATION_TREND} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    # {"error":"An internal server error occurred","errorCode":500}
    @tag("testing.failed")
    @task
    def get_clones_activity_trend_api(self):
        with self.client.get(
            f"{datapanorama_paths.CONSUMPTION_CLONES_ACTIVITY_TREND}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.CONSUMPTION_CLONES_ACTIVITY_TREND} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.CONSUMPTION_CLONES_ACTIVITY_TREND} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_inventory_storage_systems_summary_api(self):
        with self.client.get(
            f"{datapanorama_paths.INVENTORY_STORAGE_SYSTEMS_SUMMARY}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.INVENTORY_STORAGE_SYSTEMS_SUMMARY} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.INVENTORY_STORAGE_SYSTEMS_SUMMARY} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_inventory_storage_system_info_api(self):
        with self.client.get(
            f"{datapanorama_paths.INVENTORY_STORAGE_SYSTEMS_INFO}?includeArrayInfo=true",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.INVENTORY_STORAGE_SYSTEMS_INFO} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.INVENTORY_STORAGE_SYSTEMS_INFO} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_inventory_systems_cost_trend_api(self):
        with self.client.get(
            f"{datapanorama_paths.INVENTORY_STORAGE_SYSTEMS_COST_TREND}?noOfMonths=12&granularity={self.granularity}&start-time={self.starttime}&end-time={self.endtime}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(
                f"Get API {datapanorama_paths.INVENTORY_STORAGE_SYSTEMS_COST_TREND} response code is {response.status_code}"
            )
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.INVENTORY_STORAGE_SYSTEMS_COST_TREND} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @tag("tested")
    @task
    def get_applineage_summary_api(self):
        with self.client.get(
            f"{datapanorama_paths.APPLINEAGE_SUMMARY}",
            headers=self.headers.authentication_header,
            catch_response=True,
            proxies=self.proxies,
        ) as response:
            logger.info(f"Get API {datapanorama_paths.APPLINEAGE_SUMMARY} response code is {response.status_code}")
            if response.status_code != codes.ok:
                response.failure(
                    f"Failed to get {datapanorama_paths.APPLINEAGE_SUMMARY} (,StatusCode : {str(response.status_code)},response: {response.text}"
                )
            logger.info(response.text)

    @task
    def on_completion(self):
        self.interrupt()
