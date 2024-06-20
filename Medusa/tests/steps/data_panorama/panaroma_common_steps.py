################################################################
#
# File: panaroma_common_steps.py
# Author: Kranthi Kumar
# Date: Oct 15 2022
#
# (C) Copyright 2023 - Hewlett Packard Enterprise Development LP
#
################################################################
#
# Description:
#      module implementation.
#      Script contain S3 common
################################################################


import calendar
import datetime
from datetime import datetime, timedelta
import logging
from dateutil.relativedelta import relativedelta, MO
from enum import Enum
import json
from pathlib import Path
import threading
import time
import shutil
import random
import subprocess
from json import dumps
import os
import paramiko
import findspark
import pandas as pd
import pyspark
import pyspark.sql.functions as functions
from kafka import KafkaProducer
import sqlalchemy
from lib.dscc.data_panorama.app_lineage.models.app_lineage import *
from lib.dscc.data_panorama.consumption.models.clones import *
from lib.dscc.data_panorama.consumption.models.snapshots import *
from lib.dscc.data_panorama.consumption.models.volumes import *
from lib.dscc.data_panorama.inventory_manager.models.inventory_manager import *
from lib.platform.storage_array.alletra_6k.alletra_6k_api import AlletraNimble
from lib.platform.storage_array.alletra_9k.alletra_9k_api import AlletraThreePar
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import *
from pyspark.sql.types import *
from tests.e2e.data_panorama.mock_data_generate.spark_tables.aggregated_tables import (
    create_spark_tables,
)
from tests.e2e.data_panorama.panorama_context import Context
from tests.steps.data_panorama.json_data_generator.data_generator import (
    JsonDataGenerator,
)
from functools import reduce
from utils.common_helpers import get_project_root
from lib.platform.storage_array.ssh_connection import SshConnection
import numpy as np
import sys

logger = logging.getLogger()


@udf(returnType=StringType())
def harmony_start_date(input_date):
    """_summary_
     Since The harmony calculates 30 days average starting from jan-3-2000 and not by monthly average. This function returns the months starting date for a given collection time as per harmony's calcuction of start date.
    Args:
        input_date (_type_): Actual collection startdate

    Returns:
        _type_: returns the starting date as per harmonys calculations
    """
    today = np.datetime64("today", "D")
    harmony_start_date = "2000-01-03"
    date_range = np.arange(start=harmony_start_date, stop=today, step=30, dtype="datetime64[D]")
    np_input_date = np.datetime64(input_date)
    greater_dates_index = (np.where(date_range > np_input_date))[0]
    # Previous index to greater date will be start date index
    start_date_index = greater_dates_index - 1
    start_date = date_range[start_date_index][0]
    return str(start_date)


def write_to_json(df: pd.DataFrame, path: str, sort_by):
    if not df.empty:  # If dataframe is not empty then sort it
        df = df.sort_values(by=sort_by)

    path = _create_test_dir(path)

    df.to_json(path, orient="records", indent=4)


def _create_test_dir(path):
    """Folder name with the test case name will be created. Here the output json files can be stored

    Args:
        path (str): Full path of .json file
    """
    parent_dir = path.split("/")[0]
    file_name = path.split("/")[1]
    paths = path.split("_")
    dir_name = [p for p in paths if ".json" in p]
    dir_name = dir_name[0].split(".json")[0]
    os.makedirs(f"{parent_dir}/{dir_name}", exist_ok=True)
    return f"{parent_dir}/{dir_name}/{file_name}"


class Granularity(Enum):
    daily = "day"
    hourly = "collectionHour"
    weekly = "week"


class PanaromaCommonSteps(object):
    def __init__(self, context: Context, load_mock=False):
        self.context = context
        self.alletra_6k_obj = AlletraNimble(context=context)
        self.alletra_9k_obj = AlletraThreePar(context=context)
        self.json_gen_obj = JsonDataGenerator()
        self.vol_data_frame = ""
        self.clone_data_frame = ""
        self.snaps_data_frame = ""
        self.vol_usage_data_frame = ""
        self.vol_perf_data_frame = ""
        self.inventory_data_frame = ""
        self.snap_data_frame = ""
        self.spark_clone_data_frame = ""
        self.spark_clone_data_frame = ""
        self.spark_snaps_data_frame = ""
        self.spark_vol_perf_data_frame = ""
        self.spark_vol_usage_data_frame = ""
        self.mock_vol_usage_latest_collection = ""
        self.spark_clone_usage_data_frame = ""
        self.spark_inventory_data_frame = ""
        self.spark_app_data_frame = ""
        self.generated_data = []
        self.app_snap_data = ""
        self.app_clone_data = ""
        self.spark = ""
        self.client = ""
        self.mock_folder = ""
        self.cost_dict = ""
        self.spquery_inventory_sys_data = pd.DataFrame({})
        # Update this file as per the uploaded collection
        self.golden_db_path = self.context.golden_db_path
        self.input_golden_db_path = self.context.input_golden_db_path
        if load_mock:
            self.load_mock_data()
        # Create folder for test json results
        self.json_path = "out"
        os.makedirs(self.json_path, exist_ok=True)

    def load_spark_module_obj(self):
        findspark.init()
        self.spark = SparkSession.builder.appName("Medusa Saprk").master("local[1]").getOrCreate()

    def load_mock_data(self):
        """
        Loading spark tables from sqlite db file

        """
        # DB name required
        FILE_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
        out_db_name = f"{FILE_PATH}/../../../{self.golden_db_path}"
        engine = sqlalchemy.create_engine("sqlite:///%s" % out_db_name, execution_options={"sqlite_raw_colnames": True})
        conn = engine.connect()

        input_db_name = f"{FILE_PATH}/../../../{self.input_golden_db_path}"
        input_engine = sqlalchemy.create_engine(
            "sqlite:///%s" % input_db_name, execution_options={"sqlite_raw_colnames": True}
        )
        input_conn = input_engine.connect()

        self.context.cost_dict = pd.read_sql_table("systems_cis_info", con=input_conn)
        self.context.mock_collection_data = pd.read_sql_table("collections_info", con=input_conn)
        self.context.mock_sys_lastcoll = pd.read_sql_table("spark_sys_lastcollection", con=conn)
        self.context.mock_vol_lastcoll = pd.read_sql_table("spark_vol_lastcollection", con=conn)
        self.context.mock_snap_lastcoll = pd.read_sql_table("spark_snap_lastcollection", con=conn)
        self.context.mock_clone_lastcoll = pd.read_sql_table("spark_clone_lastcollection", con=conn)
        self.context.mock_app_lastcoll = pd.read_sql_table("spark_app_lastcollection", con=conn)
        self.context.mock_vol_allcoll = pd.read_sql_table("spark_vol_all_collection", con=conn)
        self.context.mock_vol_usage_lastcoll = pd.read_sql_table("spark_volusage_lastcollection", con=conn)
        self.context.mock_vol_perf_allcoll = pd.read_sql_table("spark_volperf_all_collection", con=conn)
        self.context.mock_clone_allcoll = pd.read_sql_table("spark_clone_all_collection", con=conn)
        self.context.mock_app_lastcoll_with_sys = pd.read_sql_table("spark_app_lastcollection_with_sys_info", con=conn)
        self.context.mock_snap_all = pd.read_sql_table("spark_snap_all_collection", con=conn)
        self.context.mock_snap_usage = pd.read_sql_table("spark_snap_usage_collection", con=conn)
        self.spquery_inventory_sys_data = pd.read_sql_table("spquery_inventory_sys_data", con=conn)
        self.spquery_sys_monthly_cost = pd.read_sql_table("spquery_sys_monthly_cost", con=conn)
        self.spark_system_cost = pd.read_sql_table("spark_system_cost", con=conn)

    def create_config(
        self,
        array_data_set: dict = {},
        pre_clean_up: bool = False,
    ):
        """
        create_config: method will use to create the configuration on both alletra6k and 9k arrays parelally using threads.
        -------------

        Parameters:
        -----------
            array_data_set:-
                Type: Dictionary
                usage: it will collect dicyionary in below format, dictionary can contains both alletra6k and 9k array names.
                        arrayname is a key and value is list format, each index inside the list will be one data set.
                        each data set represent fields like below
                        [<year><month><days><hour><min><volcount><thickvolcount><snapcountpervolume>]
                        - Ex:- [0, 3, 1, 3, 10, 2, 1, 2] in this data set config script will change date to
                                0 Year 3 months 1day 3hours 10min back and create 2 volumes with in that 1 thick volume
                                    - and 2 snaps per alternate volume
                data_set = {
                    array_name : [[0, 3, 0, 0, 0, 2, 1, 2], [2, 3, 0, 0, 0, 5, 4, 0], [5, 3, 0, 0, 0, 4, 2, 1]....[],[]],
                    array_name : [[0, 3, 0, 0, 0, 2, 1, 2], [1, 3, 0, 0, 0, 5, 4, 0], [1, 4, 0, 0, 0, 4, 2, 1]....[],[]]]
                }
                Note: Keys(array names) are mandatory in the dictionary, value for key can be empty or data set
                        if data set empty it wiwll pick default data setspecified in script.
                        - value for key is list of list
            pre_clean_up:-
                Type: boolean
                usage: if pre_clean_up True, before starting configuration array firat it will clean up array than starts
                        the configuration
                Note: If config script fails any reason, it will report error than rectify error in array and retrigger script with
                        pre cleanup as a False, so script will not clean array it will start where it fails with either default
                        data set or provided data set.

        Return:
            dict :- config created dictionary
        """

        assert array_data_set, "Required one array name to trigger configuration"
        alletra_6k_thread_list = []
        alletra_9k_thread_list = []
        alletra_6k_array_info = self.alletra_6k_obj.array_info
        alletra_9k_array_info = self.alletra_9k_obj.array_info
        for array_name in array_data_set:
            if alletra_6k_array_info[array_name]["os"] == "nimble":
                alletra_6k_thread = threading.Thread(
                    target=self.alletra_6k_obj.create_array_config,
                    args=(array_name, array_data_set[array_name], pre_clean_up),
                )
                alletra_6k_thread_list.append(alletra_6k_thread)
                alletra_6k_thread.start()
            elif alletra_9k_array_info[array_name]["os"] == "3par":
                alletr_9k_array_name = array_name + "." + alletra_9k_array_info[array_name]["domain"]
                alletra_9k_thread = threading.Thread(
                    target=self.alletra_9k_obj.create_array_config,
                    args=(
                        alletr_9k_array_name,
                        array_data_set[array_name],
                        pre_clean_up,
                    ),
                )
                alletra_9k_thread_list.append(alletra_9k_thread)
                alletra_9k_thread.start()
        else:
            total_threads = alletra_6k_thread_list + alletra_9k_thread_list
            for thread in total_threads:
                thread.join()

        self.context.alletra_6k_created_config_info = self.alletra_6k_obj.created_config_info
        self.context.alletra_9k_created_config_info = self.alletra_9k_obj.created_config_info
        return (
            self.alletra_6k_obj.created_config_info,
            self.alletra_9k_obj.created_config_info,
        )

    def clear_config(self, array_names: list = [], post: bool = True):
        """
        create_config: method will use to clear the configuration alletra6k and 9k arrays parelally using threads.
        -------------

        Parameters:
        -----------
            array_names:-
                Type: list
                usage: it will collect array names in a list with comma separate
            post:-
                Type: boolean
                usage: if post True, it will execute script generated volumes and clones directly, so that we can
                reduce time complexity.
        Return:
            None
        """
        alletra_6k_thread_list = []
        alletra_9k_thread_list = []
        alletra_6k_array_info = self.alletra_6k_obj.array_info
        alletra_9k_array_info = self.alletra_9k_obj.array_info
        for arr_name in array_names:
            if alletra_6k_array_info[arr_name]["os"] == "nimble":
                thread = threading.Thread(
                    target=self.alletra_6k_obj.clear_config,
                    args=(arr_name, post),
                )
                alletra_6k_thread_list.append(thread)
                thread.start()
            elif alletra_9k_array_info[arr_name]["os"] == "3par":
                alletr_9k_array_name = arr_name + "." + alletra_9k_array_info[arr_name]["domain"]
                alletra_9k_thread = threading.Thread(
                    target=self.alletra_9k_obj.create_array_config,
                    args=(alletr_9k_array_name, post),
                )
                alletra_9k_thread_list.append(alletra_9k_thread)
                alletra_9k_thread.start()
        else:
            total_threads = alletra_6k_thread_list + alletra_9k_thread_list
            for thread in total_threads:
                thread.join()
        print("INFO: Clear config done on all arrays...")

    def mock_json_data_generate(
        self,
        data_set: dict = {},
        customer_id: str = "03bf4f5020022edecad3a7642bfb5391",
        days_back_data: int = 360,
    ):
        self.json_gen_obj.generate_collection_data(
            data_set=data_set, customer_id=customer_id, days_back_data=days_back_data
        )
        """
        (
            self.context.mock_vol_data,
            self.context.mock_snap_data,
            self.context.mock_clone_data,
            self.context.mock_vol_usage_data,
            self.context.mock_vol_perf_data,
            self.context.mock_app_data,
            self.context.mock_snap_app_data,
            self.context.mock_clone_app_data,
            self.context.mock_inventory_data,
            self.context.mock_total_snaps,
            self.context.mock_total_clones,
        ) = self.json_gen_obj.generate_collection_data(
            data_set=data_set, customer_id=customer_id, days_back_data=days_back_data
        )

        self.generated_data = [
            self.context.mock_vol_data,
            self.context.mock_snap_data,
            self.context.mock_clone_data,
            self.context.mock_app_data,
            self.context.mock_inventory_data,
            self.context.mock_total_snaps,
            self.context.mock_total_clones,
        ]

        return self.generated_data
        """

    def upload_to_server(self, mock_data_foldername=""):
        self.client = SshConnection(hostname="10.239.73.120", username="root", password="HPE_ftc3404", sftp=True)
        self.mock_folder = mock_data_foldername if mock_data_foldername else self.mock_folder
        os.environ["UPLOADFOLDERNAME"] = self.mock_folder
        # spark_data_json_name = get_project_root() / "tests/steps/data_panorama/json_data_generator/spark_json_data.json"
        # self.client.get(f"/tmp/{self.mock_folder}/spark_json_data.json", spark_data_json_name)
        # with open(spark_data_json_name) as f:
        #    json_to_dict = json.load(f)
        # self.mock_folder = json_to_dict["upload_folder_name"]
        # os.remove(spark_data_json_name)
        json_to_dict = None
        remote_path = f"/tmp/{self.mock_folder}"
        self.client.get_all(remote_path, "/tmp")
        for root, folder, files in os.walk(f"/tmp/{self.mock_folder}/costinfo"):
            cost_info_gz_file = f"{root}/{files[0]}"
            id1 = random.randint(0, 100)
            id2 = random.randint(100, 200)
            upload_random_number = f"PQATEST{id1}{id2}"

            curl_cmd = f'curl -X POST -v -F key1=value1 -F file=@{cost_info_gz_file} \
                http://10.239.75.201:10031/upload -H "X-INFOSIGHT-UPLOAD-SERVER-META-FILEDOMAIN:starburst" \
                -H "X-INFOSIGHT-UPLOAD-SERVER-META-FILETYPE:PQA2Cis" \
                -H "X-INFOSIGHT-UPLOAD-SERVER-META-FILESIZE: 0" \
                -H "X-INFOSIGHT-UPLOAD-SERVER-META-SN: {upload_random_number}" --noproxy "*"'
            output_stream = subprocess.Popen(curl_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, err = output_stream.communicate()
            err = str(err)
            p_status = output_stream.wait()
            for line in err.split("\n"):
                if "HTTP/1.1 200 OK" in line:
                    print(
                        "********************************************************************************************"
                    )
                    print(f"* {root}/{cost_info_gz_file} UPLOAD COMPLETED SUCCESSFULLY")
                    print(
                        "********************************************************************************************"
                    )
                else:
                    print("********************************************************************************")
                    print(f"* {root}/{cost_info_gz_file} FILE UPLOAD FAILED")
                    print("********************************************************************************")
                    print(line)

        upload_flag = 0
        for root, folder, files in os.walk(f"/tmp/{self.mock_folder}"):
            ordered_files = [None, None, None]
            if "costinfo" in root:
                continue
            upload_flag += 1
            for gzfile in files:
                if "json" in gzfile:
                    continue

                if "dt1" in gzfile:
                    ordered_files[0] = gzfile
                if "dt2" in gzfile:
                    ordered_files[1] = gzfile
                if "eoc" in gzfile:
                    ordered_files[2] = gzfile

            for ordered_gzfile in ordered_files:
                print(datetime.now())
                file_to_upload = f"{root}/{ordered_gzfile}"
                id1 = random.randint(0, 100)
                id2 = random.randint(100, 200)
                upload_random_number = f"PQATEST{id1}{id2}"
                curl_cmd = f'curl -X POST -v -F key1=value1 -F file=@{file_to_upload} \
                    http://10.239.75.201:10031/upload -H "X-INFOSIGHT-UPLOAD-SERVER-META-FILEDOMAIN:starburst" \
                    -H "X-INFOSIGHT-UPLOAD-SERVER-META-FILETYPE:PQA2Fleet" \
                    -H "X-INFOSIGHT-UPLOAD-SERVER-META-FILESIZE: 0" \
                    -H "X-INFOSIGHT-UPLOAD-SERVER-META-SN: {upload_random_number}" --noproxy "*"'
                output_stream = subprocess.Popen(curl_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, err = output_stream.communicate()
                err = str(err)
                p_status = output_stream.wait()
                for line in err.split("\n"):
                    if "HTTP/1.1 200 OK" in line:
                        print(
                            "********************************************************************************************"
                        )
                        print(f"* {root}/{ordered_gzfile} UPLOAD COMPLETED SUCCESSFULLY")
                        print(
                            "********************************************************************************************"
                        )
                    else:
                        print("********************************************************************************")
                        print(f"* {root}/{ordered_gzfile} FILE UPLOAD FAILED")
                        print("********************************************************************************")
                        print(line)
            print(datetime.now())
            if upload_flag == 100:
                print("One Month data upload completed")
                time.sleep(3700)
                upload_flag = 0
        shutil.rmtree(f"/tmp/{self.mock_folder}")

    def find_date_range(self, start_date, end_date):
        date_format = "%Y-%m-%dT%H:%M:%S.%fZ"
        converted_start_date = datetime.strptime(start_date, date_format)
        converted_end_date = datetime.strptime(end_date, date_format)
        # converted_start_date = datetime.strptime(start_date.split(" ")[0], "%Y-%m-%d")
        # converted_end_date = datetime.strptime(end_date.split(" ")[0], "%Y-%m-%d")
        return (converted_end_date - converted_start_date).days

    def spark_total_cust_size(self):
        self.load_spark_module_obj()
        # pd_data_frame = pd.json_normalize(self.context.mock_inventory_data)
        # convert_dict = {
        #    "storagesystotalused": int,
        #    "arrtotalused": int,
        #    "arrusablecapacity": int,
        #    "storagesysusablecapacity": int,
        # }
        # pd_data_frame = pd_data_frame.astype(convert_dict)
        max_start_time = self.context.mock_sys_lastcoll["collectionstarttime"].max()

        self.spark_sys_size_data_frame = self.spark.createDataFrame(self.context.mock_sys_lastcoll)
        total_cust_size_df = (
            self.spark_sys_size_data_frame.select("collectionstarttime", "arrusablecapacity")
            .where(f"collectionstarttime == '{max_start_time}'")
            .agg(sum("arrusablecapacity").alias("totalcutsize"))
        )
        return int(total_cust_size_df.collect()[0][0])

    def spark_vol_consumption(self):
        volusage_last_df = self.context.mock_vol_usage_lastcoll
        volusage_lastcoll_dict = self._vol_consumption_info(volusage_last_df)
        logger.debug(volusage_lastcoll_dict)

        sys_df = self.spark_system_cost
        cumulative_cost = self._calculate_overall_volconsumption_cost(volusage_last_df, sys_df)
        logger.debug(cumulative_cost)

        volusage_allcoll_df = self.context.mock_vol_allcoll
        vol_utilbytes_dict = self._get_volconsumption_utilizedbytes(volusage_allcoll_df)

        current_month_agg_usage_cost, prev_month_agg_usage_cost = self._get_volconsumption_cost(volusage_allcoll_df)

        logger.info(f"Current month cost : {current_month_agg_usage_cost}")
        logger.info(f"Previous month cost : {prev_month_agg_usage_cost}")

        volconsumption_dict = {
            "currentMonthUtilizedSizeInBytes": vol_utilbytes_dict["current_month"],
            "previousMonthUtilizedSizeInBytes": vol_utilbytes_dict["previous_month"],
            "customerId": vol_utilbytes_dict["customer_id"],
            "previousMonthCost": prev_month_agg_usage_cost,
            "currentMonthCost": current_month_agg_usage_cost,
            "cost": cumulative_cost,
            "numVolumes": volusage_last_df.shape[0],
            "totalSizeInBytes": volusage_last_df["volumesize_bytes"].sum(),
            "utilizedSizeInBytes": volusage_last_df["usedsize_bytes"].sum(),
        }
        logger.debug(volconsumption_dict)
        return volconsumption_dict

    def _get_volconsumption_cost(self, volusage_allcoll_df):
        """
        Summary: Get current month and previous month utlilization Cost
        """
        volusage_cost = self._calculate_volusage_monthly_cost(volusage_allcoll_df)

        current_month_agg_usage_cost = 0
        prev_month_agg_usage_cost = 0

        current_mon = self._get_current_month()
        df = volusage_cost[volusage_cost["collectionstarttime"] == current_mon]
        if not df.empty:
            current_month_agg_usage_cost = df["agg_usage_cost"].values[0]

        prev_mon = self._get_previous_month()
        df = volusage_cost[volusage_cost["collectionstarttime"] == prev_mon]
        if not df.empty:
            prev_month_agg_usage_cost = df["agg_usage_cost"].values[0]

        return current_month_agg_usage_cost, prev_month_agg_usage_cost

    def _get_volconsumption_utilizedbytes(self, volusage_allcoll_df) -> dict:
        """Get current and previous month all volume utilized bytes

        Args:
            volusage_allcoll_df (pd.DataFrame): Volume usage all collection dataframe

        Returns:
            dict: Current+month and previous month utilized bytes with the customer id
        """
        vol_consumption_df = self._volconsumption_monthly(volusage_allcoll_df)

        current_mon_utilbytes = self._vol_consumption_current_month(vol_consumption_df)

        prev_month_util_bytes = self._vol_consumption_prev_month(vol_consumption_df)
        return {
            "current_month": current_mon_utilbytes,
            "previous_month": prev_month_util_bytes,
            "customer_id": vol_consumption_df.iloc[0]["customer_id"],
        }

    def _vol_consumption_prev_month(self, vol_consumption_df):
        prev_mon = self._get_previous_month()
        prev_month_df = vol_consumption_df[vol_consumption_df["collectionstarttime"] == prev_mon]
        if not prev_month_df.empty:
            prev_month_utilized_bytes = prev_month_df["agg_utilized_size_bytes"].values[0]
        else:
            prev_month_utilized_bytes = 0
        return prev_month_utilized_bytes

    def _get_previous_month(self):
        prev_mon = (pd.Timestamp.today() - pd.offsets.MonthEnd(1)).strftime("%Y-%m")
        return prev_mon

    def _vol_consumption_current_month(self, vol_consumption_df):
        current_mon = self._get_current_month()
        current_month_df = vol_consumption_df[vol_consumption_df["collectionstarttime"] == current_mon]
        if not current_month_df.empty:
            current_month_utilized_bytes = current_month_df["agg_utilized_size_bytes"].values[0]
        else:
            current_month_utilized_bytes = 0
        return current_month_utilized_bytes

    def _get_current_month(self):
        current_mon = pd.Timestamp.today().strftime("%Y-%m")
        return current_mon

    def _calculate_volusage_monthly_cost(self, vol_usage_data):
        """calculate the utilized size systemwise and then calculate usage_cost.
        Each system will have different per gb cost so have to fetch systemwise usage cost

        Args:
            vol_usage_data (pd.DataFrame): Volume usage all collection

        Returns:
            (pd.DataFrame) : Dataframe with usage_cost
        """
        volusage_df = (
            vol_usage_data.groupby(
                [pd.PeriodIndex(vol_usage_data["collectionstarttime"], freq="M"), "custid", "storagesysid"]
            )
            .agg(
                total_volusedsize_bytes=("usedsize_bytes", "sum"),
                num_coll_per_month=("collectionname", "nunique"),
                customer_id=("custid", "first"),
            )
            .reset_index()
        )

        volusage_df["agg_volusedsize_gib"] = (
            volusage_df["total_volusedsize_bytes"] / volusage_df["num_coll_per_month"]
        ) / (1024**3)

        sys_df = self.spark_system_cost

        volusage_df.rename(columns={"storagesysid": "system_id"}, inplace=True)
        consump_df = pd.merge(volusage_df, sys_df[["system_id", "per_gb_cost"]], on="system_id")
        consump_df["usage_cost"] = consump_df["agg_volusedsize_gib"] * consump_df["per_gb_cost"]
        df = (
            consump_df.groupby(["collectionstarttime", "custid"])
            .agg(agg_usage_cost=("usage_cost", "sum"))
            .reset_index()
        )
        return df

    def _volconsumption_monthly(self, volusage_allcoll_df):
        """Overall volume consumption for monthly. It will add agg_utlilized bytes per month

        Args:
            volusage_allcoll_df (_type_): _description_

        Returns:
            _type_: _description_
        """
        vol_consumption_df = volusage_allcoll_df.groupby(
            [pd.PeriodIndex(volusage_allcoll_df["collectionstarttime"], freq="M"), "custid"]
        ).agg(
            total_volusedsize_bytes=("usedsize_bytes", "sum"),
            num_coll_per_month=("collectionname", "nunique"),
            customer_id=("custid", "first"),
        )
        # total used size bytes will be available for each collection. So aggregate it by num of collection
        vol_consumption_df["agg_utilized_size_bytes"] = (
            vol_consumption_df["total_volusedsize_bytes"] / vol_consumption_df["num_coll_per_month"]
        ).astype(int)
        vol_consumption_df = vol_consumption_df.reset_index()
        return vol_consumption_df

    def _calculate_overall_volconsumption_cost(self, volusage_last_df, sys_df):
        volusage_sys = (
            volusage_last_df.groupby("storagesysid").agg(vol_used_size=("usedsize_bytes", "sum")).reset_index()
        )
        volusage_sys.rename(columns={"storagesysid": "system_id"}, inplace=True)
        volusage_sys_cost = pd.merge(volusage_sys, sys_df[["per_gb_cost", "system_id"]], on="system_id")
        volusage_sys_cost["usage_cost"] = (
            volusage_sys_cost["vol_used_size"] / (1024**3) * volusage_sys_cost["per_gb_cost"]
        )
        cost = volusage_sys_cost["usage_cost"].sum()
        return cost

    def _vol_consumption_info(self, volusage_last_df):
        vol_lastcoll_data = pd.DataFrame()
        vol_lastcoll_data["num_Volumes"] = [volusage_last_df.shape[0]]
        vol_lastcoll_data["vol_total_size_in_bytes"] = [volusage_last_df["volumesize_bytes"].sum()]
        vol_lastcoll_data["vol_used_size_in_bytes"] = [volusage_last_df["usedsize_bytes"].sum()]
        vol_lastcoll_dict = vol_lastcoll_data.to_dict("records")[0]
        return vol_lastcoll_dict

    def spark_vol_cost_trend(self, **params):
        self.load_spark_module_obj()
        start_date = params["start_date"]
        end_date = params["end_date"]

        volusage_allcoll_df = self.context.mock_vol_allcoll
        volusage_cost = self._calculate_volusage_monthly_cost(volusage_allcoll_df)
        volusage_cost["collectionstarttime"] = volusage_cost["collectionstarttime"].astype(str) + "-01"
        volcost_trens_df = volusage_cost[
            (volusage_cost["collectionstarttime"] > start_date) & (volusage_cost["collectionstarttime"] <= end_date)
        ]
        volcost_trens_df["agg_usage_cost"] = volcost_trens_df["agg_usage_cost"] 
        

        converted_dict = volcost_trens_df.to_json(orient="table")
        json1_data = json.loads(converted_dict)
        return json1_data

    def spark_vol_usage_trend(self, **params):
        self.load_spark_module_obj()
        start_date = params["start_date"]
        end_date = params["end_date"]
        granularity = params["granularity"]

        # if granularity == 0:
        #     differance = self.find_date_range(start_date, end_date)
        #     if differance <= 7:
        #         granularity = "collectionHour"
        #     elif differance > 7 and differance <= 180:
        #         granularity = "daily"
        #     else:
        #         granularity = "weekly"
        if granularity == 0:
            differance = self.find_date_range(start_date, end_date)
            if differance <= 7:
                granularity = "collectionHour"
            elif differance > 7 and differance <= 180:
                granularity = "daily"
                starttime_object = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                start_hour_number = starttime_object.hour
                endtime_object = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                end_hour_number = endtime_object.hour
                if start_hour_number > 0:
                    start_date = starttime_object + timedelta(days=1)
                    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                if end_hour_number > 0:
                    end_date = endtime_object.replace(hour=20, minute=0, second=0, microsecond=0)
            else:
                granularity = "weekly"
                starttime_object = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                next_monday = starttime_object + relativedelta(weekday=MO)
                start_date = next_monday.date()
                endtime_object = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S.%fZ")
                previous_monday = endtime_object - relativedelta(weeks=1, weekday=MO)
                end_date = previous_monday.date()

        self.vol_data_frame = self.context.mock_vol_allcoll

        vol_usage_df = self.vol_data_frame

        vol_allcoll = self.vol_data_frame
        vol_in_time_range = vol_allcoll[
            (vol_allcoll["collectionstarttime"] >= start_date) & (vol_allcoll["collectionstarttime"] <= end_date)
        ]

        if granularity == Granularity.hourly.value:
            collection_hour_avg = vol_usage_df[
                (vol_usage_df["collectionendtime"] >= start_date) & (vol_usage_df["collectionendtime"] < end_date)
            ]
            collection_hour_df = (
                collection_hour_avg.groupby(["collectionstarttime", "collectionendtime", "custid"])
                .sum("usedsize_bytes")
                .reset_index()
            )

            # API response comes in descending order so sort descending it.
            sorted_df = collection_hour_df.sort_values(by=["collectionendtime"], ascending=True).reset_index()
            converted_dict = sorted_df.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity

        elif granularity == Granularity.daily.value:
            daily_avg = (
                vol_in_time_range.groupby(
                    [pd.PeriodIndex(vol_in_time_range["collectionendtime"], freq="D"), "collectionname", "custid"]
                )
                .agg({"usedsize_bytes": "sum"})
                .reset_index()
                .rename(columns={"collectionendtime": "collectiontime"})
            )
            day_avg = daily_avg.groupby(["collectiontime", "custid"]).agg({"usedsize_bytes": "mean"}).reset_index()
            day_avg["usedsize_bytes"] = day_avg["usedsize_bytes"].astype("int64")

            converted_dict = day_avg.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity
        elif granularity == Granularity.weekly.value:
            vol_in_time_range["collection_date"] = pd.to_datetime(vol_in_time_range["collectionstarttime"]).dt.date
            week_avg = (
                vol_in_time_range.groupby(
                    [pd.PeriodIndex(vol_in_time_range["collectionendtime"], freq="W"), "collectionname", "custid"]
                )
                .agg({"usedsize_bytes": "sum"})
                .reset_index()
                .rename(columns={"collectionendtime": "collectiontime"})
            )
            week_average = week_avg.groupby(["collectiontime", "custid"]).agg({"usedsize_bytes": "mean"}).reset_index()
            week_average["usedsize_bytes"] = week_average["usedsize_bytes"].astype("int64")

            # pandas_data_frame = result_df.toPandas()
            converted_dict = week_average.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            # weekly_df.show()
            return json1_data, granularity

    def spark_vol_creation_trend(self, **params):
        start_date = params["start_date"]
        end_date = params["end_date"]
        granularity = params["granularity"]

        

        vol_latest_coll = self.context.mock_vol_lastcoll
        vol_all_coll = self.context.mock_vol_allcoll
        
        first_coll_start_time = vol_all_coll[vol_all_coll["collectionname"] =="collection-1"]["collectionstarttime"].values[0]
        # Min creation time allowed is created 8 hrs before first collection time
        min_creation_time = first_coll_start_time - pd.Timedelta(hours=8)

        # remove UTC string from creationTime
        vol_latest_coll["creation_time"] = pd.to_datetime(vol_latest_coll["creationTime"].str.replace(".000000 \+0000 UTC",""))
        vol_latest_coll["creation_date"] = vol_latest_coll["creation_time"].dt.date
        # Pick the volumes created since 8 hr before first collection
        vol_created_df = vol_latest_coll[vol_latest_coll["creation_time"] > min_creation_time]
        vol_created_df = vol_created_df[(vol_created_df["creation_time"] >= start_date) & (vol_created_df["creation_time"] <=end_date)]
       

        if granularity == Granularity.hourly.value:
            creation_trend = self._vol_creation_trend_collectionhour(start_date, end_date, vol_all_coll)
            json1_data = json.loads(creation_trend)
            return json1_data, granularity
        elif granularity == Granularity.daily.value:
            
            creation_trend_day_df = self._vol_creation_trend_day(vol_created_df)
            creation_trend: dict = creation_trend_day_df.to_json(orient="table")
            json1_data = json.loads(creation_trend)
            return json1_data, granularity
        elif granularity == Granularity.weekly.value:
            
            creation_trend_week_df = self._vol_creation_trend_week(vol_created_df)
            creation_trend: dict = creation_trend_week_df.to_json(orient="table")
            json1_data = json.loads(creation_trend)
            return json1_data, granularity

    def _vol_creation_trend_collectionhour(self, start_date, end_date, vol_all_coll: pd.DataFrame)-> dict:
        """  Steps:
            Get each collection from start time and end time
            Find the volumes newly added in the collection
                Volume creation date should be greater than 8 hr from current collection end time
            For each collection add the newly created count

        Args:
            start_date (_type_): _description_
            end_date (_type_): _description_
            vol_all_coll (_type_): all volumes in all collection

        Returns:
            _type_: _description_
        """
        vol_in_time_range = vol_all_coll[(vol_all_coll["collectionendtime"] >= start_date ) & (vol_all_coll["collectionendtime"] <= end_date)]
        vol_in_time_range["aggrWindowTimestamp"] = vol_in_time_range["collectionstarttime"] - pd.Timedelta(hours=8)
        vol_count_each_collection = (
                vol_in_time_range.groupby(["collectionendtime", "custid","aggrWindowTimestamp"])
                .agg(volumecount=("volumeId", "count"), vol_list=("name", list))
                .reset_index()
            )

        vol_created_newly = vol_in_time_range[
                    (vol_in_time_range["creationTime"] >= vol_in_time_range["aggrWindowTimestamp"])
            ]         
        new_volcreated_count = (
                vol_created_newly.groupby(["collectionendtime", "custid","aggrWindowTimestamp"])
                .agg(newvolumes_created=("volumeId", "count"), vol_list=("name", list))
                .reset_index()
            )
            # Merge the newly created volume count in each collectionhour
        coll_hour_df = pd.merge(vol_count_each_collection,new_volcreated_count[["collectionendtime","custid","newvolumes_created","aggrWindowTimestamp"]],how="left")
        coll_hour_df["newvolumes_created"].fillna(0,inplace=True) # if no volumes created in a collection it will be NaN. Modify it to 0 instead of NaN

        creation_trend :dict = coll_hour_df.to_json(orient="table")
        return creation_trend

    def _vol_creation_trend_week(self, vol_df):
        """Volume creation trend weekly granularity

        Args:
            vol_df (_type_): _description_

        Returns:
            _type_: _description_
        """
        vol_df["week_start_date"] = (
                vol_df["creation_time"].dt.to_period("W").dt.start_time
            )

        creation_trend_week_df = (
                vol_df.groupby(["week_start_date", "custid"])
                .agg(volumecount=("volumeId", "count"), vol_list=("name", list))
                .reset_index()
            )

        creation_trend_week_df["updatedAt"] = pd.to_datetime(creation_trend_week_df["week_start_date"]).dt.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        
        return creation_trend_week_df

    def _vol_creation_trend_day(self, vol_df):
        """Vol creation trend day granularity

        Args:
            vol_df (_type_): _description_

        Returns:
            _type_: _description_
        """
        # vol_df = vol_latest_coll[vol_latest_coll["creation_time"] > min_creation_time]
        creation_trend_day_df = (
                vol_df.groupby(["creation_date", "custid"])
                .agg(volumecount=("volumeId", "count"), vol_list=("name", list))
                .reset_index()
            )

        creation_trend_day_df["updatedAt"] = pd.to_datetime(creation_trend_day_df["creation_date"]).dt.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        
        return creation_trend_day_df

    def spark_vol_activity_trend(self, **params):
        self.load_spark_module_obj()
        self.vol_data_frame = self.context.mock_vol_allcoll
        # pd_data_frame = pd.json_normalize(self.vol_data_frame)
        # convert_dict = {"volumeId": str, "custid": str, "provisiontype": str}
        # pd_data_frame = pd_data_frame.astype(convert_dict)
        self.spark_vol_data_frame = self.spark.createDataFrame(self.vol_data_frame)

        get_max_values = self.spark_vol_data_frame.select("volumesize_bytes", "avgiops").agg(
            max("volumesize_bytes").alias("maxvolsize"), max("avgiops").alias("maxio")
        )

        pro_type = "" if not params["provisiontype"] else params["provisiontype"]
        min_vol_size = 0 if not params["min_vol_size"] else params["min_vol_size"]
        max_vol_size = (
            get_max_values.select("maxvolsize").rdd.flatMap(list).collect()[0] + 1
            if not params["max_vol_size"]
            else params["max_vol_size"]
        )
        min_io = 0 if not params["min_io"] else params["min_io"]
        max_io = (
            get_max_values.select("maxio").rdd.flatMap(list).collect()[0] + 1
            if not params["max_io"]
            else params["max_io"]
        )

        collection_end_time = self.vol_data_frame["collectionendtime"].max()
        if pro_type:
            # Adding column month for avg, changing collection start date to every month first
            convert_date_month = self.spark_vol_data_frame.select(
                "collectionstarttime",
                "volumeId",
                "name",
                "provisiontype",
                "volumesize_bytes",
                "usedsize_bytes",
                "creationTime",
                month("collectionstarttime").alias("month"),
                year("collectionstarttime").alias("year"),
                round(months_between(current_date(), "creationTime")).alias("age"),
                "arrid",
                "avgiops",
                "utilizedPercentage"
            )

            # Generating monthly average
            monthly_avg_info = convert_date_month.groupBy("volumeId", "month", "year").agg(
                avg("avgiops").alias("ioactivity"),
            )

            # Adding startdate and ioactivity as list
            activity_trend_info = monthly_avg_info.groupBy("volumeId").agg(
                collect_list(struct("year", "month", "ioactivity")).alias("activitytrendinfo")
            )

            # get the latest vol activity data based on collection end time
            latest_vol_activity_data = self.spark_vol_data_frame.select(
                "collectionstarttime",
                "volumeId",
                "custid",
                "name",
                "provisiontype",
                "volumesize_bytes",
                "usedsize_bytes",
                "creationTime",
                year("collectionstarttime").alias("year"),
                round(months_between(current_date(), "creationTime")).alias("age"),
                "arrid",
                "avgiops",
                "storagesysid",
                "system_name",
                "utilizedPercentage"
            ).where(
                f"collectionendtime == '{collection_end_time}' and provisiontype == '{pro_type}' and volumesize_bytes >= '{min_vol_size}' and volumesize_bytes <= '{max_vol_size}' and avgiops >= '{min_io}' and avgiops < '{max_io}'"
            )
            # latest_vol_activity_data.show(400)
            # join the latest collection data and avg avgiops collection data to a single dataframe.
            act_trend_info_final = latest_vol_activity_data.join(
                activity_trend_info,
                activity_trend_info.volumeId == latest_vol_activity_data.volumeId,
                "inner",
            ).drop(latest_vol_activity_data.volumeId)

            pandas_data_frame = act_trend_info_final.toPandas()
            converted_dict = pandas_data_frame.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data
        else:
            # Adding column month for avg, changing collection start date to every month first
            convert_date_month = self.spark_vol_data_frame.select(
                "collectionstarttime",
                "volumeId",
                "name",
                "provisiontype",
                "volumesize_bytes",
                "usedsize_bytes",
                "creationTime",
                month("collectionstarttime").alias("month"),
                year("collectionstarttime").alias("year"),
                round(months_between(current_date(), "creationTime")).alias("age"),
                "arrid",
                "avgiops",
                "utilizedPercentage"
            )

            # Generating monthly average
            monthly_avg_info = convert_date_month.groupBy("volumeId", "month", "year").agg(
                avg("avgiops").alias("ioactivity"),
            )
            # Adding startdate and ioactivity as list
            activity_trend_info = monthly_avg_info.groupBy("volumeId").agg(
                collect_list(struct("year", "month", "ioactivity")).alias("activitytrendinfo")
            )

            # get the latest vol activity data based on collection end time

            latest_vol_activity_data = self.spark_vol_data_frame.select(
                "collectionstarttime",
                "volumeId",
                "custid",
                "name",
                "provisiontype",
                "volumesize_bytes",
                "usedsize_bytes",
                "creationTime",
                year("collectionstarttime").alias("year"),
                round(months_between(current_date(), "creationTime")).alias("age"),
                "arrid",
                "avgiops",
                "storagesysid",
                "system_name",
                "utilizedPercentage"
            ).where(
                f"collectionendtime == '{collection_end_time}' and volumesize_bytes >= '{min_vol_size}' and volumesize_bytes <= '{max_vol_size}' and avgiops >= '{min_io}' and avgiops < '{max_io}'"
            )
            # latest_vol_activity_data.show(400)
            # join the latest collection data and avg avgiops collection data to a single dataframe.
            act_trend_info_final = latest_vol_activity_data.join(
                activity_trend_info,
                activity_trend_info.volumeId == latest_vol_activity_data.volumeId,
                "inner",
            ).drop(latest_vol_activity_data.volumeId)

            pandas_data_frame = act_trend_info_final.toPandas()
            converted_dict = pandas_data_frame.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data

    def spark_vol_activity_trend_by_io(self, **params) -> dict:
        pro_type = "" if not params["provisiontype"] else params["provisiontype"]
        min_io = 10 if not params["min_io"] else params["min_io"]
        max_io = 100 if not params["max_io"] else params["max_io"]

        volusage_last_collection_df = self.context.mock_vol_usage_lastcoll
        vol_all_collection_df = self.context.mock_vol_allcoll
        system_collection_data = self.context.mock_sys_lastcoll

        vol_last_df = volusage_last_collection_df
        vol_df_by_prov_type: pd.DataFrame = vol_last_df[(vol_last_df["provisiontype"] == pro_type)]
        vol_df = vol_df_by_prov_type[
            [
                "volumeId",
                "name",
                "provisiontype",
                "volumesize_bytes",
                "usedsize_bytes",
                "creationTime",
                "avgiops",
                "storagesysid",
                "custid",
                "collectionstarttime",
                "utilizedPercentage"
            ]
        ]

        vol_ioactivity: dict = {"items": []}
        # Get the volumes last 7 days average Iops which is between min_io and max_io
        for index, row in vol_df.iterrows():
            vol_activity_df = vol_all_collection_df[
                (vol_all_collection_df["provisiontype"] == pro_type)
                & (vol_all_collection_df["volumeId"] == row["volumeId"])
            ]
            # Get last 7 days of data frame excluding today
            daily_volperf = (
                vol_activity_df.groupby(
                    [pd.PeriodIndex(vol_activity_df["collectionstarttime"], freq="D"), "custid", "volumeId"]
                )
                .agg({"avgiops": "last"})
                .reset_index()
            )
            daily_volperf["collectionstarttime"] = daily_volperf["collectionstarttime"].astype(np.datetime64)
            # vol_df = self._get_daily_volperf(daily_volperf)
            # print(vol_df)
            last_7days_avg_iops = self.calculate_last7days_avgiops(daily_volperf)
            # last_7days_avg_iops = last_7days_df["avgiops"].mean()

            if last_7days_avg_iops > min_io and last_7days_avg_iops < max_io:
                temp_dict = {}
                temp_dict = row.to_dict()

                temp_dict["last7days_avgiops"] = last_7days_avg_iops
                # calculate monthly ioaverage
                monthly_average = daily_volperf.groupby(
                    [pd.PeriodIndex(daily_volperf["collectionstarttime"], freq="M"), "custid", "volumeId"]
                ).agg(
                    {"avgiops": "mean"},
                )
                # monthly_average = daily_avg.groupby(pd.PeriodIndex(daily_avg["collectionstarttime"], freq="M"))[
                #     "avgiops"
                # ].mean()
                monthly_ioactivity = monthly_average.reset_index()
                date_time = pd.to_datetime(monthly_ioactivity["collectionstarttime"].astype(str))
                timestamp_list = date_time.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                vol_last_df = pd.DataFrame({"timeStamp": timestamp_list, "ioActivity": monthly_ioactivity["avgiops"]})
                monthly_activity_trend = vol_last_df.to_dict("records")
                temp_dict["activityTrendInfo"] = monthly_activity_trend

                # system name
                system = system_collection_data["storagesysname"][
                    (system_collection_data["storagesysid"] == row["storagesysid"])
                ].drop_duplicates()
                # system_name = system["storagesysname"].drop_duplicates()
                temp_dict["system"] = system.squeeze()

                vol_ioactivity["items"].append(temp_dict)

        return vol_ioactivity, vol_df_by_prov_type

    def spark_vol_activity_trend_by_size(self, **params) -> dict:
        pro_type = "" if not params["provisiontype"] else params["provisiontype"]
        min_vol_size = 1000000000 if not params["min_vol_size"] else params["min_vol_size"]
        max_vol_size = 2000000000 if not params["max_vol_size"] else params["max_vol_size"]

        vol_last_collection_data = self.context.mock_vol_usage_lastcoll
        vol_all_collection_data = self.context.mock_vol_allcoll
        system_collection_data = self.context.mock_sys_lastcoll

        vol_last_df = vol_last_collection_data
        filtered_vol_activity: pd.DataFrame = vol_last_df[
            (vol_last_df["provisiontype"] == pro_type)
            & (vol_last_df["usedsize_bytes"] > min_vol_size)
            & (vol_last_df["usedsize_bytes"] < max_vol_size)
        ]
        vol_df = filtered_vol_activity[
            [
                "volumeId",
                "name",
                "provisiontype",
                "volumesize_bytes",
                "usedsize_bytes",
                "creationTime",
                "avgiops",
                "storagesysid",
                "custid",
                "collectionstarttime",
                "utilizedPercentage"
            ]
        ]
        vol_ioactivity: dict = {"items": []}

        for index, row in vol_df.iterrows():
            temp_dict = {}
            temp_dict = row.to_dict()
            vol_activity_df = vol_all_collection_data[
                (vol_all_collection_data["provisiontype"] == pro_type)
                & (vol_all_collection_data["volumeId"] == row["volumeId"])
            ]
            # calculate monthly ioaverage
            daily_avg = vol_activity_df.groupby(
                [pd.PeriodIndex(vol_activity_df["collectionstarttime"], freq="D"), "custid"]
            ).agg(
                {"avgiops": "last", "volumeId": "first", "collectionstarttime": "first"},
            )
            monthly_average = daily_avg.groupby(pd.PeriodIndex(daily_avg["collectionstarttime"], freq="M"))[
                "avgiops"
            ].mean()
            monthly_ioactivity = monthly_average.reset_index()
            date_time = pd.to_datetime(monthly_ioactivity["collectionstarttime"].astype(str))
            timestamp_list = date_time.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            vol_last_df = pd.DataFrame({"timeStamp": timestamp_list, "ioActivity": monthly_ioactivity["avgiops"]})
            monthly_activity_trend = vol_last_df.to_dict("records")
            temp_dict["activityTrendInfo"] = monthly_activity_trend
            # Get last 7 days of data frame excluding today
            last_7days_avgiops = self.calculate_last7days_avgiops(daily_avg)

            temp_dict["last7days_avgiops"] = last_7days_avgiops
            # system name
            system = system_collection_data["storagesysname"][
                (system_collection_data["storagesysid"] == row["storagesysid"])
            ].drop_duplicates()
            # system_name = system["storagesysname"].drop_duplicates()
            temp_dict["system"] = system.squeeze()

            vol_ioactivity["items"].append(temp_dict)

        return vol_ioactivity

    def calculate_last7days_avgiops(self, vol_activity_df):
        today = (datetime.utcnow()).date()
        last_7days = today - timedelta(days=7)
        last_7days_df = vol_activity_df[
            (vol_activity_df["collectionstarttime"] >= pd.to_datetime(last_7days))
            & (vol_activity_df["collectionstarttime"] < pd.to_datetime(today))
        ]
        last_7days_aviops_df = last_7days_df.groupby(["custid", "volumeId"]).agg({"avgiops": "mean"}).reset_index()
        last_7days_aviops = -1
        if not last_7days_df.empty:
            last_7days_aviops = last_7days_aviops_df["avgiops"].values[0]
        return last_7days_aviops

    def spark_vol_uuid_usage_trend(self, **params):
        self.load_spark_module_obj()
        vol_uuid = params["vol_uuid"]
        self.vol_data_frame = self.context.mock_vol_allcoll

        # self.spark_vol_data_frame = self.create_spark_data_frame(self.vol_data_frame)
        # pd_data_frame = pd.json_normalize(self.vol_data_frame)
        # convert_dict = {"volumeId": str, "custid": str, "provisiontype": str}
        # pd_data_frame = pd_data_frame.astype(convert_dict)

        self.spark_clone_data_frame = self.spark.createDataFrame(self.vol_data_frame)

        self.spark_clone_data_frame.createOrReplaceTempView("tempviewdf")

        finaldf2 = self.spark_clone_data_frame.select(
            "collectionstarttime",
            "usedsize_bytes",
            "custid",
            "volumeId",
            "storagesysid",
            "volumesize_bytes",
            "creationTime",
            "provisiontype",
        ).where(f"volumeId == '{vol_uuid}'")
        maxtime = finaldf2.select("collectionstarttime").agg(max("collectionstarttime").alias("maxtime"))
        last_coll_start_time = maxtime.collect()[0][0]

        final_usage_trend_df = finaldf2.select(
            "collectionstarttime",
            "usedsize_bytes",
            "custid",
            "storagesysid",
            "volumeId",
            "volumesize_bytes",
            "creationTime",
            "provisiontype",
        ).where(f"collectionstarttime == '{last_coll_start_time}'")

        pandas_data_frame = final_usage_trend_df.toPandas()
        converted_dict = pandas_data_frame.to_json(orient="table")
        json1_data = json.loads(converted_dict)
        return json1_data

    def spark_vol_uuid_time_stamp_usage_trend(self, **params):
        self.load_spark_module_obj()
        start_date = params["start_date"]
        end_date = params["end_date"]
        granularity = params["granularity"]
        vol_uuid = params["vol_uuid"]
        system_id = params["system_id"]

        # if granularity == 0:
        #     differance = self.find_date_range(start_date, end_date)
        #     if differance <= 7:
        #         granularity = "collectionHour"
        #     elif differance > 7 and differance <= 180:
        #         granularity = "daily"
        #     else:
        #         granularity = "weekly"

        self.vol_data_frame = self.context.mock_vol_allcoll
        self.spark_clone_data_frame = self.spark.createDataFrame(self.vol_data_frame)
        self.spark_clone_data_frame.createOrReplaceTempView("tempviewdf")

        finaldf2 = self.spark_clone_data_frame.select(
            weekofyear("collectionendtime").alias("week"),
            dayofweek("collectionendtime").alias("weekday"),
            hour("collectionendtime").alias("hour"),
            dayofmonth("collectionendtime").alias("day"),
            to_date("collectionendtime").alias("collectiontime"),
            "collectionstarttime",
            "collectionendtime",
            "usedsize_bytes",
            "custid",
            "volumeId",
            "storagesysid",
            "collectionname",
        ).where(
            f"volumeId == '{vol_uuid}' and storagesysid == '{system_id}' and collectionendtime >= '{start_date}' and collectionendtime < '{end_date}'"
        )
        vol_allcoll = self.vol_data_frame
        vol_in_time_range = vol_allcoll[
            (vol_allcoll["volumeId"] == vol_uuid)
            & (vol_allcoll["storagesysid"] == system_id)
            & (vol_allcoll["collectionendtime"] >= start_date)
            & (vol_allcoll["collectionendtime"] <= end_date)
        ]

        if granularity == Granularity.hourly.value:
            hourly_df = finaldf2.groupBy("collectionendtime", "custid").agg(
                sum("usedsize_bytes").alias("totalusedsize")
            )

            sorted_df = hourly_df.orderBy(desc("collectionendtime"))
            pandas_data_frame = sorted_df.toPandas()
            converted_dict = pandas_data_frame.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity

        elif granularity == Granularity.daily.value:
            vol_in_time_range["collection_date"] = pd.to_datetime(vol_in_time_range["collectionstarttime"]).dt.date
            day_avg = (
                vol_in_time_range.groupby(
                    [pd.PeriodIndex(vol_in_time_range["collectionendtime"], freq="D"), "collectionname", "custid"]
                )
                .agg({"usedsize_bytes": "sum"})
                .reset_index()
                .rename(columns={"collectionendtime": "collectiontime"})
            )
            day_average = day_avg.groupby(["collectiontime", "custid"]).agg({"usedsize_bytes": "mean"}).reset_index()
            day_average["usedsize_bytes"] = day_average["usedsize_bytes"].astype("int64")
            converted_dict = day_average.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity

        elif granularity == Granularity.weekly.value:
            vol_in_time_range["collection_date"] = pd.to_datetime(vol_in_time_range["collectionstarttime"]).dt.date
            week_avg = (
                vol_in_time_range.groupby(
                    [pd.PeriodIndex(vol_in_time_range["collectionendtime"], freq="W"), "collectionname", "custid"]
                )
                .agg({"usedsize_bytes": "sum"})
                .reset_index()
                .rename(columns={"collectionendtime": "collectiontime"})
            )
            week_average = week_avg.groupby(["collectiontime", "custid"]).agg({"usedsize_bytes": "mean"}).reset_index()
            week_average["usedsize_bytes"] = week_average["usedsize_bytes"].astype("int64")
            converted_dict = week_average.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity

    def spark_vol_uuid_io_trend(self, **params):
        start_date = params["start_date"]
        end_date = params["end_date"]
        granularity = params["granularity"]
        vol_uuid = params["vol_uuid"]
        volperf_df = self.context.mock_vol_perf_allcoll
        if granularity == Granularity.hourly.value:
            collection_hour_avg = volperf_df[
                (volperf_df["id"] == vol_uuid)
                & (volperf_df["collectionendtime"] >= start_date)
                & (volperf_df["collectionendtime"] < end_date)
            ]
            print(collection_hour_avg)

            # API response comes in descending order so sort descending it.
            sorted_df = collection_hour_avg.sort_values(by=["collectionstarttime"], ascending=False).reset_index()
            converted_dict = sorted_df.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity

        elif granularity == Granularity.daily.value:
            volperf_between_dates = volperf_df[
                (volperf_df["id"] == vol_uuid)
                & (volperf_df["collectionstarttime"] >= start_date)
                & (volperf_df["collectionstarttime"] < end_date)
            ]
            daily_volperf_df = self._get_daily_volperf(volperf_between_dates)
            print(daily_volperf_df)
            daily_volperf_df.rename(
                columns={"collectionstarttime": "collectiontime", "avgiops": "avg_io_trend"}, inplace=True
            )
            # API response comes in descending order so sort descending it.
            sorted_df = daily_volperf_df.sort_values(by=["collectiontime"], ascending=False).reset_index()
            converted_dict = sorted_df.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity

        elif granularity == Granularity.weekly.value:
            # Week start day will be normally on Monday.
            # Group by collection_week_start to do io trend calculation for that week
            volperf_between_dates = volperf_df[
                (volperf_df["id"] == vol_uuid)
                & (volperf_df["collectionendtime"] >= start_date)
                & (volperf_df["collectionendtime"] <= end_date)
            ]
            daily_df = self._get_daily_volperf(volperf_between_dates)
            # From daily volperf df calculate weekly avgiops
            weekly_avg = (
                daily_df.groupby([pd.PeriodIndex(daily_df["collectionstarttime"], freq="W"), "custid"])
                .agg({"avgiops": "mean", "id": "first"})
                .reset_index()
                .rename(columns={"collectionstarttime": "collectiontime"})
            )

            weekly_df = weekly_avg[
                (weekly_avg["id"] == vol_uuid)
                & (weekly_avg["collectiontime"] >= start_date)
                & (weekly_avg["collectiontime"] <= end_date)
            ]
            print(weekly_df)

            # API response comes in descending order so sort descending it.
            sorted_df = weekly_df.sort_values(by=["collectiontime"], ascending=False).reset_index()
            converted_dict = weekly_df.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity

    def _get_daily_volperf(self, volperf_df):
        # As avg iops is for last 24 hours. We can fetch the last avgiops value of a day to avgiops
        daily_volperf = (
            volperf_df.groupby([pd.PeriodIndex(volperf_df["collectionstarttime"], freq="D"), "custid"])
            .agg({"avgiops": "last", "id": "first"})
            .reset_index()
        )
        daily_volperf["collectionstarttime"] = daily_volperf["collectionstarttime"].astype(np.datetime64)

        return daily_volperf

    def _get_daily_clone_iops(self, clone: pd.DataFrame) -> pd.DataFrame:
        # As avg iops is for last 24 hours. We can fetch the last avgiops value of a day to avgiops
        daily_iops = (
            clone.groupby([pd.PeriodIndex(clone["collectionstarttime"], freq="D"), "custid"])
            .agg({"avgiops": "last", "cloneid": "first"})
            .reset_index()
        )
        daily_iops["collectionstarttime"] = daily_iops["collectionstarttime"].astype(np.datetime64)
        # daily_iops.rename(columns={"avg_iops": "avgiops"}, inplace=True)

        return daily_iops

    def spark_clone_io_trend(self, **params):
        start_date = params["start_date"]
        end_date = params["end_date"]
        granularity = params["granularity"]
        clone_id = params["vol_uuid"]
        clone_all_df = self.context.mock_clone_allcoll
        if granularity == Granularity.hourly.value:
            collection_hour_avg = clone_all_df[
                (clone_all_df["cloneid"] == clone_id)
                & (clone_all_df["collectionendtime"] >= start_date)
                & (clone_all_df["collectionendtime"] < end_date)
            ]
            print(collection_hour_avg)

            # API response comes in descending order so sort descending it.
            sorted_df = collection_hour_avg.sort_values(by=["collectionstarttime"], ascending=False).reset_index()
            converted_dict = sorted_df.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity

        elif granularity == Granularity.daily.value:
            clone_between_dates = clone_all_df[
                (clone_all_df["cloneid"] == clone_id)
                & (clone_all_df["collectionstarttime"] >= start_date)
                & (clone_all_df["collectionstarttime"] < end_date)
            ]
            daily_clone_io: pd.DataFrame = self._get_daily_clone_iops(clone_between_dates)
            print(daily_clone_io)
            daily_clone_io.rename(
                columns={"collectionstarttime": "collectiontime", "avgiops": "avg_io_trend"}, inplace=True
            )
            # API response comes in descending order so sort descending it.
            sorted_df = daily_clone_io.sort_values(by=["collectiontime"], ascending=False).reset_index()
            converted_dict = sorted_df.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity

        elif granularity == Granularity.weekly.value:
            # Week start day will be normally on Monday.
            # Group by collection_week_start to do io trend calculation for that week
            clone_between_dates = clone_all_df[
                (clone_all_df["cloneid"] == clone_id)
                & (clone_all_df["collectionendtime"] >= start_date)
                & (clone_all_df["collectionendtime"] <= end_date)
            ]
            daily_df = self._get_daily_clone_iops(clone_between_dates)
            # From daily volperf df calculate weekly avgiops
            weekly_avg = (
                # [pd.PeriodIndex(daily_df["collectionstarttime"], freq="W"),"custid"]
                daily_df.groupby([pd.PeriodIndex(daily_df["collectionstarttime"], freq="W"), "custid"])
                .agg({"avgiops": "mean", "cloneid": "first"})
                .reset_index()
                .rename(columns={"collectionstarttime": "collectiontime"})
            )
            print(weekly_avg)

            # API response comes in descending order so sort descending it.
            sorted_df = weekly_avg.sort_values(by=["collectiontime"], ascending=False).reset_index()
            converted_dict = weekly_avg.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity

    def spark_vol_uuid_snap_data(self, **params):
        self.load_spark_module_obj()
        vol_uuid = params["vol_uuid"]
        start_date = params["start_date"]
        end_date = params["end_date"]
        granularity = params["granularity"]

        snap_data_frame = self.context.mock_snap_all
        filtered_snap_data_frame = snap_data_frame[
            (snap_data_frame["volume_id"] == vol_uuid)
            & (snap_data_frame["collection_end_date"] >= start_date)
            & (snap_data_frame["collection_end_date"] <= end_date)
        ]
        snap_df = filtered_snap_data_frame[
            (filtered_snap_data_frame["creation_time"] < filtered_snap_data_frame["collection_end_date"])
            & (
                filtered_snap_data_frame["creation_time"]
                >= filtered_snap_data_frame["collection_end_date"] - pd.Timedelta(hours=8)
            )
        ]
        snap_df_by_snapvalue = (
            snap_df.groupby(["collection_end_date", "snap_id", "snap_type", "volume_id", "customer_id"])
            .agg(numberofsnaps=("snap_type", "count"))
            .reset_index()
        )
        snap_df_by_snapvalue["numberofadhocsnaps"] = [
            row["numberofsnaps"] if row["snap_type"] == "adhoc" else 0 for index, row in snap_df_by_snapvalue.iterrows()
        ]
        snap_df_by_snapvalue["numberofperiodicsnaps"] = [
            row["numberofsnaps"] if row["snap_type"] == "periodic" else 0
            for index, row in snap_df_by_snapvalue.iterrows()
        ]
        if granularity == Granularity.hourly.value:
            hour_avg = snap_df_by_snapvalue
            hour_avg["collection_end_date"] = hour_avg["collection_end_date"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            converted_dict = hour_avg.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity
        elif granularity == Granularity.daily.value:
            day_avg = (
                snap_df_by_snapvalue.groupby(
                    [
                        pd.PeriodIndex(snap_df_by_snapvalue["collection_end_date"], freq="D"),
                        "customer_id",
                        "snap_type",
                        "volume_id",
                    ]
                )
                .agg(
                    adhoc_snap_count=("numberofadhocsnaps", "sum"), periodic_snap_count=("numberofperiodicsnaps", "sum")
                )
                .reset_index()
            )
            day_avg["collection_end_date"] = day_avg["collection_end_date"].dt.start_time.dt.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            converted_dict = day_avg.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity
        elif granularity == Granularity.weekly.value:
            week_avg = (
                snap_df_by_snapvalue.groupby(
                    [
                        pd.PeriodIndex(snap_df_by_snapvalue["collection_end_date"], freq="W"),
                        "customer_id",
                        "volume_id",
                    ]
                )
                .agg(
                    adhoc_snap_count=("numberofadhocsnaps", "sum"), periodic_snap_count=("numberofperiodicsnaps", "sum")
                )
                .reset_index()
            )
            week_avg["collection_end_date"] = week_avg["collection_end_date"].dt.start_time.dt.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            converted_dict = week_avg.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity

    def spark_vol_uuid_clone_data(self, **params):
        self.load_spark_module_obj()
        start_date = params["start_date"]
        end_date = params["end_date"]
        granularity = params["granularity"]
        vol_uuid = params["vol_uuid"]

        clone_data_frame = self.context.mock_clone_allcoll
        filtered_clone_data_frame = clone_data_frame[
            (clone_data_frame["cloneparentid"] == vol_uuid)
            & (clone_data_frame["clonecreationtime"] >= start_date)
            & (clone_data_frame["clonecreationtime"] <= end_date)
        ]
        clone_df = filtered_clone_data_frame[
            (filtered_clone_data_frame["clonecreationtime"] < filtered_clone_data_frame["collectionendtime"])
            & (
                filtered_clone_data_frame["clonecreationtime"]
                >= filtered_clone_data_frame["collectionendtime"] - pd.Timedelta(hours=8)
            )
        ]

        if granularity == Granularity.hourly.value:
            hourly_df = (
                clone_df.groupby(
                    [
                        "collectionendtime",
                        "custid",
                        # "cloneid",
                        "cloneparentid",
                    ]
                )
                .agg(clonesize=("clonesize", "sum"), numberofclones=("cloneparentid", "count"))
                .reset_index()
            )
            hourly_df["collectionendtime"] = hourly_df["collectionendtime"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            converted_dict = hourly_df.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity

        elif granularity == Granularity.daily.value:
            daily_df = (
                clone_df.groupby(
                    [
                        pd.PeriodIndex(clone_df["collectionendtime"], freq="D"),
                        "custid",
                        "cloneid",
                        "cloneparentid",
                    ]
                )
                .agg(clonesize=("clonesize", "sum"), numberofclones=("cloneparentid", "count"))
                .reset_index()
            )
            daily_df["collectionendtime"] = daily_df["collectionendtime"].dt.start_time.dt.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            converted_dict = daily_df.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity

        elif granularity == Granularity.weekly.value:
            weekly_df = (
                clone_df.groupby(
                    [
                        pd.PeriodIndex(clone_df["collectionendtime"], freq="W"),
                        "custid",
                        "cloneid",
                        "cloneparentid",
                    ]
                )
                .agg(clonesize=("clonesize", "sum"), numberofclones=("cloneparentid", "count"))
                .reset_index()
            )
            print(weekly_df)
            weekly_avg = weekly_df.drop_duplicates(subset=["cloneid"])
            weekly_avg["collectionendtime"] = weekly_avg["collectionendtime"].dt.start_time.dt.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            converted_dict = weekly_avg.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity

    def spark_snap_shot_consumption(self, **params):
        """This function execute spark query on mock/array data present in database and calculate the snapshot consumption

        Returns:
            dict: key/data pair fields represents the snapshot consumption
        """
        self.load_spark_module_obj()
        self.snap_data_frame = self.context.mock_snap_usage
        system_data = self.spark_system_cost
        system_data = self.spark.createDataFrame(system_data)
        self.snap_data_frame = self.spark.createDataFrame(self.snap_data_frame)
        self.snap_data_frame.createOrReplaceTempView("tempviewdf")

        # Selecting the required fields for calculating the snapshot consumption
        self.snap_data_frame = self.snap_data_frame.select(
            "collection_end_date",
            "collection_start_date",
            "collection_name",
            "snapsize_bytes",
            "volume_id",
            "system_id",
            "customer_id",
            "snap_id",
        )
        # Get last collection info
        collection_df = self.context.mock_collection_data
        unique_collection_list = collection_df["collection_name"].unique()
        latest_collection = unique_collection_list[-1]

        # Retrieve snapshots for last collection
        snapshot_last_collection = self.snap_data_frame[self.snap_data_frame["collection_name"] == latest_collection]

        # Counting total number of snapshots
        numSnapshots = snapshot_last_collection.select(count("snap_id")).collect()[0][0]

        # Get customer ID
        customer_id = snapshot_last_collection.select(first("customer_id")).collect()[0][0]

        # As snapsize_byte represent (mentioned as field inside volume dictionary in colsolidated json) is size of all snapshots, need to drop duplicate rows where one volume have multiple snapshots
        snap_size_df = self.snap_data_frame.dropDuplicates(["collection_end_date", "volume_id", "system_id"])
        snapshot_last_collection = snapshot_last_collection.dropDuplicates(
            ["collection_end_date", "volume_id", "system_id"]
        )

        # code to calculate the overall cost for all snapshots and total size for all snapshots

        cost, total_size_bytes = self.get_cost_total_snap_size_byte(system_data, snapshot_last_collection)

        # calculating the cost for current and previous month

        snap_size_df = snap_size_df.withColumn("month", date_format("collection_start_date", "yyyy-MM"))

        snapshot_monthly_snap_size = snap_size_df.groupby("month", "system_id", "customer_id").agg(
            sum("snapsize_bytes").alias("sum_of_snapsize_bytes"),
            (functions.countDistinct("collection_name").alias("count")),
        )

        # current month snapshot cost calculation
        month_value = pd.Timestamp.today().strftime("%Y-%m")
        current_month_cost = self.get_cost_for_month(system_data, snapshot_monthly_snap_size, month_value)

        # previous month snapshot cost calculation

        month_value = (pd.Timestamp.today() - pd.offsets.MonthEnd(1)).strftime("%Y-%m")

        previous_month_cost = self.get_cost_for_month(system_data, snapshot_monthly_snap_size, month_value)

        snapshot_consumption = {
            "num_of_Snapshots": numSnapshots,
            "total_size_bytes": total_size_bytes,
            "cost": cost,
            "current_month_cost": current_month_cost,
            "previous_month_cost": previous_month_cost,
            "previous_month_cost": previous_month_cost,
            "customer_id": customer_id,
        }

        return snapshot_consumption

    def get_cost_total_snap_size_byte(self, system_data, snapshot_last_collection):
        """This function calculate overall cost for all snapshots and total size of snapshots in bytes

        Args:
            system_data (data frame): data having system and cost info
            snapshot_last_collection (dataframe): data frame which have info of all snapshosts in last collection

        Returns:
            float(cost),int(total_size_bytes) : overall cost of snapshots size , snapshot size in bytes
        """
        snapshot_last_coll_sys_wise = snapshot_last_collection.groupby("system_id", "customer_id").agg(
            sum("snapsize_bytes").alias("total_sum_of_snaphots"),
        )

        snap_df = snapshot_last_coll_sys_wise.join(system_data.select("system_id", "per_gb_cost"), on=["system_id"])

        snap_df = snap_df.withColumn("snapsize_in_gb", (col("total_sum_of_snaphots") / (1024**3)))

        snap_df = snap_df.withColumn("cost_per_gb", (col("snapsize_in_gb") * col("per_gb_cost")))

        cost = snap_df.select(sum("cost_per_gb")).collect()[0][0]

        # Calculating the total size bytes for all snapshots
        total_size_bytes = snap_df.select(sum("total_sum_of_snaphots")).collect()[0][0]

        return cost, total_size_bytes

    def get_cost_for_month(self, system_data, snapshot_monthly_snap_size, month_value):
        """This function calculate the cost for given month

        Args:
            system_data (dataframe): data frame having system and cost info
            snapshot_monthly_snap_size (dataframe): snapshot dataframe which have month wise size of snapshots
            month_value (date): month for which cost needs to be calculated e.g "2023-07"

        Returns:
            float: cost of snapshots for month
        """
        current_month_snap_data = snapshot_monthly_snap_size.filter(snapshot_monthly_snap_size["month"] == month_value)
        if current_month_snap_data.count() > 0:
            current_month_snap_data = current_month_snap_data.withColumn(
                "avg_snapsize", (col("sum_of_snapsize_bytes") / col("count"))
            )
            current_month_snap_data = current_month_snap_data.withColumn(
                "avg_snapsize_in_gb", (col("avg_snapsize") / (1024**3))
            )
            current_month_snap_data = current_month_snap_data.join(
                system_data.select("system_id", "per_gb_cost"), on=["system_id"]
            )
            current_month_snap_data = current_month_snap_data.withColumn(
                "month_cost_in_gb", (col("avg_snapsize_in_gb") * col("per_gb_cost"))
            )
            month_cost = current_month_snap_data.select(sum("month_cost_in_gb")).collect()[0][0]
        else:
            month_cost = 0

        return month_cost

    def spark_snapshot_cost_trend(self, **params):
        """This function execute a spark query to get the snapshot cost trend data

        Returns:
            dict: key/value pair required for the snapshot cost trend data
        """

        start_month = params["start_date"].strftime("%Y-%m")
        end_month = params["end_date"].strftime("%Y-%m")
        self.load_spark_module_obj()
        self.snap_data_frame = self.context.mock_snap_usage
        system_data = self.spark_system_cost
        self.snap_data_frame = self.spark.createDataFrame(self.snap_data_frame)
        system_data = self.spark.createDataFrame(system_data)
        self.snap_data_frame.createOrReplaceTempView("tempviewdf")

        # columns = ["year", "month", "cost", "currency", "customer_id"]
        # snap_cost_trend = pd.DataFrame(columns=columns)

        self.snap_data_frame = self.snap_data_frame.select(
            "collection_end_date",
            "collection_start_date",
            "collection_name",
            "snapsize_bytes",
            "system_id",
            "volume_id",
            "customer_id",
        )

        # As snapsize_byte represent (mentioned as field inside volume dictionary in colsolidated json) is size of all snapshots, need to drop duplicate rows where one volume have multiple snapshots
        snap_size_df = self.snap_data_frame.dropDuplicates(["collection_end_date", "volume_id"])

        snap_df = snap_size_df.join(
            system_data.select("system_id", "per_gb_cost", "currency", "customer_id"), on=["system_id", "customer_id"]
        )
        # calculating snapshots hourly sum of bytes per system
        hourly_cost_df = (
            snap_df.select("*")
            .groupBy("collection_end_date", "system_id", "customer_id")
            .agg(
                sum("snapsize_bytes").alias("total_size"),
                min("per_gb_cost").alias("per_gb_cost"),
                min("collection_name").alias("cname"),
                min("currency").alias("currency"),
            )
        )
        # calulating sanpshot's hourly cost per system
        hourly_cost_df = hourly_cost_df.withColumn("snap_size_gb", (col("total_size") / (1024**3)))
        hourly_cost_df = hourly_cost_df.withColumn("snap_cost", (col("snap_size_gb") * col("per_gb_cost")))

        # calculating monthly cost for snapshots

        snap_size_df = hourly_cost_df.withColumn("month", date_format("collection_end_date", "yyyy-MM"))

        snapshot_monthly_snap_size = snap_size_df.groupby("month", "customer_id").agg(
            sum("snap_cost").alias("sum_of_cost"),
            (functions.countDistinct("cname").alias("count")),
            min("currency").alias("currency"),
        )

        snapshot_monthly_snap_size = snapshot_monthly_snap_size.withColumn(
            "finalcost", (col("sum_of_cost") / col("count"))
        )
        # selecting cost for 6 months
        snapshot_monthly_snap_size = snapshot_monthly_snap_size.filter((col('month') >= start_month) & (col('month') <= end_month))

        snap_cost_trend = snapshot_monthly_snap_size.toPandas()
        converted_dict = snap_cost_trend.to_json(orient="table")
        json1_data = json.loads(converted_dict)
        return json1_data

    def spark_snap_usage_trend(self, **params):
        """This fucction get the mock data and execute the spark query to calculate snapshot usage trend grph for hourly, daily and weekly time period.

        Returns:
            dict: list of key/values represent the snapshot usage trend graph
        """
        self.load_spark_module_obj()

        start_date = params["start_date"]
        end_date = params["end_date"]
        granularity = params["granularity"]

        if granularity == Granularity.daily.value:
            starttime_object = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            start_hour_number = starttime_object.hour
            endtime_object = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            end_hour_number = endtime_object.hour
            if start_hour_number > 0:
                start_date = starttime_object + timedelta(days=1)
                start_date = start_date.replace(hour=0, minute=0, second=0)
            if end_hour_number > 0:
                end_date = endtime_object.replace(hour=20, minute=0, second=0)
        if granularity == Granularity.weekly.value:
            starttime_object = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            next_monday = starttime_object + relativedelta(weekday=MO)
            start_date = next_monday.date()

        self.snap_data_frame = self.context.mock_snap_usage

        all_snapshots_size_data = self.spark.createDataFrame(self.snap_data_frame)

        all_snapshots_size_data.createOrReplaceTempView("tempviewdf")

        # filtering collection data based on required fields for snapshot trend graph

        all_snapshots_size_data = all_snapshots_size_data.select(
            weekofyear("collection_end_date").alias("week"),
            dayofweek("collection_end_date").alias("weekday"),
            hour("collection_end_date").alias("hour"),
            dayofmonth("collection_end_date").alias("day"),
            to_date("collection_end_date").alias("collectiontime"),
            "collection_end_date",
            "collection_start_date",
            "collection_name",
            "snapsize_bytes",
            "volume_id",
            "customer_id",
        )
        # As snapsize_byte represent (mentioned as field inside volume dictionary in colsolidated json) is size of all snapshots, need to drop duplicate rows where one volume have multiple snapshots
        all_snapshots_updated_size_data = all_snapshots_size_data.dropDuplicates(["collection_end_date", "volume_id"])

        if granularity == Granularity.hourly.value:
            snap_usage_df = (
                all_snapshots_updated_size_data.select("*")
                .where(f"collection_end_date >= '{start_date}' and collection_end_date < '{end_date}'")
                .groupBy("week", "hour", "collection_end_date", "customer_id")
                .agg(sum("snapsize_bytes").alias("totalUsageInBytes"))
            )

        elif granularity == Granularity.daily.value:
            daily_sum_df = (
                all_snapshots_updated_size_data.select("*")
                .where(f"collection_end_date >= '{start_date}' and collection_end_date < '{end_date}'")
                .groupBy("week", "day", "collectiontime", "customer_id")
                .agg(
                    sum("snapsize_bytes").alias("totalusedsize"),
                    (functions.countDistinct("collection_name").alias("count")),
                    min("collection_start_date").alias("min_collection_time"),
                )
            )
            #  Some collections where hour of min_collection_time is > 0 and total collections per day are < 3 then time needs to set as 00:00:00
            daily_sum_updated_time_df = daily_sum_df.withColumn(
                "collectiontime",
                when(
                    (col("count") < 3) & (hour(col("min_collection_time")) > 0),
                    col("min_collection_time").cast("timestamp").cast("date"),
                ).otherwise(col("min_collection_time")),
            )

            snap_usage_df = daily_sum_updated_time_df.withColumn(
                "totalUsageInBytes",
                functions.col("totalusedsize") / functions.col("count"),
            )

        elif granularity == Granularity.weekly.value:
            wsd = all_snapshots_updated_size_data.withColumn(
                "collectiontime", expr("to_date(collectiontime)")
            ).withColumn("week_start", date_sub(next_day("collectiontime", "Mon"), 7))

            weekly_sum_df = (
                wsd.select("*")
                .where(f"collection_end_date >= '{start_date}' and collection_end_date <= '{end_date}'")
                .groupBy("week_start", "customer_id")
                .agg(
                    sum("snapsize_bytes").alias("totalusedsize"),
                    (functions.countDistinct("collection_name").alias("count")),
                    min("week_start").alias("collectiontime"),
                )
            )

            snap_usage_df = weekly_sum_df.withColumn(
                "totalUsageInBytes", functions.col("totalusedsize") / functions.col("count")
            )

        pandas_data_frame = snap_usage_df.toPandas()
        converted_dict = pandas_data_frame.to_json(orient="table")
        json1_data = json.loads(converted_dict)
        return json1_data, granularity

    def spark_snap_creation_data(self, **params):
        """This function execute the spark query to get the snapshot creation trend graph

        Returns:
            dict: key values define the snapshot creation trend graph
        """

        self.load_spark_module_obj()
        start_date = params["start_date"]
        end_date = params["end_date"]
        granularity = params["granularity"]
        self.snap_data_frame = self.context.mock_snap_all
        snap_list_df = self.spark.createDataFrame(self.snap_data_frame)
        snap_list_df.createOrReplaceTempView("tempviewdf")

        # Snapshot creation window  for every collection  is collection_start_time - 8H 
        snap_list_df=snap_list_df.withColumn("creation_window",expr("collection_start_date - INTERVAL 8 HOURS"))

        # filtering collection data required fields
        snap_creation_list_within_start_end_date = snap_list_df.select(
            "customer_id",
            "snap_id",
            "snap_name",
            "snap_type",
            "collection_name",
            "creation_window",
            "creation_time",
            "collection_start_date",
            "collection_end_date",
        ).orderBy(col("collection_start_date"))

       
        # calculating the periodic and adhoc snap count for evey collection for snapshot creation trend based on creation time (it should be created within (collection start time - 8H) and (creation start time ))
        snap_creation_hourly_trend = (
            snap_creation_list_within_start_end_date.withColumn(
                "is_within_window",
                when(
                    (
                        (col("creation_time") >= expr("collection_start_date - INTERVAL 8 HOURS")) & (col("creation_time") < col("collection_start_date"))
                    ),
                    True,
                ).otherwise(False),
            )
            .withColumn(
                "adhoc_count_within_window",
                when((col("is_within_window") == True) & (col("snap_type") == "adhoc"), 1).otherwise(0)
                # calculating adhoc snapshot count
            )
            .withColumn(
                "periodic_count_within_window",
                when((col("is_within_window") == True) & (col("snap_type") == "periodic"), 1).otherwise(0),
                # calculating periodic snapshot count
            )
        )
        snap_creation_hourly_trend= snap_creation_hourly_trend.withColumnRenamed("collection_end_date", "update_time")


        if granularity == Granularity.hourly.value:
            snap_creation_hourly_trend = snap_creation_hourly_trend.groupby( 
                "customer_id", "creation_window"
                ).agg(
                    sum("adhoc_count_within_window").alias("total_adhoc_count"),
                    sum("periodic_count_within_window").alias("total_periodic_count"),
                    min("update_time").alias("updatedAt")
                    )
            snap_creation_final_result_df = snap_creation_hourly_trend.select("*").where(f"updatedAt >= '{start_date}' and updatedAt < '{end_date}'")
            

        elif granularity == Granularity.daily.value:
            snap_creation_hourly_trend=snap_creation_hourly_trend.withColumn("creation_window_date", to_date("creation_window"))
            snap_creation_hourly_trend=snap_creation_hourly_trend.groupby("customer_id","creation_window_date").agg(sum("adhoc_count_within_window").alias("total_adhoc_count"),sum("periodic_count_within_window").alias("total_periodic_count"))

            endtime_object = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
            if endtime_object.hour > 0:
                end_date = endtime_object.replace(hour=00, minute=0, second=0)
            snap_creation_final_result_df =snap_creation_hourly_trend.select("*").where(f"creation_window_date >= '{start_date}' and creation_window_date < '{end_date}'")
            

        elif granularity == Granularity.weekly.value:
            wsd = snap_creation_hourly_trend.withColumn(
                "creation_window_date", expr("to_date(creation_window)")
            ).withColumn("week_start", date_sub(next_day("creation_window_date", "Mon"), 7))
            snap_creation_final_result_df = wsd.groupBy("week_start", "customer_id").agg(
                sum("adhoc_count_within_window").alias("total_adhoc_count"),
                sum("periodic_count_within_window").alias("total_periodic_count"),
            ).withColumn("update_time", to_timestamp("week_start"))

            starttime_object = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            next_monday = starttime_object + relativedelta(weekday=MO)
            start_date = next_monday.date()

            snap_creation_final_result_df = snap_creation_final_result_df.select("*").where(f"week_start >= '{start_date}' and week_start < '{end_date}'")

        # BFF ignores perticular collection(hourly,daily,weekly) when adhoc and periodic snapshot count is zero while ploting graph  
        snap_creation_final_result_df=snap_creation_final_result_df.filter((snap_creation_final_result_df.total_adhoc_count !=0) | (snap_creation_final_result_df.total_periodic_count!= 0))
        
        pandas_data_frame = snap_creation_final_result_df.toPandas()
        converted_dict = pandas_data_frame.to_json(orient="table")
        json1_data = json.loads(converted_dict)
        return json1_data, granularity

    def unionAll(self, *dfs):
        return reduce(DataFrame.unionAll, dfs)

   

    def spark_snap_age_trend(self):
        """This function will collect the required data for Snapshot age trend graph 

        Returns:
            dict : key values for snapshot age trend graph
        """
        self.load_spark_module_obj()
        self.snap_data_frame = self.context.mock_snap_all
        collection_data = self.context.mock_collection_data
        coll_list = collection_data["collection_name"].unique()
        latest_collection_name= coll_list[-1]
        # Get all snapshot in last collection
        self.snap_data_frame = self.snap_data_frame[self.snap_data_frame["collection_name"] == latest_collection_name]

        self.spark_snaps_data_frame = self.spark.createDataFrame(self.snap_data_frame)
        self.spark_snaps_data_frame.createOrReplaceTempView("tempviewdf")

        snap_df = self.spark_snaps_data_frame.select("creation_time","collection_end_date","customer_id","snap_id","collection_id","snapshot_size_in_bytes")
        # Calulating snapshot age (bucket)
        snap_age_df = snap_df.withColumn(
            "age_range",
            when(
                (col("creation_time")  > expr("collection_end_date - INTERVAL 6 MONTHS")),
                "0-6 months",
            )
            .when(
                (col("creation_time") <= expr("collection_end_date - INTERVAL 6 MONTHS"))
                & (col("creation_time") > expr("collection_end_date - INTERVAL 12 MONTHS")),
                "6-12 months",
            )
            .when(
                (col("creation_time") <= expr("collection_end_date - INTERVAL 12 MONTHS"))
                & (col("creation_time") < expr("collection_end_date - INTERVAL 24 MONTHS")),
                "1-2 years",
            )
            .when(
                (col("creation_time") <= expr("collection_end_date - INTERVAL 24 MONTHS"))
                & (col("creation_time") > expr("collection_end_date - INTERVAL 36 MONTHS")),
                "2-3 years",
            )
            .when(
                (col("creation_time")<= expr("collection_end_date - INTERVAL 36 MONTHS")),
                "3+ years",
            ),
        )

        snap_max_size_from_last_collection=snap_age_df

        # finding the max size snapshot from collection
        snap_size_range_partition_df= snap_max_size_from_last_collection.groupby("customer_id","collection_id").agg(max("snapshot_size_in_bytes").alias("size_bucket"))

        # bucket size_byte conversion- constants 
        MiB = 1024**2
        GiB = 1024**3
        TiB = 1024**4
        PiB = 1024**5

        # Calculating the size range of bucket 
        snap_size_range_partition_df= snap_size_range_partition_df.withColumn(
            "bucket_size_range", 
            when((col("size_bucket") >= 0) & (col("size_bucket") <= 10 * MiB), "10 MiB")
            .when((col("size_bucket") >= 10 * MiB ) & (col("size_bucket") <= 100 * MiB), "100 MiB")
            .when((col("size_bucket") >= 100 * MiB ) & (col("size_bucket") <= GiB), "1 GiB")
            .when((col("size_bucket") >= GiB ) & (col("size_bucket") <= 10 * GiB), "10 GiB")
            .when((col("size_bucket") >= 10 * GiB ) & (col("size_bucket") <= 100 * GiB), "100 GiB")
            .when((col("size_bucket") >= 100 * GiB) & (col("size_bucket") <= TiB), "1 TiB")
            .when((col("size_bucket") >= TiB) & (col("size_bucket") <= 10 * TiB), "10 TiB")
            .when((col("size_bucket") >= 10 * TiB) & (col("size_bucket") <= 100* TiB), "100 TiB")
            .when((col("size_bucket") >= 100 * TiB) & (col("size_bucket") <= PiB), "1 PiB")
            .when((col("size_bucket") >= PiB) & (col("size_bucket") <= 10* PiB), "10 PiB")            
            )
        # calculating the partition value for the sub buckets
        snap_size_range_partition_df=snap_size_range_partition_df.withColumn(
            "subbucket_range_limit", 
            when(col("bucket_size_range") == "10 MiB", 3 * MiB)
            .when(col("bucket_size_range") == "100 MiB", 30 * MiB)
            .when(col("bucket_size_range") == "1 GiB", 300 * MiB)
            .when(col("bucket_size_range") == "10 GiB", 3 * GiB)
            .when(col("bucket_size_range") == "100 GiB", 30 * GiB)
            .when(col("bucket_size_range") == "1 TiB", 300 * GiB)
            .when(col("bucket_size_range") == "10 TiB", 3 * TiB)
            .when(col("bucket_size_range") == "100 TiB", 30 * TiB)
            .when(col("bucket_size_range") == "1 PiB", 300 * TiB)
            .when(col("bucket_size_range") == "10 PiB", 3 * PiB)
        )
            
        # Seperating bucket size and unit    
        snap_size_range_partition_df=snap_size_range_partition_df.withColumn("size_value", split(col("bucket_size_range"), " ")[0]) \
                  .withColumn("size_unit", split(col("bucket_size_range"), " ")[1])
        # Converting bucket unit from bytes to Mib/GiB/TiB/PiB
        snap_size_range_partition_df=snap_size_range_partition_df.withColumn("size_unit_value",
                       when(
                           col("size_unit") =="MiB", MiB
                       )
                       .when(
                           col("size_unit") =="GiB", GiB
                       )
                       .when(
                           col("size_unit") =="TiB", TiB
                       )
                       .when(
                           col("size_unit") =="PiB", PiB
                       )
                    )
        snapshot_age_sub_bucket_df=snap_age_df.join(snap_size_range_partition_df,on=['customer_id', 'collection_id'], how='left')
        #  finding sub bucket for snapshot 
        snapshot_age_sub_bucket_df = snapshot_age_sub_bucket_df.withColumn("Sub_bucket_value",
                   when(col("snapshot_size_in_bytes") <= col("subbucket_range_limit"), "min")
                   .when((col("snapshot_size_in_bytes") > col("subbucket_range_limit")) & (col("snapshot_size_in_bytes") <= col("subbucket_range_limit") * 2), "mid")
                   .when((col("snapshot_size_in_bytes") <= col("subbucket_range_limit") * 2) & (col("snapshot_size_in_bytes") <= col("size_value") * col("size_unit_value")), "max")
                   .otherwise(None))
        
        # grouping snapshot age and finding count of snapshots for sub buckets min/mid/max
        snapshot_age_sub_bucket_df = (snapshot_age_sub_bucket_df.groupBy("customer_id", "collection_end_date", "age_range", "size_value", "size_unit") \
            .pivot("sub_bucket_value", ["min", "mid", "max"]) \
            .agg(count("*").alias("count"))).fillna(0)

        pandas_data_frame = snapshot_age_sub_bucket_df.toPandas()
        converted_dict = pandas_data_frame.to_json(orient="table")
        json1_data = json.loads(converted_dict)
        return json1_data

    def spark_snap_retention_trend(self):
        """
        This function runs a spark query on the snapshot table to find the retention trend
        Returns:
            dict: key values required for snapshot retention trend graph
        """
        self.load_spark_module_obj()
        self.snap_data_frame = self.context.mock_snap_lastcoll

        self.spark_snaps_data_frame = self.spark.createDataFrame(self.snap_data_frame)

        self.spark_snaps_data_frame.createOrReplaceTempView("tempviewdf")
        snapshot_list= self.spark_snaps_data_frame
        MAX_EPOCH_TIMESTAMP = "2038-01-19 03:14:07"  # 2147483647  in ms 
        etl_notset_time ="1970-01-01 00:00:00"

        dt1_snap_list = snapshot_list.filter(snapshot_list.devicetype == 'HPE Alletra 9000')
        dt1_retention_df = self.get_dt1_retention_bucket(dt1_snap_list, MAX_EPOCH_TIMESTAMP, etl_notset_time)

        # DT2 calculation
        dt2_snap_list = snapshot_list.filter(snapshot_list.devicetype == 'HPE Alletra 6000')
        dt2_retention_df = self.get_dt2_retention_bucket(dt2_snap_list)

        # Merging both dt1 and dt2 data 
        snapshots_with_retention_bucket=dt1_retention_df.union(dt2_retention_df)

        # finding adhoc and periodic count for each  retention age range  
        snapshots_with_retention_bucket = snapshots_with_retention_bucket.groupBy("custid","bucket") \
        .agg(
            sum(col("isAdhoc").cast("int")).alias("adhoc_count"),
            (sum((1 - col("isAdhoc").cast("int")))).alias("periodic_count")
        )

        pandas_data_frame = snapshots_with_retention_bucket.toPandas()
        converted_dict = pandas_data_frame.to_json(orient="table")
        json1_data = json.loads(converted_dict)
        return json1_data

    def get_dt2_retention_bucket(self, dt2_snap_list):
        """This function calculate retetion age bucket for dt2 snapshots

        Args:
            dt2_snap_list (df): list of dt2 snapshots

        Returns:
            df: dt2 retetion bucket info
        """
        
        dt2_snap_list=dt2_snap_list.select("custid","snapid","snaptype","total_clone_count","expiry_time", "is_replica","replication_status","schedule_id","period_unit","isAdhoc","collectionendtime")
        # Adding values for is_unmanaged and is_manually_managed on the basis of snapshot type  
        dt2_snap_list=dt2_snap_list.withColumn(
            "is_unmanaged", 
            when(col("isAdhoc"),True).otherwise(False)
            ).withColumn(
                "is_manually_managed",
                when(col("isAdhoc"),True).otherwise(False)
            )
        # calculate dt2 retetion time as per condtions 
        dt2_snap_list= dt2_snap_list.withColumn(
            "etl_retention_time", 
            when(
                (col("total_clone_count") > 0), "MAX_EPOCH_TIMESTAMP"
            )
            .when(
                col("is_manually_managed"), "MAX_EPOCH_TIMESTAMP"
            )
            .when(
                (col("is_unmanaged") & (col("expiry_time")==0 )), 0
            )
            .when(
                 (col("is_unmanaged") & (col("is_replica") | (col("replication_status") == "complete")) & (col("schedule_id")!="")), "MAX_EPOCH_TIMESTAMP"
            )
            .when(
                col("is_unmanaged"), col("expiry_time")
            )
            .when(
                (col("is_unmanaged") == False)  & (col("is_manually_managed") == False ) & ((col("schedule_id") == "") |(col("period_unit") == "")), 0
            )
            .otherwise(None)
            # This is case if both is_unmanaged and is_manually_managed are false then retention time will be calculated as per approach 3 as per confluence page  (Note : This is not required with current mock data as it  not applicable) 
            #https://confluence.eng.nimblestorage.com/display/~chinmay.chaturvedi@hpe.com/Nimble+Snapshots+Retention+And+Expiration+Time+Logics
        )
        # Finding the snapshot retenion age bucket 
        dt2_snap_list=dt2_snap_list.withColumn(
            "bucket",
            when(
                col("etl_retention_time") == "MAX_EPOCH_TIMESTAMP", "Unlimited"
            )
            .when(
                col("etl_retention_time") == 0 , "Not Set"
            ).when(
                col("etl_retention_time") < col("collectionendtime"), "Lapsed"
            )
            .when(
                (col("etl_retention_time") >= col("collectionendtime"))
                & (col("etl_retention_time") < expr("collectionendtime + INTERVAL 6 MONTHS")),
                "0-6 months",
            )
            .when(
                (col("etl_retention_time") >= expr("collectionendtime + INTERVAL 6 MONTHS"))
                & (col("etl_retention_time") < expr("collectionendtime + INTERVAL 12 MONTHS")),
                "6-12 months",
            )
            .when(
                (col("etl_retention_time") >= expr("collectionendtime + INTERVAL 12 MONTHS"))
                & (col("etl_retention_time") < expr("collectionendtime + INTERVAL 24 MONTHS")),
                "1-2 years",
            )
            .when(
                (col("etl_retention_time") >= expr("collectionendtime + INTERVAL 24 MONTHS"))
                & (col("etl_retention_time") < expr("collectionendtime + INTERVAL 36 MONTHS")),
                "2-3 years",
            )
            .when(
                (col("etl_retention_time") >= expr("collectionendtime + INTERVAL 36 MONTHS")),
                "3+ years",
            )
        )

        dt2_snap_list=dt2_snap_list.select("custid","snapid","isAdhoc","bucket")
        return dt2_snap_list

    def get_dt1_retention_bucket(self, dt1_retention_df, MAX_EPOCH_TIMESTAMP, etl_notset_time):
        """This function calculate snapshot retention bucket inforamtion 

        Args:
            dt1_retention_df (_type_): dt1 snapshot list
            MAX_EPOCH_TIMESTAMP (_type_): tetenton value 2038-01-19 03:14:07
            etl_notset_time (_type_):  retention value 1970-01-01 00:00:00                             

        Returns:
            df: dt1 snapshot with retention inforamtion
        """
        
        dt1_retention_df =  dt1_retention_df.select("custid","snapid","expirationtime_ms","retentiontime_ms","isAdhoc", "collectionendtime")
        # setting expiration time as 0 for adhoc snapshots
        dt1_retention_df =  dt1_retention_df.withColumn("expirationtime_ms", when(col("isAdhoc"),0).otherwise(col("expirationtime_ms")))
        # DT1 retention time calulation on the basis of expiration_time and retention time 
        dt1_retention_df=dt1_retention_df.withColumn(
                "etl_retention_time",
                when((col("expirationtime_ms") == 0.0) & (col("retentiontime_ms") == 0.0),datetime.strptime(MAX_EPOCH_TIMESTAMP,"%Y-%m-%d %H:%M:%S")) 
                .when(col("retentiontime_ms") == 0.0,datetime.strptime(etl_notset_time,"%Y-%m-%d %H:%M:%S"))
                      .otherwise(from_unixtime(col("retentiontime_ms")/1000).cast("timestamp"))     
                )
        #Finding retention age bucket for snapshot on the basis of retetion applied/not
        dt1_retention_df= dt1_retention_df.withColumn(
            "bucket", when(
                ((col("expirationtime_ms") == 0.0) & (col("retentiontime_ms") == 0.0)), "Unlimited"
            )
            .when(
                 col("retentiontime_ms") == 0.0,"Not Set"
            )
            .when(
                col("etl_retention_time") < col("collectionendtime"), "Lapsed"
            )
            .when(
                (col("etl_retention_time") >= col("collectionendtime"))
                & (col("etl_retention_time") < expr("collectionendtime + INTERVAL 6 MONTHS")),
                "0-6 months",
            )
            .when(
                (col("etl_retention_time") >= expr("collectionendtime + INTERVAL 6 MONTHS"))
                & (col("etl_retention_time") < expr("collectionendtime + INTERVAL 12 MONTHS")),
                "6-12 months",
            )
            .when(
                (col("etl_retention_time") >= expr("collectionendtime + INTERVAL 12 MONTHS"))
                & (col("etl_retention_time") < expr("collectionendtime + INTERVAL 24 MONTHS")),
                "1-2 years",
            )
            .when(
                (col("etl_retention_time") >= expr("collectionendtime + INTERVAL 24 MONTHS"))
                & (col("etl_retention_time") < expr("collectionendtime + INTERVAL 36 MONTHS")),
                "2-3 years",
            )
            .when(
                (col("etl_retention_time") >= expr("collectionendtime + INTERVAL 36 MONTHS")),
                "3+ years",
            )
            )
        
        dt1_retention_df=dt1_retention_df.select("custid","snapid","isAdhoc","bucket")
        return dt1_retention_df

    def spark_snap_list_snapshot_details(self, **params):
        """This  function returns snapshot details from mock/actual array data

        Returns:
            dict: list of fields which represent snapshot details
        """
        self.load_spark_module_obj()
        # using snap_all_collections table for extracting required data
        self.snap_data_frame = self.context.mock_snap_all
        self.spark_snaps_data_frame = self.spark.createDataFrame(self.snap_data_frame)

        snapshot_df = self.spark_snaps_data_frame.select(
            "collection_id", "snap_name", "snap_id","collection_end_date", "system_id","system_name", "customer_id", "creation_time"
        )

        snapshot_df = snapshot_df.groupby("snap_name","snap_id","system_id", "system_name", "customer_id"
            ).agg(
                min("creation_time").alias("creation_time"),
                min("collection_end_date").alias("update_time")
            )

        pandas_data_frame = snapshot_df.toPandas()
        converted_dict = pandas_data_frame.to_json(orient="table")
        json1_data = json.loads(converted_dict)
        return json1_data

    def spark_clone_consumption(self, **params):
        clone_usage_data = self.context.mock_clone_allcoll
        collection_data = self.context.mock_collection_data

        coll_list = collection_data["collection_name"].unique()
        latest_collection = coll_list[-1]
        clone_usage_last_df = clone_usage_data[clone_usage_data["collectionname"] == latest_collection]
        clone_last_coll_dict = self._clones_consumption_info(clone_usage_last_df)

        sys_df = self.spark_system_cost
        clusage_sys_cost = self._calculate_clone_usage_cost(sys_df, clone_usage_last_df)

        # monthly clone consumption is calculated
        clone_consumption_df = self._clone_monthly_consumption(clone_usage_data)
        current_month_utilized_bytes = self._clone_current_month_consumption(clone_consumption_df)
        prev_month_utilized_bytes = self._clone_prev_month_consumption(clone_consumption_df)
        clusage_cost = self._calculate_cloneusage_monthly_cost(clone_usage_data)

        current_month_agg_usage_cost = 0
        current_mon = self._get_current_month()
        c_df = clusage_cost[clusage_cost["collectionstarttime"] == current_mon]
        if not c_df.empty:
            current_month_agg_usage_cost = c_df["agg_usage_cost"].values[0]

        prev_month_agg_usage_cost = 0
        prev_mon = self._get_previous_month()
        p_df = clusage_cost[clusage_cost["collectionstarttime"] == prev_mon]
        if not p_df.empty:
            prev_month_agg_usage_cost = p_df["agg_usage_cost"].values[0]

        print(current_month_agg_usage_cost)
        print(prev_month_agg_usage_cost)
        clone_avg_dict = {
            "current_month_utilized_size_in_bytes": current_month_utilized_bytes,
            "previous_month_utilized_size_in_bytes": prev_month_utilized_bytes,
            "customer_id": clone_consumption_df.iloc[0]["customer_id"],
            "prev_month_usage_cost": prev_month_agg_usage_cost,
            "current_month_usage_cost": current_month_agg_usage_cost,
            "cost": clusage_sys_cost["usage_cost"].sum(),
        }

        return clone_last_coll_dict, clone_avg_dict

    def _calculate_clone_usage_cost(self, sys_df, clone_usage_last_df):
        clusage_sys = (
            clone_usage_last_df.groupby("storagesysid").agg(clone_used_size=("cloneusedsize", "sum")).reset_index()
        )
        clusage_sys.rename(columns={"storagesysid": "system_id"}, inplace=True)
        clusage_sys_cost = pd.merge(clusage_sys, sys_df[["per_gb_cost", "system_id"]], on="system_id")
        clusage_sys_cost["usage_cost"] = (
            clusage_sys_cost["clone_used_size"] / (1024**3) * clusage_sys_cost["per_gb_cost"]
        )

        return clusage_sys_cost

    def _calculate_cloneusage_monthly_cost(self, clone_usage_data):
        clusage_df = (
            clone_usage_data.groupby(
                [pd.PeriodIndex(clone_usage_data["collectionstarttime"], freq="M"), "custid", "storagesysid"]
            )
            .agg(
                total_cloneusedsize_bytes=("cloneusedsize", "sum"),
                num_coll_per_month=("collectionname", "nunique"),
                customer_id=("custid", "first"),
            )
            .reset_index()
        )

        sys_df = self.spark_system_cost

        clusage_df["agg_cloneusedsize_gib"] = (
            clusage_df["total_cloneusedsize_bytes"] / clusage_df["num_coll_per_month"]
        ) / (1024**3)

        clusage_df.rename(columns={"storagesysid": "system_id"}, inplace=True)
        consump_df = pd.merge(clusage_df, sys_df[["system_id", "per_gb_cost"]], on="system_id")
        consump_df["usage_cost"] = consump_df["agg_cloneusedsize_gib"] * consump_df["per_gb_cost"]
        df = (
            consump_df.groupby(["collectionstarttime", "custid"])
            .agg(agg_usage_cost=("usage_cost", "sum"))
            .reset_index()
        )
        return df

    def _clone_prev_month_consumption(self, clone_consumption_df):
        prev_mon = self._get_previous_month()
        prev_month_df = clone_consumption_df[clone_consumption_df["collectionstarttime"] == prev_mon]
        prev_month_utilized_bytes = 0
        if not prev_month_df.empty:
            prev_month_utilized_bytes = prev_month_df["agg_utilized_size"].values[0]

        return prev_month_utilized_bytes

    def _clone_current_month_consumption(self, clone_consumption_df):
        current_mon = self._get_current_month()
        current_month_df = clone_consumption_df[clone_consumption_df["collectionstarttime"] == current_mon]
        current_month_utilized_bytes = 0
        if not current_month_df.empty:
            current_month_utilized_bytes = current_month_df["agg_utilized_size"].values[0]
        return current_month_utilized_bytes

    def _clone_monthly_consumption(self, clone_usage_data):
        clone_consumption_df = clone_usage_data.groupby(
            [pd.PeriodIndex(clone_usage_data["collectionstarttime"], freq="M"), "custid"]
        ).agg(
            total_cloneusedsize=("cloneusedsize", "sum"),
            num_coll_per_month=("collectionname", "nunique"),
            customer_id=("custid", "first"),
        )
        # If we divide by num
        clone_consumption_df["agg_utilized_size"] = (
            clone_consumption_df["total_cloneusedsize"] / clone_consumption_df["num_coll_per_month"]
        ).astype(int)
        clone_consumption_df = clone_consumption_df.reset_index()
        return clone_consumption_df

    def _clones_consumption_info(self, clone_usage_last_df) -> dict:
        clone_last_coll_data = pd.DataFrame()
        # temp_df = clone_usage_data[clone_usage_data["collectionname"] == latest_collection]
        clone_last_coll_data["total_clone_count"] = [clone_usage_last_df.shape[0]]
        clone_last_coll_data["clone_total_size_in_bytes"] = [clone_usage_last_df["clonesize"].sum()]
        clone_last_coll_data["clone_used_size_in_bytes"] = [clone_usage_last_df["cloneusedsize"].sum()]
        clone_last_coll_dict = clone_last_coll_data.to_dict("records")[0]

        return clone_last_coll_dict

    def spark_clone_cost_trend(self, **params):
        self.load_spark_module_obj()
        start_date = params["start_date"]
        end_date = params["end_date"]
        clone_usage_data_frame = self.context.mock_clone_allcoll

        clone_cost_trend = self._calculate_cloneusage_monthly_cost(clone_usage_data_frame)
        start_date = self.get_first_date_month(start_date)
        end_date = self.get_last_date_month(end_date)
        clone_cost_data = clone_cost_trend[
            (clone_cost_trend["collectionstarttime"] >= start_date)
            & (clone_cost_trend["collectionstarttime"] <= end_date)
        ]
        return clone_cost_data

    def get_last_date_month(self,date: str):
        date = datetime.strptime(date,'%Y-%m-%d %H:%M:%S')
        date = date.replace(day=calendar.monthrange(date.year, date.month)[1]).strftime("%Y-%m-%d %H:%M:%S")
        return date

    def get_first_date_month(self,date: str):
        return datetime.strptime(date,'%Y-%m-%d %H:%M:%S').replace(day=1).strftime("%Y-%m-%d %H:%M:%S")

    def spark_clone_usage_trend(self, **params):
        self.load_spark_module_obj()
        start_date = params["start_date"]
        end_date = params["end_date"]
        granularity = params["granularity"]

        if not granularity:
            s_date = start_date.replace(" ", "T") + ".000Z"
            e_date = end_date.replace(" ", "T") + ".000Z"
            differance = self.find_date_range(s_date, e_date)
            if differance <= 7:
                granularity = "collectionHour"

            elif differance > 7 and differance <= 180:
                granularity = "day"
                starttime_object = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
                start_hour_number = starttime_object.hour
                endtime_object = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
                end_hour_number = endtime_object.hour
                if start_hour_number > 0:
                    start_date = starttime_object + timedelta(days=1)
                    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    start_date = start_date.strftime("%Y-%m-%d %H:%M:%S")
                if end_hour_number > 0:
                    end_date = endtime_object.replace(hour=20, minute=0, second=0, microsecond=0)
                    end_date = end_date.strftime("%Y-%m-%d %H:%M:%S")
            else:
                granularity = "week"
                starttime_object = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
                next_monday = starttime_object + relativedelta(weekday=MO)
                start_date = next_monday.date()
                start_date = start_date.strftime("%Y-%m-%d %H:%M:%S")
                endtime_object = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
                previous_monday = endtime_object - relativedelta(weeks=1, weekday=MO)
                end_date = previous_monday.date()
                end_date = end_date.strftime("%Y-%m-%d %H:%M:%S")
        else:
            if granularity == "day":
                starttime_object = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
                start_hour_number = starttime_object.hour
                endtime_object = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
                end_hour_number = endtime_object.hour
                if start_hour_number > 0:
                    start_date = starttime_object + timedelta(days=1)
                    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    start_date = start_date.strftime("%Y-%m-%d %H:%M:%S")
                if end_hour_number > 0:
                    end_date = endtime_object.replace(hour=20, minute=0, second=0, microsecond=0)
                    end_date = end_date.strftime("%Y-%m-%d %H:%M:%S")
            elif granularity == "week":
                starttime_object = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
                next_monday = starttime_object + relativedelta(weekday=MO)
                start_date = next_monday.date()
                start_date = start_date.strftime("%Y-%m-%d %H:%M:%S")
                endtime_object = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
                previous_monday = endtime_object - relativedelta(weeks=1, weekday=MO)
                # end_date = previous_monday.date()
                # end_date = end_date.strftime("%Y-%m-%d %H:%M:%S")

        self.clone_usage_data_frame = self.context.mock_clone_allcoll

        self.spark_clone_data_frame = self.spark.createDataFrame(self.clone_usage_data_frame)

        self.spark_clone_data_frame.createOrReplaceTempView("tempviewdf")

        clone_all_collec = self.clone_usage_data_frame
        filtered_clone_all_collec_bytime = clone_all_collec[
            (clone_all_collec["collectionstarttime"] >= start_date)
            & (clone_all_collec["collectionstarttime"] <= end_date)
        ]

        if granularity == Granularity.hourly.value:
            hourly_df = clone_all_collec[
                (clone_all_collec["collectionendtime"] >= start_date)
                & (clone_all_collec["collectionendtime"] < end_date)
            ]
            hourly_avg_df = (
                hourly_df.groupby(["collectionstarttime", "collectionendtime", "custid"])
                .sum("cloneusedsize")
                .reset_index()
            )
            hourly_avg_df["cloneusedsize"] = hourly_avg_df["cloneusedsize"].astype("int64")

            # API response comes in descending order so sort descending it.
            sorted_df = hourly_avg_df.sort_values(by=["collectionendtime"], ascending=True).reset_index()
            converted_dict = sorted_df.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity
        elif granularity == Granularity.daily.value:
            daily_avg = (
                filtered_clone_all_collec_bytime.groupby(
                    [
                        pd.PeriodIndex(filtered_clone_all_collec_bytime["collectionendtime"], freq="D"),
                        "collectionname",
                        "custid",
                    ]
                )
                .agg({"cloneusedsize": "sum"})
                .reset_index()
                .rename(columns={"collectionendtime": "collectiontime"})
            )
            day_avg = daily_avg.groupby(["collectiontime", "custid"]).agg({"cloneusedsize": "mean"}).reset_index()
            day_avg["cloneusedsize"] = day_avg["cloneusedsize"].astype("int64")
            day_avg["collectiontime"] = day_avg["collectiontime"].astype(str)

            converted_dict = day_avg.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity
        elif granularity == Granularity.weekly.value:
            filtered_clone_all_collec_bytime["collection_date"] = pd.to_datetime(
                filtered_clone_all_collec_bytime["collectionstarttime"]
            ).dt.date
            week_avg = (
                filtered_clone_all_collec_bytime.groupby(
                    [
                        pd.PeriodIndex(filtered_clone_all_collec_bytime["collectionendtime"], freq="W"),
                        "collectionname",
                        "custid",
                    ]
                )
                .agg({"cloneusedsize": "sum"})
                .reset_index()
                .rename(columns={"collectionendtime": "collectiontime"})
            )
            week_average = week_avg.groupby(["collectiontime", "custid"]).agg({"cloneusedsize": "mean"}).reset_index()
            week_average["cloneusedsize"] = week_average["cloneusedsize"].astype("int64")
            week_average["collectiontime"] = week_average["collectiontime"].astype(str)

            converted_dict = week_average.to_json(orient="table")
            json1_data = json.loads(converted_dict)
            return json1_data, granularity

    def spark_clone_creation_data(self, **params):
        self.load_spark_module_obj()
        start_date = params["start_date"]
        end_date = params["end_date"]
        granularity = params["granularity"]

        if granularity == 0:
            differance = self.find_date_range(start_date, end_date)
            if differance <= 7:
                granularity = Granularity.hourly.value
            elif differance > 7 and differance <= 180:
                granularity = Granularity.daily.value
            else:
                granularity = Granularity.weekly.value

        clone_all_collection: pd.DataFrame = self.context.mock_clone_allcoll
        clone_latest_collection: pd.DataFrame = self.context.mock_clone_lastcoll

        clone_latest_collection["creation_time"] = pd.to_datetime(clone_latest_collection["clonecreationtime"].str.replace(".000000 \+0000 UTC",""))

        if granularity == Granularity.hourly.value:
            collection_hour_df = self._clone_creation_collectionhour_trend(start_date, end_date, clone_all_collection)
            collection_hour_trend: dict = collection_hour_df.to_json(orient="table")
            json1_data = json.loads(collection_hour_trend)
            return json1_data, granularity

        elif granularity == Granularity.daily.value:
            daily_df = self._clone_creation_day_trend(start_date, end_date, clone_latest_collection)
            collection_hour_trend = daily_df.to_json(orient="table")
            json1_data = json.loads(collection_hour_trend)
            return json1_data, granularity
        elif granularity == Granularity.weekly.value:
            weekly_df = self._clone_creation_weekly_trend(start_date, end_date, clone_latest_collection)
            
            collection_hour_trend = weekly_df.to_json(orient="table")
            json1_data = json.loads(collection_hour_trend)
            return json1_data, granularity

    def _clone_creation_day_trend(self, start_date, end_date, clone_latest_collection: pd.DataFrame) -> pd.DataFrame:
        """Clone creation daily trend for given time period

        Args:
            start_date (str): start date
            end_date (str): end date
            clone_latest_collection (pd.DataFrame): latest collection clone table

        Returns:
            pd.DataFrame: clone creation day trend dataframe
        """
        clone_in_time_range = clone_latest_collection[
                (clone_latest_collection["creation_time"] >= start_date[:10])
                & (clone_latest_collection["creation_time"] <= end_date)
            ]
            
        daily_df = (
                clone_in_time_range.groupby(
                    [pd.PeriodIndex(clone_in_time_range["creation_time"], freq="D"), "custid"]
                )
                .agg(clonecount=("cloneid", "count"), clone_list=("clonename", list))
                .reset_index()
            )
        daily_df["updatedAt"] = daily_df["creation_time"].dt.start_time.dt.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        
        return daily_df

    def _clone_creation_weekly_trend(self, start_date, end_date, clone_latest_collection: pd.DataFrame)-> pd.DataFrame:
        """Clone creation weekly trend for given time period.

        Args:
            start_date (str): start date
            end_date (str): end date
            clone_latest_collection (pd.DataFrame): latest collection clone table

        Returns:
            pd.DataFrame: weekly trend dataframe
        """
        clone_in_time_range = clone_latest_collection[
                (clone_latest_collection["creation_time"] >= start_date[:10])
                & (clone_latest_collection["creation_time"] <= end_date)
            ]
            
        weekly_df = (
                clone_in_time_range.groupby(
                    [pd.PeriodIndex(clone_in_time_range["creation_time"], freq="W"), "custid"]
                )
                .agg(clonecount=("cloneid", "count"), clone_list=("clonename", list))
                .reset_index()
            )
        weekly_df["updatedAt"] = weekly_df["creation_time"].dt.start_time.dt.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        
        return weekly_df

    def _clone_creation_collectionhour_trend(self, start_date, end_date, clone_all_collection: pd.DataFrame) -> pd.DataFrame:
        """Create clone creation collection hour trend for given time period - For each collection how many clones are created

        Args:
            start_date (datetime): _description_
            end_date (datetime): enddate
            clone_all_collection_df (pd.DataFrame): clone all collection table dataframe

        Returns:
            pd.DataFrame: collection hour trend
        """
        clone_in_time_range = clone_all_collection[
                (clone_all_collection["collectionendtime"] >= start_date)
                & (clone_all_collection["collectionendtime"] <= end_date)
            ]
        clone_in_time_range["aggrWindowTimestamp"] = clone_in_time_range["collectionstarttime"] - pd.Timedelta(hours=8)
        filtered_clone_in_time_range = clone_in_time_range[
                (clone_in_time_range["clonecreationtime"] < clone_in_time_range["collectionstarttime"])
                & (
                    clone_in_time_range["clonecreationtime"]
                    >= clone_in_time_range["aggrWindowTimestamp"]
                )
            ]
        collection_hour_df = (
                filtered_clone_in_time_range.groupby(["collectionendtime", "custid","aggrWindowTimestamp"])
                .agg(clonecount=("clonevolumeid", "count"), clone_list=("clonename", list))
                .reset_index()
            )
        collection_hour_df["collectionendtime"] = collection_hour_df["collectionendtime"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        collection_hour_df["aggrWindowTimestamp"] = collection_hour_df["aggrWindowTimestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        return collection_hour_df

    def _clone_creation_trend_day(self, clone_df)-> pd.DataFrame:
        """Clone creation trend day granularity

        Args:
            clone_df (_type_): _description_

        Returns:
            _type_: _description_
        """
        # vol_df = vol_latest_coll[vol_latest_coll["creation_time"] > min_creation_time]
        creation_trend_day_df = (
                clone_df.groupby(["creation_date", "custid"])
                .agg(volumecount=("clonevolumeid", "count"), vol_list=("clonename", list))
                .reset_index()
            )

        creation_trend_day_df["updatedAt"] = pd.to_datetime(creation_trend_day_df["creation_date"]).dt.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        
        return creation_trend_day_df

    def spark_clone_activity_trend(self, **params):
        self.load_spark_module_obj()
        provision_type = params["provisiontype"]
        minio = params["minio"]
        maxio = params["maxio"]
        minclonesize = params["minclonesize"]
        maxclonesize = params["maxclonesize"]

        self.clone_usage_data_frame = self.context.mock_clone_allcoll
        self.spark_clone_usage_data_frame = self.spark.createDataFrame(self.clone_usage_data_frame)
        clo_activity_df = (
            self.spark_clone_usage_data_frame.select(
                year("collectionstarttime").alias("year"),
                month("collectionstarttime").alias("month"),
                "clonename",
                "cloneid",
                "avgiops",
            )
            .where("clone == 'true'")
            .groupby("year", "month", "cloneid", "clonename")
            .agg(avg("avgiops").alias("avg_iops"))
        )
        clone_activity_trend_df = clo_activity_df.toPandas()
        clone_activity_trend_grp = clone_activity_trend_df.groupby("cloneid")
        clone_activity_trend_dict = {}
        for index, df in clone_activity_trend_grp:
            clone_avg_iops_list = []
            for index, row in df.iterrows():
                clone_year = row["year"]
                clone_month = row["month"]
                time_stamp = str(pd.to_datetime(datetime(clone_year, clone_month, 1))).replace(" ", "T") + "Z"
                io_activity = row["avg_iops"]
                clone_avg_iops_dict = {
                    "timeStamp": time_stamp,
                    "ioActivity": io_activity,
                }
                clone_avg_iops_list.append(clone_avg_iops_dict)
            # clone_activity_trend_dict[df.iloc[0]["cloneid"]] = df.to_dict(orient="records")
            clone_activity_trend_dict[df.iloc[0]["cloneid"]] = clone_avg_iops_list

        self.clone_data_frame = self.context.mock_clone_lastcoll
        # pd_data_frame = pd.json_normalize(self.clone_data_frame)
        # convert_dict = {"clonevolumeid": str, "provisiontype": str}
        # pd_data_frame = pd_data_frame.astype(convert_dict)

        self.spark_clone_data_frame = self.spark.createDataFrame(self.clone_data_frame)

        """
        collectionendtime|              custid|               arrid|       cloneparentid|provisiontype|             
        cloneid|clonesize|cloneusedsize|       clonevolumeid|   clonecreationtime|           clonename|mounted
        """
        if provision_type and minio is None and minclonesize is None:
            finaldf = self.spark_clone_data_frame.select(
                "collectionstarttime",
                "custid",
                "clonename",
                "cloneid",
                "system_id",
                "provisiontype",
                "cloneusedsize",
                "clonesize",
                "clonecreationtime",
                "mounted",
                "avg_iops",
            ).where(self.spark_clone_data_frame["provisiontype"] == provision_type)
            pandas_data_frame = finaldf.toPandas()
            converted_dict = pandas_data_frame.to_json(orient="table")
            json1_data = json.loads(converted_dict)

        elif minio and provision_type is None and minclonesize is None:
            finaldf = self.spark_clone_data_frame.select(
                "collectionstarttime",
                "custid",
                "clonename",
                "cloneid",
                "system_id",
                "provisiontype",
                "cloneusedsize",
                "avg_iops",
                "clonecreationtime",
                "mounted",
                "avg_iops",
            ).where(
                (self.spark_clone_data_frame["avg_iops"] >= minio) & (self.spark_clone_data_frame["avg_iops"] < maxio)
            )
            pandas_data_frame = finaldf.toPandas()
            converted_dict = pandas_data_frame.to_json(orient="table")
            json1_data = json.loads(converted_dict)

        elif minclonesize and provision_type is None and minio is None:
            finaldf = self.spark_clone_data_frame.select(
                "collectionstarttime",
                "custid",
                "clonename",
                "cloneid",
                "system_id",
                "provisiontype",
                "cloneusedsize",
                "clonesize",
                "clonecreationtime",
                "mounted",
                "avg_iops",
            ).where(
                (self.spark_clone_data_frame["cloneusedsize"] >= minclonesize)
                & (self.spark_clone_data_frame["cloneusedsize"] < maxclonesize)
            )
            pandas_data_frame = finaldf.toPandas()
            converted_dict = pandas_data_frame.to_json(orient="table")
            json1_data = json.loads(converted_dict)

        elif provision_type and minclonesize and minio is None:
            finaldf = self.spark_clone_data_frame.select(
                "collectionstarttime",
                "custid",
                "clonename",
                "cloneid",
                "system_id",
                "provisiontype",
                "cloneusedsize",
                "clonesize",
                "clonecreationtime",
                "mounted",
                "avg_iops",
            ).where(
                (self.spark_clone_data_frame["provisiontype"] == provision_type)
                & (self.spark_clone_data_frame["cloneusedsize"] >= minclonesize)
                & (self.spark_clone_data_frame["cloneusedsize"] < maxclonesize)
            )
            pandas_data_frame = finaldf.toPandas()
            converted_dict = pandas_data_frame.to_json(orient="table")
            json1_data = json.loads(converted_dict)

        elif provision_type and minio and minclonesize is None:
            finaldf = self.spark_clone_data_frame.select(
                "collectionstarttime",
                "custid",
                "clonename",
                "cloneid",
                "system_id",
                "provisiontype",
                "cloneusedsize",
                "clonesize",
                "clonecreationtime",
                "mounted",
                "avg_iops",
            ).where(
                (self.spark_clone_data_frame["provisiontype"] == provision_type)
                & (self.spark_clone_data_frame["avg_iops"] >= minio)
                & (self.spark_clone_data_frame["avg_iops"] < maxio)
            )
            pandas_data_frame = finaldf.toPandas()
            converted_dict = pandas_data_frame.to_json(orient="table")
            json1_data = json.loads(converted_dict)

        elif minio and minclonesize and provision_type is None:
            finaldf = self.spark_clone_data_frame.select(
                "collectionstarttime",
                "custid",
                "clonename",
                "cloneid",
                "system_id",
                "provisiontype",
                "cloneusedsize",
                "clonesize",
                "clonecreationtime",
                "mounted",
                "avg_iops",
            ).where(
                (self.spark_clone_data_frame["avg_iops"] >= minio)
                & (self.spark_clone_data_frame["avg_iops"] < maxio)
                & (self.spark_clone_data_frame["cloneusedsize"] >= minclonesize)
                & (self.spark_clone_data_frame["cloneusedsize"] < maxclonesize)
            )
            pandas_data_frame = finaldf.toPandas()
            converted_dict = pandas_data_frame.to_json(orient="table")
            json1_data = json.loads(converted_dict)

        elif minio and minclonesize and provision_type:
            finaldf = self.spark_clone_data_frame.select(
                "collectionstarttime",
                "custid",
                "clonename",
                "cloneid",
                "system_id",
                "provisiontype",
                "cloneusedsize",
                "clonesize",
                "clonecreationtime",
                "mounted",
                "avg_iops",
            ).where(
                (self.spark_clone_data_frame["avg_iops"] >= minio)
                & (self.spark_clone_data_frame["avg_iops"] < maxio)
                & (self.spark_clone_data_frame["cloneusedsize"] >= minclonesize)
                & (self.spark_clone_data_frame["cloneusedsize"] < maxclonesize)
                & (self.spark_clone_data_frame["provisiontype"] == provision_type)
            )
            pandas_data_frame = finaldf.toPandas()
            converted_dict = pandas_data_frame.to_json(orient="table")
            json1_data = json.loads(converted_dict)

        else:
            finaldf = self.spark_clone_data_frame.select(
                "collectionstarttime",
                "custid",
                "clonename",
                "cloneid",
                "system_id",
                "provisiontype",
                "cloneusedsize",
                "clonesize",
                "clonecreationtime",
                "mounted",
                "avg_iops",
            )
            pandas_data_frame = finaldf.toPandas()
            converted_dict = pandas_data_frame.to_json(orient="table")
            json1_data = json.loads(converted_dict)
        return clone_activity_trend_dict, json1_data

    def spark_clone_activity_trend_by_io(self, **params):
        self.load_spark_module_obj()
        provision_type = params["provisiontype"]
        minio = params["minio"]
        maxio = params["maxio"]

        clone_activity_trend: dict = {"items": []}
        clone_all_collection_df = self.context.mock_clone_allcoll
        clone_last_collec_df = self.context.mock_clone_lastcoll
        system_data_df = self.context.mock_sys_lastcoll
        clone_lastcollection_by_ptype: pd.DataFrame = clone_last_collec_df[
            (clone_last_collec_df["provisiontype"] == provision_type)
        ]
        for index, row in clone_lastcollection_by_ptype.iterrows():
            activity_df = clone_all_collection_df[
                (clone_all_collection_df["clonename"] == row["clonename"])
                & (clone_all_collection_df["provisiontype"] == provision_type)
            ]
            last_7days_avg_iops = self.last7days_clone_activity(activity_df)

            if last_7days_avg_iops > minio and last_7days_avg_iops < maxio:
                temp_dict = {}
                temp_dict = row.to_dict()

                temp_dict["last7days_avgiops"] = last_7days_avg_iops
                # calculate monthly ioaverage
                daily_average = activity_df.groupby(
                    [pd.PeriodIndex(activity_df["collectionstarttime"], freq="D"), "custid"]
                ).agg(
                    {"avgiops": "last", "cloneid": "first", "collectionstarttime": "first"},
                )
                monthly_average = daily_average.groupby(pd.PeriodIndex(daily_average["collectionstarttime"], freq="M"))[
                    "avgiops"
                ].mean()
                monthly_ioactivity = monthly_average.reset_index()
                date_time = pd.to_datetime(monthly_ioactivity["collectionstarttime"].astype(str))
                timestamp_list = date_time.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                monthly_activity_trend = pd.DataFrame(
                    {"timeStamp": timestamp_list, "ioActivity": monthly_ioactivity["avgiops"]}
                )
                clone_monthly_activity_trend = monthly_activity_trend.to_dict("records")
                temp_dict["activityTrendInfo"] = clone_monthly_activity_trend

                # Get system name from system table
                system = system_data_df["storagesysname"][
                    (system_data_df["storagesysid"] == row["system_id"])
                ].drop_duplicates()
                temp_dict["system"] = system.squeeze()

                clone_activity_trend["items"].append(temp_dict)
        return clone_activity_trend, clone_lastcollection_by_ptype

    def spark_clone_activity_trend_by_size(self, **params):
        self.load_spark_module_obj()
        provision_type = params["provisiontype"]
        minCloneSize = params["minCloneSize"]
        maxCloneSize = params["maxCloneSize"]

        clone_activity_trend: dict = {"items": []}
        clone_all_collection_df = self.context.mock_clone_allcoll
        clone_last_collec_df = self.context.mock_clone_lastcoll
        system_data_df = self.context.mock_sys_lastcoll
        clone_lastcollection_by_ptype: pd.DataFrame = clone_last_collec_df[
            (clone_last_collec_df["provisiontype"] == provision_type)
        ]
        clone_lastcollection_df: pd.DataFrame = clone_last_collec_df[
            (clone_last_collec_df["provisiontype"] == provision_type)
            & (clone_last_collec_df["cloneusedsize"] > minCloneSize)
            & (clone_last_collec_df["cloneusedsize"] < maxCloneSize)
        ]
        for index, row in clone_lastcollection_df.iterrows():
            activity_df = clone_all_collection_df[
                (clone_all_collection_df["clonevolumeid"] == row["clonevolumeid"])
                & (clone_all_collection_df["provisiontype"] == provision_type)
            ]
            temp_dict = {}
            temp_dict = row.to_dict()
            # Get last 7 days io avg
            last_7days_avg_iops = self.last7days_clone_activity(activity_df)
            temp_dict["last7days_avgiops"] = last_7days_avg_iops

            # calculate monthly ioaverage
            daily_average = activity_df.groupby(
                [pd.PeriodIndex(activity_df["collectionstarttime"], freq="D"), "custid"]
            ).agg(
                {"avgiops": "last", "cloneid": "first", "collectionstarttime": "first"},
            )
            monthly_average = daily_average.groupby(pd.PeriodIndex(daily_average["collectionstarttime"], freq="M"))[
                "avgiops"
            ].mean()
            monthly_ioactivity = monthly_average.reset_index()
            date_time = pd.to_datetime(monthly_ioactivity["collectionstarttime"].astype(str))
            timestamp_list = date_time.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            monthly_activity_trend = pd.DataFrame(
                {"timeStamp": timestamp_list, "ioActivity": monthly_ioactivity["avgiops"]}
            )
            clone_monthly_activity_trend = monthly_activity_trend.to_dict("records")
            temp_dict["activityTrendInfo"] = clone_monthly_activity_trend

            # Get system name from system table
            system = system_data_df["storagesysname"][
                (system_data_df["storagesysid"] == row["system_id"])
            ].drop_duplicates()
            temp_dict["system"] = system.squeeze()

            clone_activity_trend["items"].append(temp_dict)

        return clone_activity_trend, clone_lastcollection_by_ptype

    def last7days_clone_activity(self, clone_activity_df):
        today = (datetime.utcnow()).date()
        last_7days = today - timedelta(days=7)
        last_7days_df = clone_activity_df[
            (clone_activity_df["collectionstarttime"] >= pd.to_datetime(last_7days))
            & (clone_activity_df["collectionstarttime"] <= pd.to_datetime(today))
        ]
        last_collec_7days_df = (
            last_7days_df.groupby([pd.PeriodIndex(last_7days_df["collectionstarttime"], freq="D"), "custid"])
            .agg({"avgiops": "last", "cloneid": "first"})
            .reset_index()
        )
        last_7days_aviops = -1
        if not last_7days_df.empty:
            last_7days_aviops = last_collec_7days_df["avgiops"].mean()
        return last_7days_aviops

    def spark_app_list_data(self):
            """
            This function execute query to collection the applications's list and its corresponding data like numofVolumes, numofsnaps, numofclones etc

            Return : resutns the key/value pairs of fields required application details

            """
            # self.load_spark_module_obj()
            # Getting the content of table spark_app_lastcollection
            self.snap_data_frame = self.context.mock_app_lastcoll_with_sys


            # app_list_df = self.spark.createDataFrame(self.app_data_frame)
            # generate volume snap count, volume count and volume count
            columns = ["applicationname",
                        "applicationid",
                        "volumeclonecount",
                        "volumesnapcount",
                        "volid",
                        "clone",
                        "custid",
                        "system_name",
                        "system_id",
                        "devicetype"]
            # Only devicetype2 supports applineage in beta release.
            dt2_app = self.snap_data_frame[self.snap_data_frame["devicetype"] == "HPE Alletra 6000"][columns]
            applineage_df = dt2_app.groupby(["applicationname", "applicationid", "system_id", "custid"]).agg(
                    numClones=("volumeclonecount", "sum"), 
                    numSnapshots=("volumesnapcount", "sum"), 
                    sysname=("system_name", "first"), 
                    numVolumes=pd.NamedAgg(column='clone', aggfunc=lambda x: (x == 'false').sum()) # Clone field is false for volumes. Count the volumes without clones.
                ).reset_index()
            
            # Convert pandas dataframe to string
            converted_dict = applineage_df.to_json(orient="table")
            # Convert string to dict
            json1_data = json.loads(converted_dict)

            return json1_data

    def spark_app_vol_list_data(self, app_id: str = "", system_id: str = ""):
        """This function  run spack query to get the volume list for specific application

        Args:
            app_id (str): application ID. Defaults to "".
            system_id (str): system ID. Default to "".
        Returns:
            dict: list of key/pairs(fields) needed for volume details
        """
        self.load_spark_module_obj()

        self.snap_data_frame = self.context.mock_app_lastcoll_with_sys


        self.spark_clone_data_frame = self.spark.createDataFrame(self.snap_data_frame)

        app_df = self.spark_clone_data_frame.select(
            "volume_display_name",
            "volid",
            "volumesnapcount",
            "volumeclonecount",
            "volumetotalsize_bytes",
            "volumeusedsize_bytes",
            "system_id",
            "system_name",
            "state",
            "clone",
            "city",
            "postal_code",
            "custid",
            "country",
            "devicetype",
        ).where(f"applicationid = '{app_id}'and system_id = '{system_id}' and clone = 'false'")

        pandas_data_frame = app_df.toPandas()
        converted_dict = pandas_data_frame.to_json(orient="table")
        json1_data = json.loads(converted_dict)

        return json1_data

    def spark_app_vol_snap_list_data(self, vol_uuid: str = ""):
        self.load_spark_module_obj()
        # self.app_data_frame = self.context.mock_snap_app_data

        self.snap_data_frame = self.context.mock_snap_lastcoll
        clone_df = self.context.mock_clone_lastcoll

        # self.spark_clone_data_frame = self.spark.createDataFrame(self.app_data_frame)
        # pd_data_frame = pd.json_normalize(self.app_data_frame)
        # convert_dict = {"volumeid": str, "expirationtime": str, "retentiontime": str}
        # pd_data_frame = pd_data_frame.astype(convert_dict)

        self.spark_clone_data_frame = self.spark.createDataFrame(self.snap_data_frame)

        app_df = (
            self.spark_clone_data_frame.select("snapname", "snapid", "expirationtime", "creationtime", "snapsize","custid")
            .where(f"volumeid == '{vol_uuid}'")
            .groupBy("snapname", "snapid", "expirationtime", "creationtime","custid")
            .agg(sum("snapsize").alias("totalsnapsize"))
        )


        pandas_data_frame = app_df.toPandas()
        clone_snap = clone_df.groupby(["base_snap_id","custid"]).agg(numClones=("cloneid","count")).reset_index()
        snap_clone_lineage = pd.merge(pandas_data_frame, clone_snap, left_on=["snapid", "custid"], right_on=["base_snap_id","custid"], how = "left").fillna(0)
        converted_dict = snap_clone_lineage.to_json(orient="table")
        json1_data = json.loads(converted_dict)

        return json1_data

    def spark_app_vol_clone_list_data(self, snap_id: str = ""):
        self.load_spark_module_obj()
        self.snap_data_frame = self.context.mock_clone_lastcoll
        # pd_data_frame = pd.json_normalize(self.app_data_frame)
        # convert_dict = {"clonevolumeid": str}
        # pd_data_frame = pd_data_frame.astype(convert_dict)

        self.spark_clone_data_frame = self.spark.createDataFrame(self.snap_data_frame)

        app_df = (
            self.spark_clone_data_frame.select(
                "clonename",
                "cloneid",
                "clonesize",
                "cloneusedsize",
                "clonecreationtime",
                "custid",
            )
            .where(f"base_snap_id == '{snap_id}'")
            .distinct()
        )

        pandas_data_frame = app_df.toPandas()
        snap_df = self.context.mock_snap_lastcoll

        snap_clone = snap_df.groupby(["volumeid","custid"]).agg(numSnapshots=("snapid","count")).reset_index()
        snap_clone_lineage = pd.merge(pandas_data_frame, snap_clone, left_on=["cloneid", "custid"], right_on=["volumeid","custid"], how = "left").fillna(0)

        converted_dict = snap_clone_lineage.to_json(orient="table")
        json1_data = json.loads(converted_dict)

        return json1_data

    def spark_inventory_storage_system_summary(self):
        self.load_spark_module_obj()
        self.snap_data_frame = self.context.mock_sys_lastcoll

        # pd_data_frame = pd.json_normalize(self.app_data_frame)
        # convert_dict = {"storagesystotalused": str, "arrtotalused": str, "arrusablecapacity": str}
        # pd_data_frame = pd_data_frame.astype(convert_dict)

        self.spark_clone_data_frame = self.spark.createDataFrame(self.snap_data_frame)
        inv_df = (
            self.spark_clone_data_frame.select(
                "custid",
                "storagesysid",
                "storagesystotalused",
                "storagesysusablecapacity",
            )
            .groupBy("custid", "storagesysid")
            .agg(
                max("storagesystotalused").alias("totalused"),
                max("storagesysusablecapacity").alias("totalsize"),
            )
            .groupBy("custid")
            .agg(
                count("storagesysid").alias("totalsystems"),
                sum("totalused").alias("totalused"),
                sum("totalsize").alias("totalsize"),
            )
        )
        cost = self.spquery_inventory_sys_data["cost"].sum()
        pandas_data_frame = inv_df.toPandas()
        pandas_data_frame["cost"] = cost
        converted_dict = pandas_data_frame.to_json(orient="table")
        json1_data = json.loads(converted_dict)

        return json1_data

    def spark_inventory_storage_system_cost_trend(self, **params) -> dict:
        """In the inventory page storage system cost trend will be there. This method will simulate array response for that.
        It will display the cost of all arrays for customer from the first collection date to today's date.

        Returns:
            dict: storage system cost trend dict
        """
        

        cost_df = self.spquery_sys_monthly_cost
        start_date = self.context.mock_collection_data["collection_start_date"].min()
        end_date = self.context.mock_collection_data["collection_start_date"].max()

        daily_cost_df = pd.DataFrame(columns=['date', 'cost',"system_id","array_id","customer_id"])
        for index, row in cost_df.iterrows():
            current_date = row['Period_start_date']
            # current_date = pd.to_datetime(start_date)
            
            # Iterate from start_date to end_date (inclusive)
            while current_date <= row['Period_end_date'] and current_date <= pd.to_datetime("today"):
                daily_cost_df = daily_cost_df.append({'date': current_date, 'cost': row['remaining_cost'], "array_id": row["array_id"], "customer_id": row["customer_id"], "system_id": row["system_id"]}, ignore_index=True)
                current_date += pd.Timedelta(days=1)
        mask = (daily_cost_df["date"] >= start_date) & (daily_cost_df["date"] <= end_date)
        daily_cost_df = daily_cost_df.loc[mask]
        monthly_cost_array_wise = (
            daily_cost_df.groupby([pd.Grouper(key="date", freq="M"), "customer_id","system_id","array_id"])
            .agg(monthly_cost=("cost", "mean"))
            .reset_index()
        )
        monthly_cost_all_array = (
            monthly_cost_array_wise.groupby([pd.Grouper(key="date", freq="M"), "customer_id"])
            .agg(monthly_cost=("monthly_cost", "sum"))
            .reset_index()
        )
        monthly_cost_all_array["month"] = pd.DatetimeIndex(monthly_cost_all_array["date"]).month
        monthly_cost_all_array["year"] = pd.DatetimeIndex(monthly_cost_all_array["date"]).year

        converted_dict = monthly_cost_all_array.to_json(orient="table")
        json1_data = json.loads(converted_dict)
        return json1_data

    def spark_inventory_storage_systems(self):
        FILE_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
        db_name = f"{FILE_PATH}/../../../{self.golden_db_path}"
        engine = sqlalchemy.create_engine("sqlite:///%s" % db_name, execution_options={"sqlite_raw_colnames": True})
        conn = engine.connect()
        storage_sys_df = pd.read_sql_table("spquery_inventory_sys_data", con=conn)
        storage_array_df = pd.read_sql_table("spquery_inventory_array_data", con=conn)

        storage_sys_dict = storage_sys_df.to_json(orient="table")
        storage_sys_data = json.loads(storage_sys_dict)

        storage_array_dict = storage_array_df.to_json(orient="table")
        storage_array_data = json.loads(storage_array_dict)

        return storage_sys_data, storage_array_data

    def spark_get_sample_vol_io_trend_within_timerange(self, start_date, end_date) -> dict:
        """Get sample Volume IO trend data within given time range(start date and end date)

        Args:
            start_date (_type_): start date
            end_date (_type_): end date

        Returns:
            dict: volume io trend will be returned as dictionary format
        """
        self.load_spark_module_obj()
        self.vol_data_frame = self.context.mock_vol_perf_allcoll

        # pd_data_frame = pd.json_normalize(self.vol_data_frame)
        # convert_dict = {"id": str, "custid": str}
        # pd_data_frame = pd_data_frame.astype(convert_dict)

        self.spark_clone_data_frame = self.spark.createDataFrame(self.vol_data_frame)

        self.spark_clone_data_frame.createOrReplaceTempView("tempviewdf")

        df_volume_io_trend = self.spark_clone_data_frame.select(
            weekofyear("collectionstarttime").alias("week"),
            dayofweek("collectionstarttime").alias("weekday"),
            hour("collectionstarttime").alias("hour"),
            dayofmonth("collectionstarttime").alias("day"),
            to_date("collectionstarttime").alias("collectiontime"),
            "collectionstarttime",
            "custid",
            "id",
            "avgiops",
        ).where(f"collectionstarttime >= '{start_date}' and collectionstarttime <= '{end_date}'")
        pandas_data_frame = df_volume_io_trend.sample(0.1).toPandas()
        converted_dict = pandas_data_frame.to_json(orient="table")
        df_volume_io_trend_dict = json.loads(converted_dict)

        return df_volume_io_trend_dict

    def spark_get_sample_vol_io_trend(self) -> dict:
        """Get sample Volume io trend for all volume in all time range.

        Returns:
            dict: sample volume io trend in dictionary format
        """
        self.load_spark_module_obj()
        self.vol_data_frame = self.context.mock_vol_perf_allcoll

        # pd_data_frame = pd.json_normalize(self.vol_data_frame)
        # convert_dict = {"id": str, "custid": str}
        # pd_data_frame = pd_data_frame.astype(convert_dict)

        self.spark_clone_data_frame = self.spark.createDataFrame(self.vol_data_frame)

        self.spark_clone_data_frame.createOrReplaceTempView("tempviewdf")

        df_volume_io_trend = self.spark_clone_data_frame.select(
            weekofyear("collectionstarttime").alias("week"),
            dayofweek("collectionstarttime").alias("weekday"),
            hour("collectionstarttime").alias("hour"),
            dayofmonth("collectionstarttime").alias("day"),
            to_date("collectionstarttime").alias("collectiontime"),
            "collectionstarttime",
            "custid",
            "id",
            "avgiops",
        )
        pandas_data_frame = df_volume_io_trend.sample(0.1).toPandas()
        converted_dict = pandas_data_frame.to_json(orient="table")
        df_volume_io_trend_dict = json.loads(converted_dict)

        return df_volume_io_trend_dict

    def spark_inventory_product_details(self, sys_uuid: str = ""):
        self.load_spark_module_obj()
        self.inv_data_frame = self.context.mock_sys_lastcoll

        # pd_data_frame = pd.json_normalize(self.inv_data_frame)
        # convert_dict = {"storagesystotalused": str, "arrtotalused": str, "arrusablecapacity": str}
        # pd_data_frame = pd_data_frame.astype(convert_dict)

        self.spark_clone_data_frame = self.spark.createDataFrame(self.inv_data_frame)

        inv_df = (
            self.spark_clone_data_frame.select(
                "custid",
                "storagesysname",
                "storagesysid",
                "devicetype",
                "arrname",
            )
            .where(f"storagesysid == '{sys_uuid}'")
            .distinct()
        )

        pandas_data_frame = inv_df.toPandas()
        converted_dict = pandas_data_frame.to_json(orient="table")
        json1_data = json.loads(converted_dict)
        return json1_data

    def trigger_data_collection():
        topic = "panorama.fleet.hauler.collection"
        data = {}
        server = []
        producer = KafkaProducer(
            bootstrap_servers=server,
            value_serializer=lambda x: dumps(x).encode("utf-8"),
        )
        producer.send(topic, value=data)

    def get_all_response(self, func, limit=0, offset=0, **params):
        """
        Function to calculate and trigger multiple API/Array calls based on limit and offset. Collected response will be unified into single dictionary and converted to corresponding Class object.
        Arguments:
            func        (R) - Variable to recieve array or API methods and reused
            limit: int  (O) - Limit =0, means retreive all the records. Value passed to limit, means retreive number of records equal to value passed.
            offset: int (O) - Default value of pageOffset is 0. Determines from which offset the data should be read from table.
            params:     (O) - set of query parameters required for func()

        """
        response_list = []
        items = []

        # Get total items using default api call
        result = func(**params)
        total = result.total
        dataclass_type = type(result)
        if total != 0:
            # limit is passed as param
            limit_is_passed = limit != 0
            if limit_is_passed:
                rem_items = limit
            else:
                rem_items = total

            # Decide number of function calls required to get the complete set of data keeping 1000 as the maximum value of limit/pagelimit
            MAX_LIMIT = 1000
            while rem_items:
                if rem_items > MAX_LIMIT:
                    limit = MAX_LIMIT
                    rem_items = rem_items - limit
                elif rem_items < 10:
                    limit = 10
                    rem_items = 0
                else:
                    limit = rem_items
                    rem_items = rem_items - limit
                params["limit"] = limit
                params["offset"] = offset
                response_list.append(func(**params))
                offset += limit

            # Get list of parameters present as part of items dictionary
            sample_response = response_list[0].items[0]
            response_type = type(sample_response)
            response_params = list(response_type.__dataclass_fields__.keys())
            for item in response_list:
                for val in item.items:
                    temp_dict = {}
                    for param in response_params:
                        temp_dict[param] = val.__getattribute__(param)
                    items.append(temp_dict)

        # Compose dictionary by combining multiple response object
        response_dict = {"items": items, "count": 10, "offset": 0, "total": total}

        # Convert the dictionary to object using models and return the object.
        response_obj = dataclass_type(**response_dict)
        return response_obj

    def get_all_response_volactivity(self, func, limit=0, offset=0, **params):
        """
        Function to calculate and trigger multiple API/Array calls based on limit and offset where response will have list within list.
        Collected response will be unified into single dictionary and converted to corresponding Class object.
        Arguments:
            func        (R) - Variable to recieve array or API methods and reused
            limit: int  (O) - Limit =0, means retreive all the records. Value passed to limit, means retreive number of records equal to value passed.
            offset: int (O) - Default value of pageOffset is 0. Determines from which offset the data should be read from table.
            params:     (O) - set of query parameters required for func()
        """
        response_list = []
        items = []

        # Get total items using default api call
        # total = func(**params).total
        result = func(**params)
        total = result.total
        dataclass_type = type(result)
        # dataclass_type = type(func(**params))
        if total != 0:
            if limit != 0:
                rem_items = limit
            else:
                rem_items = total

            # Decide number of function calls required to get the complete set of data keeping 1000 as the maximum value of limit/pagelimit
            while rem_items:
                if rem_items > 1000:
                    limit = 1000
                    rem_items = rem_items - limit
                elif rem_items < 10:
                    limit = 10
                    rem_items = 0
                else:
                    limit = rem_items
                    rem_items = rem_items - limit
                params["limit"] = limit
                params["offset"] = offset
                response_list.append(func(**params))
                offset += limit

            # Get list of parameters present as part of items dictionary
            # Get the variables of class VolumeActivity to build dictionary
            # response_params = [
            #    param for param in dir(response_list[0].items[0]) if param not in dir(type(response_list##[0].items[0]))
            # ]
            response_params = list(VolumeActivity.__dataclass_fields__.keys())
            # Get the variables of class ActivityTrendDetail to build dictionary
            vars = list(ActivityTrendDetail.__dataclass_fields__.keys())
            # vars = [
            #    vars
            #   for vars in dir(response_list[0].items[0].activityTrendInfo[0])
            #   if vars not in dir(type(response_list[0].items[0].activityTrendInfo[0]))
            # ]

            items = []
            for item in response_list:
                for val in item.items:
                    temp_dict = {}
                    for param in response_params:
                        if param != "activityTrendInfo":
                            temp_dict[param] = val.__getattribute__(param)
                        else:
                            activity_list = []
                            if val.__getattribute__(param) != None:
                                for iter in val.__getattribute__(param):
                                    activity_dict = {}
                                    for var in vars:
                                        activity_dict[var] = iter.__getattribute__(var)
                                    activity_list.append(activity_dict)
                            else:
                                activity_list = None
                            temp_dict[param] = activity_list
                    items.append(temp_dict)

        # Compose dictionary by combining multiple response object
        response_dict = {"items": items, "count": 10, "offset": 0, "total": total}

        # Convert the dictionary to object using models and return the object.
        response_obj = dataclass_type(**response_dict)
        return response_obj

    def calculate_timeinterval(self, years=0, months=0, days=0, hours=0, minutes=0):
        """
        Function that provides startTime and endTime for filtering to be used in test cases.
        Arguments:
                            years= number of years to be backdated
                            months= number of months to be backdated
                            days= number of days to be backdated
                            hours= number of hours to be backdated
                            minutes= number of minutes to be backdated

        Return:
                Returns a dictionary of Starttime and endtime.

            endTimeime -> will be the current date and time.
            startTime -> will be the backdate from the current date and time based on the parameters passed.

        eg:- if years = 1, start-time will be backdated to 1 year from the current date
                     if months = 6, start-time will be backdated to 6 months from the current date
                     if days = 15, start-time will be backdated to 15 days from the current date
                     if months =3 and days =9, start-time will be backdated to 3 months 9 days from the current date
        """

        # etime = self.get_last_collection_end_time()
        etime = datetime.now()
        stime = etime - relativedelta(years=years, months=months, days=days, hours=hours, minutes=minutes)
        time_interval = {
            "starttime": stime.isoformat("T") + "Z",
            "endtime": etime.isoformat("T") + "Z",
        }
        return time_interval

    def get_timeinterval(self, granularity, etime=datetime.now()):
        """Method to get start and end time for API calls based on the granularity

        Args:
            granularity (str): Allowed values for "granularity" parameter are collectionHour, day and week.

        Returns:
            time_interval (dict): Returns start and end time as per granularity in dict format.
        """
        end_time = datetime(etime.year, etime.month, etime.day, etime.hour, etime.minute)
        if granularity == Granularity.hourly.value:
            start_time = end_time - relativedelta(days=random.randint(1, 7))
        if granularity == Granularity.daily.value:
            stime = end_time - relativedelta(days=random.randint(8, 180))
            start_time = datetime(stime.year, stime.month, stime.day)
        if granularity == Granularity.weekly.value:
            stime = end_time - relativedelta(days=random.randint(200, 360))
            stime = stime - relativedelta(days=stime.weekday())
            start_time = datetime(stime.year, stime.month, stime.day)
        time_interval = {
            "starttime": start_time.isoformat("T") + "Z",
            "endtime": end_time.isoformat("T") + "Z",
        }
        return time_interval

    def get_last_collection_end_time(self) -> datetime:
        """From the spark tables get the last collection end time

        Returns:
            datetime: last collection end time will be in this format (yyyy-mm-dd h:m:s) ex: 2022-03-12 01:32:20
        """
        self.vol_data_frame = self.context.mock_vol_lastcoll
        # pd_data_frame = pd.json_normalize(self.vol_data_frame)
        collection_end_time = self.vol_data_frame["collectionendtime"].max()
        etime = datetime.strptime(str(collection_end_time), "%Y-%m-%d %H:%M:%S")
        return etime

    def get_last_collection_start_time(self) -> datetime:
        """From the spark tables get the last collection start time

        Returns:
            datetime: last collection end time will be in this format (yyyy-mm-dd h:m:s) ex: 2022-03-12 01:32:20
        """
        self.vol_data_frame = self.context.mock_vol_lastcoll
        # pd_data_frame = pd.json_normalize(self.vol_data_frame)
        collection_start_time = self.vol_data_frame["collectionstarttime"].max()
        stime = datetime.strptime(str(collection_start_time), "%Y-%m-%d %H:%M:%S")
        return stime

    def convert_dict_keys_to_kebab_case(self, params):
        """This function converts keys of the dictionary from Pascal/Camel case to kebab case

        Returns:
            params:  dictionary (keys with kebab case)
        """

        def to_kebab_case(string):
            # Convert the first letter of the string to lowercase
            kebab_string = string[0].lower() + string[1:]
            # Replace any uppercase letters with a hyphen and lowercase letter
            kebab_string = "".join(["-" + i.lower() if i.isupper() else i for i in kebab_string])
            return kebab_string

        kebab_params = {}
        for key, value in params.items():
            kebab_key = to_kebab_case(key)
            kebab_params[kebab_key] = value
        return kebab_params

    def get_all_response_cloneactivity(self, func, limit=0, offset=0, **params):
        """
        Function to calculate and trigger multiple API/Array calls based on limit and offset where response will have list within list.
        Collected response will be unified into single dictionary and converted to corresponding Class object.
        This function will be used when collected response related to clone activity trend is required.
        Arguments:
            func        (R) - Variable to recieve array or API methods and reused
            limit: int  (O) - Limit =0, means retreive all the records. Value passed to limit, means retreive number of records equal to value passed.
            offset: int (O) - Default value of pageOffset is 0. Determines from which offset the data should be read from table.
            params:     (O) - set of query parameters required for func()
        """
        response_list = []
        items = []

        # Get total items using default api call
        result, temp_dict = func(**params)
        total = result.total
        dataclass_type = type(result)
        if total != 0:
            if limit != 0:
                rem_items = limit
            else:
                rem_items = total

            # Decide number of function calls required to get the complete set of data keeping 1000 as the maximum value of limit/pagelimit
            while rem_items:
                if rem_items > 1000:
                    limit = 1000
                    rem_items = rem_items - limit
                elif rem_items < 10:
                    limit = 10
                    rem_items = 0
                else:
                    limit = rem_items
                    rem_items = rem_items - limit
                params["limit"] = limit
                params["offset"] = offset
                query_result, query_dict = func(**params)
                response_list.append(query_result)
                offset += limit

            # Get list of parameters present as part of items dictionary
            # Get the variables of class CloneActivity to build dictionary
            response_params = list(CloneActivity.__dataclass_fields__.keys())

            # Get the variables of class ActivityTrendDetail to build dictionary
            vars = list(CloneActivityTrendDetail.__dataclass_fields__.keys())

            items = []
            for item in response_list:
                for val in item.items:
                    temp_dict = {}
                    for param in response_params:
                        if param != "activityTrendInfo":
                            temp_dict[param] = val.__getattribute__(param)
                        else:
                            activity_list = []
                            if val.__getattribute__(param) != None:
                                for iter in val.__getattribute__(param):
                                    activity_dict = {}
                                    for var in vars:
                                        activity_dict[var] = iter.__getattribute__(var)
                                    activity_list.append(activity_dict)
                            else:
                                activity_list = None
                            temp_dict[param] = activity_list
                    items.append(temp_dict)

        # Compose dictionary by combining multiple response object
        response_dict = {"items": items, "count": 10, "offset": 0, "total": total}

        # Convert the dictionary to object using models and return the object.
        response_obj = dataclass_type(**response_dict)
        return response_obj, response_dict
