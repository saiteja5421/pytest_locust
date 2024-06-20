import json
import logging
import os
import pathlib
import pandas as pd
import numpy as np

import sqlalchemy

# from lib.platform.storage_array.ssh_connection import SshConnection

logger = logging.getLogger()


class StorageTables:
    """Tables required to create mock API response will be generated.
    Volume, volume_usage,volume_performance, cost_data ,application,snapshots and clone related tables will be  created
    from collection json
    """

    def __init__(self):
        self.sys_inventory_table = pd.DataFrame()
        self.volume_table = pd.DataFrame()
        self.clone_table = pd.DataFrame()
        # spark app data using spark clone data ,so calling after spark_clone_data
        self.application_table = pd.DataFrame()
        self.volusage_table = pd.DataFrame()
        self.volume_performance_table = pd.DataFrame()
        self.snapshot_table = pd.DataFrame()
        self.cost_table = pd.DataFrame()

    def _get_collection_json_files(self, mock_dir):
        """From mock directory get all the mock collection json files
        Returns:
            list: mock json file list
        """
        mock_file_list = []
        for json_file in pathlib.Path(mock_dir).glob("**/*.json"):
            mock_file_list.append(json_file)
        return mock_file_list

    def _get_cost_info_files(self, mock_dir):
        """From mock directory get the cost info gz file
        Returns:
            list: cost info gz file
        """
        cost_info_file_list = []
        for costinfo in pathlib.Path(mock_dir).glob("**/cis.json"):
            cost_info_file_list.append(costinfo)
        return cost_info_file_list

    def _get_latest_collection_files(self, mock_dir):
        collection_dir_list = []
        for collection_dir in pathlib.Path(mock_dir).glob("**/*.json"):
            collection_dir_list.append(collection_dir)
        logger.info(collection_dir_list)
        latest_file = sorted(collection_dir_list)[-1]
        latest_collection_dir = os.path.dirname(latest_file)

        latest_collection_mock_files = []
        for json_file in pathlib.Path(latest_collection_dir).glob("**/*.json"):
            latest_collection_mock_files.append(json_file)

        return latest_collection_mock_files

    def create_table_from_multiple_collection(self, mock_dir):
        """Tables from raw data (json) will be created.
        Selected fields required for REST API response will be created as tables.

        """
        # Tables like Volume,Snapshot,Clone and etc will be created from latest collection.
        latest_collection = self._get_latest_collection_files(mock_dir)
        for mock_file in latest_collection:
            try:
                self.create_tables_from_latest_collection(mock_file)
            except Exception as e:
                print(e)

        # Volume usage and performance tables will be created from all collection as Trend graphs required to precess
        # all collection details
        mock_file_list = self._get_collection_json_files(mock_dir)
        for mock_file in mock_file_list:
            try:
                print(f" ================== Processing collection {mock_file} ===============================")
                self.create_volusage_perf_tables(mock_file)
                print(f" ================== Collection {mock_file} is completed ===============================")
            except Exception as e:
                print(e)

        # Cost info table will be created at last
        cost_info_file_list = self._get_cost_info_files(mock_dir)
        for cost_file in cost_info_file_list:
            print(f" ================== Processing cost info {cost_file} ===============================")
            cost_rows = self.generate_cost_table(cost_file)
            self.cost_table = pd.concat([self.cost_table, cost_rows], ignore_index=True)
            print(f" ================== cost info {cost_file} processing completed ===============================")

    def create_tables_from_latest_collection(self, mock_file):
        """This function will create all the storage table except Volume usage and volume performance table
            These tables required to be created from latest collection

        Returns:
            _type_: Each table will be concatenated with records fetched from this file
        """
        self._get_common_fields(mock_file)
        if self._mock_json_dict["CollectionType"] == "EOC":
            return None
        if len(self._mock_json_dict["Systems"]) == 0:
            return None
        # get rows from each collection and append to appropriate tables
        sys_inventory_rows = self.generate_inventory_table()
        self.sys_inventory_table = pd.concat([self.sys_inventory_table, sys_inventory_rows], ignore_index=True)

        vol_rows = self.generate_volume_table()
        self.volume_table = pd.concat([self.volume_table, vol_rows], ignore_index=True)

        clone_rows = self.generate_clone_table()
        self.clone_table = pd.concat([self.clone_table, clone_rows], ignore_index=True)

        # spark app data using spark clone data ,so calling after spark_clone_data
        app_rows = self.generate_app_table(clone_rows)
        self.application_table = pd.concat([self.application_table, app_rows], ignore_index=True)

        vol_df = vol_rows[["id", "arrid"]]
        if type(clone_rows):
            clone_df = pd.DataFrame()
        else:
            clone_df = clone_rows[["cloneid", "arrid"]]
            clone_df.rename(columns={"cloneid": "id"}, inplace=True)
        vol_clone_df = pd.concat([vol_df, clone_df], ignore_index=True)

        snap_rows = self.generate_snap_table(vol_clone_df)
        self.snapshot_table = pd.concat([self.snapshot_table, snap_rows], ignore_index=True)

    def _get_common_fields(self, mock_file):
        with open(mock_file) as f:
            self._mock_json_dict = json.load(f)
        self._common_fields = {
            "collection_start_time": self._mock_json_dict["CollectionStartTime"],
            "collection_end_time": self._mock_json_dict["CollectionEndTime"],
            "customer_id": self._mock_json_dict["PlatformCustomerID"],
            "collection_id": self._mock_json_dict["CollectionID"],
        }

        if self._mock_json_dict["CollectionType"] != "EOC":
            self._device_type = self._mock_json_dict["DeviceType"]
            self._volumes = self._mock_json_dict["Volumes"]
        self._collection_type = self._mock_json_dict["CollectionType"]

    def create_volusage_perf_tables(self, mock_file):
        """From single raw data json file ,it will create table of records.

        Returns:
            _type_: Each table will be concatenated with records fetched from this file
        """

        self._get_common_fields(mock_file)
        if self._mock_json_dict["CollectionType"] == "EOC":
            return None
        if len(self._mock_json_dict["Systems"]) == 0:
            return None
        vol_usage_rows = self.generate_volume_usage_table()
        self.volusage_table = pd.concat([self.volusage_table, vol_usage_rows], ignore_index=True)

        vol_perf_rows = self.generate_vol_performance_table()
        self.volume_performance_table = pd.concat([self.volume_performance_table, vol_perf_rows], ignore_index=True)

    def create_all_tables_from_mock_file(self, mock_file):
        """From single raw data json file ,it will create table of records.

        Returns:
            _type_: Each table will be concatenated with records fetched from this file
        """
        self._get_common_fields(mock_file)
        if self._mock_json_dict["CollectionType"] == "EOC":
            return None
        if len(self._mock_json_dict["Systems"]) == 0:
            return None
        # get rows from each collection and append to appropriate tables
        sys_inventory_rows = self.generate_inventory_table()
        self.sys_inventory_table = pd.concat([self.sys_inventory_table, sys_inventory_rows], ignore_index=True)

        vol_rows = self.generate_volume_table()
        self.volume_table = pd.concat([self.volume_table, vol_rows], ignore_index=True)

        clone_rows = self.generate_clone_table()
        self.clone_table = pd.concat([self.clone_table, clone_rows], ignore_index=True)

        # spark app data using spark clone data ,so calling after spark_clone_data
        app_rows = self.generate_app_table(clone_rows)
        self.application_table = pd.concat([self.application_table, app_rows], ignore_index=True)

        vol_df = vol_rows[["id", "arrid"]]
        clone_df = clone_rows[["cloneid", "arrid"]]
        clone_df.rename(columns={"cloneid": "id"}, inplace=True)
        vol_clone_df = pd.concat([vol_df, clone_df], ignore_index=True)

        snap_rows = self.generate_snap_table(vol_clone_df)
        self.snapshot_table = pd.concat([self.snapshot_table, snap_rows], ignore_index=True)

        vol_usage_rows = self.generate_volume_usage_table()
        self.volusage_table = pd.concat([self.volusage_table, vol_usage_rows], ignore_index=True)

        vol_perf_rows = self.generate_vol_performance_table()
        self.volume_performance_table = pd.concat([self.volume_performance_table, vol_perf_rows], ignore_index=True)

    def _convert_to_bytes(self, size_mb):
        size_bytes = size_mb * 1024**2
        return np.format_float_positional(size_bytes, trim="-")

    def _convert_to_mb(self, size_bytes):
        """Convert from bytes to Megabytes

        Returns:
            _type_: _description_
        """
        size_mb = round(int(size_bytes) / 1024**2)
        return np.format_float_positional(size_mb, trim="-")

    def _get_provision_type(self, thin_provision):
        """Get thin or thick provision value"""
        return "thin" if thin_provision == True else "thick"

    def _get_snap_type(self, is_unmanaged):
        return "periodic" if is_unmanaged else "adhoc"

    def _generate_volume_columns(self):
        """Columns fetched for Volume table from both the device types

        Returns:
            DataFrame: Volumes dataframe with columns [volid,arrayid,volumename,
            volumeTotalSizeBytes,volumeUsageBytes,volumeTotalSizeMiB,volumeUsedSizeMiB,volumecreationtime,volumeexpiresat]
        """
        vol_data_df_list = []
        # Volumes is a dictionary of list ,so parse each dictionary and get array id ,volume list then noremalize
        for array_id, vol_list in self._volumes.items():
            vol_data_df = pd.DataFrame()
            raw_df = pd.json_normalize(vol_list, max_level=2)
            if raw_df.empty:
                continue
            vol_data_df["volid"] = raw_df["id"]
            vol_data_df["arrayid"] = array_id
            vol_data_df["volumename"] = raw_df["name"]

            if self._device_type == "deviceType1":
                vol_data_df["volumeTotalSizeBytes"] = raw_df["sizeMiB"].apply(self._convert_to_bytes)
                vol_data_df["volumeUsageBytes"] = raw_df["usedSizeMiB"].apply(self._convert_to_bytes)
                vol_data_df["volumeTotalSizeMiB"] = raw_df["sizeMiB"]
                vol_data_df["volumeUsedSizeMiB"] = raw_df["usedSizeMiB"]
                vol_data_df["volumecreationtime"] = raw_df["creationTime.ms"]
                vol_data_df["volumeexpiresat"] = 0
            else:
                vol_data_df["volumeTotalSizeBytes"] = raw_df["size"]
                vol_data_df["volumeUsageBytes"] = raw_df["total_usage_bytes"]
                vol_data_df["volumeTotalSizeMiB"] = raw_df["size"].apply(self._convert_to_mb)
                vol_data_df["volumeUsedSizeMiB"] = raw_df["total_usage_bytes"].apply(self._convert_to_mb)
                vol_data_df["volumecreationtime"] = raw_df["creation_time"]
                vol_data_df["volumeexpiresat"] = 0  # No expiration value is there for volume at dev type2(nimble)

            vol_data_df_list.append(vol_data_df)

        volumes_df = pd.concat(vol_data_df_list, ignore_index=True)
        return volumes_df

    def generate_volume_table(self):
        """It will create volume table fields from raw data

        Returns:
            Dataframe: volume table dataframe
        """

        vol_data_df_list = []
        # Volumes is a dictionary of list ,so parse each dictionary and get array id ,volume list then normalize
        for array_id, vol_list in self._volumes.items():
            vol_data_df = pd.DataFrame()
            raw_df = pd.json_normalize(vol_list, max_level=2)
            # print(raw_df)
            if raw_df.empty:
                continue
            if self._device_type == "deviceType1":
                raw_df = raw_df[
                    raw_df["name"].str.startswith(".") == False
                ]  # Do not take system volumes. Sys vol starts with .
                raw_df = raw_df[raw_df["policy.system"] == False]
                vol_data_df = raw_df[["id", "name"]]
                vol_data_df["volumeId"] = raw_df["volumeId"]
                vol_data_df["volsize"] = raw_df["sizeMiB"].apply(self._convert_to_bytes)
                vol_data_df["usedsizeBytes"] = raw_df["usedSizeMiB"].apply(self._convert_to_bytes)
                vol_data_df["volsizeMiB"] = raw_df["sizeMiB"]
                vol_data_df["usedsize"] = raw_df["usedSizeMiB"]
                vol_data_df["provisionType"] = raw_df["thinProvisioned"].apply(self._get_provision_type)
                vol_data_df["creationTime"] = pd.to_datetime(raw_df["creationTime.ms"], unit="ms")
            else:
                vol_only = raw_df[(raw_df["clone"] == False)]  # Do not clone .
                vol_data_df = vol_only[["id", "name"]]
                vol_data_df["volumeId"] = vol_only["id"]
                vol_data_df["volsize"] = vol_only["size"]
                vol_data_df["usedsizeBytes"] = vol_only["vol_usage_compressed_bytes"]
                vol_data_df["volsizeMiB"] = vol_only["size"].apply(self._convert_to_mb)
                vol_data_df["usedsize"] = vol_only["vol_usage_compressed_bytes"].apply(self._convert_to_mb)
                vol_data_df["provisionType"] = vol_only["thinly_provisioned"].apply(self._get_provision_type)
                vol_data_df["creationTime"] = pd.to_datetime(vol_only["creation_time"], unit="ms")
                vol_data_df["num_snaps"] = vol_only["num_snaps"]
                vol_data_df["parent_vol_name"] = vol_only["parent_vol_name"]
                vol_data_df["parent_vol_id"] = vol_only["parent_vol_id"]
                vol_data_df["base_snap_name"] = vol_only["base_snap_name"]
                vol_data_df["base_snap_id"] = vol_only["base_snap_id"]
                vol_data_df["isClone"] = vol_only["clone"]
                # selected_df.loc[selected_df['thinProvisioned'] == False, 'ProvisionType'] = "thin"

            vol_data_df["arrid"] = array_id
            vol_data_df["devicetype"] = self._device_type
            self._add_common_fields(vol_data_df)

            vol_data_df_list.append(vol_data_df)
        if len(vol_data_df_list) == 0:
            raise Exception(
                f"There are no volumes created yet for the array: {array_id} of device type: {self._device_type}."
            )

        volumes_df = pd.concat(vol_data_df_list, ignore_index=True)
        return volumes_df

    def generate_volume_usage_table(self):
        """Volume usage table will be created from raw mock json

        Returns:
            Pandas.dataframe: Volume usage records
        """
        # TODO: But this is more of an array usage. Discuss and decide

        vol_usage_data_df_list = []
        array_capacity_df = self._get_array_capacity_columns()
        # As each volume is dictionary with array_id as key, loop it
        for array_id, vol_list in self._volumes.items():
            raw_volumes_df = pd.json_normalize(vol_list, max_level=2)
            # print(raw_volumes_df)
            vol_usage_data_df = pd.DataFrame()
            if raw_volumes_df.empty:
                continue
            vol_usage_data_df = raw_volumes_df[["id", "name"]]
            if self._device_type == "deviceType1":
                vol_usage_data_df["volumesize"] = raw_volumes_df["sizeMiB"].apply(self._convert_to_bytes)
                vol_usage_data_df["usedsizeBytes"] = raw_volumes_df["usedSizeMiB"].apply(self._convert_to_bytes)
                vol_usage_data_df["volumeId"] = raw_volumes_df["volumeId"]
                vol_usage_data_df["volumesizeMiB"] = raw_volumes_df["sizeMiB"]
                vol_usage_data_df["usedsize"] = raw_volumes_df["usedSizeMiB"]
                vol_usage_data_df["provisiontype"] = raw_volumes_df["thinProvisioned"].apply(self._get_provision_type)
            else:
                vol_usage_data_df["volumesize"] = raw_volumes_df["size"]
                vol_usage_data_df["usedsizeBytes"] = raw_volumes_df["total_usage_bytes"]
                vol_usage_data_df["volumeId"] = raw_volumes_df["id"]
                vol_usage_data_df["volumesizeMiB"] = raw_volumes_df["size"].apply(self._convert_to_mb)
                vol_usage_data_df["usedsize"] = raw_volumes_df["total_usage_bytes"].apply(self._convert_to_mb)
                vol_usage_data_df["provisiontype"] = raw_volumes_df["thinly_provisioned"].apply(
                    self._get_provision_type
                )
                # vol_data_df['avgiops'] =

            # Add below fields for all volume usage elements
            vol_usage_data_df["arrid"] = array_id
            self._add_common_fields(vol_usage_data_df)

            vol_usage_data_df_list.append(vol_usage_data_df)

        volumes_df = pd.concat(vol_usage_data_df_list, ignore_index=True)
        # array_capacity_df contains array total usage and used size(in bytes and MB)
        vol_usage_merged = volumes_df.merge(array_capacity_df, how="left", on="arrid")
        return vol_usage_merged

    def generate_clone_table(self):
        """clone table will be generated from raw data
        clone data available only for devicetype2(Nimble array)

        Returns:
            Pandas.Dataframe: clone table records
        """
        # Spark_clone data and Spakr_app_clonedata are same

        if self._mock_json_dict["DeviceType"] != "deviceType2":
            return None

        clone_list = []
        # common_fields = self._common_fields
        for storagesysid, vol_list in self._volumes.items():
            clone_data_df = pd.DataFrame()

            volumes_df = pd.json_normalize(vol_list, max_level=2)
            # Fetch the cloned volumes
            if volumes_df.empty:
                continue
            cloned_volumes_df = volumes_df[volumes_df["clone"] == True]
            # print(cloned_volumes_df)

            clone_data_df["cloneparentid"] = cloned_volumes_df["parent_vol_id"]
            clone_data_df["provisiontype"] = cloned_volumes_df["thinly_provisioned"].apply(self._get_provision_type)
            clone_data_df["cloneid"] = cloned_volumes_df["id"]
            clone_data_df["clonevolumeid"] = cloned_volumes_df[
                "id"
            ]  # TODO: Both cloneid and clonevolumeid are same . is it correct?
            clone_data_df["clonename"] = cloned_volumes_df["name"]
            clone_data_df["dedupe_enabled"] = cloned_volumes_df["dedupe_enabled"]
            clone_data_df["clonesize_mib"] = cloned_volumes_df["size"]
            clone_data_df["clonesizebytes"] = cloned_volumes_df["size"] * 1024 * 1024
            clone_data_df["clonecreationtime"] = cloned_volumes_df["creation_time"]
            clone_data_df["cloneusedsizebytes"] = cloned_volumes_df["total_usage_bytes"]
            clone_data_df["compressedusedbytes"] = cloned_volumes_df["vol_usage_compressed_bytes"]
            clone_data_df["mounted"] = False  # TODO: Is it correct?
            clone_data_df["num_snaps"] = cloned_volumes_df["num_snaps"]
            clone_data_df["parent_vol_name"] = cloned_volumes_df["parent_vol_name"]
            clone_data_df["parent_vol_id"] = cloned_volumes_df["parent_vol_id"]
            clone_data_df["base_snap_name"] = cloned_volumes_df["base_snap_name"]
            clone_data_df["base_snap_id"] = cloned_volumes_df["base_snap_id"]
            clone_data_df["isClone"] = cloned_volumes_df["clone"]

            clone_data_df["storagesysid"] = storagesysid
            clone_data_df["arrid"] = storagesysid
            self._add_common_fields(clone_data_df)
            clone_list.append(clone_data_df)

        clones_df = pd.concat(clone_list, ignore_index=True)
        return clones_df

    def _get_array_capacity_columns(self):
        """Array capacity columns such as array id, array total size array total used size will be returned

        Returns:
            Dataframe: Dataframe with columns [arrid,arrtotalsize,arrtotalused,arrtotalsizeBytes,arrtotalusedBytes]
        """
        mock_data = self._mock_json_dict
        arr_capacity_df = pd.DataFrame()

        if mock_data["DeviceType"] == "deviceType2":
            systems_list_dict = mock_data["Systems"]
            systems_df = pd.json_normalize(systems_list_dict, max_level=2)
            array_list_df = systems_df.explode(
                "arrays.items"
            ).reset_index()  # reset index will avoid duplicate index in this case.
            # This will get the array details which is inside system
            arrays_df = pd.json_normalize(array_list_df["arrays.items"])

            arr_capacity_df["arrid"] = arrays_df["id"]
            arr_capacity_df["arrtotalsizeBytes"] = arrays_df["usable_capacity_bytes"]
            arr_capacity_df["arrtotalusedBytes"] = arrays_df["usage"]
            arr_capacity_df["arrtotalsize"] = arrays_df["usable_capacity_bytes"].apply(self._convert_to_mb)
            arr_capacity_df["arrtotalused"] = arrays_df["usage"].apply(self._convert_to_mb)
        else:
            systems_capacity_list_dict = mock_data["SystemCapacity"]
            sys_capacity_df = pd.json_normalize(systems_capacity_list_dict, max_level=2)
            if sys_capacity_df.empty:
                raise Exception(f"There are no volumes created yet for this array of device type: {self._device_type} ")
            arr_capacity_df["arrid"] = sys_capacity_df.id
            arr_capacity_df["arrtotalsize"] = sys_capacity_df["capacityByTier.usableCapacity"]
            arr_capacity_df["arrtotalused"] = sys_capacity_df["capacityByTier.totalUsed"]
            arr_capacity_df["arrtotalsizeBytes"] = sys_capacity_df["capacityByTier.usableCapacity"].apply(
                self._convert_to_bytes
            )
            arr_capacity_df["arrtotalusedBytes"] = sys_capacity_df["capacityByTier.totalUsed"].apply(
                self._convert_to_bytes
            )
        return arr_capacity_df

    def generate_vol_performance_table(self):
        """Volume performance table will be generated from raw mock table

        Returns:
            _type_: _description_
        """
        performance_df = pd.DataFrame()
        volume_performance_dict = self._mock_json_dict["VolumePerformance"]
        volperf_raw_df = pd.json_normalize(volume_performance_dict, max_level=2)
        # performance_df["arrid"] = volperf_raw_df["systemId"]
        performance_df["id"] = volperf_raw_df["volumeId"]
        # performance_df["custid"] = volperf_raw_df["customerId"]
        if self._device_type == "deviceType2":
            performance_df["avgiops"] = volperf_raw_df["iops.total.avg_1day"]
        else:
            performance_df["avgiops"] = volperf_raw_df["iops.total.avgOf1day"]

        performance_df["collectionstarttime"] = self._common_fields["collection_start_time"]
        performance_df["collectionendtime"] = self._common_fields["collection_end_time"]
        performance_df["collectionId"] = self._common_fields["collection_id"]
        return performance_df

    def generate_app_table(self, clone_dataframe):
        """Create application table from raw mock json

        Args:
            clone_dataframe (Pandas.Dataframe): clone details are required for application data

        Returns:
            Pandas.Dataframe: application table dataframe
        """
        application_list = []

        if self._device_type == "deviceType1":
            appset = self._mock_json_dict["Applicationsets"]
            for array_id, app_list in appset.items():
                appset_raw_df = pd.json_normalize(app_list)
                appset_df = pd.DataFrame()
                appset_df["appsetname"] = appset_raw_df["appSetName"]
                appset_df["appname"] = appset_raw_df["appSetType"]
                appset_df["appsetid"] = appset_raw_df["appSetId"]
                appset_df["appusedsize"] = 0  # TODO What is the use of this param?
                appset_df["devicetype"] = self._device_type

                # Volume id is a list ,so flatten it with explode method
                # TODO Some application may not have any volumes associated with it. IS it correct?
                appset_df["volid"] = appset_raw_df["members"]
                appset_df = appset_df.explode("volid")
                # appset_df['arrayId'] = array_id
                self._add_common_fields(appset_df)
                # There is n clone in Devicetype1(Primera) so it is set as 0
                appset_df["volumeclonecount"] = 0
                application_list.append(appset_df)
        else:
            volumes_dict = self._mock_json_dict["Volumes"]
            for array_id, vol_list in volumes_dict.items():
                volumes_raw_df = pd.json_normalize(vol_list)
                # If perfpolicy Id is empty then the volume is not associated with any app
                if volumes_raw_df.empty:
                    continue
                appset_raw_df = volumes_raw_df[volumes_raw_df["perfpolicy_id"] != ""]
                appset_df = pd.DataFrame()
                appset_df["appsetid"] = appset_raw_df["perfpolicy_id"]
                appset_df["appsetname"] = appset_raw_df["perfpolicy_name"]
                appset_df["appname"] = appset_raw_df["perfpolicy_name"]
                appset_df["appusedsize"] = 0  # TODO What is the use of this param?
                appset_df["volid"] = appset_raw_df["id"]
                appset_df["devicetype"] = self._device_type
                appset_df["isClone"] = appset_raw_df["clone"]

                self._add_common_fields(appset_df)
                application_list.append(appset_df)

        app_list_df = pd.concat(application_list, ignore_index=True)
        logging.info(f"Application rows,columns count {app_list_df.shape}")

        # volumes = mock_data_dict['Volumes']
        vol_common_data_df = self._generate_volume_columns()
        logging.info(f"volume table rows,columns count {vol_common_data_df.shape}")

        # Volume and app dataframe columns will be merged. It is left join ,so even if volume id is null in app_list_df
        # , it will be retained.  .
        # volume may be there without app , but can app be there without volumes? If volumes are Null then mock data is
        # wrong
        app_vol_data_merged = app_list_df.merge(vol_common_data_df, on="volid", how="left")
        snap_dict = self._mock_json_dict["Snapshots"]

        snap_data_df = self._get_snap_count(snap_dict)
        # Some volumes may not have snapshot, so doing left join. So all the app with snap as well without snap will be
        # retained
        app_snap_data_merged = app_vol_data_merged.merge(snap_data_df, on="volid", how="left")
        # print(app_snap_data_merged)

        # Merge Clone count
        if self._device_type == "deviceType2":
            # Get the volume (cloneparentid is volume id) and it's clone count only if it is devicetype2(nimble)
            volclone_data = clone_dataframe.groupby(["cloneparentid"]).size().reset_index(name="volumeclonecount")
            volclone_data.rename(columns={"cloneparentid": "volid"}, inplace=True)
            # If the app has volume which has clone then it will be merged
            spark_app_data = app_snap_data_merged.merge(volclone_data, on="volid", how="left")
        else:
            spark_app_data = app_snap_data_merged

        return spark_app_data

    def _add_common_fields(self, appset_df):
        appset_df["collectionstarttime"] = self._common_fields["collection_start_time"]
        appset_df["collectionendtime"] = self._common_fields["collection_end_time"]
        appset_df["collectionId"] = self._common_fields["collection_id"]
        appset_df["custid"] = self._common_fields["customer_id"]

    def generate_snap_table(self, volume_dataframe):
        """Generate snapshot table from raw mock data

        Args:
            volume_dataframe (pandas.dataframe): volume dataframe required to get array id correspond to volume

        Returns:
            Pandas.Dataframe: snapshot dataframe
        """
        # Spark snap data and spark app snap data are same
        # Below are the columns required to be created
        """
            "collectionstarttime": "2021-11-20 05:58:30",
            "collectionendtime": "2021-11-20 05:58:30",
            "volumeid": "4c8d6c31-8a0b-2221-93a8-1403b2363176",
            "arrid": "093a28a53987d127d7000000000000000000000001",
            "snapid": "j2jnixn94i30nbzodpfrpqwu6e9nxdo7",
            "snapname": "pqa-dt2-vol-5-snap-0",
            "snapsize": 16447,
            "expirationtime": "2022-10-28 05:53:30",
            "retentiontime": "2022-10-28 05:53:30",
            "snaptype": "adhoc",
            "creationtime": "2021-07-30 06:12:02",
            "custid": "03bf4f5020022edecad3a7642bfb5391"
        """
        snap_data_list = []
        snapshots = self._mock_json_dict["Snapshots"]
        # For device 1
        for vol_id, snap_list in snapshots.items():
            snap_raw_df = pd.json_normalize(snap_list, max_level=2)
            snap_data_df = pd.DataFrame()
            if self._device_type == "deviceType1":
                no_snapshots = snap_raw_df.empty
                if no_snapshots:
                    # In case of device type 1 there is no snapshot so return it immediately with empty dataframe
                    # empty dataframe is return as expected output is dataframe or list of dataframe
                    return snap_data_df
                # snap_data_df['arrid'] = snap_raw_df['systemId']
                snap_data_df["snapMiB"] = snap_raw_df["sizeMiB"]
                snap_data_df["snapsizeBytes"] = snap_raw_df["sizeMiB"].apply(self._convert_to_bytes)
                snap_data_df["snaptype"] = "adhoc"
                snap_data_df["expirationtime"] = None
                if "expirationTime" in snap_raw_df:
                    if not snap_raw_df["expirationTime"].isnull().values[0]:
                        snap_data_df["expirationtime"] = pd.to_datetime(snap_raw_df["expirationTime.Ms"], unit="ms")

                snap_data_df["creationtime"] = pd.to_datetime(snap_raw_df["creationTime.Ms"], unit="ms")

                snap_data_df["retentiontime"] = None
                if "retentionTime" in snap_raw_df:
                    if not snap_raw_df["retentionTime"].isnull().values[0]:
                        snap_data_df["retentiontime"] = pd.to_datetime(snap_raw_df["retentionTime.Ms"], unit="ms")
            else:  # dt2
                snap_data_df["snapsizeBytes"] = snap_raw_df["size"]
                snap_data_df["snapMiB"] = snap_raw_df["size"].apply(self._convert_to_mb)
                snap_data_df["snaptype"] = snap_raw_df["is_unmanaged"].apply(self._get_snap_type)
                # tmp_df = pd.DataFrame()
                snap_data_df["creationtime"] = pd.to_datetime(snap_raw_df["creation_time"], unit="s")
                snap_data_df["expirationtime"] = pd.to_datetime(snap_raw_df["expiry_time"], unit="s")
                snap_data_df["retentiontime"] = snap_data_df["expirationtime"]

            snap_data_df["snapname"] = snap_raw_df["name"]
            snap_data_df["snapid"] = snap_raw_df["id"]
            # snap_data_df["vol_name"] = snap_raw_df["vol_name"]
            snap_data_df["volumeId"] = vol_id
            snap_data_df["devicetype"] = self._device_type

            self._add_common_fields(snap_data_df)

            snap_data_list.append(snap_data_df)

        snap_data_list = pd.concat(snap_data_list, ignore_index=True)
        # To fetch array Id
        volume_subset = volume_dataframe[["id", "arrid"]]
        # volume_subset.rename(columns = {'arrayId':'arrid'}, inplace = True)
        volume_subset.rename(columns={"id": "volumeId"}, inplace=True)
        # With the snapshot data append array id. Inner is used because only when volume id is there ,we need to get
        # array id
        snapdata_final = snap_data_list.merge(volume_subset, on="volumeId", how="left")

        return snapdata_final

    def generate_inventory_table(self):
        """Generate Inventory table with below columns. This is generated from Systems entry in mock data.
        Values given below are sample.

        "collectionstarttime": "2021-11-20 05:58:30",
        "collectionendtime": "2021-11-20 05:58:30",
        "custid": "03bf4f5020022edecad3a7642bfb5391",
        "arrid": "4ENC4AB8OC",
        "storagesysid": "4ENC4AB8OC",
        "numofarrays": 1,
        "devicetype": "devicetype1",
        "storagesysname": "system_4ENC4AB8OC",
        "arrname": "system_4ENC4AB8OC",
        "storagesystotalused": 2536248,
        "storagesysusablecapacity": 718539772,
        "arrtotalused": 2536248,
        "arrusablecapacity": 718539772
        """
        system_df = pd.DataFrame()
        logger.info("hi")
        system_data = self._mock_json_dict["Systems"]
        systems_raw_df = pd.json_normalize(system_data, max_level=2)
        if systems_raw_df.empty:
            return pd.DataFrame()
        if self._device_type == "deviceType1":
            system_df = self._gen_dt1_inventory_table(systems_raw_df)

        else:
            # This will create a row for each array
            systems_raw_df = systems_raw_df.explode(
                "arrays.items"
            ).reset_index()  # reset index will avoid duplicate index in this case.
            # This will get the array details which is inside system
            arrays_df = pd.json_normalize(systems_raw_df["arrays.items"])
            system_df["arrid"] = arrays_df["id"]
            system_df["arrname"] = arrays_df["name"]
            system_df["dedupe_ratio"] = systems_raw_df["dedupe_ratio"]
            system_df["arrtotalused"] = arrays_df["usage"]
            system_df["arrusablecapacity"] = arrays_df["usable_capacity_bytes"]
            system_df["storagesystotalused"] = systems_raw_df["usage"]
            system_df["storagesysusablecapacity"] = systems_raw_df["usable_capacity_bytes"]

        # Below fields are common for both the devices ( Nimble and Primera)
        system_df["storagesysid"] = systems_raw_df["id"]
        system_df["devicetype"] = self._device_type
        system_df["storagesysname"] = systems_raw_df["name"]
        # Find the number of array present in Storage system. In Primera (devtype1 - each system is an array. But in
        # Nimble - A storage system can have multiple array)
        systems_grouped = system_df.groupby("storagesysid").size()
        array_counted_df = systems_grouped.reset_index(name="num_array")
        system_df = system_df.merge(array_counted_df, on="storagesysid", how="inner")

        system_df["collectionId"] = self._common_fields["collection_id"]
        system_df["collectionStartTime"] = self._common_fields["collection_start_time"]
        system_df["collectionEndTime"] = self._common_fields["collection_end_time"]

        return system_df

    def _gen_dt1_inventory_table(self, systems_raw_df):
        system_df = pd.DataFrame()
        system_df["arrid"] = systems_raw_df["id"]
        system_df["arrname"] = systems_raw_df["name"]

        # system_capacity = self._mock_json_dict["SystemCapacity"][1]
        for array_detail in self._mock_json_dict["SystemCapacity"]:
            if array_detail["systemid"] == systems_raw_df["id"][0]:
                system_capacity = array_detail
                break
        sys_capacity_raw_df = pd.json_normalize(system_capacity, max_level=2)
        if sys_capacity_raw_df.empty:
            print("There is no data available for System Capacity, there are probably no volumes created yet.")
            return pd.DataFrame()
        system_df["arrtotalused"] = (
            (
                sys_capacity_raw_df.loc[
                    (system_df["arrid"] == sys_capacity_raw_df.systemid),
                    "capacitySummary.allocated.total",
                ]
            )
            .astype(int)
            .apply(self._convert_to_bytes)
        )
        system_df["arrusablecapacity"] = (
            (
                sys_capacity_raw_df.loc[
                    (system_df["arrid"] == sys_capacity_raw_df.systemid),
                    "capacitySummary.total",
                ]
            )
            .astype(int)
            .apply(self._convert_to_bytes)
        )
        system_df["storagesystotalused"] = system_df["arrtotalused"]
        system_df["storagesysusablecapacity"] = system_df["arrusablecapacity"]
        return system_df

    def generate_cost_table(self, cost_info_file):
        """Generate cost data table from Cost file.
        For entire collection only one cost info file would be present

        Args:
            cost_info_file (_type_): _description_

        Returns:
            pandas.Dataframe: Cost info dataframe
        """
        """
            "PUNYKYPG72": {
                "city": "New York",
                "state": "New York",
                "country": "Northeastern United States",
                "postalCode": "10017"
        """
        cost_df = pd.DataFrame()
        # with open(cost_info_file, "rb") as f:
        #     file_content = f.read()
        with open(cost_info_file) as f:
            cost_info_json = json.load(f)
        # cost_info_json = json.loads(file_content)
        cost_dict = cost_info_json["costAndLocationInfo"]
        raw_df = pd.json_normalize(cost_dict, max_level=2)
        # print(raw_df)
        cost_df["systemId"] = raw_df["systemId"]
        cost_df["city"] = raw_df["locationInfo.city"]
        cost_df["state"] = raw_df["locationInfo.state"]
        cost_df["country"] = raw_df["locationInfo.country"]
        cost_df["postalCode"] = raw_df["locationInfo.postalCode"]

        return cost_df

    def _get_snap_count(self, snap_dict):
        """volume id and snapshot count for that volume will be fetched

        Args:
            snap_dict (_type_): snapcount dataframe

        Returns:
            Pandas.dataframe: Snap count dataframe
        """
        snap_df_list = []
        for vol_id, snap_list in snap_dict.items():
            snap_raw_df = pd.json_normalize(snap_list)
            data = {
                "volid": [vol_id],
                "volumesnapcount": [snap_raw_df.shape[0]],
            }  # Each row under a snapshots.
            snap_df = pd.DataFrame(data)
            snap_df_list.append(snap_df)
            # print(snap_df)
        snap_count_df = pd.concat(snap_df_list, ignore_index=True)
        return snap_count_df


def _convert_to_dict(dataframes):
    converted_dict = dataframes.to_json(orient="table", index=False)
    json_dict = json.loads(converted_dict)
    # data frame will have both schema and data . we need data which has table records
    return json_dict["data"]


def create_tables_from_collection(mock_dir, db_file="aggregated_db.sqlite"):
    """Storage tables will be created from given mock data directory.
    Mock data dir contains multiple collection json and a single cost info data file.
    From this data all the tables will be created

    Args:
        mock_dir (_type_): _description_
        outfile (str, optional): _description_. Defaults to "sparkdata.json".
    """

    # For each collection file , get spark tables such as spark_volume_data, spark_vol_usage and etc.
    table = StorageTables()
    table.create_table_from_multiple_collection(mock_dir)

    # upload_folder_name = os.path.basename(mock_dir)
    # _write_storage_table_json(outfile, table, upload_folder_name)
    _create_aggregated_db(table, db_file)


def generate_spark_table_from_single_file(mock_file, outfile="sparksingledata.json"):
    """Storage tables will be created from given mock data directory.
    Mock data dir contains multiple collection json and a single cost info data file.
    From this data all the tables will be created

    Args:
        mock_dir (_type_): _description_
        outfile (str, optional): _description_. Defaults to "sparkdata.json".
    """

    # For each collection file , get spark tables such as spark_volume_data, spark_vol_usage and etc.
    table = StorageTables()
    table.create_all_tables_from_mock_file(mock_file)
    upload_folder_name = os.path.basename(mock_file)
    _write_storage_table_json(outfile, table, upload_folder_name)


def _write_storage_table_json(outfile, table, upload_folder_name):
    spark_vol_data_dict = _convert_to_dict(table.volume_table)
    spark_clone_data_dict = _convert_to_dict(table.clone_table)
    spark_perf_data_dict = _convert_to_dict(table.volume_performance_table)
    spark_volusage_dict = _convert_to_dict(table.volusage_table)
    spark_appdata_dict = _convert_to_dict(table.application_table)
    spark_snapdata_dict = _convert_to_dict(table.snapshot_table)
    spark_inventory_dict = _convert_to_dict(table.sys_inventory_table)
    spark_cost_dict = _convert_to_dict(table.cost_table)

    spark_json_table_dict = {}
    spark_json_table_dict["spark_voldata"] = spark_vol_data_dict
    spark_json_table_dict["spark_volusage"] = spark_volusage_dict
    spark_json_table_dict["spark_volperf"] = spark_perf_data_dict
    spark_json_table_dict["spark_appdata"] = spark_appdata_dict
    spark_json_table_dict["spark_snapdata"] = spark_snapdata_dict
    spark_json_table_dict["spark_clonedata"] = spark_clone_data_dict
    spark_json_table_dict["spark_invdata"] = spark_inventory_dict
    spark_json_table_dict["spark_costdata"] = spark_cost_dict
    spark_json_table_dict["upload_folder_name"] = upload_folder_name

    with open(outfile, "w") as json_file:
        json.dump(spark_json_table_dict, json_file)


def _create_aggregated_db(table: StorageTables, db_file):
    # out_db_name = f"/mock_aggregated_db.sqlite"
    engine = sqlalchemy.create_engine("sqlite:///%s" % db_file, execution_options={"sqlite_raw_colnames": True})
    # conn = engine.connect()

    table.volume_table.to_sql("volume_last_collection", engine, if_exists="replace", index=False)
    # Create a dictionary mapping storagesysid to dedupe_ratio
    dedupe_dict = table.sys_inventory_table.set_index("storagesysid")["dedupe_ratio"].to_dict()

    # Add a new column 'dedupe_ratio' to clone_table conditionally
    table.clone_table["dedupe_ratio"] = table.clone_table["storagesysid"].map(dedupe_dict)
    table.clone_table["compressedusedbytes_deduped"] = (
        table.clone_table["compressedusedbytes"] / table.clone_table["dedupe_ratio"]
    )
    table.clone_table.to_sql("clone_last_collection", engine, if_exists="replace", index=False)

    sysname_dict = table.sys_inventory_table.set_index("storagesysid")["storagesysname"].to_dict()
    table.application_table["sysname"] = table.application_table["arrayid"].map(sysname_dict)
    table.application_table.to_sql("app_last_collection", engine, if_exists="replace", index=False)
    table.snapshot_table.to_sql("snapshot_last_collection", engine, if_exists="replace", index=False)
    table.sys_inventory_table.to_sql("system_last_collection", engine, if_exists="replace", index=False)
    table.volume_performance_table.to_sql("volperf_all_collection", engine, if_exists="replace", index=False)
    table.volusage_table.to_sql("volusage_all_collection", engine, if_exists="replace", index=False)
    if not table.cost_table.empty:
        table.cost_table.to_sql("system_cis", engine, if_exists="replace", index=False)


# def copy_to_remote(
#     hostname="10.239.73.120",
#     username="root",
#     password="HPE_ftc3404",
#     source="spark_data.json",
#     out_dir="/tmp/spark_test_data.json",
# ):
#     client = SshConnection(hostname=hostname, username=username, password=password, sftp=True)
#     client.put(source, out_dir)
#     client.sftp_close()


if __name__ == "__main__":
    mock_dir = "lib/dscc/data_panorama/data_collector/out"
    spark_table = f"{mock_dir}/aggregateddb.sqlite"
    create_tables_from_collection(mock_dir, spark_table)
