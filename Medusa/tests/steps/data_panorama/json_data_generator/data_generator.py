################################################################
#
# File: data_generator.py
# Author: Kranthi Kumar
# Date: Oct 15 2022
#
# (C) Copyright 2016 - Hewlett Packard Enterprise Development LP
#
################################################################
#
# Description:
#      module implementation.
#      Script will generate consolidated json Mock data and upload to upload server
################################################################

import calendar
import copy
import datetime
import gc
import json
import os
import pickle
import random
import string
import shutil
import gzip
import pytz
import time
from dateutil.relativedelta import relativedelta
from utils.common_helpers import get_project_root
import re
import pandas as pd
from lib.platform.storage_array.ssh_connection import SshConnection


class JsonDataGenerator(object):
    def __init__(self):
        self.final_json_dict_dt1: dict = {}
        self.final_json_dict_dt2: dict = {}
        self.final_table_dict: dict = {}
        self.jsons_path = get_project_root() / "tests/steps/data_panorama/json_data_generator/"
        self.json_data_set = {}
        self.hauler_type = "Fleet"
        self.num_collections = 0
        self.system_date = ""
        self.json_name_index = 1
        self.collection_start_time = ""
        self.vol_creation_time = ""
        self.eoc_collection_start_time = ""
        self.collection_end_time = ""
        self.eoc_collection_end_time = ""
        self.cust_id = ""
        self.num_of_coll_per_cust = 0
        self.total_used = 0
        self.first_coll_vol_count = 0
        self.first_coll_snp_count = 0
        self.first_coll_clone_count = 0
        self.per_coll_vol_count = 0
        self.per_coll_snp_count = 0
        self.per_coll_clone_count = 0
        self.mounted_vol_count = 0
        self.per_coll_mounted_vol_count = 0
        self.vol_size = 0
        self.snp_size = 0
        self.clone_size = 0
        self.used_size_mb = 0
        self.vol_index = 1
        self.dt1_all_coll_temp_dict = {}
        self.dt1_all_coll_sys_data = []
        self.dt1_all_coll_sys_cap_data = []
        self.dt2_all_coll_sys_data = []
        self.dt1_arr_ids = []
        self.dt2_arr_ids = []
        self.per_coll_total_used = {}
        self.per_coll_total_used_dt2 = {}
        self.dt2_all_coll_temp_dict = {}
        self.pool_ids = []
        self.dt1_total_vol_count = 0
        self.dt_1_dict_data = {}
        self.dt_2_dict_data = {}
        self.dt1_all_coll_snap_dict = {}
        self.dt2_all_coll_snap_dict = {}
        self.storage_sys_ids = []
        self.vlun_index = 1
        self.dt1_all_coll_vlun_dict = {}
        self.dt2_all_coll_vlun_dict = {}
        self.vol_coll_dict = {}
        self.vol_coll_flag = 1
        self.coll_index = 1
        self.dt2_all_coll_volcoll_dict = {}
        self.vol_coll_time = 0
        self.dt1_all_app_dict = {}
        self.dt1_all_vol_perf_dict = {}
        self.dt2_all_vol_perf_dict = {}
        self.customer_dir_path = ""
        self.coll_dir_path = ""
        self.cust = 0
        self.spark_vol_data = []
        self.spark_snap_data = []
        self.spark_clone_data = []
        self.spark_vol_perf = []
        self.spark_vol_usage = []
        self.spark_app_data = []
        self.spark_inventory_data = []
        self.spark_cost_data = {}
        self.spark_app_snap_data = []
        self.spark_app_clone_data = []
        self.vol_c = 0
        self.snaps = 0
        self.clones = 0
        self.usage_vol_count = 0
        self.perf_vol_count = 0
        self.spark_frame_coll_start_time = ""
        self.spark_frame_coll_end_time = ""
        self.coll_id = ""
        self.json_name = ""
        self.spark_final_json_data = {}
        self.client = ""
        self.inv_arr_ids = {}

    def generate_random_str_with_alpha_number(self, num_of_char: int = 5):
        # call random.choices() string module to find the string in Uppercase + numeric data.
        ran = "".join(random.choices(string.ascii_lowercase + string.digits, k=num_of_char))
        return str(ran)

    def generate_array_id(self, num_of_digits=10):
        ran = "".join(random.choices(string.ascii_uppercase + string.digits, k=num_of_digits))
        return str(ran)

    def load_json_convert_dict(self, json_name):
        with open(json_name) as f:
            json_to_dict = json.load(f)
        return json_to_dict

    def convert_dict_to_json(self, dict_to_convert, json_type=""):
        hex_id = self.generate_random_str_with_alpha_number(num_of_char=29)
        if json_type == "DT1":
            hex_id += "dt1"
        if json_type == "DT2":
            hex_id += "dt2"
        if json_type == "EOC":
            hex_id += "eoc"

        if json_type == "costinfo":
            hex_id = self.generate_random_str_with_alpha_number(num_of_char=29) + "cis"

            if not os.path.exists(self.customer_dir_path + "/costinfo"):
                os.makedirs(self.customer_dir_path + "/costinfo")
            self.gz_name = self.customer_dir_path + "/" + "costinfo/" + hex_id + ".gz"
            self.json_name = self.customer_dir_path + "/" + "costinfo/" + hex_id + ".json"
            with open(self.json_name, "w") as outfile:
                json.dump(dict_to_convert, outfile)
        else:
            self.gz_name = self.customer_dir_path + "/" + self.coll_dir_path + "/" + hex_id + ".gz"
            self.json_name = self.customer_dir_path + "/" + self.coll_dir_path + "/" + hex_id + ".json"
            with open(self.json_name, "w") as outfile:
                json.dump(dict_to_convert, outfile)

        with gzip.open(self.gz_name, "wt", encoding="UTF-8") as zipfile:
            json.dump(dict_to_convert, zipfile)

    def calculate_collection_time(self, years=0, months=0, days=0, hours=0, minutes=0):
        array_date = datetime.datetime.now(datetime.timezone.utc)
        calculated_date = array_date - relativedelta(
            years=years, months=months, days=days, hours=hours, minutes=minutes
        )
        return calculated_date

    def convert_date_in_to_ms(Self, dt):
        # return calendar.timegm(time.strptime(dt, "%Y-%m-%d %H:%M:%S.%f000 %z %Z"))
        epoch = datetime.datetime.utcfromtimestamp(0).replace(tzinfo=pytz.UTC)
        return round((dt - epoch).total_seconds() * 1000)

    def convert_ms_to_date_time(self, ms, convert_type="mstodate"):
        if convert_type == "mstodate":
            converted_date_time = datetime.datetime.fromtimestamp(ms / 1000.0, tz=pytz.UTC).strftime(
                "%Y-%m-%d %H:%M:%S.%f000 %z %Z"
            )
            return converted_date_time
        elif convert_type == "stodate":
            return datetime.datetime.fromtimestamp(ms, pytz.UTC).strftime("%Y-%m-%d %H:%M:%S.%f000 %z %Z")

    def validate_data_set(self):
        self.json_data_set = {
            "num_of_customers": 2,
            "num_of_collections_per_customer": [2, 2],
            "first_col_vol_count": [6, 6],
            "per_col_vol_count": [4, 3],
            "first_col_snap_count": [10, 8],
            "per_col_snap_count": [10, 5],
            "first_col_clone_count": [5, 5],
            "per_col_clone_count": [5, 5],
            "first_col_mounted_vol_count": [2, 4],
            "per_col_mounted_vol_count": [1, 3],
            "first_col_mounted_clone_count": [2, 2],
            "per_col_mounted_clone_count": [2, 2],
            "all_thin_count": False,
            "all_thick_count": False,
            "array_count_device_type_1": [2, 2],
            "storage_system_count_device_type_2": [2, 2],
            "array_count_device_type_2": [2, 2],
            "nodes_per_array": 2,
            "HaulerType": "Fleet",
            "deviceType": [["deviceType1", "deviceType2"], ["deviceType1", "deviceType2"]],
            "CollectionType": "Inventory",
            "number_of_app_per_array": [[2, 2], [2, 2]],
            "per_collection_app_count": [[1, 1], [1, 1]],
            "volume_count_per_app": 2,
        }

    def create_json_data_set(self, user_passed_data_set: dict = {}):
        self.json_data_set = {
            "num_of_customers": 1,
            "num_of_collections_per_customer": [2],
            "first_col_vol_count": [10],
            "per_col_vol_count": [20],
            "first_col_snap_count": [10],
            "per_col_snap_count": [5],
            "first_col_clone_count": [10],
            "per_col_clone_count": [5],
            "first_col_mounted_vol_count": [2],
            "per_col_mounted_vol_count": [1],
            "first_col_mounted_clone_count": [2],
            "per_col_mounted_clone_count": [1],
            "all_thin_count": False,
            "all_thick_count": False,
            "array_count_device_type_1": [2],
            "storage_system_count_device_type_2": [2],
            "array_count_device_type_2": [2],
            "nodes_per_array": 2,
            "HaulerType": "Fleet",
            "deviceType": [["deviceType1", "deviceType2"]],
            "CollectionType": "Inventory",
            "number_of_app_per_array": [[2, 2]],
            "per_collection_app_count": [[1, 1]],
            "volume_count_per_app": 2,
        }
        for field, field_val in user_passed_data_set.items():
            self.json_data_set[field] = field_val

    def reset_final_json_dict(self):
        self.final_json_dict_dt1 = {}
        self.final_json_dict_dt1["Systems"] = []
        self.final_json_dict_dt1["SystemCapacity"] = []
        self.final_json_dict_dt1["Volumes"] = {}
        self.final_json_dict_dt2 = {}
        self.final_json_dict_dt2["Systems"] = []
        self.final_json_dict_dt2["Volumes"] = {}
        self.final_json_dict_dt1["Snapshots"] = {}
        self.final_json_dict_dt2["Snapshots"] = {}
        self.final_json_dict_dt1["Vluns"] = {}
        self.final_json_dict_dt2["VolumeCollections"] = {}
        self.final_json_dict_dt1["Applicationsets"] = {}
        self.final_json_dict_dt1["VolumePerformance"] = []
        self.final_json_dict_dt2["VolumePerformance"] = []
        self.final_json_dict_dt1["Error"] = {}
        self.final_json_dict_dt2["Error"] = {}

    def calculate_snap_count(self):
        snap_count_f_coll = (
            self.json_data_set["first_col_snap_count"] * self.json_data_set["array_count_device_type_2"][self.cust]
        )
        snap_count_per_coll = (
            self.json_data_set["per_col_snap_count"] * self.num_of_coll_per_cust
        ) * self.json_data_set["array_count_device_type_2"][self.cust]
        return snap_count_f_coll + snap_count_per_coll

    def set_coll_global_vars(self, cust):
        self.num_of_coll_per_cust = self.json_data_set["num_of_collections_per_customer"][cust]
        self.first_coll_vol_count = (
            2
            if round(
                self.json_data_set["first_col_vol_count"][cust]
                / (
                    self.json_data_set["array_count_device_type_1"][cust]
                    + self.json_data_set["array_count_device_type_2"][cust]
                )
            )
            <= 3
            else round(
                self.json_data_set["first_col_vol_count"][cust]
                / (
                    self.json_data_set["array_count_device_type_1"][cust]
                    + self.json_data_set["array_count_device_type_2"][cust]
                )
            )
        )
        self.first_coll_snp_count = (
            2
            if round(
                self.json_data_set["first_col_snap_count"][cust]
                / (
                    self.json_data_set["array_count_device_type_1"][cust]
                    + self.json_data_set["array_count_device_type_2"][cust]
                )
            )
            <= 3
            else round(
                self.json_data_set["first_col_snap_count"][cust]
                / (
                    self.json_data_set["array_count_device_type_1"][cust]
                    + self.json_data_set["array_count_device_type_2"][cust]
                )
            )
        )
        self.first_coll_clone_count = (
            2
            if round(
                self.json_data_set["first_col_clone_count"][cust]
                / (
                    self.json_data_set["array_count_device_type_1"][cust]
                    + self.json_data_set["array_count_device_type_2"][cust]
                )
            )
            else round(
                self.json_data_set["first_col_clone_count"][cust]
                / (
                    self.json_data_set["array_count_device_type_1"][cust]
                    + self.json_data_set["array_count_device_type_2"][cust]
                )
            )
        )
        self.per_coll_vol_count = (
            2
            if round(
                self.json_data_set["per_col_vol_count"][cust]
                / (
                    self.json_data_set["array_count_device_type_1"][cust]
                    + self.json_data_set["array_count_device_type_2"][cust]
                )
            )
            <= 3
            else round(
                self.json_data_set["per_col_vol_count"][cust]
                / (
                    self.json_data_set["array_count_device_type_1"][cust]
                    + self.json_data_set["array_count_device_type_2"][cust]
                )
            )
        )
        self.per_coll_snp_count = (
            2
            if round(
                self.json_data_set["per_col_snap_count"][cust]
                / (
                    self.json_data_set["array_count_device_type_1"][cust]
                    + self.json_data_set["array_count_device_type_2"][cust]
                )
            )
            else round(
                self.json_data_set["per_col_snap_count"][cust]
                / (
                    self.json_data_set["array_count_device_type_1"][cust]
                    + self.json_data_set["array_count_device_type_2"][cust]
                )
            )
        )
        self.per_coll_clone_count = (
            2
            if round(
                self.json_data_set["per_col_clone_count"][cust]
                / (
                    self.json_data_set["array_count_device_type_1"][cust]
                    + self.json_data_set["array_count_device_type_2"][cust]
                )
            )
            <= 3
            else round(
                self.json_data_set["per_col_clone_count"][cust]
                / (
                    self.json_data_set["array_count_device_type_1"][cust]
                    + self.json_data_set["array_count_device_type_2"][cust]
                )
            )
        )
        self.mounted_vol_count = round(
            self.json_data_set["first_col_mounted_vol_count"][cust]
            / (
                self.json_data_set["array_count_device_type_1"][cust]
                + self.json_data_set["array_count_device_type_2"][cust]
            )
        )
        self.per_coll_mounted_vol_count = round(
            self.json_data_set["per_col_mounted_vol_count"][cust]
            / (
                self.json_data_set["array_count_device_type_1"][cust]
                + self.json_data_set["array_count_device_type_2"][cust]
            )
        )
        self.mounted_clone_count = round(
            self.json_data_set["first_col_mounted_clone_count"][cust]
            / (
                self.json_data_set["array_count_device_type_1"][cust]
                + self.json_data_set["array_count_device_type_2"][cust]
            )
        )
        self.per_coll_mounted_clone_count = round(
            self.json_data_set["per_col_mounted_clone_count"][cust]
            / (
                self.json_data_set["array_count_device_type_1"][cust]
                + self.json_data_set["array_count_device_type_2"][cust]
            )
        )

    def reset_all_global_vars(self):
        self.dt1_arr_ids = []
        self.dt2_arr_ids = []
        self.dt1_all_coll_sys_data = []
        self.dt2_all_coll_sys_data = []
        self.total_used = 0
        self.vol_size = 0
        self.snp_size = 0
        self.clone_size = 0
        self.used_size_mb = 0
        self.vol_index = 1
        self.dt1_all_coll_temp_dict = {}
        self.dt1_all_coll_sys_cap_data = []
        self.per_coll_total_used = {}
        self.dt2_all_coll_temp_dict = {}
        self.pool_ids = []
        self.dt1_total_vol_count = 0
        self.dt_1_dict_data = {}
        self.dt_2_dict_data = {}
        self.dt1_all_coll_snap_dict = {}
        self.dt2_all_coll_snap_dict = {}
        self.storage_sys_ids = []
        self.vlun_index = 1
        self.dt1_all_coll_vlun_dict = {}
        self.dt2_all_coll_vlun_dict = {}
        self.vol_coll_dict = {}
        self.vol_coll_flag = 1
        self.coll_index = 1
        self.dt2_all_coll_volcoll_dict = {}
        self.dt1_all_app_dict = {}
        self.dt1_all_vol_perf_dict = {}
        self.dt2_all_vol_perf_dict = {}
        self.collection_start_time = ""
        self.collection_end_time = ""
        self.spark_frame_coll_start_time = ""
        self.spark_frame_coll_end_time = ""

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
                return self.convert_float_to_decimal((vol_size / 1024.0), precision)
            elif vol_size_out == "MB":
                return self.convert_float_to_decimal((vol_size / 1024.0**2), precision)
            elif vol_size_out == "GB":
                return self.convert_float_to_decimal((vol_size / 1024.0**3), precision)
        elif vol_size_in == "KB":
            if vol_size_out == "B":
                return self.convert_float_to_decimal((vol_size * 1024.0), precision)
            elif vol_size_out == "MB":
                return self.convert_float_to_decimal((vol_size / 1024.0), precision)
            elif vol_size_out == "GB":
                return self.convert_float_to_decimal((vol_size / 1024.0**2), precision)
        elif vol_size_in == "MB":
            if vol_size_out == "B":
                return vol_size * 1024.0**2
            elif vol_size_out == "KB":
                return self.convert_float_to_decimal((vol_size * 1024.0), precision)
            elif vol_size_out == "GB":
                return self.convert_float_to_decimal((vol_size / 1024.0), precision)
        elif vol_size_in == "GB":
            if vol_size_out == "B":
                return self.convert_float_to_decimal((vol_size * 1024.0**3), precision)
            elif vol_size_out == "KB":
                return self.convert_float_to_decimal((vol_size * 1024.0**2), precision)
            elif vol_size_out == "MB":
                return self.convert_float_to_decimal((vol_size * 1024.0), precision)

    def generate_EOC_data(self, cust_id, dtypes):
        dtype_status = {}
        for dt in dtypes:
            dtype_status[dt] = "Success"
        dt_eoc = {
            "Version": "1.0",
            "PlatformCustomerID": "ubomzo8szzwne4owc0jdsgim2dhfaawxcw1b9",
            "CollectionID": self.coll_id,
            "Region": "us-west-2",
            "ApplicationCustomerID": cust_id,
            "ApplicationInstanceID": "89ead31f-3a92-4f37-980a-d324d7d538f6",
            "CollectionTrigger": "Planned",
            "CollectionStartTime": self.eoc_collection_start_time,
            "CollectionEndTime": self.eoc_collection_end_time,
            "HaulerType": "Fleet",
            "CollectionType": "EOC",
            "DeviceTypeUploadStatus": dtype_status,
        }
        return dt_eoc

    def generate_inv_cost_data(self, cust_id, r_time):
        cost_loc_info = {"costAndLocationInputs": []}
        temp_cost_loc_dict = {}
        #
        temp_spark_cost_info = {}
        total_cost = 0
        loc_list = [
            "Colorado:Fort Collins:CO 80528:United States",
            "California:San Jose:CA 95002:United States",
            "Texas:Spring:TX 77389:United States",
            "Colorado:Colorado Springs:CO 80919:United States",
            "north carolina:NC 27703:north carolina:United States",
            "Washington:Washington:DC 20004:United States",
            "California:Roseville:CA 95747:United States",
            "New York:New York:10017:Northeastern United States",
        ]

        loc_dict = {}
        for system in self.inv_arr_ids:
            loc_choice = random.choice(loc_list).split(":")
            temp_cost_loc_dict["systemId"] = system
            self.spark_cost_data[system] = {}
            temp_cost_loc_dict["costInfo"] = []
            temp_cost_loc_dict["locationInfo"] = {
                "city": loc_choice[1],
                "state": loc_choice[0],
                "country": loc_choice[3],
                "postalCode": loc_choice[2],
            }
            self.spark_cost_data[system] = {
                "city": loc_choice[1],
                "state": loc_choice[0],
                "country": loc_choice[3],
                "postalCode": loc_choice[2],
            }
            loc_dict[loc_choice[2]] = 1
            temp_cost_info = {}
            for arr in self.inv_arr_ids[system]:
                temp_cost_info["arrayId"] = arr
                cost = random.randint(30000, 60000)
                total_cost += cost
                temp_cost_info["cost"] = cost
                temp_cost_info["currencyType"] = "USD"
                months_to_depriciate = random.randint(3, 10)
                if months_to_depriciate != 0:
                    total_cost += cost
                calculated_date = r_time
                dep_start_date = self.convert_date_in_to_ms(calculated_date)
                temp_cost_info["depreciationStartDate"] = dep_start_date
                temp_cost_info["monthsToDepreciate"] = months_to_depriciate
                temp_cost_loc_dict["costInfo"].append(copy.deepcopy(temp_cost_info))
            cost_loc_info["costAndLocationInputs"].append(copy.deepcopy(temp_cost_loc_dict))
        rand_number = random.randint(100, 999)
        r_time_stamp = r_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        cost_loc_info.update(
            {
                "requestTimestamp": r_time_stamp,
                "requestUuid": f"b9{rand_number}a2a-f596-4f5c-b60a-974d19c8b{rand_number}",
                "customerId": cust_id,
            }
        )

        self.spark_cost_data[cust_id] = total_cost
        self.spark_cost_data["numoflocations"] = len(loc_dict.keys())
        return cost_loc_info

    def generate_collection_data(self, data_set: dict = {}, customer_id: str = "", days_back_data: int = 0):
        self.create_json_data_set(user_passed_data_set=data_set)
        for customer in range(self.json_data_set["num_of_customers"]):
            self.dt1_all_vol_perf_dict["VolumePerformance"] = []
            self.dt2_all_vol_perf_dict["VolumePerformance"] = []
            self.cust = customer
            # Under this directory collection will be stored
            random_dir_name = self.generate_random_str_with_alpha_number(num_of_char=8)
            local_path = get_project_root() / f"tests/e2e/data_panorama/mock_data_generate/{random_dir_name}"
            self.customer_dir_path = str(local_path)
            if not os.path.exists(local_path):
                os.makedirs(local_path)
            self.dt_1_dict_data = self.load_json_convert_dict(str(self.jsons_path) + "/device_type_1.json")
            self.dt_2_dict_data = self.load_json_convert_dict(str(self.jsons_path) + "/device_type_2.json")
            self.set_coll_global_vars(cust=customer)
            start_time = self.calculate_collection_time(days=days_back_data)
            end_time = start_time + relativedelta(years=0, months=0, days=0, hours=0, minutes=5)

            self.collection_start_time = start_time.strftime("%Y-%m-%d %H:%M:%S.%f000 %z %Z")

            # self.spark_frame_coll_start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")

            self.collection_end_time = end_time.strftime("%Y-%m-%d %H:%M:%S.%f000 %z %Z")

            self.spark_frame_coll_end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")
            self.spark_frame_coll_start_time = end_time.strftime("%Y-%m-%d %H:%M:%S")
            self.eoc_collection_start_time = self.collection_end_time
            self.eoc_collection_end_time = end_time + relativedelta(years=0, months=0, days=0, hours=0, minutes=5)
            self.eoc_collection_end_time = self.eoc_collection_end_time.strftime("%Y-%m-%d %H:%M:%S.%f000 %z %Z")
            self.system_date = self.collection_start_time

            # self.cust_id = self.generae_random_str_with_alpha_number(num_of_char=32)
            self.cust_id = customer_id
            for collection in range(self.json_data_set["num_of_collections_per_customer"][customer]):
                self.coll_id = self.generate_random_str_with_alpha_number(num_of_char=32)
                self.coll_dir_path = f"{self.coll_id}-collection-{collection}"
                if not os.path.exists(str(self.customer_dir_path) + "/" + self.coll_dir_path):
                    os.makedirs(str(self.customer_dir_path) + "/" + self.coll_dir_path)

                self.dt1_update_prev_vol_usage()
                self.dt2_update_prev_vol_usage()
                dtypes = []

                for d_type in self.json_data_set["deviceType"][customer]:
                    dtypes.append(d_type)
                    self.reset_final_json_dict()
                    self.generate_single_fields(
                        self.cust_id,
                        self.collection_start_time,
                        self.collection_end_time,
                        d_type,
                        self.json_data_set["HaulerType"],
                        self.json_data_set["CollectionType"],
                    )

                    self.generate_system_data(
                        device_type_1_dict_data=self.dt_1_dict_data,
                        device_type_2_dict_data=self.dt_2_dict_data,
                        device_type=d_type,
                        cust_id=self.cust_id,
                        coll_num=collection,
                    )
                eoc_data = self.generate_EOC_data(cust_id=self.cust_id, dtypes=dtypes)
                self.convert_dict_to_json(eoc_data, json_type="EOC")
                start_time = start_time + relativedelta(years=0, months=0, days=0, hours=8, minutes=0)
                end_time = start_time + relativedelta(years=0, months=0, days=0, hours=0, minutes=5)
                self.vol_creation_time = start_time.strftime("%Y-%m-%d %H:%M:%S.%f000 %z %Z")
                self.collection_start_time = start_time.strftime("%Y-%m-%d %H:%M:%S.%f000 %z %Z")
                self.collection_end_time = end_time.strftime("%Y-%m-%d %H:%M:%S.%f000 %z %Z")
                self.eoc_collection_start_time = self.collection_end_time
                self.eoc_collection_end_time = end_time + relativedelta(years=0, months=0, days=0, hours=0, minutes=5)
                self.eoc_collection_end_time = self.eoc_collection_end_time.strftime("%Y-%m-%d %H:%M:%S.%f000 %z %Z")
                self.spark_frame_coll_end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")
                self.spark_frame_coll_start_time = end_time.strftime("%Y-%m-%d %H:%M:%S")

                gc.collect()
                print("**************************************************")
                print("* Customer-{} Collection-{} Completed...          *".format(customer, collection))
                print("**************************************************")
            cost_loc_info = self.generate_inv_cost_data(self.cust_id, start_time)
            self.convert_dict_to_json(cost_loc_info, "costinfo")

            self.reset_all_global_vars()
        self.spark_final_json_data = {
            "spark_voldata": self.spark_vol_data,
            "spark_snapdata": self.spark_snap_data,
            "spark_clonedata": self.spark_clone_data,
            "spark_volusage": self.spark_vol_usage,
            "spark_volperf": self.spark_vol_perf,
            "spark_appdata": self.spark_app_data,
            "spark_appsnapdata": self.spark_app_snap_data,
            "spark_appclonedata": self.spark_app_clone_data,
            "spark_invdata": self.spark_inventory_data,
            "spark_snpascount": self.snaps,
            "spark_clonescount": self.clones,
            "upload_folder_name": random_dir_name,
            "spark_cost_dict": self.spark_cost_data,
        }
        spark_json_name = str(local_path) + "/spark_json_data.json"
        with open(spark_json_name, "w") as outfile:
            json.dump(self.spark_final_json_data, outfile)
        remote_path = "/tmp/"
        self.client = SshConnection(hostname="10.239.73.120", username="root", password="HPE_ftc3404", sftp=True)
        self.client.put_all(local_path, remote_path)
        with open("mock_file", "w") as mFh:
            mFh.write(random_dir_name)
        # remote_path += "/spark_json_data.json"
        # self.client.put(spark_json_name, remote_path)
        shutil.rmtree(local_path)
        # os.remove(spark_json_name)
        self.client.sftp_close()

        # return (
        #    self.spark_vol_data,
        #    self.spark_snap_data,
        #    self.spark_clone_data,
        #    self.spark_vol_usage,
        #    self.spark_vol_perf,
        #    self.spark_app_data,
        #    self.spark_app_snap_data,
        #    self.spark_app_clone_data,
        #    self.spark_inventory_data,
        #    self.snaps,
        #    self.clones,
        # )

    def generate_single_fields(
        self, cust_id, collection_start_time, collection_end_time, deviceType, HaulerType, CollectionType
    ):

        if deviceType == "deviceType1":
            collection_data = [
                {
                    "Version": "1.0",
                    "PlatformCustomerID": cust_id,
                    "CollectionID": self.coll_id,
                    "Region": "us-west-2",
                    "ApplicationCustomerID": cust_id,
                    "ApplicationInstanceID": cust_id,
                    "CollectionTrigger": "Planned",
                    "CollectionStartTime": collection_start_time,
                    "CollectionEndTime": collection_end_time,
                    "DeviceType": deviceType,
                    "HaulerType": HaulerType,
                    "CollectionType": CollectionType,
                }
            ]
            self.final_json_dict_dt1.update(collection_data[0])
        elif deviceType == "deviceType2":
            collection_data = [
                {
                    "Version": "1.0",
                    "PlatformCustomerID": cust_id,
                    "CollectionID": self.coll_id,
                    "Region": "us-west-2",
                    "ApplicationCustomerID": cust_id,
                    "ApplicationInstanceID": cust_id,
                    "CollectionTrigger": "Planned",
                    "CollectionStartTime": collection_start_time,
                    "CollectionEndTime": collection_end_time,
                    "DeviceType": deviceType,
                    "HaulerType": HaulerType,
                    "CollectionType": CollectionType,
                }
            ]
            self.final_json_dict_dt2.update(collection_data[0])

        self.final_table_dict["collectionData"] = collection_data

    def generate_device_type_1_system_data(self, device_type_1_dict_data, cust_id, coll_num):
        provision_type = "mixed"
        if self.json_data_set["all_thin_count"]:
            provision_type = "thin"
        elif self.json_data_set["all_thick_count"]:
            provision_type = "thick"

        for count in range(self.json_data_set["array_count_device_type_1"][self.cust]):
            temp_sys_data_dt1_dict = {}
            if coll_num == 0:

                arr_id = self.generate_array_id()
                self.inv_arr_ids[arr_id] = []
                cluster_nodes = []
                sys_date = calendar.timegm(time.strptime(self.system_date, "%Y-%m-%d %H:%M:%S.%f000 %z %Z"))
                device_type_1_dict_data["Systems"][0]["centerplaneType"] = (
                    str(self.json_data_set["nodes_per_array"]) + " Node Centerplane"
                )
                device_type_1_dict_data["Systems"][0]["customerId"] = cust_id
                temp_sys_data_dt1_dict["collectionstarttime"] = self.spark_frame_coll_start_time
                temp_sys_data_dt1_dict["collectionendtime"] = self.spark_frame_coll_end_time
                temp_sys_data_dt1_dict["custid"] = cust_id
                temp_sys_data_dt1_dict["arrid"] = arr_id
                temp_sys_data_dt1_dict["storagesysid"] = arr_id
                self.inv_arr_ids[arr_id].append(arr_id)
                temp_sys_data_dt1_dict["numofarrays"] = 1
                temp_sys_data_dt1_dict["devicetype"] = "devicetype1"
                device_type_1_dict_data["Systems"][0][
                    "consoleUri"
                ] = f"/data-ops-manager/storage-systems/device-type1/{arr_id}"
                device_type_1_dict_data["Systems"][0]["displayname"] = f"System system_{arr_id}"
                device_type_1_dict_data["Systems"][0]["id"] = arr_id

                for i in range(self.json_data_set["nodes_per_array"]):
                    cluster_nodes.append(i)
                device_type_1_dict_data["Systems"][0]["inClusterNodes"] = cluster_nodes

                device_type_1_dict_data["Systems"][0]["manufacturing"]["serialNumber"] = arr_id
                device_type_1_dict_data["Systems"][0]["name"] = f"system_{arr_id}"
                temp_sys_data_dt1_dict["storagesysname"] = f"system_{arr_id}"
                temp_sys_data_dt1_dict["arrname"] = f"system_{arr_id}"
                device_type_1_dict_data["Systems"][0]["nodesCount"] = self.json_data_set["nodes_per_array"]

                device_type_1_dict_data["Systems"][0]["nodesPresent"] = cluster_nodes
                device_type_1_dict_data["Systems"][0]["onlineNodes"] = cluster_nodes

                device_type_1_dict_data["Systems"][0]["parameters"]["ServiceProcessorCookie"] = f"SP{arr_id}"
                device_type_1_dict_data["Systems"][0]["resourceUri"] = f"/api/v1/storage-systems/device-type1/{arr_id}"
                device_type_1_dict_data["Systems"][0]["systemDate"] = sys_date
                device_type_1_dict_data["Systems"][0]["systemWWN"] = "2FF7000" + self.generate_array_id(num_of_digits=9)

                for index, a_links in enumerate(device_type_1_dict_data["Systems"][0]["associatedLinks"]):
                    r_type = device_type_1_dict_data["Systems"][0]["associatedLinks"][index]["type"]
                    r_uri = f"/api/v1/storage-systems/device-type1/{arr_id}/{r_type}"
                    device_type_1_dict_data["Systems"][0]["associatedLinks"][index]["resourceUri"] = r_uri
                dt1_mod_data = pickle.dumps(device_type_1_dict_data["Systems"][0])
                self.dt1_all_coll_sys_data.append(pickle.loads(dt1_mod_data))
                self.final_json_dict_dt1["Systems"].append(pickle.loads(dt1_mod_data))
                dt1_mod_sys_cap_data = pickle.dumps(
                    self.generate_system_capacity(device_type_1_dict_data["SystemCapacity"], arr_id, cust_id, coll_num)
                )
                cap_data = pickle.loads(dt1_mod_sys_cap_data)
                temp_sys_data_dt1_dict["storagesystotalused"] = cap_data["capacityByTier"]["totalUsed"]
                temp_sys_data_dt1_dict["storagesysusablecapacity"] = cap_data["capacityByTier"]["usableCapacity"]

                temp_sys_data_dt1_dict["arrtotalused"] = cap_data["capacityByTier"]["totalUsed"]
                temp_sys_data_dt1_dict["arrusablecapacity"] = cap_data["capacityByTier"]["usableCapacity"]

                self.dt1_all_coll_sys_cap_data.append(pickle.loads(dt1_mod_sys_cap_data))
                self.final_json_dict_dt1["SystemCapacity"].append(pickle.loads(dt1_mod_sys_cap_data))
                number_of_apps = self.json_data_set["number_of_app_per_array"][self.cust][count]
                num_of_vols_per_app = self.json_data_set["volume_count_per_app"]
                vol_data = self.generate_dt1_vol_data(
                    device_type_1_dict_data["Volumes"],
                    arr_id,
                    cust_id,
                    provision_type,
                    coll_num,
                    number_of_apps,
                    num_of_vols_per_app,
                )
                self.final_json_dict_dt1["Volumes"][arr_id] = vol_data
                self.dt1_arr_ids.append(arr_id)
                self.spark_inventory_data.append(copy.deepcopy(temp_sys_data_dt1_dict))
            else:
                self.final_json_dict_dt1["Systems"] = self.dt1_all_coll_sys_data
                temp_sys_data_dt1_dict["collectionstarttime"] = self.spark_frame_coll_start_time
                temp_sys_data_dt1_dict["collectionendtime"] = self.spark_frame_coll_end_time
                temp_sys_data_dt1_dict["custid"] = self.dt1_all_coll_sys_data[count]["customerId"]
                temp_sys_data_dt1_dict["arrid"] = self.dt1_all_coll_sys_data[count]["id"]
                temp_sys_data_dt1_dict["storagesysid"] = self.dt1_all_coll_sys_data[count]["id"]
                temp_sys_data_dt1_dict["numofarrays"] = 1
                temp_sys_data_dt1_dict["storagesysname"] = self.dt1_all_coll_sys_data[count]["name"]
                temp_sys_data_dt1_dict["arrname"] = self.dt1_all_coll_sys_data[count]["name"]
                temp_sys_data_dt1_dict["devicetype"] = "devicetype1"
                dt1_mod_sys_cap_data = pickle.dumps(
                    self.generate_system_capacity(
                        device_type_1_dict_data["SystemCapacity"], self.dt1_arr_ids[count], cust_id, coll_num
                    )
                )
                cap_data = pickle.loads(dt1_mod_sys_cap_data)
                self.final_json_dict_dt1["SystemCapacity"].append(pickle.loads(dt1_mod_sys_cap_data))
                temp_sys_data_dt1_dict["storagesystotalused"] = cap_data["capacityByTier"]["totalUsed"]
                temp_sys_data_dt1_dict["storagesysusablecapacity"] = cap_data["capacityByTier"]["usableCapacity"]

                temp_sys_data_dt1_dict["arrtotalused"] = cap_data["capacityByTier"]["totalUsed"]
                temp_sys_data_dt1_dict["arrusablecapacity"] = cap_data["capacityByTier"]["usableCapacity"]

                number_of_apps = self.json_data_set["per_collection_app_count"][self.cust][count]
                num_of_vols_per_app = self.json_data_set["volume_count_per_app"]
                self.spark_inventory_data.append(copy.deepcopy(temp_sys_data_dt1_dict))
                vol_data = self.generate_dt1_vol_data(
                    device_type_1_dict_data["Volumes"],
                    self.dt1_arr_ids[count],
                    cust_id,
                    provision_type,
                    coll_num,
                    number_of_apps,
                    num_of_vols_per_app,
                )
                self.final_json_dict_dt1["Volumes"][self.dt1_arr_ids[count]] = vol_data

    def generate_device_type_2_system_data(self, device_type_2_dict_data, cust_id, coll_num):
        provision_type = "mixed"
        if self.json_data_set["all_thin_count"]:
            provision_type = "thin"
        elif self.json_data_set["all_thick_count"]:
            provision_type = "thick"
        temp_sys_data_dt2_dict = {}

        for storage_system in range(self.json_data_set["storage_system_count_device_type_2"][self.cust]):
            if coll_num == 0:
                sys_id_rand_num = random.randint(13105, 93105)
                storage_system_id = f"003a28a{sys_id_rand_num}d127d700000000000000000000000{storage_system + 1}"
                self.inv_arr_ids[storage_system_id] = []
                self.storage_sys_ids.append(storage_system_id)
                name = "storage-system-panorama-" + str(storage_system)
                target_name = "iqn.2007-11.com.nimblestorage:g-panorama-g3a28a43105d127d" + str(storage_system)
                last_login = self.system_date.split(" ")[0]
                sys_date = calendar.timegm(time.strptime(self.system_date, "%Y-%m-%d %H:%M:%S.%f000 %z %Z"))

                self.usable_cap = random.randint(500050024, 4000565076)
                raw_cap = random.randint(4000565076, 5000565076)
                year = random.randint(2010, 2020)
                month = random.randint(1, 12)
                day = random.randint(1, 30)
                c_time = f"{year}-{month}-{day} 05:19:56.518559000 +0000 UTC"
                try:
                    array_gen_time = calendar.timegm(time.strptime(c_time, "%Y-%m-%d %H:%M:%S.%f000 %z %Z"))
                except ValueError:
                    array_gen_time = calendar.timegm(time.strptime(c_time, "%Y-%m-%d %H:%M:%S.%f000 %z %Z"))
                temp_sys_data_dt2_dict["collectionstarttime"] = self.spark_frame_coll_start_time
                temp_sys_data_dt2_dict["collectionendtime"] = self.spark_frame_coll_end_time
                temp_sys_data_dt2_dict["custid"] = cust_id
                temp_sys_data_dt2_dict["storagesysid"] = storage_system_id
                temp_sys_data_dt2_dict["numofarrays"] = self.json_data_set["array_count_device_type_2"][self.cust]
                device_type_2_dict_data["Systems"][0]["id"] = storage_system_id
                device_type_2_dict_data["Systems"][0]["name"] = name
                temp_sys_data_dt2_dict["storagesysname"] = name
                temp_sys_data_dt2_dict["devicetype"] = "devicetype2"

                device_type_2_dict_data["Systems"][0]["group_target_name"] = target_name
                device_type_2_dict_data["Systems"][0]["usable_capacity_bytes"] = int(
                    self.format_size(self.usable_cap, "MB", "B")
                )

                temp_sys_data_dt2_dict["storagesysusablecapacity"] = int(self.format_size(self.usable_cap, "MB", "B"))
                temp_sys_data_dt2_dict["storagesystotalused"] = 0

                device_type_2_dict_data["Systems"][0]["raw_capacity"] = int(raw_cap)
                device_type_2_dict_data["Systems"][0]["free_space"] = int(self.format_size(self.usable_cap, "MB", "B"))
                device_type_2_dict_data["Systems"][0]["last_login"] = f"root @ {last_login}T15:45:01+0530 from Console"
                device_type_2_dict_data["Systems"][0]["date"] = sys_date
                device_type_2_dict_data["Systems"][0]["num_snaps"] = self.calculate_snap_count()
                device_type_2_dict_data["Systems"][0]["num_snapcolls"] = 50
                device_type_2_dict_data["Systems"][0]["generation"] = array_gen_time
                device_type_2_dict_data["Systems"][0]["customerId"] = cust_id

                for index, a_links in enumerate(device_type_2_dict_data["Systems"][0]["associated_links"]):
                    r_type = device_type_2_dict_data["Systems"][0]["associated_links"][index]["type"]
                    r_uri = f"/api/v1/storage-systems/device-type2/{storage_system_id}/{r_type}"
                    device_type_2_dict_data["Systems"][0]["associated_links"][index]["resourceUri"] = r_uri

                device_type_2_dict_data["Systems"][0][
                    "consoleUri"
                ] = f"/data-ops-manager/storage-systems/device-type2/{storage_system_id}"
                device_type_2_dict_data["Systems"][0][
                    "resourceUri"
                ] = f"/api/v1/storage-systems/device-type2/{storage_system_id}/{storage_system_id}"
                usable_capacity_per_arr = round(
                    self.usable_cap / self.json_data_set["array_count_device_type_2"][self.cust]
                )

                storage_sys_items = pickle.dumps(device_type_2_dict_data["Systems"][0])
                self.final_json_dict_dt2["Systems"].append(pickle.loads(storage_sys_items))
                self.final_json_dict_dt2["Systems"][storage_system]["arrays"]["items"] = []
                self.dt2_arr_ids.append([])
                for count in range(self.json_data_set["array_count_device_type_2"][self.cust]):
                    arr_rand_num = random.randint(13105, 93105)
                    arr_id = f"093a28a{arr_rand_num}d127d700000000000000000000000{count + 1}"
                    temp_sys_data_dt2_dict["arrid"] = arr_id
                    self.inv_arr_ids[storage_system_id].append(arr_id)
                    self.dt2_arr_ids[storage_system].append(arr_id)
                    self.total_used = random.randint(2050024, 2705024)
                    if arr_id not in self.per_coll_total_used_dt2:
                        self.per_coll_total_used_dt2[arr_id] = {}
                        self.per_coll_total_used_dt2[arr_id].update({"total_used": self.total_used})
                        self.per_coll_total_used_dt2[arr_id].update({"total_arr_space": usable_capacity_per_arr})
                    else:
                        self.per_coll_total_used_dt2[arr_id]["total_used"] += self.total_used

                    pool_id = self.generate_random_str_with_alpha_number(num_of_char=42)
                    self.pool_ids.append(pool_id)
                    array_name = name + "-" + str(count)
                    device_type_2_dict_data["Systems"][0]["arrays"]["items"][0]["id"] = arr_id
                    device_type_2_dict_data["Systems"][0]["arrays"]["items"][0]["name"] = array_name

                    temp_sys_data_dt2_dict["arrname"] = array_name
                    device_type_2_dict_data["Systems"][0]["arrays"]["items"][0]["full_name"] = array_name
                    device_type_2_dict_data["Systems"][0]["arrays"]["items"][0]["search_name"] = array_name

                    r1 = random.choice("abcdefghijklmnopqrstuvwxyz")
                    r2 = random.choice("abcdefghijklmnopqrstuvwxyz")
                    r3 = random.choice("abcdefghijklmnopqrstuvwxyz")
                    r4 = random.randint(10, 99)
                    s_no = f"{r1}{r3}-0{r2}{r3}{r1}{r4}"
                    device_type_2_dict_data["Systems"][0]["arrays"]["items"][0]["serial"] = s_no
                    device_type_2_dict_data["Systems"][0]["arrays"]["items"][0]["creation_time"] = array_gen_time
                    device_type_2_dict_data["Systems"][0]["arrays"]["items"][0]["usable_capacity_bytes"] = int(
                        self.format_size(usable_capacity_per_arr, "MB", "B")
                    )
                    device_type_2_dict_data["Systems"][0]["arrays"]["items"][0]["raw_capacity_bytes"] = int(
                        self.format_size(usable_capacity_per_arr, "MB", "B")
                    )
                    device_type_2_dict_data["Systems"][0]["arrays"]["items"][0]["available_bytes"] = int(
                        self.format_size(usable_capacity_per_arr, "MB", "B")
                    )

                    device_type_2_dict_data["Systems"][0]["arrays"]["items"][0]["usage"] = int(
                        self.format_size(self.per_coll_total_used_dt2[arr_id]["total_used"], "MB", "B")
                    )

                    self.final_json_dict_dt2["Systems"][storage_system]["usage"] += int(
                        self.format_size(self.per_coll_total_used_dt2[arr_id]["total_used"], "MB", "B")
                    )

                    temp_sys_data_dt2_dict["arrtotalused"] = int(
                        self.format_size(self.per_coll_total_used_dt2[arr_id]["total_used"], "MB", "B")
                    )
                    temp_sys_data_dt2_dict["storagesystotalused"] += temp_sys_data_dt2_dict["arrtotalused"]
                    temp_sys_data_dt2_dict["arrusablecapacity"] = int(
                        self.format_size(usable_capacity_per_arr, "MB", "B")
                    )
                    device_type_2_dict_data["Systems"][0]["arrays"]["items"][0]["generation"] = array_gen_time
                    device_type_2_dict_data["Systems"][0]["arrays"]["items"][0]["customerId"] = cust_id
                    device_type_2_dict_data["Systems"][0]["arrays"]["items"][0]["pool_id"] = pool_id
                    device_type_2_dict_data["Systems"][0]["arrays"]["items"][0][
                        "consoleUri"
                    ] = f"/data-ops-manager/storage-systems/device-type2/{storage_system_id}"
                    device_type_2_dict_data["Systems"][0]["arrays"]["items"][0][
                        "resourceUri"
                    ] = f"/api/v1/storage-systems/device-type2/{storage_system_id}/{arr_id}"
                    array_items = pickle.dumps(device_type_2_dict_data["Systems"][0]["arrays"]["items"][0])
                    self.final_json_dict_dt2["Systems"][storage_system]["arrays"]["items"].append(
                        pickle.loads(array_items)
                    )
                    self.dt2_all_coll_sys_data = self.final_json_dict_dt2["Systems"]
                    self.spark_inventory_data.append(copy.deepcopy(temp_sys_data_dt2_dict))
                    number_of_apps = self.json_data_set["number_of_app_per_array"][self.cust][count]
                    num_of_vols_per_app = self.json_data_set["volume_count_per_app"]
                    vol_data = self.generate_dt2_vol_data(
                        device_type_2_dict_data["Volumes"],
                        arr_id,
                        cust_id,
                        provision_type,
                        coll_num,
                        pool_id,
                        self.total_used,
                        storage_system_id,
                        number_of_apps,
                        num_of_vols_per_app,
                    )
                    self.final_json_dict_dt2["Volumes"][arr_id] = vol_data
            else:
                self.dt2_all_coll_sys_data[storage_system]["usage"] = 0
                for ind, arr in enumerate(self.dt2_arr_ids[storage_system]):
                    self.total_used = random.randint(105024, 1050024)
                    if arr not in self.per_coll_total_used_dt2:
                        self.per_coll_total_used_dt2[arr] = {}
                        self.per_coll_total_used_dt2[arr].update({"total_used": self.total_used})
                    else:
                        self.per_coll_total_used_dt2[arr]["total_used"] += self.total_used
                    self.dt2_all_coll_sys_data[storage_system]["arrays"]["items"][ind]["usage"] = self.format_size(
                        self.per_coll_total_used_dt2[arr]["total_used"], "MB", "B"
                    )
                    self.dt2_all_coll_sys_data[storage_system]["usage"] += int(
                        self.format_size(self.per_coll_total_used_dt2[arr]["total_used"], "MB", "B")
                    )
                    temp_sys_data_dt2_dict["collectionstarttime"] = self.spark_frame_coll_start_time
                    temp_sys_data_dt2_dict["collectionendtime"] = self.spark_frame_coll_end_time
                    temp_sys_data_dt2_dict["custid"] = cust_id
                    temp_sys_data_dt2_dict["storagesysid"] = self.dt2_all_coll_sys_data[storage_system]["id"]
                    temp_sys_data_dt2_dict["numofarrays"] = self.json_data_set["array_count_device_type_2"][self.cust]
                    temp_sys_data_dt2_dict["storagesysname"] = self.dt2_all_coll_sys_data[storage_system]["name"]
                    temp_sys_data_dt2_dict["devicetype"] = "devicetype2"
                    temp_sys_data_dt2_dict["storagesysusablecapacity"] = int(
                        self.dt2_all_coll_sys_data[storage_system]["usable_capacity_bytes"]
                    )
                    temp_sys_data_dt2_dict["storagesystotalused"] = self.dt2_all_coll_sys_data[storage_system]["usage"]
                    temp_sys_data_dt2_dict["arrid"] = self.dt2_all_coll_sys_data[storage_system]["arrays"]["items"][
                        ind
                    ]["id"]
                    temp_sys_data_dt2_dict["arrname"] = self.dt2_all_coll_sys_data[storage_system]["arrays"]["items"][
                        ind
                    ]["name"]
                    temp_sys_data_dt2_dict["arrtotalused"] = int(
                        self.dt2_all_coll_sys_data[storage_system]["arrays"]["items"][ind]["usage"]
                    )
                    temp_sys_data_dt2_dict["arrusablecapacity"] = self.dt2_all_coll_sys_data[storage_system]["arrays"][
                        "items"
                    ][ind]["usable_capacity_bytes"]

                    self.spark_inventory_data.append(copy.deepcopy(temp_sys_data_dt2_dict))
                    number_of_apps = self.json_data_set["per_collection_app_count"][self.cust][ind]
                    num_of_vols_per_app = self.json_data_set["volume_count_per_app"]
                    vol_data = self.generate_dt2_vol_data(
                        device_type_2_dict_data["Volumes"],
                        arr,
                        cust_id,
                        provision_type,
                        coll_num,
                        self.pool_ids[ind],
                        self.total_used,
                        self.storage_sys_ids[storage_system],
                        number_of_apps,
                        num_of_vols_per_app,
                    )
                    self.final_json_dict_dt2["Volumes"][arr] = vol_data
                self.final_json_dict_dt2["Systems"] = self.dt2_all_coll_sys_data

    def generate_system_data(self, device_type_1_dict_data, device_type_2_dict_data, device_type, cust_id, coll_num):
        if device_type == "deviceType1":
            self.generate_device_type_1_system_data(
                device_type_1_dict_data=device_type_1_dict_data, cust_id=cust_id, coll_num=coll_num
            )
            self.convert_dict_to_json(self.final_json_dict_dt1, json_type="DT1")

        elif device_type == "deviceType2":
            self.generate_device_type_2_system_data(
                device_type_2_dict_data=device_type_2_dict_data, cust_id=cust_id, coll_num=coll_num
            )
            self.convert_dict_to_json(self.final_json_dict_dt2, json_type="DT2")

    def generate_system_capacity(self, device_type_1_dict_data, arr_id, cust_id, coll_num):
        self.total_used = random.randint(2050024, 2705024) if coll_num == 0 else random.randint(105024, 1050024)
        if arr_id not in self.per_coll_total_used:
            self.per_coll_total_used[arr_id] = {}
            self.per_coll_total_used[arr_id].update({"total_used": self.total_used})
        else:
            self.per_coll_total_used[arr_id]["total_used"] += self.total_used
        if coll_num == 0:
            self.usable_cap = random.randint(500050024, 4000565076)
            self.per_coll_total_used[arr_id].update({"usable_cap": self.usable_cap})

        for ind, link in enumerate(device_type_1_dict_data[0]["associatedLinks"]):
            device_type_1_dict_data[0]["associatedLinks"][ind][
                "resourceUri"
            ] = f"/api/v1/storage-systems/device-type1/{arr_id}"
        device_type_1_dict_data[0]["capacityByTier"]["totalUsed"] = int(
            self.format_size(self.per_coll_total_used[arr_id]["total_used"], "MB", "B")
        )
        device_type_1_dict_data[0]["capacityByTier"]["usableCapacity"] = int(
            self.format_size(self.per_coll_total_used[arr_id]["usable_cap"], "MB", "B")
        )
        device_type_1_dict_data[0]["customerId"] = cust_id
        device_type_1_dict_data[0]["id"] = arr_id
        device_type_1_dict_data[0]["systemid"] = arr_id
        return device_type_1_dict_data[0]

    def dt2_calculate_vol_space(self, vol_cnt, coll_num, total_used):

        space_per_vol = round(total_used / vol_cnt)
        self.vol_size = space_per_vol
        collection_remains = self.num_of_coll_per_cust - coll_num
        self.used_size_mb = round(self.vol_size / collection_remains)

    def dt1_calculate_vol_space(self, arr_id, vol_cnt, coll_num):
        space_per_vol = round(self.per_coll_total_used[arr_id]["total_used"] / vol_cnt)
        self.vol_size = space_per_vol
        coll_remains = self.num_of_coll_per_cust - coll_num
        self.used_size_mb = round(self.vol_size / coll_remains)

    def get_vol_creation_date_in_ms(self, coll_num, convert_type="milliseconds"):
        if coll_num == 0:
            if convert_type == "milliseconds":
                splited_date = self.system_date.split(" ")[0].split("-")
                year = random.randint(0, 7)
                if int(splited_date[1]) == 1:
                    mon_to_generate = 1
                else:
                    mon_to_generate = int(splited_date[1]) - 1
                mon = random.randint(1, mon_to_generate)
                day = random.randint(1, 27)
                vol_cre_date = self.calculate_collection_time(years=year, months=mon, days=day)
                creation_date_in_ms = self.convert_date_in_to_ms(vol_cre_date)
                return creation_date_in_ms + 100
            elif convert_type == "seconds":
                splited_date = self.system_date.split(" ")[0].split("-")
                year = random.randint(0, 7)
                if int(splited_date[1]) == 1:
                    mon_to_generate = 1
                else:
                    mon_to_generate = int(splited_date[1]) - 1
                mon = random.randint(1, mon_to_generate)
                day = random.randint(1, 27)
                vol_cre_date = self.calculate_collection_time(years=year, months=mon, days=day)
                return vol_cre_date.timestamp() + 100

        hours = random.randint(1, 7)
        str_to_date = datetime.datetime.strptime(self.vol_creation_time, "%Y-%m-%d %H:%M:%S.%f000 %z %Z")
        vol_cre_date = str_to_date - relativedelta(years=0, months=0, days=0, hours=hours, minutes=0)

        if convert_type == "milliseconds":
            creation_date_in_ms = self.convert_date_in_to_ms(vol_cre_date)
            return creation_date_in_ms + 100
        elif convert_type == "seconds":
            return vol_cre_date.timestamp() + 100

    def create_vol_name(self, dev_type):
        vol_name = f"pqa-{dev_type}-vol-{self.vol_index}"
        self.vol_index += 1
        return vol_name

    def dt1_update_prev_vol_usage(self):
        temp_vol_perf_dict_dt1 = {}
        vol_index = 0
        pre_vol_data_frame = pd.DataFrame.from_dict(self.dt1_all_coll_temp_dict)
        self.dt1_all_coll_temp_dict = []

        key_list = [
            "collectionstarttime",
            "collectionendtime",
            "arrtotalsize",
            "arrtotalused",
            "arrid",
            "custid",
            "volumeId",
            "volumesize",
            "usedsize",
            "creationTime",
            "provisiontype",
            "avgiops",
            "name",
        ]
        values_list = []
        avg_dict = {}
        for arr in pre_vol_data_frame.keys():
            for ind in pre_vol_data_frame.index:
                coll_used_size = random.randint(2000, 5000)
                pre_vol_data_frame[arr][ind]["usedSizeMiB"] = coll_used_size

                # if not pre_vol_data_frame[arr][ind]["physicalCopy"]:
                avg_8_hours = random.randint(10, 80)
                avg_dict[pre_vol_data_frame[arr][ind]["id"]] = avg_8_hours
                pro_type = "thick"
                if pre_vol_data_frame[arr][ind]["thinProvisioned"]:
                    pro_type = "thin"
                values_list.append(
                    [
                        self.spark_frame_coll_start_time,
                        self.spark_frame_coll_end_time,
                        0,
                        0,
                        pre_vol_data_frame[arr][ind]["systemId"],
                        pre_vol_data_frame[arr][ind]["customerId"],
                        pre_vol_data_frame[arr][ind]["id"],
                        pre_vol_data_frame[arr][ind]["sizeMiB"],
                        self.format_size(pre_vol_data_frame[arr][ind]["usedSizeMiB"], "MB", "B"),
                        self.convert_ms_to_date_time(pre_vol_data_frame[arr][ind]["creationTime"]["ms"]),
                        pro_type,
                        avg_8_hours,
                        pre_vol_data_frame[arr][ind]["name"],
                    ]
                )
        vol_usage_df = pd.DataFrame(values_list, columns=key_list)
        # print(vol_usage_df.to_dict("r"))
        # print(vol_usage_df.to_dict("record"))
        self.spark_vol_usage.extend(vol_usage_df.to_dict("record"))
        # print(self.spark_vol_usage)
        self.dt1_all_coll_temp_dict = pre_vol_data_frame.to_dict("list")
        # print(self.dt1_all_coll_temp_dict)
        # for arr in self.dt1_all_coll_temp_dict:
        #    # print(new[arr][0]["usedSizeMiB"])
        #    for ind, vol_dict in enumerate(self.dt1_all_coll_temp_dict[arr]):
        #        coll_used_size = random.randint(round(vol_dict["usedSizeMiB"] / 2), vol_dict["usedSizeMiB"])
        #        vol_dict["usedSizeMiB"] += coll_used_size
        #        if "false" in vol_dict["physicalCopy"]:
        #            self.usage_vol_count += 1
        #            spark_vol_usage_temp["collectionstarttime"] = self.spark_frame_coll_start_time
        #            spark_vol_usage_temp["collectionendtime"] = self.spark_frame_coll_end_time
        #            spark_vol_usage_temp["arrtotalsize"] = 0
        #            spark_vol_usage_temp["arrtotalused"] = 0
        #            spark_vol_usage_temp["arrid"] = vol_dict["systemId"]
        #            spark_vol_usage_temp["custid"] = vol_dict["customerId"]
        #            spark_vol_usage_temp["volumeId"] = vol_dict["id"]
        #            spark_vol_usage_temp["volumesize"] = vol_dict["sizeMiB"]
        #            spark_vol_usage_temp["usedsize"] = vol_dict["usedSizeMiB"]
        #            spark_vol_usage_temp["creationTime"] = self.convert_ms_to_date_time(vol_dict["creationTime"]["ms"])
        #            usage_temp = pickle.dumps(spark_vol_usage_temp)
        #            self.spark_vol_usage.append(pickle.loads(usage_temp))
        #            # if ind % 2 == 0:
        #            #    snap_count = random.randint(2, 5)
        #            #    converted_date_to_ms = self.get_vol_creation_date_in_ms(coll_num=1)
        #            #    self.generate_dt1_snaps_per_volume(
        #            #        arr,
        #            #        vol_dict["id"],
        #            #        vol_dict["name"],
        #            #        vol_dict["usedSizeMiB"],
        #            #        vol_dict["customerId"],
        #            #        snap_count,
        #            #        converted_date_to_ms,
        #            #    )

        vol_perf_data_frame = pd.DataFrame.from_dict(self.dt1_all_vol_perf_dict["VolumePerformance"])
        self.dt1_all_vol_perf_dict["VolumePerformance"] = []
        key_list = [
            "collectionstarttime",
            "collectionendtime",
            "arrid",
            "id",
            "custid",
            "avgiops",
        ]
        values_list = []
        for ind in vol_perf_data_frame.index:
            vol_perf_data_frame["iops"][ind]["total"]["avgOf8hours"] = avg_dict[vol_perf_data_frame["volumeId"][ind]]
            values_list.append(
                [
                    self.spark_frame_coll_start_time,
                    self.spark_frame_coll_end_time,
                    vol_perf_data_frame["systemId"][ind],
                    vol_perf_data_frame["volumeId"][ind],
                    vol_perf_data_frame["customerId"][ind],
                    avg_dict[vol_perf_data_frame["volumeId"][ind]],
                ]
            )

        vol_perf_df = pd.DataFrame(values_list, columns=key_list)
        self.spark_vol_perf.extend(vol_perf_df.to_dict("record"))
        self.dt1_all_vol_perf_dict["VolumePerformance"] = vol_perf_data_frame.to_dict("record")
        # print(self.dt1_all_vol_perf_dict["VolumePerformance"])
        # for usage_dict in self.dt1_all_vol_perf_dict["VolumePerformance"]:
        #    self.usage_vol_count += 1
        #    avg_8_hours = random.randint(10, 80)
        #    usage_dict["iops"]["total"]["avgOf8hours"] = avg_8_hours
        #    temp_vol_perf_dict_dt1["collectionstarttime"] = self.spark_frame_coll_start_time
        #    temp_vol_perf_dict_dt1["collectionendtime"] = self.spark_frame_coll_end_time
        #    temp_vol_perf_dict_dt1["arrid"] = usage_dict["systemId"]
        #    temp_vol_perf_dict_dt1["volid"] = usage_dict["volumeId"]
        #    temp_vol_perf_dict_dt1["custid"] = usage_dict["customerId"]
        #    temp_vol_perf_dict_dt1["avgiops"] = avg_8_hours
        #    s_vol_perf = pickle.dumps(temp_vol_perf_dict_dt1)
        #    self.spark_vol_perf.append(pickle.loads(s_vol_perf))
        # print(self.usage_vol_count)

    def dt2_update_prev_vol_usage(self):
        spark_vol_usage_temp = {}
        temp_vol_perf_dict_dt2 = {}
        # print (self.dt2_all_coll_temp_dict)
        # temp_dict = dict([(k, pd.Series(v)) for k, v in self.dt2_all_coll_temp_dict.items()])
        # pre_vol_data_frame_dt2 = pd.DataFrame.from_dict(temp_dict)
        # key_list = [
        #    "collectionstarttime",
        #    "collectionendtime",
        #    "arrtotalsize",
        #    "arrtotalused",
        #    "arrid",
        #    "custid",
        #    "volumeId",
        #    "volumesize",
        #    "usedsize",
        #    "creationTime",
        #    "provisiontype",
        #    "avgiops",
        #    "name"
        # ]
        # values_list = []
        # avg_dict = {}
        # for arr in pre_vol_data_frame_dt2.keys():
        #    for ind in pre_vol_data_frame_dt2.index:
        #        print (pre_vol_data_frame_dt2[arr][ind])
        #        if isinstance(pre_vol_data_frame_dt2[arr][ind], float):
        #            continue
        #        coll_used_size = random.randint(2000,5000)
        #        pre_vol_data_frame_dt2[arr][ind]["total_usage_bytes"] = coll_used_size
        #        if not pre_vol_data_frame_dt2[arr][ind]["clone"]:
        #            avg_8_hours = random.randint(10, 80)
        #            avg_dict[pre_vol_data_frame_dt2[arr][ind]["id"]] = avg_8_hours
        #
        #            if pre_vol_data_frame_dt2[arr][ind]["fullyProvisioned"]:
        #                pro_type = "thick"
        #            elif pre_vol_data_frame_dt2[arr][ind]["thinProvisioned"]:
        #                pro_type = "thin"
        #            values_list.append(
        #                [
        #                    self.spark_frame_coll_start_time,
        #                    self.spark_frame_coll_end_time,
        #                    0,
        #                    0,
        #                    pre_vol_data_frame_dt2[arr][ind]["owned_by_group_id"],
        #                    pre_vol_data_frame_dt2[arr][ind]["customerId"],
        #                    pre_vol_data_frame_dt2[arr][ind]["id"],
        #                    pre_vol_data_frame_dt2[arr][ind]["size"],
        #                    pre_vol_data_frame_dt2[arr][ind]["total_usage_bytes"],
        #                    self.convert_ms_to_date_time(pre_vol_data_frame_dt2[arr][ind]["creation_time"]),
        #                    pro_type,
        #                    avg_8_hours,
        #                    pre_vol_data_frame_dt2[arr][ind]["name"],
        #                ]
        #            )
        # vol_usage_df = pd.DataFrame(values_list, columns=key_list)
        ## print(vol_usage_df.to_dict("r"))
        # self.spark_vol_usage.extend(vol_usage_df.to_dict("record"))
        ## print(self.spark_vol_usage)
        # pre_vol_data_frame_dt2.dropna(inplace=True)
        # print (pre_vol_data_frame_dt2)
        # self.dt2_all_coll_temp_dict = pre_vol_data_frame_dt2.to_dict("list")
        ##print (self.dt2_all_coll_temp_dict)
        ## print (self.dt2_all_coll_temp_dict)
        avg_dict = {}

        for arr in self.dt2_all_coll_temp_dict:
            for ind, vol_dict in enumerate(self.dt2_all_coll_temp_dict[arr]):
                pro_type = "thick"
                coll_used_size = random.randint(2000, 5000)
                vol_dict["total_usage_bytes"] = coll_used_size
                if not vol_dict["clone"]:
                    avg_8_hours = random.randint(10, 80)
                    avg_dict[vol_dict["id"]] = avg_8_hours
                    if vol_dict["thinly_provisioned"]:
                        pro_type = "thin"

                    self.usage_vol_count += 1
                    spark_vol_usage_temp["collectionstarttime"] = self.spark_frame_coll_start_time
                    spark_vol_usage_temp["collectionendtime"] = self.spark_frame_coll_end_time
                    spark_vol_usage_temp["arrtotalsize"] = 0
                    spark_vol_usage_temp["arrtotalused"] = 0
                    spark_vol_usage_temp["arrid"] = vol_dict["owned_by_group_id"]
                    spark_vol_usage_temp["custid"] = vol_dict["customerId"]
                    spark_vol_usage_temp["volumeId"] = vol_dict["id"]
                    spark_vol_usage_temp["volumesize"] = vol_dict["size"]
                    spark_vol_usage_temp["usedsize"] = vol_dict["total_usage_bytes"]
                    # self.convert_ms_to_date_time(converted_date_to_secs, convert_type="stodate")
                    # print ("VOLUME USAGE FORMAT########", vol_dict["creation_time"])
                    # print ("##################CONVERTED TIME:", self.convert_ms_to_date_time(vol_dict["creation_time"], convert_type="stodate"))
                    spark_vol_usage_temp["creationTime"] = self.convert_ms_to_date_time(
                        vol_dict["creation_time"], convert_type="stodate"
                    )
                    spark_vol_usage_temp["provisiontype"] = pro_type
                    spark_vol_usage_temp["avgiops"] = avg_8_hours
                    spark_vol_usage_temp["name"] = vol_dict["name"]
                    vol_usage = pickle.dumps(spark_vol_usage_temp)
                    self.spark_vol_usage.append(pickle.loads(vol_usage))

                # if ind % 2 == 0:
                #    snap_count = random.randint(2, 5)
                #    converted_date_to_ms = self.get_vol_creation_date_in_ms(coll_num=1)
                #    self.generate_dt2_snaps_per_volume(
                #        arr,
                #        vol_dict["id"],
                #        vol_dict["name"],
                #        coll_used_size,
                #        vol_dict["customerId"],
                #        snap_count,
                #        converted_date_to_ms,
                #        vol_dict["owned_by_group_id"],
                #
        vol_perf_data_frame_dt2 = pd.DataFrame.from_dict(self.dt2_all_vol_perf_dict["VolumePerformance"])
        # self.dt2_all_vol_perf_dict["VolumePerformance"] = []
        key_list = [
            "collectionstarttime",
            "collectionendtime",
            "arrid",
            "id",
            "custid",
            "avgiops",
        ]
        values_list = []
        for ind in vol_perf_data_frame_dt2.index:
            # if vol_perf_data_frame_dt2["volumeId"][ind] in avg_dict:
            #    print (vol_perf_data_frame_dt2["volumeId"][ind])
            vol_perf_data_frame_dt2["iops"][ind]["total"]["avg_8hours"] = avg_dict[
                vol_perf_data_frame_dt2["volumeId"][ind]
            ]
            values_list.append(
                [
                    self.spark_frame_coll_start_time,
                    self.spark_frame_coll_end_time,
                    vol_perf_data_frame_dt2["systemId"][ind],
                    vol_perf_data_frame_dt2["volumeId"][ind],
                    vol_perf_data_frame_dt2["customerId"][ind],
                    avg_dict[vol_perf_data_frame_dt2["volumeId"][ind]],
                ]
            )

        vol_perf_df = pd.DataFrame(values_list, columns=key_list)
        self.spark_vol_perf.extend(vol_perf_df.to_dict("record"))
        self.dt2_all_vol_perf_dict["VolumePerformance"] = vol_perf_data_frame_dt2.to_dict("record")
        # for usage_dict in self.dt2_all_vol_perf_dict["VolumePerformance"]:
        #    avg_8_hours = random.randint(10, 80)
        #    usage_dict["iops"]["total"]["avgOf8hours"] = avg_8_hours
        #    temp_vol_perf_dict_dt2["collectionstarttime"] = self.spark_frame_coll_start_time
        #    temp_vol_perf_dict_dt2["collectionendtime"] = self.spark_frame_coll_end_time
        #    temp_vol_perf_dict_dt2["arrid"] = usage_dict["systemId"]
        #    temp_vol_perf_dict_dt2["volid"] = usage_dict["volumeId"]
        #    temp_vol_perf_dict_dt2["custid"] = usage_dict["customerId"]
        #    temp_vol_perf_dict_dt2["avgiops"] = avg_8_hours
        #    t_vol_perf = pickle.dumps(temp_vol_perf_dict_dt2)
        #    self.spark_vol_perf.append(pickle.loads(t_vol_perf))

    def generate_dt1_vol_data(
        self, device_type_1_dict_data, arr_id, custid, provision_type, coll_num, num_apps, num_vols_count_per_app
    ):
        spark_temp_dict = {}
        spark_clone_dt1_temp_dict = {}
        spark_vol_usage_temp_dict_dt1 = {}

        if arr_id not in self.dt1_all_coll_temp_dict:
            self.dt1_all_coll_temp_dict[arr_id] = []
        thin_or_thick = random.choices(["thin", "thick"])[0] if provision_type == "mixed" else provision_type
        vol_count = self.first_coll_vol_count if coll_num == 0 else self.per_coll_vol_count
        self.dt1_total_vol_count += vol_count
        snp_count = self.first_coll_snp_count if coll_num == 0 else self.per_coll_snp_count
        mounted_vol_count = self.mounted_vol_count if coll_num == 0 else self.per_coll_mounted_vol_count
        mounted_clones_count = self.mounted_clone_count if coll_num == 0 else self.per_coll_mounted_clone_count
        clone_count = self.first_coll_clone_count if coll_num == 0 else self.per_coll_clone_count
        if vol_count == 0:
            vol_count = 1
        self.dt1_calculate_vol_space(arr_id, vol_count, coll_num)

        self.per_coll_total_used[arr_id]["total_used"]
        if snp_count == 0:
            snp_count = 2
        vols_for_snaps = random.randint(1, snp_count)
        try:
            per_vol_snap_count = round(vols_for_snaps / snp_count)
        except ZeroDivisionError:
            per_vol_snap_count = 1
        if mounted_vol_count + mounted_clones_count >= vol_count:
            mounted_vol_choices = random.sample(range(1, vol_count), vol_count - 1)
        else:
            mounted_vol_choices = random.sample(range(1, vol_count), mounted_vol_count + mounted_clones_count)
        # app_vol_choices = random.sample(range(1, vol_count), num_vols_count_per_app * num_apps)
        vol_ids = []
        all_vol_ids = {}
        app_vol_ids = {}
        clone_count_per_vol = round(clone_count / (vol_count / 2))
        snap_vol_count = 0
        for vol in range(vol_count):
            self.vol_c += 1
            self.usage_vol_count += 1
            spark_temp_dict["custid"] = custid
            spark_temp_dict["collectionstarttime"] = self.spark_frame_coll_start_time
            spark_temp_dict["collectionendtime"] = self.spark_frame_coll_end_time
            spark_temp_dict["arrid"] = arr_id
            spark_temp_dict["totalsize"] = self.per_coll_total_used[arr_id]["usable_cap"]
            spark_temp_dict["totalused"] = self.per_coll_total_used[arr_id]["total_used"]
            spark_vol_usage_temp_dict_dt1["collectionstarttime"] = self.spark_frame_coll_start_time
            spark_vol_usage_temp_dict_dt1["collectionendtime"] = self.spark_frame_coll_end_time
            spark_vol_usage_temp_dict_dt1["arrid"] = arr_id
            spark_vol_usage_temp_dict_dt1["custid"] = custid
            spark_vol_usage_temp_dict_dt1["arrtotalsize"] = int(self.per_coll_total_used[arr_id]["usable_cap"])
            spark_vol_usage_temp_dict_dt1["arrtotalused"] = int(self.per_coll_total_used[arr_id]["total_used"])
            converted_date_to_ms = self.get_vol_creation_date_in_ms(coll_num)
            converted_date_from_ms = self.convert_ms_to_date_time(converted_date_to_ms)
            vol_name = self.create_vol_name("dt1")
            rand_num = random.randint(1111111, 9999999)
            rand_num1 = random.randint(1111, 9999)
            vol_id = f"4c8d6c31-8a0b-{rand_num1}-93a8-1403b{rand_num}"
            # vol_id = self.generae_random_str_with_alpha_number(num_of_char=32)
            letters = string.ascii_uppercase
            wwn_digits = "".join(random.choice(letters) for i in range(2))
            wwn_number = f"60002{wwn_digits}00000000000011779000{self.generate_array_id(num_of_digits=5)}"
            device_type_1_dict_data["array1"][0]["customerId"] = custid
            device_type_1_dict_data["array1"][0]["fullyProvisioned"] = False
            device_type_1_dict_data["array1"][0]["thinProvisioned"] = False
            if "thick" in thin_or_thick:
                device_type_1_dict_data["array1"][0]["fullyProvisioned"] = True
                device_type_1_dict_data["array1"][0]["thinProvisioned"] = False
                spark_temp_dict["provisiontype"] = "thick"
                spark_vol_usage_temp_dict_dt1["provisiontype"] = "thick"
            elif "thin" in thin_or_thick:
                device_type_1_dict_data["array1"][0]["thinProvisioned"] = True
                device_type_1_dict_data["array1"][0]["fullyProvisioned"] = False
                spark_temp_dict["provisiontype"] = "thin"
                spark_vol_usage_temp_dict_dt1["provisiontype"] = "thin"

            device_type_1_dict_data["array1"][0]["id"] = vol_id
            spark_temp_dict["id"] = vol_id
            spark_vol_usage_temp_dict_dt1["volumeId"] = vol_id
            vol_ids.append(vol_id)
            all_vol_ids[vol_id] = {}
            app_vol_ids[vol_id] = {"snapcount": 0, "clonecount": 0}
            device_type_1_dict_data["array1"][0]["sizeMiB"] = self.vol_size
            spark_temp_dict["volsize"] = self.vol_size
            spark_vol_usage_temp_dict_dt1["volumesize"] = self.vol_size
            device_type_1_dict_data["array1"][0]["usedSizeMiB"] = self.used_size_mb
            spark_temp_dict["usedsize"] = self.format_size(self.used_size_mb, "MB", "B")
            spark_vol_usage_temp_dict_dt1["usedsize"] = self.format_size(self.used_size_mb, "MB", "B")
            device_type_1_dict_data["array1"][0]["volumeId"] = self.vol_index - 1
            spark_temp_dict["volumeId"] = self.vol_index - 1
            device_type_1_dict_data["array1"][0]["creationTime"]["ms"] = converted_date_to_ms
            spark_temp_dict["creationTime"] = self.convert_ms_to_date_time(converted_date_to_ms)
            creation_time = re.sub(r"(.*)(\.[0-9]+\s.*)", r"\1", self.convert_ms_to_date_time(converted_date_to_ms))
            spark_vol_usage_temp_dict_dt1["creationTime"] = creation_time
            device_type_1_dict_data["array1"][0]["displayname"] = vol_name
            device_type_1_dict_data["array1"][0]["name"] = vol_name
            spark_vol_usage_temp_dict_dt1["name"] = vol_name
            spark_temp_dict["name"] = vol_name
            spark_temp_dict["mounted"] = False
            device_type_1_dict_data["array1"][0]["systemId"] = arr_id
            device_type_1_dict_data["array1"][0]["wwn"] = wwn_number
            # device_type_1_dict_data["array1"][0]["physicalCopy"] = False
            device_type_1_dict_data["array1"][0]["parentID"] = ""
            device_type_1_dict_data["array1"][0]["physParentID"] = ""
            device_type_1_dict_data["array1"][0]["baseId"] = ""
            all_vol_ids[vol_id].update(
                {
                    "vol_name": vol_name,
                    "vol_id": vol_id,
                    "cust_id": custid,
                    "arr_id": arr_id,
                    "vv_size": self.vol_size,
                    "wwn": wwn_number,
                }
            )
            vol_data = pickle.dumps(device_type_1_dict_data["array1"][0])
            vol_perf = pickle.dumps(self.dt1_generate_vol_performance(arr_id, vol_id, custid))
            spark_vol_usage_temp_dict_dt1["avgiops"] = pickle.loads(vol_perf)["iops"]["total"]["avgOf8hours"]
            self.dt1_all_vol_perf_dict["VolumePerformance"].append(pickle.loads(vol_perf))
            self.dt1_all_coll_temp_dict[arr_id].append(pickle.loads(vol_data))
            s_vol_data = pickle.dumps(spark_temp_dict)
            self.spark_vol_data.append(pickle.loads(s_vol_data))
            vol_usage = pickle.dumps(spark_vol_usage_temp_dict_dt1)
            self.spark_vol_usage.append(pickle.loads(vol_usage))
            app_vol_ids[vol_id].update({"snapcount": per_vol_snap_count})
            app_vol_ids[vol_id]["clones"] = []
            app_vol_ids[vol_id]["snaps"] = []
            """
            if vol % 2 == 0:
                converted_date_to_ms = self.get_vol_creation_date_in_ms(coll_num)
                device_type_1_dict_data["array1"][0]["baseId"] = vol_id
                device_type_1_dict_data["array1"][0]["copyOfID"] = self.vol_index - 1
                device_type_1_dict_data["array1"][0]["parentID"] = vol_id
                device_type_1_dict_data["array1"][0]["physParentID"] = vol_id
                device_type_1_dict_data["array1"][0]["physicalCopy"] = True
                clone_parent_id = vol_id
                app_vol_ids[clone_parent_id].update({"clonecount": clone_count_per_vol})
                for clone in range(clone_count_per_vol):
                    self.clones += 1
                    spark_clone_dt1_temp_dict["collectionstarttime"] = self.spark_frame_coll_start_time
                    spark_clone_dt1_temp_dict["collectionendtime"] = self.spark_frame_coll_end_time
                    spark_clone_dt1_temp_dict["custid"] = custid
                    spark_clone_dt1_temp_dict["arrid"] = arr_id
                    spark_clone_dt1_temp_dict["cloneparentid"] = clone_parent_id
                    converted_date_to_ms += 357653
                    clone_vol_id = self.generae_random_str_with_alpha_number(num_of_char=32)
                    vol_name = self.create_vol_name("dt1-physical-copy")
                    device_type_1_dict_data["array1"][0]["customerId"] = custid

                    if thin_or_thick == "thick":
                        device_type_1_dict_data["array1"][0]["fullyProvisioned"] = True
                        spark_clone_dt1_temp_dict["provisiontype"] = "thick"
                    elif thin_or_thick == "thin":
                        device_type_1_dict_data["array1"][0]["thinProvisioned"] = True
                        spark_clone_dt1_temp_dict["provisiontype"] = "thin"
                    device_type_1_dict_data["array1"][0]["id"] = clone_vol_id
                    spark_clone_dt1_temp_dict["cloneid"] = clone_vol_id
                    vol_ids.append(clone_vol_id)
                    all_vol_ids[clone_vol_id] = {}
                    device_type_1_dict_data["array1"][0]["sizeMiB"] = self.vol_size
                    spark_clone_dt1_temp_dict["clonesize"] = self.vol_size
                    device_type_1_dict_data["array1"][0]["usedSizeMiB"] = self.used_size_mb
                    spark_clone_dt1_temp_dict["cloneusedsize"] = self.used_size_mb
                    device_type_1_dict_data["array1"][0]["volumeId"] = self.vol_index - 1
                    spark_clone_dt1_temp_dict["clonevolumeid"] = self.vol_index - 1
                    device_type_1_dict_data["array1"][0]["creationTime"]["ms"] = converted_date_to_ms
                    spark_clone_dt1_temp_dict["clonecreationtime"] = self.convert_ms_to_date_time(converted_date_to_ms)
                    device_type_1_dict_data["array1"][0]["displayname"] = vol_name
                    device_type_1_dict_data["array1"][0]["name"] = vol_name
                    spark_clone_dt1_temp_dict["clonename"] = vol_name
                    device_type_1_dict_data["array1"][0]["systemId"] = arr_id
                    device_type_1_dict_data["array1"][0]["wwn"] = wwn_number
                    spark_clone_dt1_temp_dict["mounted"] = "false"
                    all_vol_ids[clone_vol_id].update(
                        {
                            "vol_name": vol_name,
                            "vol_id": clone_vol_id,
                            "cust_id": custid,
                            "arr_id": arr_id,
                            "vv_size": self.vol_size,
                            "wwn": wwn_number,
                        }
                    )
                    vol_data = pickle.dumps(device_type_1_dict_data["array1"][0])
                    self.dt1_all_coll_temp_dict[arr_id].append(pickle.loads(vol_data))
                    clone_data = pickle.dumps(spark_clone_dt1_temp_dict)
                    self.spark_clone_data.append(pickle.loads(clone_data))
                    app_vol_ids[clone_parent_id]["clones"].append(pickle.loads(clone_data))
                """
            if snap_vol_count != vols_for_snaps:
                snap_data, snap_data_app = self.generate_dt1_snaps_per_volume(
                    arr_id, vol_id, vol_name, self.used_size_mb, custid, per_vol_snap_count, converted_date_to_ms
                )

                app_vol_ids[vol_id]["snaps"] = snap_data_app
                self.final_json_dict_dt1["Snapshots"] = snap_data
                snap_vol_count += 1

        for mounted_vol in mounted_vol_choices:
            for ind, spark_vol_dict in enumerate(self.spark_vol_data):
                if all_vol_ids[vol_ids[mounted_vol]]["vol_id"] in spark_vol_dict:
                    self.spark_vol_data[ind]["mounted"] = True
                else:
                    self.spark_vol_data[ind]["mounted"] = False
            self.generate_dt1_mounted_vols(
                all_vol_ids[vol_ids[mounted_vol]]["vol_name"],
                all_vol_ids[vol_ids[mounted_vol]]["vol_id"],
                all_vol_ids[vol_ids[mounted_vol]]["cust_id"],
                all_vol_ids[vol_ids[mounted_vol]]["arr_id"],
                all_vol_ids[vol_ids[mounted_vol]]["vv_size"],
                all_vol_ids[vol_ids[mounted_vol]]["wwn"],
            )
        self.final_json_dict_dt1["Vluns"] = self.dt1_all_coll_vlun_dict
        app_data = pickle.dumps(self.generate_app_data(num_apps, num_vols_count_per_app, custid, arr_id, app_vol_ids))

        self.final_json_dict_dt1["Applicationsets"] = pickle.loads(app_data)
        json_vol_perf = pickle.dumps(self.dt1_all_vol_perf_dict["VolumePerformance"])
        self.final_json_dict_dt1["VolumePerformance"] = pickle.loads(json_vol_perf)
        return self.dt1_all_coll_temp_dict[arr_id]

    def generate_dt2_vol_data(
        self,
        device_type_2_dict_data,
        arr_id,
        custid,
        provision_type,
        coll_num,
        pool_id,
        total_used,
        storage_sys_id,
        num_apps,
        num_vols_count_per_app,
    ):
        if arr_id not in self.dt2_all_coll_temp_dict:
            self.dt2_all_coll_temp_dict[arr_id] = []
        spark_temp_vol_dict = {}
        spark_clone_temp_dt2_dict = {}
        spark_vol_usage_temp_dict_dt2 = {}
        app_vol_list = {}

        thin_or_thick = random.choices(["thin", "thick"])[0] if provision_type == "mixed" else provision_type
        vol_count = self.first_coll_vol_count if coll_num == 0 else self.per_coll_vol_count
        snp_count = self.first_coll_snp_count if coll_num == 0 else self.per_coll_snp_count
        if snp_count >= vol_count:
            vols_for_snaps = random.randint(vol_count, snp_count)
        else:
            vols_for_snaps = random.randint(snp_count, vol_count)
        try:
            per_vol_snap_count = round(vols_for_snaps / snp_count)
        except ZeroDivisionError:
            per_vol_snap_count = 1
        # per_vol_snap_count = 1 if per_vol_snap_count == 0 else per_vol_snap_count
        clone_count = self.first_coll_clone_count if coll_num == 0 else self.per_coll_clone_count
        try:
            per_vol_clone_count = round(vol_count / clone_count)
        except ZeroDivisionError:
            per_vol_clone_count = 1
        if vol_count == 0:
            vol_count = 1
        self.dt2_calculate_vol_space(vol_count, coll_num, total_used)
        snap_count = 0
        for vol in range(vol_count):
            self.vol_c += 1
            self.usage_vol_count += 1
            spark_temp_vol_dict["collectionstarttime"] = self.spark_frame_coll_start_time
            spark_temp_vol_dict["collectionendtime"] = self.spark_frame_coll_end_time
            spark_temp_vol_dict["totalused"] = self.per_coll_total_used_dt2[arr_id]["total_used"]
            spark_temp_vol_dict["totalsize"] = self.per_coll_total_used_dt2[arr_id]["total_arr_space"]
            spark_vol_usage_temp_dict_dt2["collectionstarttime"] = self.spark_frame_coll_start_time
            spark_vol_usage_temp_dict_dt2["collectionendtime"] = self.spark_frame_coll_end_time
            spark_vol_usage_temp_dict_dt2["arrid"] = arr_id
            spark_vol_usage_temp_dict_dt2["custid"] = custid
            spark_vol_usage_temp_dict_dt2["arrtotalsize"] = int(self.per_coll_total_used_dt2[arr_id]["total_arr_space"])
            spark_vol_usage_temp_dict_dt2["arrtotalused"] = int(self.per_coll_total_used_dt2[arr_id]["total_used"])
            converted_date_to_secs = int(self.get_vol_creation_date_in_ms(coll_num, convert_type="seconds"))
            converted_date_from_ms = self.convert_ms_to_date_time(converted_date_to_secs, convert_type="stodate")
            if self.vol_index == 1:
                self.vol_coll_time = converted_date_to_secs
            vol_name = self.create_vol_name("dt2")
            rand_num = random.randint(1111111, 9999999)
            rand_num1 = random.randint(1111, 9999)
            vol_id = f"4c8d6c31-8a0b-{rand_num1}-93a8-1403b{rand_num}"
            # vol_id_rand_num = random.randint(13105, 93105)
            # vol_id = f"063a28a{vol_id_rand_num}d127d700000000000000000000000{self.vol_c}"
            # vol_id = self.generae_random_str_with_alpha_number(num_of_char=32)
            l_modified = int(converted_date_to_secs) + 300
            device_type_2_dict_data["array1"][0]["customerId"] = custid
            spark_temp_vol_dict["custid"] = custid
            # device_type_2_dict_data["array1"][0]["fullyProvisioned"] = True
            device_type_2_dict_data["array1"][0]["thinly_provisioned"] = True
            if thin_or_thick == "thick":
                # device_type_2_dict_data["array1"][0]["fullyProvisioned"] = True
                device_type_2_dict_data["array1"][0]["thinly_provisioned"] = False
                spark_temp_vol_dict["provisiontype"] = "thick"
                spark_vol_usage_temp_dict_dt2["provisiontype"] = "thick"
            elif thin_or_thick == "thin":
                device_type_2_dict_data["array1"][0]["thinly_provisioned"] = True
                # device_type_2_dict_data["array1"][0]["fullyProvisioned"] = False
                spark_temp_vol_dict["provisiontype"] = "thin"
                spark_vol_usage_temp_dict_dt2["provisiontype"] = "thin"

            spark_temp_vol_dict["mounted"] = "false"
            device_type_2_dict_data["array1"][0]["id"] = vol_id
            spark_vol_usage_temp_dict_dt2["volumeId"] = vol_id
            spark_temp_vol_dict["id"] = vol_id
            spark_temp_vol_dict["volumeId"] = vol_id
            device_type_2_dict_data["array1"][0]["name"] = vol_name
            spark_vol_usage_temp_dict_dt2["name"] = vol_name
            spark_temp_vol_dict["name"] = vol_name
            device_type_2_dict_data["array1"][0]["full_name"] = f"default:/{vol_name}"
            device_type_2_dict_data["array1"][0]["search_name"] = vol_name
            device_type_2_dict_data["array1"][0]["size"] = self.vol_size
            spark_vol_usage_temp_dict_dt2["volumesize"] = self.vol_size
            spark_temp_vol_dict["volsize"] = self.vol_size
            device_type_2_dict_data["array1"][0]["perfpolicy_name"] = ""
            device_type_2_dict_data["array1"][0]["perfpolicy_id"] = ""
            device_type_2_dict_data["array1"][0]["owned_by_group_id"] = arr_id
            spark_temp_vol_dict["arrid"] = arr_id
            device_type_2_dict_data["array1"][0]["pool_id"] = pool_id
            device_type_2_dict_data["array1"][0]["creation_time"] = converted_date_to_secs
            creation_time = re.sub(
                r"(.*)(\.[0-9]+\s.*)",
                r"\1",
                self.convert_ms_to_date_time(converted_date_to_secs, convert_type="stodate"),
            )
            # convert_type == "mstodate"
            spark_vol_usage_temp_dict_dt2["creationTime"] = creation_time
            spark_temp_vol_dict["creationTime"] = self.convert_ms_to_date_time(
                converted_date_to_secs, convert_type="stodate"
            )
            device_type_2_dict_data["array1"][0]["last_modified"] = l_modified
            device_type_2_dict_data["array1"][0]["total_usage_bytes"] = self.used_size_mb
            spark_vol_usage_temp_dict_dt2["usedsize"] = self.used_size_mb
            spark_temp_vol_dict["usedsize"] = self.used_size_mb
            device_type_2_dict_data["array1"][0]["clone"] = False
            device_type_2_dict_data["array1"][0]["parent_vol_name"] = ""
            device_type_2_dict_data["array1"][0]["parent_vol_id"] = ""
            device_type_2_dict_data["array1"][0]["base_snap_name"] = ""
            device_type_2_dict_data["array1"][0]["base_snap_id"] = ""
            device_type_2_dict_data["array1"][0]["associated_links"][0][
                "resourceUri"
            ] = f"/api/v1/storage-systems/device-type2/{arr_id}"
            device_type_2_dict_data["array1"][0][
                "consoleUri"
            ] = f"/data-ops-manager/storage-systems/device-type2/{arr_id}/volumes/{vol_id}"
            device_type_2_dict_data["array1"][0][
                "resourceUri"
            ] = f"/api/v1/storage-systems/device-type2/{arr_id}/volumes/{vol_id}"

            if vol % 2 == 0:
                if storage_sys_id in self.vol_coll_dict:
                    self.vol_coll_dict[storage_sys_id].update(
                        {
                            vol_id: {
                                "id": vol_id,
                                "vol_id": vol_id,
                                "name": vol_name,
                                "vol_name": vol_name,
                            }
                        }
                    )
                else:
                    self.vol_coll_dict = {}
                    self.vol_coll_dict[storage_sys_id] = {}
                    self.vol_coll_dict[storage_sys_id].update(
                        {
                            vol_id: {
                                "id": vol_id,
                                "vol_id": vol_id,
                                "name": vol_name,
                                "vol_name": vol_name,
                            }
                        }
                    )
                coll_count = random.randint(1, 3)
                if len(self.vol_coll_dict[storage_sys_id].keys()) == coll_count:
                    vol_coll_name = f"pqa-{storage_sys_id}-collection-{self.coll_index}"
                    vol_coll_id = (
                        f"{self.generate_random_str_with_alpha_number(num_of_char=18)}000000000000000000000005"
                    )

                    coll_data = pickle.dumps(
                        self.generate_vol_coll_data(
                            vol_coll_name, vol_coll_id, self.vol_coll_dict, self.vol_coll_time, custid
                        )
                    )
                    self.final_json_dict_dt2["VolumeCollections"] = pickle.loads(coll_data)
                    self.coll_index += 1
            vol_data = pickle.dumps(device_type_2_dict_data["array1"][0])
            self.dt2_all_coll_temp_dict[arr_id].append(pickle.loads(vol_data))
            v_perf = pickle.dumps(self.dt2_generate_vol_performance(arr_id, vol_id, custid))
            spark_vol_usage_temp_dict_dt2["avgiops"] = pickle.loads(v_perf)["iops"]["total"]["avgOf8hours"]
            self.dt2_all_vol_perf_dict["VolumePerformance"].append(pickle.loads(v_perf))
            app_vol_list[vol_id] = {"snapcount": 0, "clonecount": 0}
            app_vol_list[vol_id]["clones"] = []
            app_vol_list[vol_id]["snaps"] = []
            s_vol_data = pickle.dumps(spark_temp_vol_dict)
            self.spark_vol_data.append(pickle.loads(s_vol_data))
            s_usage = pickle.dumps(spark_vol_usage_temp_dict_dt2)
            self.spark_vol_usage.append(pickle.loads(s_usage))
            if snap_count != vols_for_snaps:
                snap_data, snap_app_data, snp_creation_time = self.generate_dt2_snaps_per_volume(
                    arr_id,
                    vol_id,
                    vol_name,
                    self.used_size_mb,
                    custid,
                    per_vol_snap_count,
                    converted_date_to_secs,
                    storage_sys_id,
                )
                app_vol_list[vol_id]["snapcount"] = per_vol_snap_count
                app_vol_list[vol_id]["snaps"] = snap_app_data
                self.final_json_dict_dt2["Snapshots"] = snap_data
                snap_count += 1
                device_type_2_dict_data["array1"][0]["clone"] = True
                device_type_2_dict_data["array1"][0]["parent_vol_name"] = vol_name
                device_type_2_dict_data["array1"][0]["parent_vol_id"] = vol_id
                device_type_2_dict_data["array1"][0]["base_snap_name"] = snap_data[vol_id][0]["name"]
                device_type_2_dict_data["array1"][0]["base_snap_id"] = snap_data[vol_id][0]["id"]
                app_vol_list[vol_id]["clonecount"] = per_vol_clone_count
                clone_parent_id = vol_id
                for clone in range(per_vol_clone_count):
                    self.clones += 1
                    spark_clone_temp_dt2_dict["collectionstarttime"] = self.spark_frame_coll_start_time
                    spark_clone_temp_dt2_dict["collectionendtime"] = self.spark_frame_coll_end_time
                    spark_clone_temp_dt2_dict["custid"] = custid
                    spark_clone_temp_dt2_dict["arrid"] = arr_id
                    spark_clone_temp_dt2_dict["cloneparentid"] = clone_parent_id
                    vol_name = self.create_vol_name("dt2-clone")
                    rand_num = random.randint(1111111, 9999999)
                    rand_num1 = random.randint(1111, 9999)
                    clone_id = f"4c8d6c31-8a0b-{rand_num1}-93a8-1403b{rand_num}"
                    converted_date_to_secs = snp_creation_time + 200
                    # vol_id = self.generae_random_str_with_alpha_number(num_of_char=32)
                    l_modified = int(converted_date_to_secs) + 300
                    device_type_2_dict_data["array1"][0]["customerId"] = custid
                    if thin_or_thick == "thick":
                        # device_type_2_dict_data["array1"][0]["fullyProvisioned"] = True
                        device_type_2_dict_data["array1"][0]["thinly_provisioned"] = False
                        spark_clone_temp_dt2_dict["provisiontype"] = "thick"
                    elif thin_or_thick == "thin":
                        device_type_2_dict_data["array1"][0]["thinly_provisioned"] = True
                        # device_type_2_dict_data["array1"][0]["fullyProvisioned"] = False
                        spark_clone_temp_dt2_dict["provisiontype"] = "thin"

                    device_type_2_dict_data["array1"][0]["id"] = clone_id
                    spark_clone_temp_dt2_dict["cloneid"] = clone_id
                    spark_clone_temp_dt2_dict["clonevolumeid"] = clone_id
                    device_type_2_dict_data["array1"][0]["name"] = vol_name
                    spark_clone_temp_dt2_dict["clonename"] = vol_name
                    device_type_2_dict_data["array1"][0]["full_name"] = f"default:/{vol_name}"
                    device_type_2_dict_data["array1"][0]["search_name"] = vol_name
                    device_type_2_dict_data["array1"][0]["size"] = self.vol_size
                    spark_clone_temp_dt2_dict["clonesize"] = self.vol_size
                    device_type_2_dict_data["array1"][0]["perfpolicy_name"] = ""
                    device_type_2_dict_data["array1"][0]["perfpolicy_id"] = ""
                    device_type_2_dict_data["array1"][0]["owned_by_group_id"] = arr_id
                    device_type_2_dict_data["array1"][0]["pool_id"] = pool_id
                    device_type_2_dict_data["array1"][0]["creation_time"] = int(converted_date_to_secs)
                    spark_clone_temp_dt2_dict["clonecreationtime"] = self.convert_ms_to_date_time(
                        converted_date_to_secs, convert_type="stodate"
                    )
                    device_type_2_dict_data["array1"][0]["last_modified"] = l_modified
                    device_type_2_dict_data["array1"][0]["total_usage_bytes"] = self.used_size_mb
                    spark_clone_temp_dt2_dict["cloneusedsize"] = self.used_size_mb
                    spark_clone_temp_dt2_dict["mounted"] = False
                    device_type_2_dict_data["array1"][0]["associated_links"][0][
                        "resourceUri"
                    ] = f"/api/v1/storage-systems/device-type2/{arr_id}"
                    device_type_2_dict_data["array1"][0][
                        "consoleUri"
                    ] = f"/data-ops-manager/storage-systems/device-type2/{arr_id}/volumes/{clone_id}"
                    device_type_2_dict_data["array1"][0][
                        "resourceUri"
                    ] = f"/api/v1/storage-systems/device-type2/{arr_id}/volumes/{clone_id}"
                    vol_data = pickle.dumps(device_type_2_dict_data["array1"][0])
                    self.dt2_all_coll_temp_dict[arr_id].append(pickle.loads(vol_data))
                    c_data = pickle.dumps(spark_clone_temp_dt2_dict)
                    self.spark_clone_data.append(pickle.loads(c_data))
                    app_vol_list[clone_parent_id]["clones"].append(pickle.loads(c_data))
        v_perf = pickle.dumps(self.dt2_all_vol_perf_dict["VolumePerformance"])
        self.final_json_dict_dt2["VolumePerformance"] = pickle.loads(v_perf)
        self.generate_app_data_dt2(num_apps, num_vols_count_per_app, app_vol_list, arr_id)
        return self.dt2_all_coll_temp_dict[arr_id]

    def generate_dt1_snaps_per_volume(self, arr, vol_id, vol_name, used_size, custid, snap_count, c_date):
        if vol_id not in self.dt1_all_coll_snap_dict:
            self.dt1_all_coll_snap_dict.update({vol_id: []})
        spark_temp_snap_dict = {}
        app_snp_dict = []
        for snap in range(snap_count):
            self.snaps += 1
            spark_temp_snap_dict["collectionstarttime"] = self.spark_frame_coll_start_time
            spark_temp_snap_dict["collectionendtime"] = self.spark_frame_coll_end_time
            spark_temp_snap_dict["volumeid"] = vol_id
            creation_time = random.randint(c_date + 3577800, c_date + 3557792800)
            # self.spark_frame_coll_start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")

            exp_time = random.randint(creation_time + 357898600, creation_time + 35778998600)
            snap_id = self.generate_random_str_with_alpha_number(num_of_char=32)
            snap_name = f"{vol_name}-snap-{snap}"
            snap_size = random.randint(round(used_size / 3), used_size)
            snap_type = random.choice(["ro", "rw"])
            self.dt_1_dict_data["Snapshots"]["vol"][0]["creationTime"]["Ms"] = creation_time
            convert_date_format = datetime.datetime.strptime(
                self.convert_ms_to_date_time(creation_time), "%Y-%m-%d %H:%M:%S.%f000 %z %Z"
            )
            snap_spark_creation_time = convert_date_format.strftime("%Y-%m-%d %H:%M:%S")
            spark_temp_snap_dict["creationtime"] = snap_spark_creation_time

            self.dt_1_dict_data["Snapshots"]["vol"][0]["customerId"] = custid
            spark_temp_snap_dict["custid"] = custid
            self.dt_1_dict_data["Snapshots"]["vol"][0]["expirationTime"]["Ms"] = exp_time
            convert_date_format = datetime.datetime.strptime(
                self.convert_ms_to_date_time(exp_time), "%Y-%m-%d %H:%M:%S.%f000 %z %Z"
            )
            snap_spark_exp_time = convert_date_format.strftime("%Y-%m-%d %H:%M:%S")
            spark_temp_snap_dict["expirationtime"] = snap_spark_exp_time
            self.dt_1_dict_data["Snapshots"]["vol"][0]["id"] = snap_id
            spark_temp_snap_dict["snapid"] = snap_id
            self.dt_1_dict_data["Snapshots"]["vol"][0]["name"] = snap_name
            self.dt_1_dict_data["Snapshots"]["vol"][0]["displayname"] = snap_name
            spark_temp_snap_dict["snapname"] = snap_name
            self.dt_1_dict_data["Snapshots"]["vol"][0]["retentionTime"]["Ms"] = exp_time
            spark_temp_snap_dict["retentiontime"] = snap_spark_exp_time
            self.dt_1_dict_data["Snapshots"]["vol"][0]["sizeMiB"] = snap_size
            spark_temp_snap_dict["snapsize"] = snap_size
            self.dt_1_dict_data["Snapshots"]["vol"][0]["snapshotType"] = snap_type
            spark_temp_snap_dict["snaptype"] = "adhoc"
            self.dt_1_dict_data["Snapshots"]["vol"][0]["systemId"] = arr
            spark_temp_snap_dict["arrid"] = arr
            self.dt_1_dict_data["Snapshots"]["vol"][0]["type"] = snap_type
            snap_data = pickle.dumps(self.dt_1_dict_data["Snapshots"]["vol"][0])
            self.dt1_all_coll_snap_dict[vol_id].append(pickle.loads(snap_data))
            snp_data = pickle.dumps(spark_temp_snap_dict)
            self.spark_snap_data.append(pickle.loads(snp_data))
            app_snp_dict.append(pickle.loads(snp_data))
        return self.dt1_all_coll_snap_dict, app_snp_dict

    def generate_dt2_snaps_per_volume(
        self, arr, vol_id, vol_name, used_size, custid, snap_count, c_date, storage_sys_id
    ):
        if vol_id not in self.dt2_all_coll_snap_dict:
            self.dt2_all_coll_snap_dict.update({vol_id: []})
        spark_temp_snap_dict_dt2 = {}
        app_snaps = []

        for snap in range(snap_count):
            self.snaps += 1
            spark_temp_snap_dict_dt2["collectionstarttime"] = self.spark_frame_coll_start_time
            spark_temp_snap_dict_dt2["collectionendtime"] = self.spark_frame_coll_end_time
            spark_temp_snap_dict_dt2["volumeid"] = vol_id
            spark_temp_snap_dict_dt2["arrid"] = arr
            creation_time = random.uniform(c_date + 600, c_date + 2400)
            snap_id = self.generate_random_str_with_alpha_number(num_of_char=32)
            snap_name = f"{vol_name}-snap-{snap}"
            snap_size = random.randint(round(used_size / 3), used_size)
            status = random.choices([True, False])
            expiry = random.randint(1, 100)
            unmanaged = random.choice([True, False])

            self.dt_2_dict_data["Snapshots"]["vol"][0]["id"] = snap_id
            spark_temp_snap_dict_dt2["snapid"] = snap_id
            self.dt_2_dict_data["Snapshots"]["vol"][0]["name"] = snap_name
            spark_temp_snap_dict_dt2["snapname"] = snap_name
            self.dt_2_dict_data["Snapshots"]["vol"][0]["size"] = snap_size
            spark_temp_snap_dict_dt2["snapsize"] = snap_size
            self.dt_2_dict_data["Snapshots"]["vol"][0]["vol_name"] = vol_name
            self.dt_2_dict_data["Snapshots"]["vol"][0]["vol_id"] = vol_id
            self.dt_2_dict_data["Snapshots"]["vol"][0]["online"] = status
            self.dt_2_dict_data["Snapshots"]["vol"][0]["expiry_after"] = expiry
            exp_date = self.calculate_collection_time(days=expiry).strftime("%Y-%m-%d %H:%M:%S")
            spark_temp_snap_dict_dt2["expirationtime"] = exp_date
            spark_temp_snap_dict_dt2["retentiontime"] = exp_date
            self.dt_2_dict_data["Snapshots"]["vol"][0]["is_unmanaged"] = unmanaged
            if unmanaged:
                self.dt_2_dict_data["Snapshots"]["vol"][0]["is_manually_managed"] = False
                spark_temp_snap_dict_dt2["snaptype"] = "periodic"
            else:
                self.dt_2_dict_data["Snapshots"]["vol"][0]["is_manually_managed"] = True
                spark_temp_snap_dict_dt2["snaptype"] = "adhoc"
            self.dt_2_dict_data["Snapshots"]["vol"][0]["creation_time"] = int(creation_time)
            convert_date_format = datetime.datetime.strptime(
                self.convert_ms_to_date_time(int(creation_time), convert_type="stodate"),
                "%Y-%m-%d %H:%M:%S.%f000 %z %Z",
            )
            snap_spark_creation_time = convert_date_format.strftime("%Y-%m-%d %H:%M:%S")
            spark_temp_snap_dict_dt2["creationtime"] = snap_spark_creation_time
            self.dt_2_dict_data["Snapshots"]["vol"][0]["last_modified"] = int(creation_time) + 3600
            self.dt_2_dict_data["Snapshots"]["vol"][0]["customerId"] = custid
            spark_temp_snap_dict_dt2["custid"] = custid
            for ind, links in enumerate(self.dt_2_dict_data["Snapshots"]["vol"][0]["associated_links"]):
                if links["type"] == "volumes":
                    self.dt_2_dict_data["Snapshots"]["vol"][0]["associated_links"][ind][
                        "resourceUri"
                    ] = f"/api/v1/storage-systems/device-type2/{arr}/volumes"
                else:
                    self.dt_2_dict_data["Snapshots"]["vol"][0]["associated_links"][ind][
                        "resourceUri"
                    ] = f"/api/v1/storage-systems/device-type2/{arr}"
            self.dt_2_dict_data["Snapshots"]["vol"][0][
                "resourceUri"
            ] = f"/api/v1/storage-systems/device-type2/{arr}/volumes/{vol_id}/snapshots/{snap_id}"

            snap_data = pickle.dumps(self.dt_2_dict_data["Snapshots"]["vol"][0])
            s_snp_data = pickle.dumps(spark_temp_snap_dict_dt2)
            self.spark_snap_data.append(pickle.loads(s_snp_data))
            app_snaps.append(pickle.loads(s_snp_data))
            self.dt2_all_coll_snap_dict[vol_id].append(pickle.loads(snap_data))
        return self.dt2_all_coll_snap_dict, app_snaps, creation_time

    def create_vlun_name(self, vol_name):
        v_name = f"{vol_name}-VLUN-{self.vlun_index}"
        self.vlun_index += 1
        return v_name

    def generate_dt1_mounted_vols(self, vol_name, vol_id, cust_id, arr_id, vv_size, vol_wwn):
        vlun_name = self.create_vlun_name(vol_name)
        vlun_id = self.generate_random_str_with_alpha_number(num_of_char=32)
        self.dt1_all_coll_vlun_dict[vol_id] = []

        for path in range(24):
            path_active = random.choice([True, False])
            self.dt_1_dict_data["Vluns"]["volid"][0]["active"] = path_active
            self.dt_1_dict_data["Vluns"]["volid"][0]["customerId"] = cust_id
            self.dt_1_dict_data["Vluns"]["volid"][0]["displayname"] = vlun_name
            self.dt_1_dict_data["Vluns"]["volid"][0]["id"] = vlun_id
            self.dt_1_dict_data["Vluns"]["volid"][0]["lun"] = self.vlun_index - 1
            self.dt_1_dict_data["Vluns"]["volid"][0]["systemId"] = arr_id
            self.dt_1_dict_data["Vluns"]["volid"][0]["volumeName"] = vol_name
            self.dt_1_dict_data["Vluns"]["volid"][0]["volumeWWN"] = vol_wwn
            self.dt_1_dict_data["Vluns"]["volid"][0]["vvReservedUserSpace"] = vv_size
            self.dt_1_dict_data["Vluns"]["volid"][0]["vvSize"] = vv_size
            mounted_vol_data = pickle.dumps(self.dt_1_dict_data["Vluns"]["volid"][0])
            self.dt1_all_coll_vlun_dict[vol_id].append(pickle.loads(mounted_vol_data))

    def generate_vol_coll_data(self, vol_coll_name, vol_coll_id, vol_info, creation_date, cust_id):
        for storage_sys_id in vol_info:
            self.dt_2_dict_data["VolumeCollections"]["collection1"][0]["id"] = storage_sys_id
            self.dt_2_dict_data["VolumeCollections"]["collection1"][0]["name"] = vol_coll_name
            self.dt_2_dict_data["VolumeCollections"]["collection1"][0]["full_name"] = vol_coll_name
            self.dt_2_dict_data["VolumeCollections"]["collection1"][0]["search_name"] = vol_coll_name
            self.dt_2_dict_data["VolumeCollections"]["collection1"][0]["creation_time"] = creation_date - 300
            self.dt_2_dict_data["VolumeCollections"]["collection1"][0]["last_modified_time"] = creation_date - 300
            for vol in vol_info[storage_sys_id]:
                self.dt_2_dict_data["VolumeCollections"]["collection1"][0]["volume_list"].append(
                    vol_info[storage_sys_id][vol]
                )
            self.dt_2_dict_data["VolumeCollections"]["collection1"][0]["volume_count"] = len(
                vol_info[storage_sys_id].keys()
            )
            sched_id = f"{self.generate_random_str_with_alpha_number(num_of_char=18)}000000000000000000000008"
            self.dt_2_dict_data["VolumeCollections"]["collection1"][0]["schedule_list"][0]["id"] = sched_id
            self.dt_2_dict_data["VolumeCollections"]["collection1"][0]["schedule_list"][0]["id"] = sched_id
            self.dt_2_dict_data["VolumeCollections"]["collection1"][0]["associated_links"][0][
                "resourceUri"
            ] = f"/api/v1/storage-systems/device-type2/{storage_sys_id}"
            self.dt_2_dict_data["VolumeCollections"]["collection1"][0]["customerId"] = cust_id
            self.dt_2_dict_data["VolumeCollections"]["collection1"][0]["systemId"] = storage_sys_id
            self.dt_2_dict_data["VolumeCollections"]["collection1"][0][
                "consoleUri"
            ] = f"/data-ops-manager/storage-systems/device-type2/{storage_sys_id}/volume-collections/{vol_coll_id}"
            self.dt_2_dict_data["VolumeCollections"]["collection1"][0][
                "consoleUri"
            ] = f"/api/v1/storage-systems/device-type2/{storage_sys_id}/volume-collections/{vol_coll_id}"
            if storage_sys_id in self.dt2_all_coll_volcoll_dict:
                coll_data = pickle.dumps(self.dt_2_dict_data["VolumeCollections"]["collection1"][0])
                self.dt2_all_coll_volcoll_dict[storage_sys_id].append(pickle.loads(coll_data))
            else:
                self.dt2_all_coll_volcoll_dict[storage_sys_id] = []
                col_data = pickle.dumps(self.dt_2_dict_data["VolumeCollections"]["collection1"][0])
                self.dt2_all_coll_volcoll_dict[storage_sys_id].append(pickle.loads(col_data))
            self.dt_2_dict_data["VolumeCollections"]["collection1"][0]["volume_list"] = []
        self.vol_coll_dict = {}
        return self.dt2_all_coll_volcoll_dict

    def generate_app_data(self, num_of_apps, num_of_vol_per_app, cust_id, arr_id, app_vol_choices):
        dt1_temp_app_dict = {}
        for app in range(num_of_apps):
            app_flag = 0
            vol_count_per_app = random.randint(round(num_of_vol_per_app / 2), num_of_vol_per_app)
            app_set_id = random.randint(10, 10000)
            app_set_imp = random.choice(["NORMAL", "UNKNOWN"])
            app_set_type = random.choice(
                [
                    "Microsoft SQL Server",
                    "Microsoft Exchange",
                    "Virtual Desktop",
                    "SAP HANA",
                    "Microsoft Hyper-V Cluster Shared Volume",
                    "SQL Server Logs",
                ]
            )
            exp_status = random.choice(
                [
                    "PARTIALLY_EXPORTED",
                    "NOT_EXPORTED",
                    "FULLY_EXPORTED",
                ]
            )
            dt1_temp_app_dict["collectionstarttime"] = self.spark_frame_coll_start_time
            dt1_temp_app_dict["collectionendtime"] = self.spark_frame_coll_end_time
            app_set_name = f"PQA-APP-{random.randint(10, 10000)}"
            self.dt_1_dict_data["Applicationsets"]["array"][0]["appSetId"] = app_set_id
            dt1_temp_app_dict["appsetid"] = app_set_id
            self.dt_1_dict_data["Applicationsets"]["array"][0]["appSetImportance"] = app_set_imp
            self.dt_1_dict_data["Applicationsets"]["array"][0]["appSetName"] = app_set_name
            dt1_temp_app_dict["appsetname"] = app_set_name
            self.dt_1_dict_data["Applicationsets"]["array"][0]["appSetType"] = app_set_type
            dt1_temp_app_dict["appname"] = app_set_type
            self.dt_1_dict_data["Applicationsets"]["array"][0]["customerId"] = cust_id
            dt1_temp_app_dict["custid"] = cust_id
            self.dt_1_dict_data["Applicationsets"]["array"][0]["exportStatus"] = exp_status
            self.dt_1_dict_data["Applicationsets"]["array"][0]["id"] = self.generate_random_str_with_alpha_number(
                num_of_char=32
            )
            a_vol_choices = pickle.dumps(app_vol_choices)
            a_vol_choices_decode = pickle.loads(a_vol_choices)
            for vol_id in a_vol_choices_decode:
                for vol_dict in self.dt1_all_coll_temp_dict[arr_id]:
                    if vol_dict["id"] == vol_id:
                        if app_flag == vol_count_per_app:
                            break
                        dt1_temp_app_dict["volid"] = vol_id
                        dt1_temp_app_dict["volumesnapcount"] = app_vol_choices[vol_id]["snapcount"]
                        dt1_temp_app_dict["volumeclonecount"] = app_vol_choices[vol_id]["clonecount"]
                        dt1_temp_app_dict["volumetotalsize"] = vol_dict["sizeMiB"]
                        dt1_temp_app_dict["volumeusedsize"] = vol_dict["usedSizeMiB"]
                        dt1_temp_app_dict["volumename"] = vol_dict["name"]
                        dt1_temp_app_dict["volumecreationtime"] = vol_dict["creationTime"]["ms"]
                        dt1_temp_app_dict["volumeexpiresat"] = 0
                        dt1_temp_app_dict["arrayid"] = arr_id
                        s_app_data = pickle.dumps(dt1_temp_app_dict)
                        self.spark_app_data.append(pickle.loads(s_app_data))
                        if a_vol_choices_decode[vol_id]["clones"]:
                            for clone_data in a_vol_choices_decode[vol_id]["clones"]:
                                self.spark_app_clone_data.append(copy.deepcopy(clone_data))
                        if a_vol_choices_decode[vol_id]["snaps"]:
                            for snap_data in a_vol_choices_decode[vol_id]["snaps"]:
                                self.spark_app_snap_data.append(copy.deepcopy(snap_data))
                        self.dt_1_dict_data["Applicationsets"]["array"][0]["members"].append(vol_id)

                        del app_vol_choices[vol_id]
                        app_flag += 1

            self.dt_1_dict_data["Applicationsets"]["array"][0]["name"] = app_set_name
            self.dt_1_dict_data["Applicationsets"]["array"][0]["systemId"] = arr_id

            if arr_id in self.dt1_all_app_dict:
                app_data = pickle.dumps(self.dt_1_dict_data["Applicationsets"]["array"][0])
                self.dt1_all_app_dict[arr_id].append(pickle.loads(app_data))
            else:
                self.dt1_all_app_dict[arr_id] = []
                a_data = pickle.dumps(self.dt_1_dict_data["Applicationsets"]["array"][0])
                self.dt1_all_app_dict[arr_id].append(pickle.loads(a_data))
            self.dt_1_dict_data["Applicationsets"]["array"][0]["members"] = []

        return self.dt1_all_app_dict

    def generate_app_data_dt2(self, num_of_apps, num_of_vols_per_app, volumes_dict, arr_id):
        dt2_temp_app_dict = {}
        for app in range(num_of_apps):
            app_per_vol_flag = 0
            perf_policy_id = self.generate_random_str_with_alpha_number(num_of_char=18) + "000000000000000000000001"
            perf_policy_name = f"PQA-TEST-APP-{random.randint(1,1000)}"
            dt2_temp_app_dict["collectionstarttime"] = self.spark_frame_coll_start_time
            dt2_temp_app_dict["collectionendtime"] = self.spark_frame_coll_end_time
            dt2_temp_app_dict["appsetid"] = perf_policy_id
            dt2_temp_app_dict["appsetname"] = perf_policy_name
            dt2_temp_app_dict["appname"] = perf_policy_name

            dt2_temp_app_dict["arrayid"] = arr_id
            dt2_temp_app_dict["appusedsize"] = 0
            app_vol_choices = pickle.dumps(volumes_dict)
            app_vol_choices = pickle.loads(app_vol_choices)
            for vol_id in app_vol_choices:
                for vol_dict in self.dt2_all_coll_temp_dict[arr_id]:
                    if vol_dict["id"] == vol_id and not vol_dict["clone"]:
                        if app_per_vol_flag == num_of_vols_per_app:
                            break
                        vol_dict["perfpolicy_name"] = perf_policy_name
                        vol_dict["perfpolicy_id"] = perf_policy_id
                        dt2_temp_app_dict["custid"] = vol_dict["customerId"]
                        dt2_temp_app_dict["volid"] = vol_id
                        dt2_temp_app_dict["volumesnapcount"] = app_vol_choices[vol_id]["snapcount"]
                        dt2_temp_app_dict["volumeclonecount"] = app_vol_choices[vol_id]["clonecount"]
                        dt2_temp_app_dict["volumetotalsize"] = vol_dict["size"]
                        dt2_temp_app_dict["volumeusedsize"] = vol_dict["total_usage_bytes"]
                        dt2_temp_app_dict["volumename"] = vol_dict["name"]
                        dt2_temp_app_dict["volumecreationtime"] = vol_dict["creation_time"]
                        dt2_temp_app_dict["volumeexpiresat"] = 0
                        dt2_temp_app_dict["arrayid"] = arr_id
                        if app_vol_choices[vol_id]["clones"]:
                            for clone_data in app_vol_choices[vol_id]["clones"]:
                                self.spark_app_clone_data.append(copy.deepcopy(clone_data))
                        if app_vol_choices[vol_id]["snaps"]:
                            for snap_data in app_vol_choices[vol_id]["snaps"]:
                                self.spark_app_snap_data.append(copy.deepcopy(snap_data))

                        app_dict = pickle.dumps(dt2_temp_app_dict)
                        self.spark_app_data.append(pickle.loads(app_dict))

                        del volumes_dict[vol_id]
                        app_per_vol_flag += 1

    def dt1_generate_vol_performance(self, arr_id, vol_id, cust_id):
        self.perf_vol_count += 1
        temp_vol_perf_dict_dt1 = {}
        avg_8_hours = random.randint(10, 80)
        self.dt_1_dict_data["VolumePerformance"][0]["systemId"] = arr_id
        self.dt_1_dict_data["VolumePerformance"][0]["volumeId"] = vol_id
        self.dt_1_dict_data["VolumePerformance"][0]["customerId"] = cust_id
        self.dt_1_dict_data["VolumePerformance"][0]["iops"]["total"]["avgOf8hours"] = avg_8_hours
        temp_vol_perf_dict_dt1["collectionstarttime"] = self.spark_frame_coll_start_time
        temp_vol_perf_dict_dt1["collectionendtime"] = self.spark_frame_coll_end_time
        temp_vol_perf_dict_dt1["arrid"] = arr_id
        temp_vol_perf_dict_dt1["id"] = vol_id
        temp_vol_perf_dict_dt1["custid"] = cust_id
        temp_vol_perf_dict_dt1["avgiops"] = avg_8_hours
        s_vol_perf = pickle.dumps(temp_vol_perf_dict_dt1)
        self.spark_vol_perf.append(pickle.loads(s_vol_perf))
        v_perf = pickle.dumps(self.dt_1_dict_data["VolumePerformance"][0])

        return pickle.loads(v_perf)

    def dt2_generate_vol_performance(self, arr_id, vol_id, cust_id):
        self.perf_vol_count += 1
        temp_vol_perf_dict_dt2 = {}
        avg_8_hours = random.randint(10, 80)
        self.dt_2_dict_data["VolumePerformance"][0]["systemId"] = arr_id
        self.dt_2_dict_data["VolumePerformance"][0]["volumeId"] = vol_id
        self.dt_2_dict_data["VolumePerformance"][0]["customerId"] = cust_id
        self.dt_2_dict_data["VolumePerformance"][0]["iops"]["total"]["avgOf8hours"] = avg_8_hours

        temp_vol_perf_dict_dt2["collectionstarttime"] = self.spark_frame_coll_start_time
        temp_vol_perf_dict_dt2["collectionendtime"] = self.spark_frame_coll_end_time
        temp_vol_perf_dict_dt2["arrid"] = arr_id
        temp_vol_perf_dict_dt2["id"] = vol_id
        temp_vol_perf_dict_dt2["custid"] = cust_id
        temp_vol_perf_dict_dt2["avgiops"] = avg_8_hours
        t_vol_perf = pickle.dumps(temp_vol_perf_dict_dt2)
        self.spark_vol_perf.append(pickle.loads(t_vol_perf))
        vol_perf = pickle.dumps(self.dt_2_dict_data["VolumePerformance"][0])

        return pickle.loads(vol_perf)
