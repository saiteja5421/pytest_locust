# api
from datetime import datetime
from lib.common.users.user import ApiHeader
from lib.dscc.data_panorama.consumption.api.volumes_api import VolumesInfo
from lib.dscc.data_panorama.consumption.models.volumes import *
from lib.dscc.data_panorama.consumption.models.snapshots import *
from lib.dscc.data_panorama.consumption.models.clones import *
from lib.dscc.data_panorama.app_lineage.models.app_lineage import *
from lib.dscc.data_panorama.inventory_manager.models.inventory_manager import *
from lib.dscc.data_panorama.consumption.api.snapshots_api import SnapshotsInfo
from lib.dscc.data_panorama.consumption.api.clones_api import ClonesInfo
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps


class WastageVolumes(object):
    """
    Class for Wastage volume used to host Wastage library functions.
    functions present:
        get_volume_count() - returns total number of volumes
        get_mounted_volumes() - returns list of mounted volumes
        get_non_mounted_volumes() - returns list of non_mounted volumes
        get_mounted_volumes_and_clones_count() - returns dict of mounted_volumes (list) and clones count (int)
        get_mounted_volumes_and_snaps_count() - returns dict of mounted_volumes (list) and snapshot count (int)
        get_non_mounted_volumes_and_clones_count() - returns dict of non_mounted_volumes (list) and clones count (int)
        get_non_mounted_volumes_and_snaps_count() - returns dict of non_mounted_volumes (list) and snapshot count (int)
        get_volume_type() - returns volume provision type (thin/thick) of passed volume
        get_thin_volume_list() - function to get list of thin provisioned volume
        get_thick_volume_list() - function to get list of thick provisioned volume
        get_volume_month_cost() - function to get total volume cost for given month/year
        get_snapshot_month_cost() - function to get total snapshot cost for given month/year
        get_clone_month_cost() - function to get total clone cost for given month/year
        get_mounted_clones() - returns list of clones that are mounted
        get_non_mounted_clones() - returns list of clones that are not mounted/connected
        get_clone_io_activity() - takes in clone_name and returns dict of clone name and IO activity
        get_thin_clone_list() - function to get list of thin provisioned clone
        get_thick_clone_list() - function to get list of thick provisioned clone
        get_snaps_count_based_on_age_range() - takes in snapshot age range and returns number of snapshots created during the period
        get_snaps_count_based_on_size_range() - takes in snapshot size range and returns number of snapshots in that size range
        get_clone_type() - returns provisioning type of clone passed. Returns empty string if provided clone not found.
        get_number_of_adhoc_snapshots() - returns total number of adhoc snapshots.
        get_number_of_periodic_snapshots() - returns total number of periodic snapshots.
        get_all_response_volume_path_parameter() - function to calculate and trigger multiple API/Array calls based on limit and offset with path parameter as volume_uuid

    """

    def __init__(self, url: str, api_header: ApiHeader) -> None:
        self.url = url
        self.volume_info = VolumesInfo(self.url, api_header=api_header)
        self.clones_info = ClonesInfo(self.url, api_header=api_header)
        self.snaps_info = SnapshotsInfo(self.url, api_header=api_header)

    def get_all_response(func, limit=10, offset=0, **params):
        """
        Function to calculate and trigger multiple API/Array calls based on limit and offset. Collected response will be unified into single dictionary and converted to corresponding Class object.
        Arguments:
            func        (R) - Variable to recieve array or API methods and reused
            limit: int  (O) - Default value for pageLimit is 10 and maximum value is 1000
            offset: int (O) - Default value of pageOffset is 0. Determines from which offset the data should be read from table.
            params:     (O) - set of query parameters required for func()

        """
        response_list = []
        items = []

        # Get total items using default api call
        total = func(**params).total
        if limit != 0:
            rem_items = limit
        else:
            rem_items = total

        # Decide number of function calls required to get the complete set of data keeping 1000 as the maximum value of limit/pagelimit
        while rem_items:
            if rem_items > 1000:
                limit = 1000
            else:
                limit = rem_items
            params["limit"] = limit
            params["offset"] = offset
            response_list.append(func(**params))
            rem_items = rem_items - limit
            offset += limit

        # Get list of parameters present as part of items dictionary
        response_params = [
            param for param in dir(response_list[0].items[0]) if param not in dir(type(response_list[0].items[0]))
        ]
        for item in response_list:
            for val in item.items:
                temp_dict = {}
                for param in response_params:
                    temp_dict[param] = val.__getattribute__(param)
                items.append(temp_dict)

        # Compose dictionary by combining multiple response object
        response_dict = {"items": items, "pageLimit": 10, "pageOffset": 0, "total": total}

        # Convert the dictionary to object using models and return the object.
        response_obj = type(response_list[0])(**response_dict)
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
            response_params = [
                param for param in dir(response_list[0].items[0]) if param not in dir(type(response_list[0].items[0]))
            ]
            # Get the variables of class ActivityTrendDetail to build dictionary

            vars = list(ActivityTrendDetail.__dataclass_fields__.keys())

            # vars = [
            #     vars
            #     for vars in dir(response_list[0].items[0].activityTrendInfo[0])
            #     if vars not in dir(type(response_list[0].items[0].activityTrendInfo[0]))
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

    def get_volume_count(self) -> int:
        """
        Function returns total number of volumes belonging to the user account.
        Arguments: None
        Returns: vol_count(int): Total number of volumes created
        """
        vol_info = self.volume_info.get_volumes_consumption()
        vol_count = vol_info.numVolumes
        return vol_count

    def get_mounted_volumes(self) -> list:
        """
        Function returns list of volumes that are mounted.
        Arguments: None
        Return argument: mounted_volumes (list): list of mounted volumes
        """
        mounted_volumes = []
        # vol_info = self.volume_info.get_volumes_activity_trend()
        vol_info = self.get_all_response_volactivity(self.volume_info.get_volumes_activity_trend)
        for volume in vol_info.items:
            if volume.isConnected == True:
                mounted_volumes.append(volume.name)
        return mounted_volumes

    def get_non_mounted_volumes(self) -> list:
        """
        Function returns list of volumes that are mounted.
        Arguments: None
        Return argument: non_mounted_volumes (list): list of non-mounted volumes
        """
        non_mounted_volumes = []
        # vol_info = self.volume_info.get_volumes_activity_trend()
        vol_info = self.get_all_response_volactivity(self.volume_info.get_volumes_activity_trend)
        for volume in vol_info.items:
            if volume.isConnected == False:
                non_mounted_volumes.append(volume.name)
        return non_mounted_volumes

    def get_mounted_volumes_and_clones_count(self) -> dict:
        """
        Function returns list of volumes that are mounted and total number of clones.
        Arguments: None
        Return argument: dict of mounted_volumes (list) and clones count (int)
        """
        clones_count = self.clones_info.get_clones_consumption().numClones
        mounted_volumes = self.get_mounted_volumes()
        return dict(clones_count=clones_count, mounted_volumes_list=mounted_volumes)

    def get_mounted_volumes_and_snaps_count(self) -> dict:
        """
        Function returns list of volumes that are mounted and total number of Snapshot for given volume.
        Arguments: None
        Return argument: dict of mounted_volumes (list) and snapshot count (int)
        """
        snapshot_count = self.snaps_info.get_snapshot_consumption().totalSnapshotsCreated
        mounted_volumes = self.get_mounted_volumes()
        return dict(snaps_count=snapshot_count, mounted_volumes_list=mounted_volumes)

    def get_non_mounted_volumes_and_clones_count(self) -> dict:
        """
        Function returns list of volumes that are not mounted and total number of clones for given volume.
        Arguments: None
        Return argument: dict of non_mounted_volumes (list) and clones count (int)
        """
        clones_count = self.clones_info.get_clones_consumption().numClones
        non_mounted_volumes = self.get_non_mounted_volumes()
        return dict(clones_count=clones_count, non_mounted_volumes_list=non_mounted_volumes)

    def get_non_mounted_volumes_and_snaps_count(self) -> dict:
        """
        Function returns list of volumes that are not mounted and total number of Snapshot for given volume.
        Arguments: None
        Return argument: dict of non_mounted_volumes (list) and snapshot count (int)
        """
        snapshot_count = self.snaps_info.get_snapshot_consumption().totalSnapshotsCreated
        non_mounted_volumes = self.get_non_mounted_volumes()
        return dict(snaps_count=snapshot_count, non_mounted_volumes_list=non_mounted_volumes)

    def get_volume_type(self, vol_name) -> str:
        """
        Function returns provisioning type of volume passed. Returns empty string if volume not found.
        Arguments: None
        Return argument: volume_type (str): volume provision type thin/thick
        """
        volume_type = ""
        # vol_info = self.volume_info.get_volumes_activity_trend()
        vol_info = self.get_all_response_volactivity(self.volume_info.get_volumes_activity_trend)
        for volume in vol_info.items:
            if volume.name == vol_name:
                volume_type = volume.provisionType
        return volume_type

    def get_thin_volume_list(self, provisiontype = None):
        """
        Function returns complete of thin provisioned volumes as a list.
        Arguments: None
        Return argument: thin_volume_list (list): list of thin volume
        """
        thin_volume_list = []
        # vol_info = self.volume_info.get_volumes_activity_trend()
        if provisiontype is None:
            vol_info = self.get_all_response_volactivity(self.volume_info.get_volumes_activity_trend)
        else:
            vol_info = self.get_all_response_volactivity(self.volume_info.get_volumes_activity_trend, provisiontype=provisiontype)
        for volume in vol_info.items:
            if volume.provisionType == "Thin":
                thin_volume_list.append(volume.name)
        return thin_volume_list

    def get_thick_volume_list(self, provisiontype = None):
        """
        Function returns complete of thick provisioned volumes as a list.
        Arguments: None
        Return argument: thick_volume_list (list): list of thick volume
        """
        thick_volume_list = []
        # vol_info = self.volume_info.get_volumes_activity_trend()

        if provisiontype is None:
            vol_info = self.get_all_response_volactivity(self.volume_info.get_volumes_activity_trend)
        else:
            vol_info = self.get_all_response_volactivity(self.volume_info.get_volumes_activity_trend, provisiontype=provisiontype)
        
        for volume in vol_info.items:
            if volume.provisionType == "Thick":
                thick_volume_list.append(volume.name)
        return thick_volume_list

    def get_volume_month_cost(self, year: int, month: int, startTime: datetime, endTime: datetime):
        """
        Function returns total volume usage cost for provided year/month.
        Arguments:
                year (int) R  : takes year in yyyy format
                month (int) R : takes month in 1-12 digit format
                startTime/endTime (dateTime) R : parameters should be of RFC3339 time format
        Return argument: total_volume_cost, currency_type (list): list of volume cost and currency type
                         empty list in case of time data unavailable.
        """
        monthly_cost = []
        vol_cost_obj = self.volume_info.get_volumes_cost_trend(startTime=startTime, endTime=endTime)
        for monthly_item in vol_cost_obj.items:
            if monthly_item.year == year and monthly_item.month == month:
                total_volume_cost = monthly_item.cost
                currency_type = monthly_item.currency
                monthly_cost = [total_volume_cost, currency_type]
        return monthly_cost

    def get_snapshot_month_cost(self, year: int, month: int, startTime: datetime, endTime: datetime):
        """
        Function returns total snapshot usage cost for provided year/month.
        Arguments:
                year (int) Required : takes year in yyyy format
                month (int) Required : takes month in 1-12 digit format
                                startTime/endTime (dateTime) Required : parameters should be of RFC3339 time format
        Return argument: total_snap_cost, currency_type (list): list of snapshot cost and currency type
                empty list in case of time data unavailable.
        """
        snap_cost_obj = self.snaps_info.get_snapshots_cost_trend(startTime=startTime, endTime=endTime)
        for monthly_cost in snap_cost_obj.items:
            if monthly_cost.year == year and monthly_cost.month == month:
                total_snap_cost = monthly_cost.cost
                currency_type = monthly_cost.currency
                monthly_cost = [total_snap_cost, currency_type]
        return monthly_cost

    def get_clone_month_cost(self, year: int, month: int, startTime: datetime, endTime: datetime):
        """
        Function returns total clones usage cost for provided year/month.
        Arguments:
                year (int) : takes year in yyyy format
                month (int) : takes month in 1-12 digit format
                startTime/endTime (dateTime) R : parameters should be of RFC3339 time format
        Return argument: total_clone_cost, currency_type (list): list of clones cost and currency type
        """
        monthly_cost = []
        clone_cost_obj = self.clones_info.get_clones_cost_trend(startTime=startTime, endTime=endTime)
        for monthly_item in clone_cost_obj.items:
            if monthly_item.year == year and monthly_item.month == month:
                total_clone_cost = monthly_item.cost
                currency_type = monthly_item.currency
                monthly_cost = [total_clone_cost, currency_type]
        return monthly_cost

    def get_mounted_clones(self) -> list:
        """
        Function returns list of clones that are mounted.
        Arguments: None
        Return argument: mounted_clones (list): list of mounted clones
        """
        mounted_clones = []
        clone_info = self.get_all_response(self.clones_info.get_clones_activity_trend)
        for clone in clone_info.items:
            if clone.isConnected == True:
                mounted_clones.append(clone.name)
        return mounted_clones

    def get_non_mounted_clones(self) -> list:
        """
        Function returns list of clones that are not mounted/connected.
        Arguments: None
        Return argument: non_mounted_clones (list): list of mounted clones
        """
        non_mounted_clones = []
        clone_info = self.get_all_response(self.clones_info.get_clones_activity_trend)
        for clone in clone_info.items:
            if clone.isConnected == False:
                non_mounted_clones.append(clone.name)
        return non_mounted_clones

    def get_clone_io_activity(self, clone_name: str = "") -> dict:
        """
        Function takes in clone_name and returns dict of clone name and IO activity.
        If no clone_name passed, then function returns all clones and its corresponding IO activity
        Arguments: clone_name (str, optional): name of the clone
        Return argument: clone_io_activity (dict): dictionary of clone name and ioactivity
        """
        clone_io_activity = {}
        clone_info = self.get_all_response(self.clones_info.get_clones_activity_trend)
        if clone_name:
            for clone in clone_info.items:
                if clone.name == clone_name:
                    clone_io_activity[clone.name] = clone.ioActivity
        else:
            for clone in clone_info.items:
                clone_io_activity[clone.name] = clone.ioActivity
        return clone_io_activity

    def get_thin_clone_list(self):
        """
        Function returns complete of thin provisioned clones as a list.
        Arguments: None
        Return argument: thin_clone_list (list): list of thin clones
        """
        thin_clone_list = []
        clone_info = self.get_all_response(self.clones_info.get_clones_activity_trend)
        for clone in clone_info.items:
            if clone.provisionType == "Thin":
                thin_clone_list.append(clone.name)
        return thin_clone_list

    def get_thick_clone_list(self):
        """
        Function returns complete of thick provisioned clones as a list.
        Arguments: None
        Return argument: thick_clone_list (list): list of thick clones
        """
        thick_clone_list = []
        clone_info = self.get_all_response(self.clones_info.get_clones_activity_trend)
        for clone in clone_info.items:
            if clone.provisionType == "Thick":
                thick_clone_list.append(clone.name)
        return thick_clone_list

    def get_snaps_count_based_on_age_range(self, age: str) -> int:
        """
        Function takes in snapshot age  as string and returns number of snapshots created bucket during the period.
        Arguments: age (str, Mandatory): range in months
        Return argument: bucket (int): number of snapshots created bucket during that period
        """
        numSnapshots = 0
        snaps_age_info = self.get_all_response(self.snaps_info.get_snapshots_age_trend)
        for snaps_age in snaps_age_info.items:
            for snaps_size in snaps_age.sizeInfo:
                if snaps_age.age == age:
                    numSnapshots += snaps_size.numSnapshots
        return numSnapshots

    def get_snaps_count_based_on_size_range(self, bucketSize: str) -> int:
        """
        Function takes in bucketSize and returns number of snapshots.
        Arguments: bucketSize (str, Mandatory): min or mid or max
        Return argument: numberOfSnapshotsCreated (int): number of snapshots
        """
        numberOfSnapshotsCreated = 0
        if bucketSize == "min":
            index = 0
        elif bucketSize == "mid":
            index = 1
        elif bucketSize == "max":
            index = 2
        else:
            print("BucketSize Inputs not valid and should be min or mid or max")

        snaps_age_info = self.get_all_response(self.snaps_info.get_snapshots_age_trend)

        for snaps_age in snaps_age_info.items:
            for snaps in range(len(snaps_age.sizeInfo)):
                if snaps == index:
                    numberOfSnapshotsCreated += snaps_age.sizeInfo[index]["numSnapshots"]
        return numberOfSnapshotsCreated

    def get_clone_type(self, cloneName: str) -> str:
        """
        Function returns type of clone passed. Returns empty string if provided clone not found.
        Arguments: cloneName (str, Mandatory) : name of the clone
        Return argument: clone_type (str): clone provision type thin/thick
        """
        clone_type = ""
        clone_info = self.get_all_response(self.clones_info.get_clones_activity_trend)
        for clone in clone_info.items:
            if clone.name == cloneName:
                clone_type = clone.provisionType
                return clone_type
        return clone_type

    def get_number_of_adhoc_snapshots(self) -> int:
        """
        Function returns total number of adhoc snapshots.
        Arguments: None
        Return argument: numAdhocSnapshots (int): total number of adhoc snapshots
        """
        numAdhocSnapshots = 0
        snaps_retention = self.get_all_response(self.snaps_info.get_snapshots_retention_trend)
        for snap_retention in snaps_retention.items:
            numAdhocSnapshots += snap_retention.numAdhocSnapshots
        return numAdhocSnapshots

    def get_number_of_periodic_snapshots(self) -> int:
        """
        Function returns total number of periodic snapshots
        Arguments: None
        Return argument: numPeriodicSnapshots (int): total number of periodic snapshots
        """
        numPeriodicSnapshots = 0
        snaps_retention = self.get_all_response(self.snaps_info.get_snapshots_retention_trend)
        for snap_retention in snaps_retention.items:
            numPeriodicSnapshots += snap_retention.numPeriodicSnapshots
        return numPeriodicSnapshots

    def get_all_response_volume_path_parameter(self, func, limit=0, offset=0, **params):
        """
        Function to calculate and trigger multiple API/Array calls based on limit and offset with path parameter as "volume_uuid". Collected response will be unified into single dictionary and converted to corresponding Class object.
        Arguments:
            func        (R) - Variable to recieve array or API methods and reused
            volume_uuid (R) - Volume uuid
            limit: int  (O) - Limit =0, means retreive all the records. Value passed to limit, means retreive number of records equal to value passed.
            offset: int (O) - Default value of pageOffset is 0. Determines from which offset the data should be read from table.
            params:     (O) - set of query parameters required for func()

        """
        response_list = []
        items = []

        # Get total items using default api call
        total = func(**params).total
        dataclass_type = type(func(**params))
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
            response_params = [
                param for param in dir(response_list[0].items[0]) if param not in dir(type(response_list[0].items[0]))
            ]
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
