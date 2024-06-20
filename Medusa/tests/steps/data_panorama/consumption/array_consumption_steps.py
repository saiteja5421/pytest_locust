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

# import datetime
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta, MO
from pyspark.sql.functions import date_sub, expr, when

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
    ClonesIoTrend,
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
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps, Granularity
import re

# from datetime import datetime
# from datetime import timedelta
#

# import datetime


class ArrayConfigParser(object):
    def __init__(self, context: Context, load_mock=True):
        self.steps_obj = PanaromaCommonSteps(context=context, load_mock=load_mock)
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
        # total_size = int(self.format_size(total_size, "B", "GB"))
        # total_used = int(self.format_size(total_used, "B", "GB"))
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
        """
        This function fetches all the volumes related information
        The sample response would be like response = {
           "totalVolumesCreated": 100,
           "totalSpace": 250,
           "utilizedSpace": 100,
           "unutilizedSpace": 150,
           "totalCost": 20,
           "previousMonthTotalCost": 5,
           "previousMonthUtilizedSpace": 80,
           "currentMonthTotalCost": xx
           "currentMonthUtilizedSpace": xx
           "id": id,
            "name": name,
            "type": type,
            "generation": generation,
            "resourceUri": resourceUri,
            "customerId": customerId,
            "consoleUri": consoleUri
        }

        """
        result = {}
        common_fields = self.common_field_generator()
        result.update(common_fields)
        vol_consumption_data = self.steps_obj.spark_vol_consumption()
        result["type"] = "volumes consumption"
        result["generation"] = 1
        result.update(vol_consumption_data)
        return VolumesConsumption(**result)

    def get_volumes_cost_trend(self, **params) -> VolumesCostTrend:
        """
                This function fetches the monthly cost for the volumes created.
                    If get response is success (200) then function will return object of volumescostTrend
                    In Case of failure (apart from 200) it will return the actual response code
        Query parameter should be passed as argument - num_months:int
                By default 6 months data will be shown, if the filter is passed then will be showing those many months data from the current month
        Arguments
        **params :-Required params values will be like below Ex: num_months=2
        Return:
        if status code OK:-
                response = {
                        "totalVolumesCost": [
                        {"year" : 1987, "month" : 23, "totalUsageCost" : 100, "currencyType" : "xyz"}
        ],
         "count": 1,
        }
        else response code :- 400 or 401 or 500
        """
        cost_trend_frame = self.steps_obj.spark_vol_cost_trend(
            start_date=params["start_date"], end_date=params["end_date"]
        )

        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        cost_trend_data = {"items": []}
        temp_cost_trend_data = {}
        total_index = 0
        for index, data_dict in enumerate(cost_trend_frame["data"]):
            total_index += 1

            temp_cost_trend_data = {
                "year": int(data_dict["collectionstarttime"].split("-")[0]),
                "month": int(data_dict["collectionstarttime"].split("-")[1]),
                "cost": data_dict["agg_usage_cost"],
                "currency": "USD",
            }
            common_fields = self.common_field_generator(customerId=data_dict["custid"])
            temp_cost_trend_data.update(common_fields)
            cost_trend_data["items"].append(copy.deepcopy(temp_cost_trend_data))
        cost_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
        return VolumesCostTrend(**cost_trend_data)

    def get_volumes_usage_trend(self, **params) -> VolumesUsageTrend:
        """
                This function fetches the monthly cost for the volumes created.
                    If get response is success (200) then function will return object of volumescostTrend
                    In Case of failure (apart from 200) it will return the actual response code
        Query parameter should be passed as argument - num_months:int
                By default 6 months data will be shown, if the filter is passed then will be showing those many months data from the current month
        Arguments
        **params :-Required params values will be like below Ex: num_months=2
        Return:
        if status code OK:-
                response = {
                        "totalVolumesCost": [
                        {"year" : 1987, "month" : 23, "totalUsageCost" : 100, "currencyType" : "xyz"}
        ],
         "count": 1,
        }
        else response code :- 400 or 401 or 500
        """
        granularity = 0 if "granularity" not in params else params["granularity"]
        vol_usage_trend_frame, granularity = self.steps_obj.spark_vol_usage_trend(
            start_date=params["start_date"], end_date=params["end_date"], granularity=granularity
        )
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        usage_trend_data = {"items": []}
        temp_usage_trend_data = {}
        total_index = 0
        if granularity == Granularity.hourly.value:
            for index, data_dict in enumerate(vol_usage_trend_frame["data"]):
                total_index += 1
                # if data_dict["hour"] <= 9:
                #    h = "0" + str(data_dict["hour"])
                # else:
                #    h = str(data_dict["hour"])
                time_stamp = str(data_dict["collectionendtime"])
                time_stamp = time_stamp[:-4]

                time_stamp = time_stamp.replace(" ", "T") + "Z"

                temp_usage_trend_data = {
                    "timeStamp": time_stamp,
                    "totalUsageInBytes": int(data_dict["usedsize_bytes"]),
                }
                common_fields = self.common_field_generator(
                    type="volumes usage trend", generation=1, customerId=vol_usage_trend_frame["data"][0]["custid"]
                )
                temp_usage_trend_data.update(common_fields)
                usage_trend_data["items"].append(copy.deepcopy(temp_usage_trend_data))
            usage_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return VolumesUsageTrend(**usage_trend_data)
        elif granularity == Granularity.daily.value:
            for index, data_dict in enumerate(vol_usage_trend_frame["data"]):
                total_index += 1
                temp_usage_trend_data = {
                    "timeStamp": data_dict["collectiontime"]["start_time"].replace(".000", "Z"),
                    "totalUsageInBytes": int(data_dict["usedsize_bytes"]),
                }
                common_fields = self.common_field_generator(
                    type="volumes usage trend", generation=1, customerId=data_dict["custid"]
                )
                temp_usage_trend_data.update(common_fields)
                usage_trend_data["items"].append(copy.deepcopy(temp_usage_trend_data))
            usage_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return VolumesUsageTrend(**usage_trend_data)
        elif granularity == Granularity.weekly.value:
            for index, data_dict in enumerate(vol_usage_trend_frame["data"]):
                total_index += 1
                week_date = data_dict["collectiontime"]["start_time"].replace("T00:00:00.000", "")
                date_1 = datetime.strptime(week_date, "%Y-%m-%d")
                # final_week_date = date_1 + datetime.timedelta(days=1)
                t_stamp = date_1.strftime("%Y-%m-%dT%H:%M:%SZ")

                temp_usage_trend_data = {
                    "timeStamp": t_stamp,
                    "totalUsageInBytes": int(data_dict["usedsize_bytes"]),
                }
                common_fields = self.common_field_generator(
                    type="volumes usage trend", generation=1, customerId=data_dict["custid"]
                )
                temp_usage_trend_data.update(common_fields)
                usage_trend_data["items"].append(copy.deepcopy(temp_usage_trend_data))
            usage_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return VolumesUsageTrend(**usage_trend_data)

    def get_volumes_creation_trend(self, **params) -> VolumesCreationTrend:
        # start_time, end_time, granularity
        """
                This function will create volume creation trend
        """
        granularity = 0 if "granularity" not in params else params["granularity"]
        vol_creation_trend_frame, granularity = self.steps_obj.spark_vol_creation_trend(
            start_date=params["start_date"], end_date=params["end_date"], granularity=granularity
        )

        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        creation_trend_data = {"items": []}
        temp_creation_trend_data = {}
        total_index = 0
        if granularity == Granularity.hourly.value:
            for index, data_dict in enumerate(vol_creation_trend_frame["data"]):
                if data_dict["newvolumes_created"] > 0:
                    total_index += 1
                    # coll_start_time = str(data_dict["collectionendtime"].replace(".000", "")) + "Z"
                    coll_end_time_stamp = str(data_dict["collectionendtime"].replace(".000", "")) + "Z"
                    temp_creation_trend_data = {
                        "updatedAt": coll_end_time_stamp, 
                        "aggrWindowTimestamp": str(data_dict["aggrWindowTimestamp"].replace(".000", "")) + "Z",
                        "numVolumes": data_dict["newvolumes_created"]
                        }
                    common_fields = self.common_field_generator(
                        type="volumes creation trend", generation=1, customerId=data_dict["custid"]
                    )
                    temp_creation_trend_data.update(common_fields)
                    creation_trend_data["items"].append(copy.deepcopy(temp_creation_trend_data))
            creation_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return VolumesCreationTrend(**creation_trend_data)
        elif granularity == Granularity.daily.value:
            for index, data_dict in enumerate(vol_creation_trend_frame["data"]):
                total_index += 1
                temp_creation_trend_data = {
                    "updatedAt": data_dict["updatedAt"],
                    "aggrWindowTimestamp": data_dict["updatedAt"],
                    "numVolumes": data_dict["volumecount"],
                }
                common_fields = self.common_field_generator(
                    type="volumes creation trend", generation=1, customerId=data_dict["custid"]
                )

                temp_creation_trend_data.update(common_fields)
                creation_trend_data["items"].append(copy.deepcopy(temp_creation_trend_data))
            creation_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return VolumesCreationTrend(**creation_trend_data)
        elif granularity == Granularity.weekly.value:
            for index, data_dict in enumerate(vol_creation_trend_frame["data"]):
                total_index += 1
                temp_creation_trend_data = {
                    "updatedAt": data_dict["updatedAt"],
                    "aggrWindowTimestamp": data_dict["updatedAt"],
                    "numVolumes": data_dict["volumecount"],
                }
                common_fields = self.common_field_generator(
                    type="volumes creation trend", generation=1, customerId=data_dict["custid"]
                )
                temp_creation_trend_data.update(common_fields)
                temp_creation_trend_data["customerId"] = data_dict["custid"]
                creation_trend_data["items"].append(copy.deepcopy(temp_creation_trend_data))
            creation_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return VolumesCreationTrend(**creation_trend_data)

    def get_volumes_activity_trend(self, **params) -> VolumesActivityTrend:
        """
                    This function fetches all the volumes activity for the specific customer
                        If get response is success (200) then function will return object of volumescostTrend
                        In Case of failure (apart from 200) it will return the actual response code
                        Query parameters should be passed as arguments- provisionType(O):str,minIo(O):float,maxIo(O):float,minVolumeSize(O):int,maxVolumeSize:int,country:str,state:str,city:str,postalCode:str,activityTrendGranularity:str- the other parameters are yet to be discussed(whether required or Optional)
            Allowed values for "activityTrendGranularity" are week and month. Default value is month
                The sample response would be like response = {
            "volumeActivityDetails": [
                {"volumeId" : "abc", "volumeName" : "xyz", "provisionType" : "abc", "totalSpace" : 100, "utilizedSpace" : 20, "creationTime" : 2021-11-12, "connected" : True, "ioActivity" : 23, "arrayName" : "abc", "activityTrend" : [{"timeStamp" : 2021-11-11, "ioActivity" : 30 }] }
          ],
           "count": 1,
        }
        """
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]
        pro_type = "" if "provisionType" not in params else params["provisionType"]
        min_io = 0 if "min_io" not in params else params["min_io"]
        max_io = 0 if "max_io" not in params else params["max_io"]
        min_vol_size = 0 if "minVolumeSize" not in params else params["minVolumeSize"]
        max_vol_size = 0 if "maxVolumeSize" not in params else params["maxVolumeSize"]

        activity_trend_frame = self.steps_obj.spark_vol_activity_trend(
            provisiontype=pro_type,
            min_vol_size=min_vol_size,
            max_vol_size=max_vol_size,
            min_io=min_io,
            max_io=max_io,
        )
        temp_activity_trend_data = {"items": []}
        # temp_activity_trend = {}

        # {'index': 0, 'volumeId': '063a28a72604d127d70000000000000000000000010',
        #'provisiontype': 'thin', 'volumesize': 371384, 'creationTime': '2019-10-02 13:56:08',
        #'age': 38.0, 'arrid': '093a28a81197d127d7000000000000000000000001',
        #'totalavgioactivity': 12.6666666667, 'usedsize': 8708,
        #'activitytrendinfo': [[11, 20.0], [9, 10.0], [10, 8.0]]}
        total_index = 0
        for index, data_dict in enumerate(activity_trend_frame["data"]):
            temp_activity_trend = {}
            total_index += 1
            common_fields = self.common_field_generator(
                type="volumes activity trend", generation=1, customerId=data_dict["custid"]
            )
            temp_activity_trend.update(common_fields)
            temp_activity_trend["activityTrendInfo"] = []
            temp_activity_trend["id"] = data_dict["volumeId"]
            temp_activity_trend["name"] = data_dict["name"]
            p_type = data_dict["provisiontype"].capitalize()
            temp_activity_trend["provisionType"] = p_type
            temp_activity_trend["totalSizeInBytes"] = data_dict["volumesize_bytes"]
            temp_activity_trend["utilizedSizeInBytes"] = int(data_dict["usedsize_bytes"])
            c_time = data_dict["creationTime"].replace(" ", "T") + "Z"
            # 1970-01-20T05:10:09.718000000T+0000TUTC.000Z
            c_time = re.sub("(.*)\..*", r"\1Z", c_time)
            temp_activity_trend["createdAt"] = c_time
            # temp_activity_trend["volumeCreationAge"] = data_dict["age"]
            temp_activity_trend["ioActivity"] = data_dict["avgiops"]
            # temp_activity_trend["ioActivity"] = data_dict["avgiops"]
            temp_activity_trend["system"] = data_dict["system_name"]
            temp_activity_trend["systemId"] = data_dict["storagesysid"]
            temp_activity_trend["utilizedPercentage"] = data_dict["utilizedPercentage"]
            for t_info in data_dict["activitytrendinfo"]:
                t_info_dict = {}
                month = t_info[1]
                if t_info[1] < 10:
                    month = "0" + str(t_info[1])
                t_info_dict["timeStamp"] = str(t_info[0]) + "-" + str(month) + "-" + "01" + "T00:00:00Z"
                t_info_dict["ioActivity"] = t_info[2]
                temp_activity_trend["activityTrendInfo"].append(copy.deepcopy(t_info_dict))

            temp_activity_trend_data["items"].append(temp_activity_trend)
        temp_activity_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
        return VolumesActivityTrend(**temp_activity_trend_data)

    def get_volumes_activity_trend_by_io(self, **params) -> VolumesActivityTrend:
        """
        This function fetches all the volumes activity for the specific customer
        If get response is success (200) then function will return object of volumescostTrend
        In Case of failure (apart from 200) it will return the actual response code
        Query parameters should be passed as arguments- provisionType(O):str,minIo(O):float,maxIo(O)
        The sample response would be like this,
        VolumeActivity(id='c1e3ceead2e8431c9041845d73e4cde7', name='Virtual Volume pqa_dt1_volume_30', provisionType='Thin', totalSizeInBytes=33285996544, utilizedSizeInBytes=22318940160, createdAt='2022-09-22T12:00:00Z', ioActivity=55, system='System systems_5CSC73PAC4', systemId='5CSC73PAC4', activityTrendInfo=[ActivityTrendDetail(timeStamp='2022-09-01T00:00:00Z', ioActivity=54.92), ActivityTrendDetail(timeStamp='2022-10-01T00:00:00Z', ioActivity=55.666666666666664)], type='volumes activity trend', generation=1, resourceUri='', customerId='03bf4f5020022edecad3a7642bfb5391', consoleUri='')
        """
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]
        pro_type = "" if "provisionType" not in params else params["provisionType"]
        min_io = 0 if "minIo" not in params else params["minIo"]
        max_io = 0 if "maxIo" not in params else params["maxIo"]

        activity_trend_frame_io, activity_trend_frame_ptype = self.steps_obj.spark_vol_activity_trend_by_io(
            provisiontype=pro_type,
            min_io=min_io,
            max_io=max_io,
        )
        fin_temp_activity_trend_frame = {"items": []}
        total = 0
        for key, val in activity_trend_frame_io.items():
            for row in val:
                temp_activity_trend_frame = {}
                temp_activity_trend_frame["id"] = row["volumeId"]
                temp_activity_trend_frame["name"] = row["name"]
                temp_activity_trend_frame["provisionType"] = row["provisiontype"]
                temp_activity_trend_frame["totalSizeInBytes"] = row["volumesize_bytes"]
                temp_activity_trend_frame["utilizedSizeInBytes"] = row["usedsize_bytes"]
                temp_activity_trend_frame["createdAt"] = row["creationTime"].strftime("%Y-%m-%dT%H:%M:%SZ")
                temp_activity_trend_frame["ioActivity"] = row["last7days_avgiops"]
                temp_activity_trend_frame["systemId"] = row["storagesysid"]
                temp_activity_trend_frame["system"] = row["system"]
                temp_activity_trend_frame["activityTrendInfo"] = row["activityTrendInfo"]
                temp_activity_trend_frame["type"] = "volumes activity trend"
                temp_activity_trend_frame["generation"] = 1
                temp_activity_trend_frame["resourceUri"] = ""
                temp_activity_trend_frame["consoleUri"] = ""
                temp_activity_trend_frame["customerId"] = row["custid"]
                temp_activity_trend_frame["utilizedPercentage"] = row["utilizedPercentage"]
                fin_temp_activity_trend_frame["items"].append(temp_activity_trend_frame)
                total += 1
        fin_temp_activity_trend_frame.update({"offset": page_offset, "total": total, "count": page_limit})
        return VolumesActivityTrend(**fin_temp_activity_trend_frame), activity_trend_frame_ptype

    def get_volumes_activity_trend_by_size(self, **params) -> VolumesActivityTrend:
        """
        This function fetches all the volumes activity for Thick provision type for a certain volume size range
        If get response is success (200) then function will return object of volumeactivityTrend
        In Case of failure (apart from 200) it will return the actual response code
        Query parameters should be passed as arguments- provisionType(O):str,minIo(O):float,maxIo(O)
        The sample response would be like response =
        {
            "items": [
                {
                "id": "d56654a8da4c44bdaf313805937ce696",
                "name": "pqa_dt2_volume_21",
                "provisionType": "Thick",
                "totalSizeInBytes": 3221225472,
                "utilizedSizeInBytes": 1680867328,
                "createdAt": "2022-10-10T00:00:00Z",
                "ioActivity": 55,
                "systemId": "969102a3c85b473991ca52eaafc3fe09",
                "system": "system2",
                "activityTrendInfo": [
                    {
                    "timeStamp": "2022-10-01T00:00:00Z",
                    "ioActivity": 51.714287
                    }
                ],
                "type": "volumes activity trend",
                "generation": 1,
                "resourceUri": "",
                "consoleUri": "",
                "customerId": "03bf4f5020022edecad3a7642bfb5391"
                }
            ],
            "offset": 0,
            "total": 1,
            "count": 1
            }
        """
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]
        pro_type = "" if "provisionType" not in params else params["provisionType"]
        min_vol_size = 0 if "minVolumeSize" not in params else params["minVolumeSize"]
        max_vol_size = 2000000000 if "maxVolumeSize" not in params else params["maxVolumeSize"]

        activity_trend_frame = self.steps_obj.spark_vol_activity_trend_by_size(
            provisiontype=pro_type,
            min_vol_size=min_vol_size,
            max_vol_size=max_vol_size,
        )
        fin_temp_activity_trend_frame = {"items": []}
        total = 0
        for key, val in activity_trend_frame.items():
            for row in val:
                temp_activity_trend_frame = {}
                temp_activity_trend_frame["id"] = row["volumeId"]
                temp_activity_trend_frame["name"] = row["name"]
                temp_activity_trend_frame["provisionType"] = row["provisiontype"]
                temp_activity_trend_frame["totalSizeInBytes"] = row["volumesize_bytes"]
                temp_activity_trend_frame["utilizedSizeInBytes"] = row["usedsize_bytes"]
                temp_activity_trend_frame["createdAt"] = row["creationTime"].strftime("%Y-%m-%dT%H:%M:%SZ")
                temp_activity_trend_frame["ioActivity"] = row["last7days_avgiops"]
                temp_activity_trend_frame["systemId"] = row["storagesysid"]
                temp_activity_trend_frame["system"] = row["system"]
                temp_activity_trend_frame["activityTrendInfo"] = row["activityTrendInfo"]
                temp_activity_trend_frame["type"] = "volumes activity trend"
                temp_activity_trend_frame["generation"] = 1
                temp_activity_trend_frame["resourceUri"] = ""
                temp_activity_trend_frame["consoleUri"] = ""
                temp_activity_trend_frame["customerId"] = row["custid"]
                temp_activity_trend_frame["utilizedPercentage"] = row["utilizedPercentage"]
                fin_temp_activity_trend_frame["items"].append(temp_activity_trend_frame)
                total += 1
        fin_temp_activity_trend_frame.update({"offset": page_offset, "total": total, "count": page_limit})
        return VolumesActivityTrend(**fin_temp_activity_trend_frame)

    def get_volume_usage_trend(self, **params) -> VolumeUsage:
        """
                    This function fetches the overall individual volume usage data for the specific time intervals
                        If get response is success (200) then function will return object of volumescostTrend
                        In Case of failure (apart from 200) it will return the actual response code
                        Path parameter should be passed as arguments- volume_uuid:str
                        Query params can take any of the following query parameter
                        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|monthly"
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily

        Return:
            if status code OK:-
                response = {
                "volumeUsageDetails": [
                {"timeStamp" : "2020-11-11 2:43:34", "totalVolumeUsage" : 100}
                ],
                "count": 1,
            }
            else response code :- 400 or 401 or 500
        """
        vol_uuid_usage_trend_frame = self.steps_obj.spark_vol_uuid_usage_trend(
            vol_uuid=params["vol_uuid"],
        )
        temp_vol_uuid_usage_trend_data = {}

        # 2021-11-23 17:47:57.365000000 +0000 UTC
        t_stamp = re.sub(r"(.*)(\.[0-9]+\s.*)", r"\1", vol_uuid_usage_trend_frame["data"][0]["creationTime"])
        # t_stamp = vol_uuid_usage_trend_frame["data"][0]["creationTime"]

        # t_stamp_date_format=datetime.strptime(t_stamp,"%Y-%m-%dT%H:%M:%S.%f")
        # t_stamp_str= t_stamp_date_format.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-4]
        # t_stamp = vol_uuid_usage_trend_frame["data"][0]["creationTime"][:-4]
        t_stamp = t_stamp[:-4]

        t_stamp = t_stamp.replace(" ", "T") + "Z"
        temp_vol_uuid_usage_trend_data = {
            "createdAt": t_stamp,
            "provisionType": vol_uuid_usage_trend_frame["data"][0]["provisiontype"].capitalize(),
            "utilizedSizeInBytes": int(vol_uuid_usage_trend_frame["data"][0]["usedsize_bytes"]),
            "totalSizeInBytes": int(vol_uuid_usage_trend_frame["data"][0]["volumesize_bytes"]),
        }
        common_fields = self.common_field_generator(
            type="usage per volume", generation=1, customerId=vol_uuid_usage_trend_frame["data"][0]["custid"]
        )
        temp_vol_uuid_usage_trend_data.update(common_fields)

        return VolumeUsage(**temp_vol_uuid_usage_trend_data)

    def get_volume_time_stamp_usage_trend(self, **params) -> VolumeUsageTrend:
        """
        This function fetches the overall individual volume usage data for the specific time intervals
            If get response is success (200) then function will return object of volumescostTrend
            In Case of failure (apart from 200) it will return the actual response code
            Path parameter should be passed as arguments- volume_uuid:str
            Query params can take any of the following query parameter
            During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|monthly"
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily

        Return:
            if status code OK:-
                response = {
                    "volumeUsageDetails": [
                        {
                            "timeStamp": "2023-06-05T00:00:00Z",
                            "totalUsageInBytes": 255035179008,
                            "id": "usage per volume-1685923200000",
                            "name": "usage per volume-1685923200000",
                            "type": "usage per volume",
                            "generation": 1,
                            "resourceUri": "",
                            "consoleUri": "",
                            "customerId": "03bf4f5020022edecad3a7642bfb5391"
                        },
                    "count": 1,
                }
            else response code :- 400 or 401 or 500
        """

        granularity = 0 if "granularity" not in params else params["granularity"]
        vol_uuid_usage_trend_frame, granularity = self.steps_obj.spark_vol_uuid_time_stamp_usage_trend(
            system_id=params["system_id"],
            vol_uuid=params["vol_uuid"],
            start_date=params["start_date"],
            end_date=params["end_date"],
            granularity=granularity,
        )

        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        vol_uuid_usage_trend_data = {"items": []}
        temp_vol_uuid_usage_trend_data = {}
        total_index = 0

        if granularity == Granularity.hourly.value:
            for index, data_dict in enumerate(vol_uuid_usage_trend_frame["data"]):
                total_index += 1
                time_stamp = str(data_dict["collectionendtime"])
                time_stamp = time_stamp[:-4]
                time_stamp = time_stamp.replace(" ", "T") + "Z"

                temp_vol_uuid_usage_trend_data = {
                    "timeStamp": time_stamp,
                    "totalUsageInBytes": int(data_dict["totalusedsize"]),
                }
                common_fields = self.common_field_generator(
                    type="usage per volume", generation=1, customerId=data_dict["custid"]
                )
                temp_vol_uuid_usage_trend_data.update(common_fields)
                vol_uuid_usage_trend_data["items"].append(copy.deepcopy(temp_vol_uuid_usage_trend_data))
            vol_uuid_usage_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return VolumeUsageTrend(**vol_uuid_usage_trend_data)

        elif granularity == Granularity.daily.value:
            for index, data_dict in enumerate(vol_uuid_usage_trend_frame["data"]):
                total_index += 1
                day_date = data_dict["collectiontime"]["start_time"].replace("T00:00:00.000", "")
                date_1 = datetime.strptime(day_date, "%Y-%m-%d")
                time_stamp = date_1.strftime("%Y-%m-%dT%H:%M:%SZ")
                temp_vol_uuid_usage_trend_data = {
                    "timeStamp": time_stamp,
                    "totalUsageInBytes": data_dict["usedsize_bytes"],
                }
                common_fields = self.common_field_generator(
                    type="usage per volume", generation=1, customerId=data_dict["custid"]
                )
                temp_vol_uuid_usage_trend_data.update(common_fields)
                vol_uuid_usage_trend_data["items"].append(copy.deepcopy(temp_vol_uuid_usage_trend_data))
            vol_uuid_usage_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return VolumeUsageTrend(**vol_uuid_usage_trend_data)

        elif granularity == Granularity.weekly.value:
            for index, data_dict in enumerate(vol_uuid_usage_trend_frame["data"]):
                total_index += 1
                week_date = data_dict["collectiontime"]["start_time"].replace("T00:00:00.000", "")
                date_1 = datetime.strptime(week_date, "%Y-%m-%d")
                time_stamp = date_1.strftime("%Y-%m-%dT%H:%M:%SZ")
                temp_vol_uuid_usage_trend_data = {
                    "timeStamp": time_stamp,
                    "totalUsageInBytes": data_dict["usedsize_bytes"],
                }
                common_fields = self.common_field_generator(
                    type="usage per volume", generation=1, customerId=data_dict["custid"]
                )
                temp_vol_uuid_usage_trend_data.update(common_fields)
                vol_uuid_usage_trend_data["items"].append(copy.deepcopy(temp_vol_uuid_usage_trend_data))
            vol_uuid_usage_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return VolumeUsageTrend(**vol_uuid_usage_trend_data)

    def get_volume_io_trend(self, **params) -> VolumeIoTrend:
        """
                    This function fetches the overall IO activity data for the specific time intervals
                        If get response is success (200) then function will return object of volumescostTrend
                        In Case of failure (apart from 200) it will return the actual response code
                        Path parameter should be passed as arguments- volume_uuid:str
                        Query params can take any of the following query parameter
                        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|monthly"
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily

        Return:
            if status code OK:
                response = {
                "ioactivityDetails": [
                {"timeStamp" : "2020-11-11 2:43:34", "ioactivityUsage" : 100}
            ],
            "count": 1,
            }
            else response code :- 400 or 401 or 500
        """
        granularity = 0 if "granularity" not in params else params["granularity"]
        vol_uuid_usage_trend_frame, granularity = self.steps_obj.spark_vol_uuid_io_trend(
            vol_uuid=params["vol_uuid"],
            start_date=params["start_date"],
            end_date=params["end_date"],
            granularity=granularity,
        )
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        vol_uuid_io_trend_data = {"items": []}
        temp_vol_uuid_io_trend_data = {}
        total_index = 0
        if granularity == Granularity.hourly.value:
            for index, data_dict in enumerate(vol_uuid_usage_trend_frame["data"]):
                total_index += 1
                common_fields = self.common_field_generator(
                    type="IO per volume", generation=1, customerId=data_dict["custid"]
                )
                temp_vol_uuid_io_trend_data.update(common_fields)
                time_stamp = data_dict["collectionendtime"].replace(".000", "Z")
                temp_vol_uuid_io_trend_data["timeStamp"] = time_stamp
                temp_vol_uuid_io_trend_data["ioActivity"] = data_dict["avgiops"]
                temp_vol_uuid_io_trend_data["generation"] = 1
                temp_vol_uuid_io_trend_data["customerId"] = data_dict["custid"]

                vol_uuid_io_trend_data["items"].append(copy.deepcopy(temp_vol_uuid_io_trend_data))
            vol_uuid_io_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return VolumeIoTrend(**vol_uuid_io_trend_data)
        elif granularity == Granularity.daily.value:
            for index, data_dict in enumerate(vol_uuid_usage_trend_frame["data"]):
                total_index += 1
                common_fields = self.common_field_generator(
                    type="IO per volume", generation=1, customerId=data_dict["custid"]
                )
                temp_vol_uuid_io_trend_data.update(common_fields)
                temp_vol_uuid_io_trend_data["timeStamp"] = data_dict["collectiontime"].replace(".000", "Z")
                temp_vol_uuid_io_trend_data["ioActivity"] = data_dict["avg_io_trend"]
                temp_vol_uuid_io_trend_data["generation"] = 1
                temp_vol_uuid_io_trend_data["customerId"] = data_dict["custid"]
                vol_uuid_io_trend_data["items"].append(copy.deepcopy(temp_vol_uuid_io_trend_data))
            vol_uuid_io_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return VolumeIoTrend(**vol_uuid_io_trend_data)
        elif granularity == Granularity.weekly.value:
            for index, data_dict in enumerate(vol_uuid_usage_trend_frame["data"]):
                total_index += 1
                # t_stamp = data_dict["lastcolltime"]
                # t_stamp = t_stamp.replace(" ","T")
                # t_stamp = t_stamp + ".000Z"
                common_fields = self.common_field_generator(
                    type="IO per volume", generation=1, customerId=data_dict["custid"]
                )
                week_date = data_dict["collectiontime"]["start_time"].replace("T00:00:00.000", "")
                collection_week_start = datetime.strptime(week_date, "%Y-%m-%d")
                t_stamp = collection_week_start.strftime("%Y-%m-%dT%H:%M:%SZ")
                temp_vol_uuid_io_trend_data.update(common_fields)
                temp_vol_uuid_io_trend_data["timeStamp"] = t_stamp
                temp_vol_uuid_io_trend_data["ioActivity"] = data_dict["avgiops"]
                temp_vol_uuid_io_trend_data["generation"] = 1
                temp_vol_uuid_io_trend_data["customerId"] = data_dict["custid"]
                vol_uuid_io_trend_data["items"].append(copy.deepcopy(temp_vol_uuid_io_trend_data))
            vol_uuid_io_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return VolumeIoTrend(**vol_uuid_io_trend_data)

    def get_clone_io_trend(self, **params) -> ClonesIoTrend:
        """
                    This function fetches the overall IO activity data for the specific time intervals
                        If get response is success (200) then function will return object of volumescostTrend
                        In Case of failure (apart from 200) it will return the actual response code
                        Path parameter should be passed as arguments- volume_uuid:str
                        Query params can take any of the following query parameter
                        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|monthly"
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily

        Return:
            if status code OK:
                response = {
                "ioactivityDetails": [
                {"timeStamp" : "2020-11-11 2:43:34", "ioactivityUsage" : 100}
            ],
            "count": 1,
            }
            else response code :- 400 or 401 or 500
        """
        granularity = 0 if "granularity" not in params else params["granularity"]
        vol_uuid_usage_trend_frame, granularity = self.steps_obj.spark_clone_io_trend(
            vol_uuid=params["vol_uuid"],
            start_date=params["start_date"],
            end_date=params["end_date"],
            granularity=granularity,
        )
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        clone_io_trend_data = {"items": []}
        temp_clone_io_trend_data = {}
        total_index = 0
        if granularity == Granularity.hourly.value:
            for index, data_dict in enumerate(vol_uuid_usage_trend_frame["data"]):
                total_index += 1
                common_fields = self.common_field_generator(
                    type="IO per volume", generation=1, customerId=data_dict["custid"]
                )
                temp_clone_io_trend_data.update(common_fields)
                time_stamp = data_dict["collectionendtime"].replace(".000", "Z")
                temp_clone_io_trend_data["timeStamp"] = time_stamp
                temp_clone_io_trend_data["ioActivity"] = data_dict["avgiops"]
                temp_clone_io_trend_data["generation"] = 1

                clone_io_trend_data["items"].append(copy.deepcopy(temp_clone_io_trend_data))
            clone_io_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return ClonesIoTrend(**clone_io_trend_data)
        elif granularity == Granularity.daily.value:
            for index, data_dict in enumerate(vol_uuid_usage_trend_frame["data"]):
                total_index += 1
                common_fields = self.common_field_generator(
                    type="IO per volume", generation=1, customerId=data_dict["custid"]
                )
                temp_clone_io_trend_data.update(common_fields)
                temp_clone_io_trend_data["timeStamp"] = data_dict["collectiontime"].replace(".000", "Z")
                temp_clone_io_trend_data["ioActivity"] = data_dict["avg_io_trend"]
                temp_clone_io_trend_data["generation"] = 1
                clone_io_trend_data["items"].append(copy.deepcopy(temp_clone_io_trend_data))
            clone_io_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return ClonesIoTrend(**clone_io_trend_data)
        elif granularity == Granularity.weekly.value:
            for index, data_dict in enumerate(vol_uuid_usage_trend_frame["data"]):
                total_index += 1

                common_fields = self.common_field_generator(
                    type="IO per volume", generation=1, customerId=data_dict["custid"]
                )
                week_date = data_dict["collectiontime"]["start_time"].replace("T00:00:00.000", "")

                # week_date = data_dict["collectiontime"].replace("T00:00:00.000", "")
                collection_week_start = datetime.strptime(week_date, "%Y-%m-%d")
                t_stamp = collection_week_start.strftime("%Y-%m-%dT%H:%M:%SZ")
                temp_clone_io_trend_data.update(common_fields)
                temp_clone_io_trend_data["timeStamp"] = t_stamp
                temp_clone_io_trend_data["ioActivity"] = data_dict["avgiops"]
                temp_clone_io_trend_data["generation"] = 1
                clone_io_trend_data["items"].append(copy.deepcopy(temp_clone_io_trend_data))
            clone_io_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return ClonesIoTrend(**clone_io_trend_data)

    def get_volume_replication_trend(self, **params) -> SnapshotCopies:
        """
                    This function fetches the copies created per volume
                        If get response is success (200) then function will return object of volumescostTrend
                        In Case of failure (apart from 200) it will return the actual response code
                        Path parameter should be passed as arguments- volume_uuid:str
                        Query params can take any of the following query parameter
                        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|monthly"
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily

        Return:
            if status code OK:-
                response = {
                "totalSnapshotsCopies": [
                {"timeStamp" : "2020-11-11 2:43:34", "timeInterval" : "12-06-2020", "periodicSnapshotSize" : 50, "adhocSnapshotSize": 23 }
                ],
                 "totalClonesCopies": [
                {"timeStamp" : "2020-11-11 2:43:34", "clonesSize" : 60 }
                ],
             "totalPeriodicSnapshotsCount": 1,
             "totalAdhocSnapshotsCount": 2
             "totalClonesCount":1
            }
            else response code :- 400 or 401 or 500
        """
        #
        granularity = 0 if "granularity" not in params else params["granularity"]
        vol_uuid_replica_trend_frame, granularity = self.steps_obj.spark_vol_uuid_snap_data(
            vol_uuid=params["vol_uuid"],
            start_date=params["start_date"],
            end_date=params["end_date"],
            granularity=granularity,
        )

        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        vol_uuid_replica_trend_data = {"items": []}
        temp_vol_uuid_replica_trend_data = {}
        temp_vol_uuid_replica_trend_data = {
            "timeStamp": 0,
            "periodicSnapshotSizeInBytes": 0,
            "adhocSnapshotSizeInBytes": 0,
            "numPeriodicSnapshots": 0,
            "numAdhocSnapshots": 0,
            "numClones": 0,
            "cloneSizeInBytes": 0,
        }
        total_index = 0
        if granularity == Granularity.hourly.value:
            for index, data_dict in enumerate(vol_uuid_replica_trend_frame["data"]):
                total_index += 1
                temp_vol_uuid_replica_trend_data["timeStamp"] = data_dict["collection_end_date"]
                temp_vol_uuid_replica_trend_data["numAdhocSnapshots"] = data_dict["numberofadhocsnaps"]
                temp_vol_uuid_replica_trend_data["numPeriodicSnapshots"] = data_dict["numberofperiodicsnaps"]

                common_fields = self.common_field_generator(
                    type="snapshots per volume", generation=1, customerId=data_dict["customer_id"]
                )
                temp_vol_uuid_replica_trend_data.update(common_fields)
                vol_uuid_replica_trend_data["items"].append(copy.deepcopy(temp_vol_uuid_replica_trend_data))
            vol_uuid_replica_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return SnapshotCopies(**vol_uuid_replica_trend_data)
        elif granularity == Granularity.daily.value:
            for index, data_dict in enumerate(vol_uuid_replica_trend_frame["data"]):
                total_index += 1
                temp_vol_uuid_replica_trend_data["timeStamp"] = data_dict["collection_end_date"]
                temp_vol_uuid_replica_trend_data["numAdhocSnapshots"] = data_dict["adhoc_snap_count"]
                temp_vol_uuid_replica_trend_data["numPeriodicSnapshots"] = data_dict["periodic_snap_count"]

                common_fields = self.common_field_generator(
                    type="snapshots per volume", generation=1, customerId=data_dict["customer_id"]
                )
                temp_vol_uuid_replica_trend_data.update(common_fields)
                vol_uuid_replica_trend_data["items"].append(copy.deepcopy(temp_vol_uuid_replica_trend_data))
            vol_uuid_replica_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return SnapshotCopies(**vol_uuid_replica_trend_data)
        elif granularity == Granularity.weekly.value:
            for index, data_dict in enumerate(vol_uuid_replica_trend_frame["data"]):
                total_index += 1
                temp_vol_uuid_replica_trend_data["timeStamp"] = data_dict["collection_end_date"]
                temp_vol_uuid_replica_trend_data["numAdhocSnapshots"] = data_dict["adhoc_snap_count"]
                temp_vol_uuid_replica_trend_data["numPeriodicSnapshots"] = data_dict["periodic_snap_count"]

                common_fields = self.common_field_generator(
                    type="snapshots per volume", generation=1, customerId=data_dict["customer_id"]
                )
                temp_vol_uuid_replica_trend_data.update(common_fields)
                vol_uuid_replica_trend_data["items"].append(copy.deepcopy(temp_vol_uuid_replica_trend_data))
            vol_uuid_replica_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return SnapshotCopies(**vol_uuid_replica_trend_data)

    def get_volume_replication_clone_trend(self, **params) -> CloneCopies:
        """
                    This function fetches the copies created per volume
                        If get response is success (200) then function will return object of volumescostTrend
                        In Case of failure (apart from 200) it will return the actual response code
                        Path parameter should be passed as arguments- volume_uuid:str
                        Query params can take any of the following query parameter
                        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|monthly"
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily

        Return:
            if status code OK:-
                response = {
                "totalSnapshotsCopies": [
                {"timeStamp" : "2020-11-11 2:43:34", "timeInterval" : "12-06-2020", "periodicSnapshotSize" : 50, "adhocSnapshotSize": 23 }
                ],
                 "totalClonesCopies": [
                {"timeStamp" : "2020-11-11 2:43:34", "clonesSize" : 60 }
                ],
             "totalPeriodicSnapshotsCount": 1,
             "totalAdhocSnapshotsCount": 2
             "totalClonesCount":1
            }
            else response code :- 400 or 401 or 500
        """
        #
        granularity = 0 if "granularity" not in params else params["granularity"]
        vol_uuid_replica_clone_trend_frame, granularity = self.steps_obj.spark_vol_uuid_clone_data(
            vol_uuid=params["vol_uuid"],
            start_date=params["start_date"],
            end_date=params["end_date"],
            granularity=granularity,
        )
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        vol_uuid_replica_trend_clone_data = {"items": []}
        temp_vol_uuid_replica_trend_clone_data = {}
        total_index = 0
        if granularity == Granularity.hourly.value:
            for index, data_dict in enumerate(vol_uuid_replica_clone_trend_frame["data"]):
                if len(data_dict) > 1:
                    total_index += 1
                    temp_vol_uuid_replica_trend_clone_data = {
                        "timeStamp": data_dict["collectionendtime"],
                        "sizeInBytes": data_dict["clonesize"],
                        "numClones": data_dict["numberofclones"],
                    }
                    common_fields = self.common_field_generator(
                        type="clones per volume", generation=1, customerId=data_dict["custid"]
                    )
                    temp_vol_uuid_replica_trend_clone_data.update(common_fields)
                    vol_uuid_replica_trend_clone_data["items"].append(
                        copy.deepcopy(temp_vol_uuid_replica_trend_clone_data)
                    )

            vol_uuid_replica_trend_clone_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return CloneCopies(**vol_uuid_replica_trend_clone_data)
        elif granularity == Granularity.daily.value:
            for index, data_dict in enumerate(vol_uuid_replica_clone_trend_frame["data"]):
                if len(data_dict) > 1:
                    total_index += 1
                    temp_vol_uuid_replica_trend_clone_data = {
                        "timeStamp": data_dict["collectionendtime"],
                        "sizeInBytes": data_dict["clonesize"],
                        "numClones": data_dict["numberofclones"],
                    }
                    common_fields = self.common_field_generator(
                        type="clones per volume", generation=1, customerId=data_dict["custid"]
                    )
                    temp_vol_uuid_replica_trend_clone_data.update(common_fields)
                    vol_uuid_replica_trend_clone_data["items"].append(
                        copy.deepcopy(temp_vol_uuid_replica_trend_clone_data)
                    )
            vol_uuid_replica_trend_clone_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return CloneCopies(**vol_uuid_replica_trend_clone_data)
        elif granularity == Granularity.weekly.value:
            for index, data_dict in enumerate(vol_uuid_replica_clone_trend_frame["data"]):
                total_index += 1
                temp_vol_uuid_replica_trend_clone_data = {
                    "timeStamp": data_dict["collectionendtime"],
                    "sizeInBytes": data_dict["clonesize"],
                    "numClones": data_dict["numberofclones"],
                }
                common_fields = self.common_field_generator(
                    type="clones per volume", generation=1, customerId=data_dict["custid"]
                )
                temp_vol_uuid_replica_trend_clone_data.update(common_fields)
                vol_uuid_replica_trend_clone_data["items"].append(copy.deepcopy(temp_vol_uuid_replica_trend_clone_data))
            vol_uuid_replica_trend_clone_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return CloneCopies(**vol_uuid_replica_trend_clone_data)

    def get_snapshot_consumption(self, **params) -> SnapshotConsumption:
        """
        GET request to fetch all the snapshots related information for a specific customer id
        API Request URL reference: /data-observability/v1alpha1/snapshots-consumption
        Returns response as SnapshotConsumption Dataclass object defined for API '/data-observability/v1alpha1/snapshots-consumption'

        Return:
            if status code OK:-
                response = {
                    "numSnapshots":xx,
                    "totalSizeInBytes":xx,
                    "cost": xx,
                    "previousMonthCost": xx,
                    "currentMonthCost": xx
                }
            else response code :- 400/401/500
        """

        snap_consumption_data = self.steps_obj.spark_snap_shot_consumption()
        consumption_data = {}

        common_fields = self.common_field_generator(
            type="snapshots consumption ",
            generation=1,
            customerId=snap_consumption_data["customer_id"],
            id="snapshots consumption ",
            name="snapshots consumption ",
        )
        consumption_data = {
            "numSnapshots": snap_consumption_data["num_of_Snapshots"],
            "totalSizeInBytes": snap_consumption_data["total_size_bytes"],
            "cost": snap_consumption_data["cost"],
            "previousMonthCost": snap_consumption_data["previous_month_cost"],
            "currentMonthCost": snap_consumption_data["current_month_cost"],
        }
        consumption_data.update(common_fields)

        return SnapshotConsumption(**consumption_data)

    def get_snapshots_cost_trend(self, **params) -> SnapshotCostTrend:
        """
        GET request to fetch the monthly cost for the snapshots created
        API Request URL reference: /data-observability/v1alpha1/snapshots-cost-trend
        Returns response as SnapshotCostTrend Dataclass object defined for API '/data-observability/v1alpha1/snapshots-cost-trend'
        Arguments
            start-time (R)  : Required. Value should be of RFC3339 time format (format: 2020-11-12T11:45:26.371Z)
            end-time (R)    : Required. Value should be of RFC3339 time format  (format: 2020-11-12T11:45:26.371Z)
            limit(O)        : Optional. Default value for pageLimit is 10
            offset(O)       : Optional. Default value of pageOffset is 0. Maximum "pageLimit" value is 1000

        Return:
            if status code OK:-
                response = {
                        "items": [{
                            "year": "xx",
                            "month": "xx",
                            "cost": xx
                            "currency": xx
                        }],
                        "offset": xx,
                        "count": xx,
                        "total": xx
                    }
            else response code :- 400/401/500
        """
        cost_trend_frame = self.steps_obj.spark_snapshot_cost_trend(
            start_date=params["start_date"], end_date=params["end_date"]
        )

        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        cost_trend_data = {"items": []}
        temp_cost_trend_data = {}
        total_index = 0
        for index, data_dict in enumerate(cost_trend_frame["data"]):
            total_index += 1
            common_fields = self.common_field_generator(
                type="snapshots cost trend",
                generation=1,
                customerId=data_dict["customer_id"],
                id="snapshots cost trend ",
                name="snapshots cost trend ",
            )
            year_month = datetime.strptime(data_dict["month"], "%Y-%m")
            temp_cost_trend_data = {
                "year": year_month.year,
                "month": year_month.month,
                "cost": data_dict["finalcost"],
                "currency": data_dict["currency"],
            }
            temp_cost_trend_data.update(common_fields)
            cost_trend_data["items"].append(copy.deepcopy(temp_cost_trend_data))

        cost_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})

        return SnapshotCostTrend(**cost_trend_data)

    def get_snapshots_usage_trend(self, **params) -> SnapshotUsageTrend:
        """
        GET request to fetch the overall snapshots usage data for the specific time intervals
        API Request URL reference: /data-observability/v1alpha1/snapshots-usage-trend
        If get response returns success (code: 200) then function will return object of SnapshotUsageTrend
            In Case of failure response (apart from  code: 200) it will return the actual response code
        Params can take the following query parameter as input.
        During the function call dictionary of the below parameters have to be defined and passed to params
        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|monthly"

                - startTime - (Required) Interval start time. "startTime" ]parameters should be of RFC3339 format
                - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily
        Return:
            if status code OK:-
                response = {
                        "totalSnapshotsUsage": [{
                        "timeStamp": "2022-01-21 2:43:34"
                        "totalUsageInBytes": 150
                    }],
                "count": 60,
                }
            else response code :- 400/401/500
        """
        granularity = 0 if "granularity" not in params else params["granularity"]
        snap_usage_trend_frame, granularity = self.steps_obj.spark_snap_usage_trend(
            start_date=params["startTime"], end_date=params["endTime"], granularity=granularity
        )

        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        usage_trend_data = {"items": []}
        temp_usage_trend_data = {}
        total_index = 0

        # SnapshotUsageTrend object creation for granularity - hourly

        if granularity == Granularity.hourly.value:
            for index, data_dict in enumerate(snap_usage_trend_frame["data"]):
                total_index += 1
                common_fields = self.common_field_generator(
                    type="snapshots usage trend", generation=1, customerId=data_dict["customer_id"]
                )
                time_stamp = str(data_dict["collection_end_date"])
                time_stamp = time_stamp[:-4]
                time_stamp = time_stamp.replace(" ", "T") + "Z"
                temp_usage_trend_data = {
                    "timeStamp": time_stamp,
                    "totalUsageInBytes": data_dict["totalUsageInBytes"],
                }

                temp_usage_trend_data.update(common_fields)
                usage_trend_data["items"].append(copy.deepcopy(temp_usage_trend_data))

        # SnapshotUsageTrend object creation for granularity - daily
        elif granularity == Granularity.daily.value:
            for index, data_dict in enumerate(snap_usage_trend_frame["data"]):
                total_index += 1
                common_fields = self.common_field_generator(
                    type="snapshots usage trend", generation=1, customerId=data_dict["customer_id"]
                )
                temp_usage_trend_data = {
                    "timeStamp": data_dict["collectiontime"].replace(".000", "Z"),
                    "totalUsageInBytes": int(data_dict["totalUsageInBytes"]),
                }

                temp_usage_trend_data.update(common_fields)
                usage_trend_data["items"].append(copy.deepcopy(temp_usage_trend_data))

        # SnapshotUsageTrend object creation for granularity - weekly
        elif granularity == Granularity.weekly.value:
            for index, data_dict in enumerate(snap_usage_trend_frame["data"]):
                total_index += 1
                week_date = data_dict["collectiontime"].rsplit(".", maxsplit=1)[0] + "Z"
                temp_usage_trend_data = {
                    "timeStamp": week_date,
                    "totalUsageInBytes": int(data_dict["totalUsageInBytes"]),
                }
                common_fields = self.common_field_generator(
                    type="snapshot usage trend", generation=1, customerId=data_dict["customer_id"]
                )
                temp_usage_trend_data.update(common_fields)
                usage_trend_data["items"].append(copy.deepcopy(temp_usage_trend_data))

        usage_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
        return SnapshotUsageTrend(**usage_trend_data)

    def get_snapshots_creation_trend(self, **params) -> SnapshotCreationTrend:
        """
        GET request to fetch the snapshots created for the specific time intervals
        API Request URL reference: /data-observability/v1alpha1/snapshots-creation-trend
        If get response returns success (code: 200) then function will return object of SnapshotCreationTrend
            In Case of failure response (apart from  code: 200) it will return the actual response code
                params can take the following query parameter as input.
        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be like below Ex: {startTime="time", endTime="time", granularity="hourly|weekly|daily"

                - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and daily or calculated as per difference between start date and end date ( <=7 days- hourly,  8 to 180 days -daily , Grater than 180 days as weekly). 
        Return:
            if status code OK:-
            # fields required for graph verification
                response = {
                        "totalSnapshotsCreated": [{
                        "updatedAt": xx
                        "aggrWindowTimestamp" : xx
                        "numAdhocSnapshots": xx
                        "numPeriodicSnapshots": xx
                    }],
                "count": xx,
                }
            else response code :- 400/401/500
        """

        granularity = 0 if "granularity" not in params else params["granularity"]

        # calling spark_snap_creation_data function to get the snapshot trend graph fields for all granularity in the form of key value pair 
        snp_creation_trend_frame, granularity = self.steps_obj.spark_snap_creation_data(
            start_date=params["startTime"], end_date=params["endTime"], granularity=granularity
        )

        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        creation_trend_data = {"items": []}
        temp_creation_trend_data = {}
        total_index = 0

        # SnapshotCreationTrend object creation 
        for index, data_dict in enumerate(snp_creation_trend_frame["data"]):
            total_index += 1
            common_fields = self.common_field_generator(
                type="snapshot creation trend-",id="snapshot creation trend-",name="snapshot creation trend-", generation=1, customerId=data_dict["customer_id"]
            )
            if granularity == Granularity.hourly.value:
                updatedAt =data_dict["updatedAt"].rsplit(".", maxsplit=1)[0] + "Z"
                aggrWindowTimestamp = data_dict["creation_window"].rsplit(".", maxsplit=1)[0] + "Z"
            elif granularity == Granularity.daily.value:
                updatedAt = aggrWindowTimestamp = data_dict["creation_window_date"].rsplit(".", maxsplit=1)[0] + "Z"
            else:
                updatedAt = aggrWindowTimestamp = data_dict["week_start"].rsplit(".", maxsplit=1)[0] + "Z"

            temp_creation_trend_data = {
                "updatedAt": updatedAt,
                "aggrWindowTimestamp": aggrWindowTimestamp,
                "numAdhocSnapshots": data_dict["total_adhoc_count"],
                "numPeriodicSnapshots": data_dict["total_periodic_count"],
            }
            temp_creation_trend_data.update(common_fields)
            creation_trend_data["items"].append(copy.deepcopy(temp_creation_trend_data))

        creation_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
        return SnapshotCreationTrend(**creation_trend_data)

    
    def get_snapshots_age_trend(self, **params) -> SnapshotAgeTrend:
        """
        GET request to fetch the snapshots age size related information for the specific time intervals
        API Request URL reference: /data-observability/v1alpha1/snapshots-age-trend
        Returns response as SnapshotAgeTrend Dataclass object defined for API '/data-observability/v1alpha1/snapshots-age-trend'

        Return:
            if status code OK:-
                response = {
                        "age": XX,
                        "bucket": XX,
                        "sizeUnit": XX,
                        "updatedAt": XX,
                        "sizeInfo": [
                            {
                                "numSnapshots": XX
                            },
                            {
                                "numSnapshots": XX
                            },
                            {
                                "numSnapshots": XX
                            }
                        ],
                }
            else response code :- 400/401/500
        """
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]
        snap_age_trend = self.steps_obj.spark_snap_age_trend()

        snp_age_trend_data = {"items": []}
        temp_age_trend_data = {}
        total_index = 0
        age_range = ["0-6 months", "6-12 months", "1-2 years", "2-3 years", "3+ years"]
        for index, data_dict in enumerate(snap_age_trend["data"]):
            total_index += 1
            common_fields = self.common_field_generator(
                type="snapshots age trend",
                generation=1,
                customerId=data_dict["customer_id"],
                name="snapshots age trend",
                id="snapshots age trend"
            )
            temp_age_trend_data = {
                "age": data_dict["age_range"],
                "bucket": int(data_dict["size_value"]),
                "sizeUnit" : data_dict["size_unit"],
                "updatedAt": data_dict["collection_end_date"].replace(".000", "Z"),
                "sizeInfo":[
                    {"numSnapshots": data_dict["min"]},
                    {"numSnapshots": data_dict["mid"]},
                    {"numSnapshots": data_dict["max"]}
                ]
            }
            temp_age_trend_data.update(common_fields)
            snp_age_trend_data["items"].append(copy.deepcopy(temp_age_trend_data))
            age_range.remove(data_dict["age_range"])

        # if Mock data does'nt have data for specific snapshot age  bucket and sub buckets
        if len(age_range) != 0:
            for bucket in age_range:
                total_index += 1
                common_fields = self.common_field_generator(
                    type="snapshots age trend", 
                    generation=1, 
                    customerId=snap_age_trend["data"][0]["customer_id"],
                    name="snapshots age trend",
                    id="snapshots age trend"
                )
                temp_age_trend_data = {
                    "age": bucket,
                    "bucket":int( snap_age_trend["data"][0]["size_value"]),
                    "sizeUnit" : snap_age_trend["data"][0]["size_unit"],
                    "updatedAt": snap_age_trend["data"][0]["collection_end_date"].replace(".000", "Z"),
                    "sizeInfo":[
                        {"numSnapshots": 0},
                        {"numSnapshots": 0},
                        {"numSnapshots": 0}
                    ]
                }
                temp_age_trend_data.update(common_fields)
                snp_age_trend_data["items"].append(copy.deepcopy(temp_age_trend_data))


        snp_age_trend_data.update({"count": total_index, "offset": page_offset, "total": total_index})
        return SnapshotAgeTrend(**snp_age_trend_data)

    def get_snapshots_retention_trend(self, **params) -> SnapshotRetentionTrend:
        """
        GET request to fetch the snapshots retention related information for the specific time intervals
        API Request URL reference: /api/v1/snapshots-retention-trend
        API Request URL reference: /data-observability/v1alpha1/snapshots-retention-trend
        Returns response as SnapshotRetentionTrend Dataclass object defined for API 'snapshots-retention-trend'
        Return:
            if status code OK:-
                response = {
                        "snapshotRetentionDetails": [{
                        "retentionPeriodRange": "xx-yy",
                        "numberofPeriodicSnapshotsCreated": xx,
                        "numberofAdhocSnapshotsCreated": xx,
                        "range": "xx-yy",
                        "numAdhocSnapshots": xx,
                        "numPeriodicSnapshots": xx,
                    }]
                }
            else response code :- 400/401/500
        """

        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        snap_retention_trend_data = self.steps_obj.spark_snap_retention_trend()

        retention_trend_data = {"items": []}
        temp_retention_trend_data = {}
        # supported snapshot age buckets
        snap_retention_age_range_bucket = {"0-6 months", "6-12 months", "1-2 years", "2-3 years", "3+ years", "Lapsed","Unlimited","Not Set"}
        total_index = 0

        for index, data_dict in enumerate(snap_retention_trend_data["data"]):
            total_index += 1
            common_fields = self.common_field_generator(
                type="snapshots retention trend", id="snapshots retention trend",name="snapshots retention trend", generation=1, customerId=data_dict["custid"]
            )
            temp_retention_trend_data = {
                "range": data_dict["bucket"],
                "numAdhocSnapshots": data_dict["adhoc_count"],
                "numPeriodicSnapshots": data_dict["periodic_count"],
            }
            temp_retention_trend_data.update(common_fields)
            retention_trend_data["items"].append(copy.deepcopy(temp_retention_trend_data))
            snap_retention_age_range_bucket.remove(data_dict["bucket"])

        # if Mock data does'nt have data for specific snapshot age bucket Adhoc and periodic snapshots count will be 0
        if len(snap_retention_age_range_bucket) != 0:
            total_index += 1
            for bucket in snap_retention_age_range_bucket:
                common_fields = self.common_field_generator(
                    type="snapshots retention trend", id="snapshots retention trend",name="snapshots retention trend",
                    generation=1,
                    customerId=snap_retention_trend_data["data"][0]["custid"],
                )
                temp_retention_trend_data = {
                    "range": bucket,
                    "numAdhocSnapshots": 0,
                    "numPeriodicSnapshots": 0,
                }
                temp_retention_trend_data.update(common_fields)
                retention_trend_data["items"].append(copy.deepcopy(temp_retention_trend_data))

        retention_trend_data.update({"count": total_index, "offset": page_offset, "total": total_index})
        return SnapshotRetentionTrend(**retention_trend_data)

    def get_snapshot_details(self, **params) -> Snapshots:
        """This is array consumption library function which collect details from spark library and create snapshot object with required fields

        Returns:
            Snapshots: snapshot object
        """
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        snap_details = self.steps_obj.spark_snap_list_snapshot_details()

        snapshot_data = {"items": []}
        temp_snap_data = {}
        total_index = 0

        for index, data_dict in enumerate(snap_details["data"]):
            total_index += 1
            common_fields = self.common_field_generator(
                type="snapshots info",
                generation=1,
                customerId=data_dict["customer_id"],
                name=data_dict["snap_name"],
                id="snapshots info-",
            )
            temp_snap_data = {
                "system": data_dict["system_name"],
                "systemId": data_dict["system_id"],
                "createdAt": data_dict["creation_time"].replace(".000", "Z"),
                "updatedAt": data_dict["update_time"].replace(".000", "Z"),
               
            }

            temp_snap_data.update(common_fields)
            snapshot_data["items"].append(copy.deepcopy(temp_snap_data))

        snapshot_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
        return Snapshots(**snapshot_data)

    def get_clones_consumption(self, **params) -> ClonesConsumption:
        """
        GET request API function to fetch all the clones related information for a specific customer id
        API Request URL reference: /api/v1/clones-consumption
        Returns response as ClonesConsumption Dataclass object defined for API '/api/v1/clones-consumption'
        Return:
            if status code OK:-
                response = {
                    "numClones": 110, -> Can fetch from last collection
                    "totalSizeInBytes": 529354719232, -> Can fetch from last collection
                    "utilizedSizeInBytes": 314472136704, -> Can fetch from last collection
                    "cost": 57.4061, -> Can fetch from last collection
                    "previousMonthCost": 28.894594444444444, -> calculate from all collection
                    "previousMonthUtilizedSizeInBytes": 160487574368, -> calculate from all collection
                    "currentMonthCost": 51.41898787878788, -> calculate from all collection
                    "currentMonthUtilizedSizeInBytes": 285312922220, -> calculate from all collection
                    "id": "clones consumption-1689091500000",
                    "name": "clones consumption-1689091500000",
                    "type": "clones consumption",
                    "generation": 1,
                    "resourceUri": "",
                    "consoleUri": "",
                    "customerId": "03bf4f5020022edecad3a7642bfb5391"
                }
            else response code :- 400/401/500
        """

        clone_last_coll_data, clone_avg_data = self.steps_obj.spark_clone_consumption()

        curr_mon_used_bytes = clone_avg_data["current_month_utilized_size_in_bytes"]
        prev_mon_used_bytes = clone_avg_data["previous_month_utilized_size_in_bytes"]
        curr_mon_vol_cost = clone_avg_data["current_month_usage_cost"]
        prev_mon_vol_cost = clone_avg_data["prev_month_usage_cost"]

        consumption_data = {
            "numClones": clone_last_coll_data["total_clone_count"],
            "totalSizeInBytes": clone_last_coll_data["clone_total_size_in_bytes"],
            "utilizedSizeInBytes": clone_last_coll_data["clone_used_size_in_bytes"],
            "cost": clone_avg_data["cost"],
            "previousMonthCost": prev_mon_vol_cost,
            "previousMonthUtilizedSizeInBytes": prev_mon_used_bytes,
            "currentMonthCost": curr_mon_vol_cost,
            "currentMonthUtilizedSizeInBytes": curr_mon_used_bytes,
        }
        common_fields = self.common_field_generator(
            type="clones consumption",
            generation=1,
            customerId=clone_avg_data["customer_id"],
        )
        consumption_data.update(common_fields)
        return ClonesConsumption(**consumption_data)

    def get_clones_cost_trend(self, **params) -> ClonesCostTrend:
        """
        GET request API function to fetch the monthly cost for the clones created
        API Request URL reference: /api/v1/clones-cost-trend
        It takes number of months as the query parameter. By default 6 months data will be fetched.
        If number of months is specified then it will fetch those many months data from the current month.
        Returns reponse as ClonesConsumption Dataclass object defined for API '/api/v1/clones-cost-trend'
        Return:
            if status code OK:-
                response = {
                        "totalClonesCost": [{
                        "year": 2022,
                        "month": 5,
                        "totalCostUsage": 54,
                        "currencyType": "USD"
                    }],
                    "count": 2
                }
            else response code :- 400/401/500
        """
        cost_trend_frame = self.steps_obj.spark_clone_cost_trend(
            start_date=params["start_date"], end_date=params["end_date"]
        )
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        cost_trend_data = {"items": []}
        temp_cost_trend_data = {}
        total_index = 0
        for index, data_dict in cost_trend_frame.iterrows():
            total_index += 1
            temp_cost_trend_data = {
                "year": data_dict["collectionstarttime"].year,
                "month": data_dict["collectionstarttime"].month,
                "cost": data_dict["agg_usage_cost"],
                "currency": "USD",
            }
            common_fields = self.common_field_generator(customerId=data_dict["custid"])
            temp_cost_trend_data.update(common_fields)
            cost_trend_data["items"].append(copy.deepcopy(temp_cost_trend_data))
        cost_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
        return ClonesCostTrend(**cost_trend_data)

    def get_clones_usage_trend(self, **params) -> ClonesUsageTrend:
        """
        GET request API function to fetch the overall clones usage data for the specific time intervals
        API Request URL reference: /api/v1/clones-usage-trend
        If get response returns success (code: 200) then function will return object of ClonesUsageTrend
            In Case of failure response (apart from  code: 200) it will return the actual response code
                params can take the following query parameter as input.
        During the function call dictionary of the below parameters have to be defined and passed to params

        Arguments
            **params :- Required params values will be as mentioned below Ex: {startTime="time/date", endTime="time/date", granularity="hourly|weekly|monthly"}
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily

        Return:
            if status code OK:-
                response = {
                           "totalClonesUsage": [{
                       "timeStamp":  "2020-11-11 10:00:40"
                       "totalCloneUsage": 33
                    }],
                "count": 3,
                }
            else response code :- 400/401/500
        """

        granularity = 0 if "granularity" not in params else params["granularity"]

        clone_usage_trend_frame, granularity = self.steps_obj.spark_clone_usage_trend(
            start_date=params["start_date"], end_date=params["end_date"], granularity=granularity
        )

        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        usage_trend_data = {"items": []}
        temp_usage_trend_data = {}
        total_index = 0
        if granularity == Granularity.hourly.value:
            for index, data_dict in enumerate(clone_usage_trend_frame["data"]):
                total_index += 1

                date_string = data_dict["collectionendtime"]
                time_stamp = date_string.replace(".000", "Z")
                temp_usage_trend_data = {
                    "timeStamp": time_stamp,
                    "totalUsageInBytes": data_dict["cloneusedsize"],
                }
                common_fields = self.common_field_generator(
                    type="clones usage trend", generation=1, customerId=data_dict["custid"]
                )
                temp_usage_trend_data.update(common_fields)
                usage_trend_data["items"].append(copy.deepcopy(temp_usage_trend_data))
            usage_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            # return usage_trend_data
            return ClonesUsageTrend(**usage_trend_data)
        elif granularity == Granularity.daily.value:
            for index, data_dict in enumerate(clone_usage_trend_frame["data"]):
                total_index += 1
                time_stamp = data_dict["collectiontime"] + "T00:00:00Z"
                temp_usage_trend_data = {
                    "timeStamp": time_stamp,
                    "totalUsageInBytes": data_dict["cloneusedsize"],
                }
                common_fields = self.common_field_generator(
                    type="clones usage trend", generation=1, customerId=data_dict["custid"]
                )
                temp_usage_trend_data.update(common_fields)
                usage_trend_data["items"].append(copy.deepcopy(temp_usage_trend_data))
            usage_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            # return usage_trend_data
            return ClonesUsageTrend(**usage_trend_data)
        elif granularity == Granularity.weekly.value:
            for index, data_dict in enumerate(clone_usage_trend_frame["data"]):
                total_index += 1

                week_date = data_dict["collectiontime"].split("/")[0] + "T00:00:00Z"
                temp_usage_trend_data = {
                    "timeStamp": week_date,
                    "totalUsageInBytes": data_dict["cloneusedsize"],
                }
                common_fields = self.common_field_generator(
                    type="clones usage trend", generation=1, customerId=data_dict["custid"]
                )
                temp_usage_trend_data.update(common_fields)
                usage_trend_data["items"].append(copy.deepcopy(temp_usage_trend_data))
            usage_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            # return usage_trend_data
            return ClonesUsageTrend(**usage_trend_data)

    def get_clones_creation_trend(self, **params) -> ClonesCreationTrend:
        """
        GET request API function to fetch the clones created for the specific time intervals
        API Request URL reference: /api/v1/clones-creation-trend
        If get response returns success (code: 200) then function will return object of ClonesCreationTrend
            In Case of failure response (apart from  code: 200) it will return the actual response code
                params can take the following query parameter as input.
        During the function call dictionary of the below parameters have to be defined and passed to params

         Arguments
            **params :- Required params values will be as mentioned below Ex: {startTime="time/date", endTime="time/date", granularity="hourly|weekly|monthly"}
                        - startTime - (Required) Interval start time. "startTime" parameters should be of RFC3339 format
                        - endTime - (Required) Interval end time. "endTime" parameters should be of RFC3339 format
                        - granularity - (Optional) Allowed values for "granularity" parameter are daily (point in time), hourly, weekly and monthly. Default value will be daily

        Return:
            if status code OK:-
                response = {
                        "totalClonesCreated": [{
                        "timeStamp": "2021-10-11 23:10:54"
                        "totalCloneCreated": 27
                    }],
                "count": 4,
                }
            else response code :- 400/401/500
        """
        granularity = 0 if "granularity" not in params else params["granularity"]
        clone_creation_trend_frame, granularity = self.steps_obj.spark_clone_creation_data(
            start_date=params["start_date"], end_date=params["end_date"], granularity=granularity
        )

        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        creation_trend_data = {"items": []}
        temp_creation_trend_data = {}
        total_index = 0
        if granularity == Granularity.hourly.value:
            for index, data_dict in enumerate(clone_creation_trend_frame["data"]):
                total_index += 1
                temp_creation_trend_data["updatedAt"] = data_dict["collectionendtime"]
                temp_creation_trend_data["aggrWindowTimestamp"] = data_dict["aggrWindowTimestamp"]
                temp_creation_trend_data["numClones"] = data_dict["clonecount"]
                common_fields = self.common_field_generator(generation=1, customerId=data_dict["custid"])
                temp_creation_trend_data.update(common_fields)
                creation_trend_data["items"].append(copy.deepcopy(temp_creation_trend_data))
            creation_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return ClonesCreationTrend(**creation_trend_data)
        elif granularity == Granularity.daily.value:
            for index, data_dict in enumerate(clone_creation_trend_frame["data"]):
                total_index += 1
                temp_creation_trend_data["updatedAt"] = data_dict["updatedAt"]
                temp_creation_trend_data["aggrWindowTimestamp"] = data_dict["updatedAt"]
                temp_creation_trend_data["numClones"] = data_dict["clonecount"]
                common_fields = self.common_field_generator(generation=1, customerId=data_dict["custid"])
                temp_creation_trend_data.update(common_fields)
                creation_trend_data["items"].append(copy.deepcopy(temp_creation_trend_data))
            creation_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return ClonesCreationTrend(**creation_trend_data)
        elif granularity == Granularity.weekly.value:
            for index, data_dict in enumerate(clone_creation_trend_frame["data"]):
                total_index += 1
                temp_creation_trend_data["updatedAt"] = data_dict["updatedAt"]
                temp_creation_trend_data["aggrWindowTimestamp"] = data_dict["updatedAt"]
                temp_creation_trend_data["numClones"] = data_dict["clonecount"]
                common_fields = self.common_field_generator(generation=1, customerId=data_dict["custid"])
                temp_creation_trend_data.update(common_fields)
                creation_trend_data["items"].append(copy.deepcopy(temp_creation_trend_data))
            creation_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
            return ClonesCreationTrend(**creation_trend_data)

    def get_clones_activity_trend(self, **params) -> ClonesActivityTrend:
        """
               GET request API function to fetch the all the clones activity for the specific customer.
               API Request URL reference: /api/v1/clones-activity-trend
               If get response returns success (code: 200) then function will return object of ClonesActivityTrend
                   In Case of failure response (apart from  code: 200) it will return the actual response code
                       params can take the following query parameter as input.
               During the function call dictionary of the below parameters have to be defined and passed to params

               Arguments
                   **params :- Required params values will be as mentioned below Ex: {provisionType="Thin|Thick", minIo="str", maxIo="str", minCloneSize="int", maxCloneSize="int"}
                       - provisionType - (Optional)
                       - minIo - (Optional)
                       - maxIo - (Optional)
                       - minCloneSize - (Optional)
                       - maxCloneSize - (Optional)

               Return:
                   if status code OK:-
                           response = {
            "items": [{
               "name": "test-clone-vol1",
               "provisionType": "thin",
               "utilizedSizeInBytes": 34.55,
               "totalSizeInBytes": 65.80,
               "createdAt": "2021-10-11 23:10:54",
               "ioActivity": 22.4535,
               "activityTrendInfo": [{
                   "timeStamp": "2021-10-13 08:00:00",
                   "ioActivity": 21.85
               },
               {
                   "timeStamp": "2021-10-14 08:00:00",
                   "ioActivity": 23.00
               }]
           }]
           "offset": 00,
           "count": 02
           "total": 02
        }
                   else response code :- 400/401/500
        """
        provision_type = params["provisionType"] if "provisionType" in params else None
        if "minio" in params and "maxio" in params:
            assert params["minio"] <= params["maxio"], "MinIo Param always lesser tham MaxIo param"
            minio = params["minio"]
            maxio = params["maxio"]
        else:
            minio = None
            maxio = None
        if "minCloneSize" in params and "maxCloneSize" in params:
            assert (
                params["minCloneSize"] <= params["maxCloneSize"]
            ), "Minclonesize Param always lesser tham Maxclonesize param"
            minclonesize = params["minCloneSize"]
            maxclonesize = params["maxCloneSize"]
        else:
            minclonesize = None
            maxclonesize = None

        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        activity_trend_info, clone_activity = self.steps_obj.spark_clone_activity_trend(
            provisiontype=provision_type, minio=minio, maxio=maxio, minclonesize=minclonesize, maxclonesize=maxclonesize
        )

        activity_trend_data = {"items": []}
        total_index = 0
        for index, data_dict in enumerate(clone_activity["data"]):
            temp_activity_trend_data = {}
            total_index += 1
            # temp_activity_trend_data["name"] = data_dict["clonename"]
            # temp_activity_trend_data["id"] = data_dict["cloneid"]
            temp_activity_trend_data["systemId"] = data_dict["system_id"]
            temp_activity_trend_data["provisionType"] = data_dict["provisiontype"]
            temp_activity_trend_data["utilizedSizeInBytes"] = data_dict["cloneusedsize"]
            temp_activity_trend_data["totalSizeInBytes"] = data_dict["clonesize"]
            t_stamp = re.sub(r"(.*)(\.[0-9]+\s.*)", r"\1", data_dict["clonecreationtime"])
            t_stamp = t_stamp.replace(" ", "T") + "Z"
            temp_activity_trend_data["createdAt"] = t_stamp
            temp_activity_trend_data["ioActivity"] = data_dict["avg_iops"]
            temp_activity_trend_data["activityTrendInfo"] = activity_trend_info[data_dict["cloneid"]]
            common_fields = self.common_field_generator(
                id=data_dict["cloneid"],
                name=data_dict["clonename"],
                type="clones activity trend",
                generation=1,
                customerId=data_dict["custid"],
            )
            temp_activity_trend_data.update(common_fields)
            activity_trend_data["items"].append(copy.deepcopy(temp_activity_trend_data))
        activity_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
        return ClonesActivityTrend(**activity_trend_data), activity_trend_data

    def get_clones_activity_trend_by_io(self, **params) -> ClonesActivityTrend:
        """
        This function fetches all the clone activity for the specific customer
        Query parameters should be passed as arguments- provisionType(O):str,minIo(O):float,maxIo(O)
        If get response returns success (code: 200) then function will return object of ClonesActivityTrend
        In Case of failure response (apart from  code: 200) it will return the actual response code
        params can take the following query parameter as input.
        Arguments
            **params :- Required params values will be as mentioned below Ex: {provisionType="Thin|Thick", minIo="str", maxIo="str"}
                - provisionType - (Optional)
                - minIo - (Optional)
                - maxIo - (Optional)

        Return:
            if status code OK:-
                response = {
                    ClonesActivityTrend(items=[], count=10, offset=0, total=0)
                }
            else response code :- 400/401/500
        """
        provision_type = "" if "provisionType" not in params else params["provisionType"]
        minio = 0 if "minio" not in params else params["minio"]
        maxio = 0 if "maxio" not in params else params["maxio"]
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        activity_trend_info, activity_trend_info_by_ptype = self.steps_obj.spark_clone_activity_trend_by_io(
            provisiontype=provision_type,
            minio=minio,
            maxio=maxio,
        )

        activity_trend_data = {"items": []}
        total_index = 0
        for index, row in activity_trend_info.items():
            for data_dict in row:
                temp_activity_trend_data = {}
                total_index += 1
                temp_activity_trend_data["systemId"] = data_dict["system_id"]
                temp_activity_trend_data["system"] = data_dict["system"]
                temp_activity_trend_data["provisionType"] = data_dict["provisiontype"]
                temp_activity_trend_data["totalSizeInBytes"] = data_dict["clonesize"]
                temp_activity_trend_data["utilizedSizeInBytes"] = data_dict["cloneusedsize"]
                t_stamp = re.sub(r"(.*)(\.[0-9]+\s.*)", r"\1", data_dict["clonecreationtime"])
                t_stamp = t_stamp.replace(" ", "T") + "Z"
                temp_activity_trend_data["createdAt"] = t_stamp
                temp_activity_trend_data["ioActivity"] = data_dict["last7days_avgiops"]
                temp_activity_trend_data["activityTrendInfo"] = data_dict["activityTrendInfo"]
                temp_activity_trend_data["utilizedPercentage"] = data_dict["utilizedPercentage"]
                common_fields = self.common_field_generator(
                    id=data_dict["cloneid"],
                    name=data_dict["clonename"],
                    type="clones activity trend",
                    generation=1,
                    customerId=data_dict["custid"],
                )
                temp_activity_trend_data.update(common_fields)
                activity_trend_data["items"].append(copy.deepcopy(temp_activity_trend_data))
        activity_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
        return ClonesActivityTrend(**activity_trend_data), activity_trend_info_by_ptype

    def get_clones_activity_trend_by_size(self, **params) -> ClonesActivityTrend:
        """
        This function fetches all the clone activity for the specific customer based on utilizedSizeInBytes
        Query parameters should be passed as arguments- provisionType(O):str,minCloneSize(O):float,maxCloneSize(O):float
        If get response returns success (code: 200) then function will return object of ClonesActivityTrend
        In Case of failure response (apart from  code: 200) it will return the actual response code
        params can take the following query parameter as input.
        Arguments
            **params :- Required params values will be as mentioned below Ex: {provisionType="Thin|Thick", minCloneSize="str", minCloneSize="str"}
                - provisionType - (Optional)
                - minCloneSize - (Optional)
                - maxCloneSize - (Optional)

        Return:
            if status code OK:-
                response = {
                    ClonesActivityTrend(items=[], count=10, offset=0, total=0)
                }
            else response code :- 400/401/500
        """
        provision_type = "" if "provisionType" not in params else params["provisionType"]
        minCloneSize = 0 if "minCloneSize" not in params else params["minCloneSize"]
        maxCloneSize = 9999999999 if "maxCloneSize" not in params else params["maxCloneSize"]
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        activity_trend_info, activity_trend_info_by_ptype = self.steps_obj.spark_clone_activity_trend_by_size(
            provisiontype=provision_type,
            minCloneSize=minCloneSize,
            maxCloneSize=maxCloneSize,
        )

        activity_trend_data = {"items": []}
        total_index = 0
        for index, row in activity_trend_info.items():
            for data_dict in row:
                temp_activity_trend_data = {}
                total_index += 1
                temp_activity_trend_data["systemId"] = data_dict["system_id"]
                temp_activity_trend_data["system"] = data_dict["system"]
                temp_activity_trend_data["provisionType"] = data_dict["provisiontype"]
                temp_activity_trend_data["totalSizeInBytes"] = data_dict["clonesize"]
                temp_activity_trend_data["utilizedSizeInBytes"] = data_dict["cloneusedsize"]
                t_stamp = re.sub(r"(.*)(\.[0-9]+\s.*)", r"\1", data_dict["clonecreationtime"])
                t_stamp = t_stamp.replace(" ", "T") + "Z"
                temp_activity_trend_data["createdAt"] = t_stamp
                temp_activity_trend_data["ioActivity"] = data_dict["last7days_avgiops"]
                temp_activity_trend_data["utilizedPercentage"] = data_dict["utilizedPercentage"]
                temp_activity_trend_data["activityTrendInfo"] = data_dict["activityTrendInfo"]
                common_fields = self.common_field_generator(
                    id=data_dict["cloneid"],
                    name=data_dict["clonename"],
                    type="clones activity trend",
                    generation=1,
                    customerId=data_dict["custid"],
                )
                temp_activity_trend_data.update(common_fields)
                activity_trend_data["items"].append(copy.deepcopy(temp_activity_trend_data))
        activity_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
        return ClonesActivityTrend(**activity_trend_data), activity_trend_info_by_ptype

    def get_applications(self, **params) -> ApplicationList:
        """Returning list of applications tagged with volume creation
        This will be replica of expected output of GET application list response

        Returns:
            ApplicationList: API Model as per REST API used for Applineage -applications
        """
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        app_data = self.steps_obj.spark_app_list_data()

        application_list_dict = {"items": []}
        app_dict = {}
        total_index = 0

        for index, data_dict in enumerate(app_data["data"]):
            total_index += 1
            common_fields = self.common_field_generator(
                name=data_dict["applicationname"],
                id=data_dict["applicationid"],
                type="applications lineage",
                generation=1,
                customerId=data_dict["custid"],
            )
            app_dict.update(common_fields)
            tmp_app_dict = {
                "numVolumes": data_dict["numVolumes"],
                "numSnapshots": data_dict["numSnapshots"],
                "numClones": data_dict["numClones"],
                "system": data_dict["sysname"],
                "systemId": data_dict["system_id"],
            }
            app_dict.update(tmp_app_dict)
            application_list_dict["items"].append(copy.deepcopy(app_dict))

        application_list_dict.update({"count": page_limit, "offset": page_offset, "total": total_index})

        return ApplicationList(**application_list_dict)

    def get_application_volumes_detail(self, **params) -> VolumesDetail:
        """This function returns the volume list for the given application id for expected data

        Returns:
            VolumesDetail: object having volume details
        """
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]
        app_id = params["app_id"]
        system_id = params["system_id"]

        creation_app_vol_data = self.steps_obj.spark_app_vol_list_data(app_id=app_id, system_id=system_id)

        application_vol_dict = {"items": []}
        vol_dict = {}
        total_index = 0

        for index, data_dict in enumerate(creation_app_vol_data["data"]):
            total_index += 1
            common_fields = self.common_field_generator(
                name=data_dict["volume_display_name"],
                id=data_dict["volid"],
                type="volumes application lineage",
                generation=1,
                customerId=data_dict["custid"],
            )
            vol_dict.update(common_fields)

            tmp_vol_dict = {
                "system": data_dict["system_name"],
                "systemId": data_dict["system_id"],
                "numClones": data_dict["volumeclonecount"],
                "numSnapshots": data_dict["volumesnapcount"],
                "country": data_dict["country"],
                "state": data_dict["state"],
                "city": data_dict["city"],
                "postalCode": data_dict["postal_code"],
                "utilizedSizeInBytes": int(data_dict["volumeusedsize_bytes"]),
                "totalSizeInBytes": int(data_dict["volumetotalsize_bytes"]),
            }
            vol_dict.update(tmp_vol_dict)
            application_vol_dict["items"].append(copy.deepcopy(vol_dict))

        application_vol_dict.update({"count": page_limit, "offset": page_offset, "total": total_index})
        return VolumesDetail(**application_vol_dict)

    def get_app_vol_snap_list(self, **params) -> SnapshotsDetail:
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]
        vol_uu_id = params["vol_uuid"]
        creation_app_vol_snap_data = self.steps_obj.spark_app_vol_snap_list_data(vol_uuid=vol_uu_id)
        creation_app_vol_snap_data_dict = {"items": []}
        app_vol_snap_dict = {}
        total_index = 0
        for index, data_dict in enumerate(creation_app_vol_snap_data["data"]):
            total_index += 1
            common_fields = self.common_field_generator()
            app_vol_snap_dict.update(common_fields)
            app_vol_snap_dict["name"] = data_dict["snapname"]
            app_vol_snap_dict["id"] = data_dict["snapid"]
            app_vol_snap_dict["customerId"] = data_dict["custid"]
            app_vol_snap_dict["totalSizeInBytes"] = 0 #int(self.format_size(data_dict["totalsnapsize"], "MB", "B"))
            app_vol_snap_dict["createdAt"] = data_dict["creationtime"].replace(".000", "Z")
            app_vol_snap_dict["expiresAt"] = data_dict["expirationtime"].replace(".000", "Z")
            app_vol_snap_dict["numClones"] = data_dict["numClones"] # get it from mock data

            creation_app_vol_snap_data_dict["items"].append(copy.deepcopy(app_vol_snap_dict))
        creation_app_vol_snap_data_dict.update({"count": page_limit, "offset": page_offset, "total": total_index})
        # return creation_app_vol_snap_data_dict
        return SnapshotsDetail(**creation_app_vol_snap_data_dict)

    def get_app_vol_clone_list(self, **params) -> ClonesDetail:
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]
        snap_id = params["snap_id"]
        creation_app_vol_clone_data = self.steps_obj.spark_app_vol_clone_list_data(snap_id=snap_id)
        creation_app_vol_clone_data_dict = {"items": []}
        app_vol_clone_dict = {}
        total_index = 0
        for index, data_dict in enumerate(creation_app_vol_clone_data["data"]):
            total_index += 1
            common_fields = self.common_field_generator()
            app_vol_clone_dict.update(common_fields)
            app_vol_clone_dict["name"] = data_dict["clonename"]
            app_vol_clone_dict["id"] = data_dict["cloneid"]
            app_vol_clone_dict["customerId"] = data_dict["custid"]
            app_vol_clone_dict["utilizedSizeInBytes"] = int(data_dict["cloneusedsize"]) #*(1024**2)
            app_vol_clone_dict["totalSizeInBytes"] = int(data_dict["clonesize"]) #*(1024**2)
            t_stamp = re.sub(r"(.*)(\.[0-9]+\s.*)", r"\1", data_dict["clonecreationtime"])
            t_stamp = t_stamp.replace(" ", "T") + "Z"
            #000 +0000 UTC
            app_vol_clone_dict["createdAt"] = t_stamp #data_dict["clonecreationtime"].replace(".000", "Z")
            app_vol_clone_dict["numSnapshots"] = data_dict["numSnapshots"]
            creation_app_vol_clone_data_dict["items"].append(copy.deepcopy(app_vol_clone_dict))
        creation_app_vol_clone_data_dict.update({"count": page_limit, "offset": page_offset, "total": total_index})
        # return creation_app_vol_clone_data_dict
        return ClonesDetail(**creation_app_vol_clone_data_dict)

    def get_inventory_storage_system_summary(self) -> InventoryStorageSystemsSummary:
        cost_dict = self.cost_dict
        inventory_summary_data = self.steps_obj.spark_inventory_storage_system_summary()
        temp_inv_data = {}

        numoflocations = cost_dict["postal_code"].nunique()
        temp_inv_data = {
            "numSystems": inventory_summary_data["data"][0]["totalsystems"],
            "numLocations": numoflocations,
            "utilizedSizeInBytes": int(inventory_summary_data["data"][0]["totalused"]),
            "totalSizeInBytes": int(inventory_summary_data["data"][0]["totalsize"]),
            # "cost": cost,
            "cost": int(inventory_summary_data["data"][0]["cost"]),
            "currency": "USD",
        }

        common_fields = self.common_field_generator(customerId=inventory_summary_data["data"][0]["custid"])
        temp_inv_data.update(common_fields)

        return InventoryStorageSystemsSummary(**temp_inv_data)

    def get_inventory_storage_system_cost_trend(self, **params) -> InventoryStorageSystemsCostTrend:
        cost_trend_frame = self.steps_obj.spark_inventory_storage_system_cost_trend()
        cost_dict = self.cost_dict
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]

        cost_trend_data = {"items": []}
        temp_cost_trend_data = {}
        total_index = 0
        for index, data_dict in enumerate(cost_trend_frame["data"]):
            total_index += 1

            common_fields = self.common_field_generator(generation="1")
            temp_cost_trend_data.update(common_fields)
            temp_cost_trend_data.update(
                {
                    "year": data_dict["year"],
                    "month": data_dict["month"],
                    "cost": data_dict["monthly_cost"],
                    "customerId": data_dict["customer_id"],
                    "currency": "USD",
                }
            )
            cost_trend_data["items"].append(copy.deepcopy(temp_cost_trend_data))
        cost_trend_data.update({"count": page_limit, "offset": page_offset, "total": total_index})
        # return cost_trend_data
        return InventoryStorageSystemsCostTrend(**cost_trend_data)

    def get_inventory_storage_systems(self, **params) -> InventoryStorageSystems:
        arrayInfo = False if "arrayInfo" not in params else params["arrayInfo"]
        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]
        storage_sys_data, storage_array_data = self.steps_obj.spark_inventory_storage_systems()
        inv_storage_systems = {"items": []}
        total_index = len(storage_sys_data["data"])
        for sys in storage_sys_data["data"]:
            system_dict = {}
            system_dict["id"] = sys["id"]
            system_dict["name"] = sys["name"]
            system_dict["type"] = sys["type"]
            system_dict["customerId"] = sys["customerId"]
            system_dict["numVolumes"] = sys["numVolumes"]
            system_dict["numArrays"] = sys["numArrays"]
            system_dict["numSnapshots"] = sys["numSnapshots"]
            system_dict["numClones"] = sys["numClones"]
            system_dict["postalCode"] = sys["postalCode"]
            system_dict["city"] = sys["city"]
            system_dict["country"] = sys["country"]
            system_dict["state"] = sys["state"]
            system_dict["latitude"] = sys["latitude"]
            system_dict["longitude"] = sys["longitude"]
            system_dict["utilizedSizeInBytes"] = sys["utilizedSizeInBytes"]
            system_dict["totalSizeInBytes"] = sys["totalSizeInBytes"]
            system_dict["cost"] = sys["cost"]
            system_dict["purchaseCost"] = sys["purchaseCost"]
            system_dict["currency"] = sys["currency"]
            system_dict["monthsToDepreciate"] = sys["monthsToDepreciate"]
            system_dict["boughtAt"] = sys["boughtAt"]
            system_dict["arrayInfo"] = []
            if arrayInfo and sys["type"] == "HPE Alletra 6000":
                for array in storage_array_data["data"]:
                    if sys["id"] == array["system_id"]:
                        array_dict = {
                            "name": array["array_name"],
                            "id": array["array_id"],
                            "type": array["type"],
                            "purchaseCost": array["purchaseCost"],
                            "cost": array["cost"],
                            "currency": array["currency"],
                            "monthsToDepreciate": array["monthsToDepreciate"],
                            "boughtAt": array["boughtAt"],
                            "utilizedSizeInBytes": array["utilizedSizeInBytes"],
                            "totalSizeInBytes": array["totalSizeInBytes"],
                        }
                        system_dict["arrayInfo"].append(array_dict)
            system_dict["generation"] = 1
            system_dict["resourceUri"] = ""
            system_dict["consoleUri"] = ""
            inv_storage_systems["items"].append(system_dict)

        inv_storage_systems.update({"count": page_limit, "offset": page_offset, "total": total_index})
        return InventoryStorageSystems(**inv_storage_systems)

    def get_inventory_product_details(self, **params) -> ArrayDetails:
        sys_uu_id = params["system_uuid"]

        page_limit = 10 if "pageLimit" not in params else params["pageLimit"]
        page_offset = 0 if "pageOffset" not in params else params["pageOffset"]
        product_details = self.steps_obj.spark_inventory_product_details(sys_uuid=sys_uu_id)
        print(product_details["data"])
        product_details_data = {"items": []}
        # Serial number need to be add in spark table
        for sysdata in product_details["data"]:
            temp_dict = {
                "customerId": sysdata["custid"],
                "name": sysdata["arrname"],
                "deviceType": sysdata["devicetype"],
                "serialNumber": "",
                "subscriptionInfo": [
                    {
                        "key": "",
                        "type": "",
                        "tier": "",
                        "startedAt": "",
                        "endsAt": "",
                        "quantity": "",
                        "availableQuantity": "",
                    }
                ],
                "warrantyInfo": {
                    "productNumber": "",
                    "serialNumber": "",
                    "startedAt": "",
                    "endsAt": "",
                    "status": "",
                },
                "supportCaseInfo": {
                    "productNumber": "",
                    "serialNumber": "",
                    "numPendingCases": 0,
                    "numResolvedCases": 0,
                    "timeStamp": "",
                },
            }
            common_fields = self.common_field_generator(id=params["system_uuid"], generation=1)
            temp_dict.update(common_fields)
            product_details_data["items"].append(temp_dict)
        product_details_data.update({"count": page_limit, "offset": page_offset, "total": len(product_details["data"])})
        return ArrayDetails(**product_details_data)
