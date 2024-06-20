################################################################
#
# File: array_consumption_steps.py
# Author: Kranthi Kumar
# Date: Oct 15 2022
#
# (C) Copyright 2016 - Hewlett Packard Enterprise Development LP
#
################################################################
#
# Description:
#      module implementation.
#      Script contain S3 Automation API methods
################################################################

import copy

from lib.dscc.data_panorama.app_lineage.models.app_lineage import (
    ApplicationList,
    ApplicationVolumesInfo,
    ClonesDetail,
    SnapshotsDetail,
    VolumesDetail,
)
from lib.dscc.data_panorama.consumption.models.clones import (
    ClonesActivityTrend,
    ClonesConsumption,
    ClonesCostTrend,
    ClonesCreationTrend,
    ClonesUsageTrend,
)
from lib.dscc.data_panorama.consumption.models.snapshots import (
    SnapshotAgeTrend,
    SnapshotConsumption,
    SnapshotCostTrend,
    SnapshotCreationTrend,
    SnapshotRetentionTrend,
    SnapshotUsageTrend,
    Snapshots,
)
from lib.dscc.data_panorama.consumption.models.volumes import (
    CloneCopies,
    SnapshotCopies,
    VolumeIoTrend,
    VolumesActivityTrend,
    VolumesConsumption,
    VolumesCostTrend,
    VolumesCreationTrend,
    VolumesUsageTrend,
    VolumeUsage,
    VolumeUsageTrend,
)
from lib.dscc.data_panorama.inventory_manager.models.inventory_manager import (
    InventoryStorageSystemsCostTrend,
    InventoryStorageSystemsSummary,
    InventoryStorageSystems,
    ArrayDetails,
)
from tests.e2e.data_panorama.panorama_context import Context
from tests.steps.data_panorama.panaroma_spark_methods import PanaromaSparkMethods
import re
import datetime


class ArrayData(object):
    """Class created to host methods returning array data similar to API response. Currently this has new method created for volume consumption."""

    def __init__(self, context: Context):
        self.steps_obj = PanaromaSparkMethods(context=context, load_mock=True)
        self.data_dict = {}
        self.data_dict.update(context.alletra_6k_created_config_info)
        self.data_dict.update(context.alletra_9k_created_config_info)
        self.collection_time: str = ""
        self.cost_dict = context.cost_dict

    def convert_float_to_decimal(self, flo=0.0, precision=5):
        """
        Convert a float to string of decimal.
        precision: by default 2.
        If no arg provided, return "0.00".
        """
        return ("%." + str(precision) + "f") % flo

    def format_size(self, vol_size, vol_size_in, vol_size_out, precision=0):
        """
        Convert file size to a string representing its value in B, KB, MB and GB.
        The convention is based on sizeIn as original unit and sizeOut
        as final unit.
        """
        assert vol_size_in.upper() in {"B", "KB", "MB", "GB"}, "sizeIn type error"
        assert vol_size_out.upper() in {"B", "KB", "MB", "GB"}, "sizeOut type error"
        if vol_size_in == "B":
            if vol_size_out == "KB":
                return self.convert_float_to_decimal(vol_size / 1024.0, precision)
            elif vol_size_out == "MB":
                return vol_size / 1024.0**2
            elif vol_size_out == "GB":
                return vol_size / 1024.0**3
        elif vol_size_in == "KB":
            if vol_size_out == "B":
                return self.convert_float_to_decimal(vol_size * 1024.0, precision)
            elif vol_size_out == "MB":
                return self.convert_float_to_decimal(vol_size / 1024.0, precision)
            elif vol_size_out == "GB":
                return self.convert_float_to_decimal(vol_size / 1024.0**2, precision)
        elif vol_size_in == "MB":
            if vol_size_out == "B":
                return vol_size * 1024.0**2
            elif vol_size_out == "KB":
                return self.convert_float_to_decimal(vol_size * 1024.0, precision)
            elif vol_size_out == "GB":
                return self.convert_float_to_decimal(vol_size / 1024.0, precision)
        elif vol_size_in == "GB":
            if vol_size_out == "B":
                return self.convert_float_to_decimal(vol_size * 1024.0**3, precision)
            elif vol_size_out == "KB":
                return self.convert_float_to_decimal(vol_size * 1024.0**2, precision)
            elif vol_size_out == "MB":
                return self.convert_float_to_decimal(vol_size * 1024.0, precision)

    def calculate_cost(self, total_size, total_used, cost):
        total_size = int(self.format_size(total_size, "B", "GB"))
        total_used = int(self.format_size(total_used, "B", "GB"))
        try:
            cost_per_gb = cost / int(total_size)
        except ZeroDivisionError:
            cost_per_gb = 0
        total_used_space_cost = total_used * cost_per_gb
        return total_used_space_cost

    def common_field_generator(
        self,
        id: str = "",
        name: str = "",
        type: str = "",
        generation: int = "",
        resourceUri: str = "",
        customerId: str = "",
        consoleUri: str = "",
    ):
        common_fields = {
            "id": id,
            "name": name,
            "type": type,
            "generation": generation,
            "resourceUri": resourceUri,
            "customerId": customerId,
            "consoleUri": consoleUri,
        }
        return common_fields

    def get_volume_consumption(self) -> VolumesConsumption:
        """Method to get volume consumption data from array side

        Returns:
            VolumesConsumption: Returns VolumesConsumption object with array data
        """
        total_cust_size = self.steps_obj.spark_total_cust_size()
        vol_last_coll_data, vol_avg_data = self.steps_obj.new_spark_vol_consumption()
        cost_dict = self.cost_dict
        cost = cost_dict[vol_avg_data["customer_id"]]
        cost_per_gb = cost / total_cust_size
        curr_mon_used_bytes = vol_avg_data["current_month_utilized_size_in_bytes"]
        prev_mon_used_bytes = vol_avg_data["previous_month_utilized_size_in_bytes"]
        curr_mon_vol_cost = (curr_mon_used_bytes / (1024 * 1024 * 1024)) * cost_per_gb
        prev_mon_vol_cost = (prev_mon_used_bytes / (1024 * 1024 * 1024)) * cost_per_gb

        consumption_data = {
            "numVolumes": vol_last_coll_data["total_vol_count"],
            "totalSizeInBytes": vol_last_coll_data["vol_total_size_in_bytes"],
            "utilizedSizeInBytes": vol_last_coll_data["vol_used_size_in_bytes"],
            "cost": cost,
            "previousMonthCost": prev_mon_vol_cost,
            "previousMonthUtilizedSizeInBytes": prev_mon_used_bytes,
            "currentMonthCost": curr_mon_vol_cost,
            "currentMonthUtilizedSizeInBytes": curr_mon_used_bytes,
        }
        common_fields = self.common_field_generator(
            type="volumes consumption",
            generation=1,
            customerId=vol_avg_data["customer_id"],
        )
        consumption_data.update(common_fields)
        return VolumesConsumption(**consumption_data)
