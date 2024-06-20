import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from requests import codes

from tenacity import (
    retry,
    retry_if_exception_type,
    wait_fixed,
    stop_after_delay,
)

from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from lib.common.enums.dashboard_backup_type import BackupType as TypeOfBackup
from lib.dscc.backup_recovery.vmware_protection.common.custom_error_helper import (
    BackupUsageNotFoundError,
    BackupUsageCompareError,
)
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.api.catalyst_gateway import CatalystGateway
from tests.catalyst_gateway_e2e.test_context import Context
from utils.timeout_manager import TimeoutManager


logger = logging.getLogger()


class CompareType(Enum):
    greater = auto()
    less = auto()


@dataclass
class BackupUsageCompare:
    context: Context
    atlas: CatalystGateway = field(init=False)
    psgw_id: str = field(init=False)

    disk_bytes_local_diff: int = field(default=1000)
    user_bytes_local_diff: int = field(default=1000)

    disk_bytes_cloud_diff: int = field(default=1000)
    user_bytes_cloud_diff: int = field(default=1000)

    space_ratio_local_diff: float = field(default=0.0)
    space_ratio_cloud_diff: float = field(default=0.0)

    local_store_init: dict = field(default=None)
    cloud_store_init: dict = field(default=None)
    local_store_to_compare: dict = field(default=None)
    cloud_store_to_compare: dict = field(default=None)

    def __post_init__(self):
        self.atlas = self.context.catalyst_gateway
        self.psgw_id = self.atlas.get_catalyst_gateway_id(self.context)

        logger.info(
            f"Setting local backup usage expectation disk_bytes_diff: {self.disk_bytes_local_diff}, user_bytes_diff: {self.user_bytes_local_diff},"
            f" space_ratio_diff: {self.space_ratio_local_diff}"
        )
        logger.info(
            f"Setting cloud backup usage expectation disk_bytes_diff: {self.disk_bytes_cloud_diff}, user_bytes_diff: {self.user_bytes_cloud_diff},"
            f" space_ratio_diff: {self.space_ratio_cloud_diff}"
        )
        self._get_values_init()

    def _get_values_init(self) -> None:
        """
        Get and Set initial values from summary endpoint. Before backup or before deletion of backup data.
        """
        local_store_before, cloud_store_before = self._get_backup_usage(timeout=TimeoutManager.standard_task_timeout)
        logger.info(f"Set backup usage init local store: {local_store_before}, cloud store: {cloud_store_before}")
        self.local_store_init = local_store_before
        self.cloud_store_init = cloud_store_before

    def _get_values_to_compare(self) -> None:
        """
        Get and Set values to compare from summary endpoint. After backup or after deletion of backup data.
        """
        local_store_after, cloud_store_after = self._get_backup_usage()
        logger.info(
            f"Set backup usage to compare local store: {local_store_after}," f" cloud store: {cloud_store_after}"
        )
        self.local_store_to_compare = local_store_after
        self.cloud_store_to_compare = cloud_store_after

    def _get_backup_usage(self, timeout: int = 0) -> tuple[dict, dict]:
        """
        Get local and cloud store values from dashboard/backup-capacity-usage-summary endpoint
        """

        @retry(
            retry=retry_if_exception_type((StopIteration, TypeError, IndexError)),
            stop=stop_after_delay(timeout),
            wait=wait_fixed(30),
            reraise=True,
        )
        def _fetch_usage_summary() -> tuple[dict, dict]:
            backup_summary_local = self.atlas.get_backup_capacity_usage_summary(backup_type=TypeOfBackup.local)
            logger.debug(backup_summary_local.text)
            assert (
                backup_summary_local.status_code == codes.ok
            ), f"Error fetching summary local - {backup_summary_local.text}"

            backup_summary_cloud = self.atlas.get_backup_capacity_usage_summary(backup_type=TypeOfBackup.cloud)
            logger.debug(backup_summary_cloud.text)
            assert (
                backup_summary_cloud.status_code == codes.ok
            ), f"Error fetching summary cloud- {backup_summary_cloud.text}"
            logger.debug(f"Searching for backup usage for {self.psgw_id}")
            result_local = next(
                filter(
                    lambda item: item["catalystGatewayId"] == self.psgw_id,
                    backup_summary_local.json().get("storesInfo"),
                )
            )
            result_cloud = next(
                filter(
                    lambda item: item["location"] == self.context.aws_region,
                    backup_summary_cloud.json().get("cloud"),
                )
            )
            logger.debug(f"Found backup usage with result: {result_local} for local and {result_cloud} for cloud")
            # TODO: chose which cloud store to compare instead of [0]
            return result_local["local"], result_cloud

        try:
            return _fetch_usage_summary()
        except StopIteration:
            logger.debug(
                f"All backups that have been found: {self.atlas.get_backup_capacity_usage_summary(backup_type=TypeOfBackup.local).json().get('storesInfo')}"
                f" for local and for cloud :{self.atlas.get_backup_capacity_usage_summary(backup_type=TypeOfBackup.cloud).json().get('cloud')}"
            )
            raise BackupUsageNotFoundError(self.psgw_id)

    def _compare(self, compare_type: CompareType, backup_type: BackupTypeScheduleIDs) -> None:
        """
        Prerequeites:
        1. Set expectation for local and cloud - set_expected_local_usage and set_expected_cloud_usage()
        2. Take initial values get_values_init()
        3. Run or delete backup
        4. Take values to compare get_values_to_compare()

        user_bytes_diff - 'totalUserBytes' it is whole compressed datastore used for vm.
        """

        def _compare_store(cloud_store: bool = False) -> None:
            disk_bytes_key = "totalDiskBytes"
            user_bytes_key = "totalUserBytes"
            flag_disk_bytes_cloud_failed = False
            flag_user_bytes_cloud_failed = False
            flag_disk_bytes_local_failed = False
            flag_user_bytes_local_failed = False
            error_array = []
            if cloud_store:
                init_total_disk_bytes = self.cloud_store_init[disk_bytes_key]
                value_to_compare_disk_bytes = self.cloud_store_to_compare[disk_bytes_key]
                diff_disk = self.disk_bytes_cloud_diff

                init_total_user_bytes = self.cloud_store_init[user_bytes_key]
                value_to_compare_user_bytes = self.cloud_store_to_compare[user_bytes_key]
                diff_user = self.user_bytes_cloud_diff

                logger.debug(
                    f"Comparing {disk_bytes_key}. Comparing value: {value_to_compare_disk_bytes} should be {compare_type.name}"
                    f" from initial value :{init_total_disk_bytes}, by diff: {diff_disk} bytes"
                )
                try:
                    _compare_func(init_total_disk_bytes, value_to_compare_disk_bytes, self.disk_bytes_cloud_diff)
                except AssertionError as e:
                    logger.warning(f"Comparing {disk_bytes_key} failed!")
                    flag_disk_bytes_cloud_failed = True
                    error_array.append(e)

                logger.debug(
                    f"Comparing {user_bytes_key}. Comparing value: {value_to_compare_user_bytes} should be {compare_type.name}"
                    f" from initial value :{init_total_user_bytes}, by diff: {diff_user} bytes"
                )
                try:
                    _compare_func(init_total_user_bytes, value_to_compare_user_bytes, self.user_bytes_cloud_diff)
                except AssertionError as e:
                    logger.warning(f"Comparing {user_bytes_key} failed!")
                    flag_user_bytes_cloud_failed = True
                    error_array.append(e)

            else:
                init_total_disk_bytes = self.local_store_init[disk_bytes_key]
                value_to_compare_disk_bytes = self.local_store_to_compare[disk_bytes_key]
                diff_disk = self.disk_bytes_local_diff

                init_total_user_bytes = self.local_store_init[user_bytes_key]
                value_to_compare_user_bytes = self.local_store_to_compare[user_bytes_key]
                diff_user = self.user_bytes_local_diff

                logger.debug(
                    f"Comparing {disk_bytes_key}. Comparing value: {value_to_compare_disk_bytes} should be {compare_type.name}"
                    f" from initial value :{init_total_disk_bytes}, by diff: {diff_disk} bytes"
                )
                try:
                    _compare_func(init_total_disk_bytes, value_to_compare_disk_bytes, self.disk_bytes_local_diff)
                except AssertionError as e:
                    logger.warning(f"Comparing {disk_bytes_key} failed!")
                    flag_disk_bytes_local_failed = True
                    error_array.append(e)

                logger.debug(
                    f"Comparing {user_bytes_key}. Comparing value: {value_to_compare_user_bytes} should be {compare_type.name}"
                    f" from initial value :{init_total_user_bytes}, by diff: {diff_user} bytes"
                )
                try:
                    _compare_func(init_total_user_bytes, value_to_compare_user_bytes, self.user_bytes_local_diff)
                except AssertionError as e:
                    logger.warning(f"Comparing {user_bytes_key} failed!")
                    flag_user_bytes_local_failed = True
                    error_array.append(e)

            if (
                flag_disk_bytes_cloud_failed
                or flag_user_bytes_cloud_failed
                or flag_disk_bytes_local_failed
                or flag_user_bytes_local_failed
            ):
                raise BackupUsageCompareError(error_array)

        def _compare_ratio(cloud_store: bool = False) -> None:
            ratio_key = "spaceSavingsRatio"
            if cloud_store:
                value_init = float(self.cloud_store_init[ratio_key].split(":")[0])
                value_to_compare = float(self.cloud_store_to_compare[ratio_key].split(":")[0])
                diff = self.space_ratio_cloud_diff
            else:
                value_init = float(self.local_store_init[ratio_key].split(":")[0])
                value_to_compare = float(self.local_store_to_compare[ratio_key].split(":")[0])
                diff = self.space_ratio_local_diff
            logger.debug(
                f"Comparing {ratio_key}. Comparing value: {value_to_compare} should be {compare_type.name}"
                f" from initial value :{value_init}, by diff: {diff}"
            )
            _compare_func(value_init, value_to_compare, diff)

        def _compare_func(value_init: float, value_to_compare: float, diff: float) -> None:
            if diff != 0:
                if compare_type == CompareType.greater:
                    result = value_to_compare - value_init
                else:
                    result = value_init - value_to_compare
                assert result > diff, f"Result {result} should be bigger than diff: {diff}"

        if (
            self.local_store_init
            and self.local_store_to_compare
            and (backup_type == BackupTypeScheduleIDs.local or backup_type == BackupTypeScheduleIDs.cloud)
        ):
            logger.info("Comparing local store usage")
            _compare_store()
            if self.space_ratio_local_diff > 0.0:
                _compare_ratio()
            logger.info("Local store usage -  compare success")
        else:
            logger.info("Local store usage -  nothing to compare")

        if len(self.cloud_store_to_compare) > 0 and backup_type == BackupTypeScheduleIDs.cloud:
            if len(self.cloud_store_init) == 0:
                self.cloud_store_init = {
                    "totalDiskBytes": 0,
                    "totalUserBytes": 0,
                    "spaceSavingsRatio": "0.0:1",
                }
            logger.info("Comparing cloud store usage")
            _compare_store(cloud_store=True)
            if self.space_ratio_cloud_diff > 0.0:
                _compare_ratio(cloud_store=True)
            logger.info("Cloud store usage -  compare success")
        else:
            logger.info("Cloud store usage -  nothing to compare")

    @retry(
        retry=retry_if_exception_type(BackupUsageCompareError),
        stop=stop_after_delay(2000),
        wait=wait_fixed(60),
    )
    def wait_for_usage_compare(self, compare_type: CompareType, backup_type: BackupTypeScheduleIDs) -> None:
        """
        Wait for refresh of summary data. Backend refresh metrics every 5 minutes.
        """
        # Need to add wait time here as backend metrics are taking time to update the metrics
        time.sleep(330)
        self._get_values_to_compare()
        self._compare(compare_type, backup_type)
