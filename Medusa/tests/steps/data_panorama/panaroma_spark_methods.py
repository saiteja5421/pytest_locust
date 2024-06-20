################################################################
#
# File: panaroma_common_steps.py
# Author: Kranthi Kumar
# Date: Oct 15 2022
#
# (C) Copyright 2016 - Hewlett Packard Enterprise Development LP
#
################################################################
#
# Description:
#      module implementation.
#      Script contain S3 common
################################################################


import datetime
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
from dateutil.relativedelta import relativedelta
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
from tests.e2e.data_panorama.panorama_context import Context
from tests.steps.data_panorama.json_data_generator.data_generator import (
    JsonDataGenerator,
)
from functools import reduce
from utils.common_helpers import get_project_root
from lib.platform.storage_array.ssh_connection import SshConnection
import numpy as np
import sys


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


class Granularity(Enum):
    daily = "daily"
    hourly = "collectionHour"
    weekly = "weekly"


class PanaromaSparkMethods(object):
    """Class created to host new spark methods to calculate array data. Currently has volume consumption methods"""

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
        self.app_data_frame = ""
        self.spark_vol_data_frame = ""
        self.spark_clone_data_frame = ""
        self.spark_snaps_data_frame = ""
        self.spark_vol_perf_data_frame = ""
        self.spark_vol_usage_data_frame = ""
        self.spark_inventory_data_frame = ""
        self.spark_app_data_frame = ""
        self.generated_data = []
        self.app_snap_data = ""
        self.app_clone_data = ""
        self.spark = ""
        self.client = ""
        self.mock_folder = ""
        self.cost_dict = ""
        # Update this file as per the uploaded collection
        self.mock_db_path = f"tests/data_panaroma/mock_30_days.sqlite"
        if load_mock:
            self.load_mock_data()

    def load_spark_module_obj(self):
        findspark.init()
        self.spark = SparkSession.builder.appName("Medusa Saprk").master("local[1]").getOrCreate()

    def load_mock_data(self):
        """
        Loading spark tables from sqlite db file

        """
        # DB name required
        FILE_PATH = Path(os.path.dirname(os.path.abspath(__file__)))

        db_name = f"{FILE_PATH}/../../../{self.mock_db_path}"
        engine = sqlalchemy.create_engine("sqlite:///%s" % db_name, execution_options={"sqlite_raw_colnames": True})
        conn = engine.connect()

        # collection_df = pd.read_sql_table("collections_info", con=conn)

        # self.client.sftp_close()
        self.context.mock_collection_data = pd.read_sql_table("collections_info", con=conn)
        self.context.mock_sys_lastcoll = pd.read_sql_table("spark_systems", con=conn)
        self.context.mock_vol_lastcoll = pd.read_sql_table("spark_volumes", con=conn)
        self.context.mock_snap_lastcoll = pd.read_sql_table("spark_snapshots", con=conn)
        self.context.mock_clone_lastcoll = pd.read_sql_table("spark_clones", con=conn)
        self.context.mock_app_lastcoll = pd.read_sql_table("spark_appdata", con=conn)
        self.context.mock_vol_allcoll = pd.read_sql_table("spark_volumeusage", con=conn)
        self.context.mock_vol_perf_allcoll = pd.read_sql_table("spark_volume_performance", con=conn)
        self.context.cost_dict = {"03bf4f5020022edecad3a7642bfb5391": 8800}
        self.context.mock_vol_perf_allcoll = pd.read_sql_table("spark_volusage_lastcollection", con=conn)

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

    def new_spark_vol_consumption(self):
        """New spark volume consumtion method to generate

        Returns:
            vol_last_coll_dict (dict): Last collection volume data
            vol_avg_dict (dict): All collection volume average data
        """
        self.load_spark_module_obj()
        vol_usage_data = self.context.mock_vol_allcoll
        collection_data = self.context.mock_collection_data
        vol_last_coll_data = pd.DataFrame()
        coll_list = collection_data["collection_name"].unique()
        latest_collection = coll_list[-1]
        temp_df = vol_usage_data[vol_usage_data["collectionname"] == latest_collection]
        vol_last_coll_data["total_vol_count"] = [temp_df.shape[0]]
        vol_last_coll_data["vol_total_size_in_bytes"] = [temp_df["volumesize"].sum() * 1024 * 1024]
        vol_last_coll_data["vol_used_size_in_bytes"] = [temp_df["usedsize"].sum() * 1024 * 1024]
        vol_last_coll_dict = vol_last_coll_data.to_dict("records")[0]

        FILE_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
        db_name = f"{FILE_PATH}/../../../{self.mock_db_path}"
        engine = sqlalchemy.create_engine("sqlite:///%s" % db_name, execution_options={"sqlite_raw_colnames": True})
        conn = engine.connect()
        start = collection_data[collection_data["collection_name"] == "collection-1"]["collection_start_date"][0]
        end = pd.to_datetime(datetime.now())
        period_range = pd.period_range(start=start, end=end, freq="M")
        time_df = pd.DataFrame({"time_period": period_range})
        time_df["customer_id"] = vol_usage_data.iloc[0].custid
        vol_usage_data = vol_usage_data[["collectionstarttime", "volumesize"]]
        vol_usage_data.rename(columns={"collectionstarttime": "time_period"}, inplace=True)
        vol_usage_data["time_period"] = vol_usage_data["time_period"].dt.to_period("M")
        final_df = vol_usage_data.groupby("time_period").sum().reset_index()
        time_df = pd.merge(time_df, final_df, on="time_period", how="left")
        time_df["volumesize"] = time_df["volumesize"].fillna(0).astype(int)
        time_df["time_period"] = time_df["time_period"].astype(str)
        time_df.to_sql("volume_monthly_avg", engine, if_exists="replace", index=False)
        vol_avg_dict = {
            "current_month_utilized_size_in_bytes": time_df.iloc[time_df.shape[0] - 1]["volumesize"],
            "previous_month_utilized_size_in_bytes": time_df.iloc[time_df.shape[0] - 2]["volumesize"],
            "customer_id": time_df.iloc[0]["customer_id"],
        }
        return vol_last_coll_dict, vol_avg_dict
