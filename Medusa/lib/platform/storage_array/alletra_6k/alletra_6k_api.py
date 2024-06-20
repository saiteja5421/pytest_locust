from tests.e2e.data_panorama.panorama_context import Context
from lib.platform.storage_array.ssh_connection import SshConnection

from dateutil.relativedelta import relativedelta
import datetime
import time
import random
import re
import threading
import logging
import sys

logger = logging.getLogger()


class AlletraNimble(object):
    """
    A class to represent a AletraNimble.

    Author: Kranthi  kumar

    Usage:
    ------
        obj = AletraNimble(context=context, array_name=array_name)
        obj.funcname()

    Attributes:
    -----------
        context* :- Context object
            type:- Context
        array_name :- Arraname to configure setup,  if not provieded default array will use from yml file array info
            type:- str

    Methods:
    --------
        set_data_set()
            :- Used to set the year, month, vols-count, thickvols, snaps per vol(0 means periodic snaps),clones per volume
        array_config_info()
            :- Used to get array information like size, usedspace ... ETC
        get_vol_size()
            :- Used to get total size remaining array
        set_back_date_time()
            :- Ysed to set date back to actual date
        set_date_time()
            :- Used to set date and time in array
        create_vol_coll()
            :- Used to create volume collection
        get_vol_names()
            :- Used to get volume names
        get_all_periodic_snaps()
            :- used to get all periodic snap shosts
        modify_retention_time()
            :- used to get modify retention time for snaps
        snap_del_recreate()
            :- Used to delete and recreate snaps
        add_schedule_to_vol_coll()
            :- Used to add schedule to volume collections
        mount_clones()
            :- Used to mount clones
        _snap_clone_create()
            :- Used to create snaps and clones for volume
        vol_assoc_to_vol_coll()
            :- Used to associate volume to volume collections
        create_initiator_group()
            :- Used to create initiator group on aletra 6K arrays
        _config_helper()
            :- Used to to create volume and set snap count and clones count in thread
        generate_config()
            :- Used to generate on aletra 6k arrays
        delete_clones_vols()
            :- Used to delete clones and volumes
        _get_initiator_group()
            :- Used to get all initiator groups from array
        dis_assoc_vol()
            :- Used to dis associate volumes from volume collection
        delete_script_created_clones()
            :- Used to delete all script created clones
        delete_script_created_volumes()
            :- Used to delete all script created volumes
        delete_clones()
            :- Used to delete clones
        delete_volumes()
            : Used to delete volumes
        vol_disassoc_del_vol_coll()
            : Used to disc associate volumes from vol collection and remove vol collections
        clear_config()
            :- Used to clear array configuration
        create_array_config()
            :- Used to merge all above methods in single place
    Return:
    -------
        :- return AletraNimble object
    """

    def __init__(self, context: Context):

        """
        __init__: Constructs all the necessary attributes for the AletraNimble object.
        ---------

        Parameters:
        -----------
            context* :- Context object
                type:- Context
            array_name :- Arraname to configure setup
                type:- str

        Global Variables:
        -----------------
            self.context:
                :- User passed context object storing
            self.created_config_info:
                :- After configure array this dictionary holds all config information
            self.array_info:
                :- Get and storing array information object from context array info
            self.array_name:
                :- if user not specified, pull from yml array info
            self.array_cred:
                :- Get and storing array credential object from context array credentials
            self.client:
                :- Connecting to array using SshConnection() module and storing array obj
            self.array_config:
                :- get and storing array configuration object from context array config
            self.volume_name:
                :- Defining volume name to create volumes
            self.vol_index:
                :- Volume index number to create multiple volumes
            self.clones_to_remove:
                :- all clones will be in in this variable to remove after configuration done
            self.vols_to_remove:
                :- all volumes will be in in this variable to remove after configuration done
            self.vol_coll_vol_list:
                :- all volumes list which is in collections will store in this variable
            self.vol_coll_prefi:
                :- prefix number to create volume collections
            self.vol_coll_name:
                :- volume collection name will be stored
            self.vol_coll_list:
                :- all volume collections will be stored in this variable
            mounted_clones:
                :- all mounted clones will stroed in this variable
            self.vol_size:
                :- volume size to create volumes
            self.initiator_grp_name:
                :- If user not passed initiator group name from yaml file defining initiator group name
            self.volumes_count:
                :- total volumes count to create
            self.thick_volumes_count:
                :- total thick volume count
            self.snap_count_per_vol:
                :- Total snaps per volume count
            self.modified_date:
                :- Modified date to set in array
        """

        self.context = context
        self.created_config_info = dict()
        self.array_info = self.context.array_info
        self.array_name: str = ""
        self.array_cred = self.context.array_6K_cred
        self.client: object = ""
        self.volume_name: str = ""
        self.vol_index: int = 1
        self.scheduler_index: int = 2
        self.clones_to_remove: list = []
        self.vols_to_remove: list = []
        self.vol_coll_vol_list: list = []
        self.vol_coll_prefix: int = 1
        self.vol_coll_name: str = ""
        self.vol_coll_list: list = []
        self.mounted_clones: list = []
        self.modified_date: str = ""
        self.voumes_date_data_set: list = []
        self.initiator_grp_name = ""
        self.current_data_set = []
        self.volumes_count = 1
        self.vol_size: int = 1
        self.size_in_bytes = 1
        self.thick_volumes_count = 1
        self.snap_count_per_vol = (
            random.randint(5, 25)
            if self.context.array_config.snapscountpervolume is None
            else self.context.array_config.snapscountpervolume
        )

    def set_data_set(self) -> list:
        """
        set_data_set: Constructs the data sets in list format. with in the list each list index will represent
        -------------     - year, month , volumes for perticular year, thick volumes count and snap count.
        Note: by calling method will get return volumes data sets, it can be modified based on test case demands.
        -----
        Parameters:
        -----------
            Not required

        Global Variables:
        -----------------
            Not required

        Return:
            :- Data set list
        """

        vol_count_current_year = self.volumes_count - 40
        vols_per_month_current_year = [
            vol_count_current_year // 7 + (1 if x < vol_count_current_year % 7 else 0) for x in range(7)
        ]
        thick_vol_count_remaining = self.thick_volumes_count - 20
        thick_vols_per_month_current_year = [
            thick_vol_count_remaining // 7 + (1 if x < thick_vol_count_remaining % 7 else 0) for x in range(7)
        ]
        self.voumes_date_data_set = [
            [
                0,
                1,
                0,
                0,
                0,
                vols_per_month_current_year[0],
                thick_vols_per_month_current_year[0],
                self.snap_count_per_vol,
            ],
            [0, 2, 0, 0, 0, vols_per_month_current_year[1], thick_vols_per_month_current_year[1], 0],
            [
                0,
                3,
                0,
                0,
                0,
                vols_per_month_current_year[2],
                thick_vols_per_month_current_year[2],
                self.snap_count_per_vol,
            ],
            [0, 4, 0, 0, 0, vols_per_month_current_year[3], thick_vols_per_month_current_year[3], 0],
            [
                0,
                5,
                0,
                0,
                0,
                vols_per_month_current_year[4],
                thick_vols_per_month_current_year[4],
                self.snap_count_per_vol,
            ],
            [
                0,
                6,
                0,
                0,
                0,
                vols_per_month_current_year[5],
                thick_vols_per_month_current_year[5],
                0,
            ],
            [
                0,
                9,
                0,
                0,
                0,
                vols_per_month_current_year[5],
                thick_vols_per_month_current_year[5],
                self.snap_count_per_vol,
            ],
            [1, 1, 0, 0, 0, 2, 1, 0],
            [1, 3, 0, 0, 0, 3, 2, random.randint(5, 8)],
            [1, 5, 0, 0, 0, 5, 4, 0],
            [1, 7, 0, 0, 0, 4, 2, random.randint(5, 15)],
            [2, 2, 0, 0, 0, 2, 2, 0],
            [2, 3, 0, 0, 0, 5, 1, random.randint(5, 6)],
            [2, 5, 0, 0, 0, 3, 0, 0],
            [3, 2, 0, 0, 0, 2, 1, self.snap_count_per_vol],
            [3, 3, 0, 0, 0, 3, 1, 0],
            [4, 6, 0, 0, 0, 4, 2, random.randint(1, 4)],
            [4, 9, 0, 0, 0, 2, 1, 0],
            [5, 2, 0, 0, 0, 2, 1, random.randint(5, 12)],
            [5, 10, 0, 0, 0, 3, 2, 0],
        ]
        return self.voumes_date_data_set

    def check_key_config_dict(self, key):
        if key not in self.created_config_info:
            self.created_config_info[key] = {}

    def array_config_info(self) -> None:
        """
        array_config_info: method will execute array info command and frame a dictionary each field as a key and represening value like below.
        -------------
        Model: vmware
        Extended Model: vmware-4G-0T-16F
        Serial: pqa-2-sys
        Version: 6.1.1.0-1001542-opt
        All-Flash: No
        Array name: pqa-2-sys
        Supported configuration: Yes
        Link-local IP address: 169.254.55.185
        Group ID: 6483254974321079717
        Member GID: 1
        Group Management IP: 172.21.165.34
        1G/10G_T/SFP/FC NIC: 4/0/0/0
        Total array capacity (MiB): 21815
        Total array usage (MiB): 0
        Total array cache capacity (MiB): 6405
        Volume compression: 1.00X
        Uncompressed snapshot usage including pending deletes (MiB): 0
        Snapshot compression: 1.00X
        Pending Deletes (MiB): 0
        Available space (MiB): 21815
        Dedupe capacity (MiB): 0
        Dedupe usage (MiB): 0
        Member of pool: default
        Status: reachable

        Parameters:
        -----------
            Not required

        Global Variables:
        -----------------
            Not required

        Return:
            :- N/A
        """
        cmd = f"array --info {self.array_name}"
        output = self.client.exec_cmd(cmd=cmd)
        output = (
            output.replace(" ", "")
            .replace("Link-local", "Linklocal")
            .replace("(", "")
            .replace(")", "")
            .replace("All-", "All")
        )
        self.check_key_config_dict(key=self.array_name)
        self.created_config_info[self.array_name].update({"device_type": "6k"})
        for field in output.split("\n"):
            if "/" in field:
                continue
            spli_val = field.split(":")
            self.created_config_info[self.array_name].update({spli_val[0]: spli_val[1]})

    def convert_float_to_decimal(self, flo=0.0, precision=5):
        """
        Convert a float to string of decimal.
        precision: by default 2.
        If no arg provided, return "0.00".
        """
        return ("%." + str(precision) + "f") % flo

    def format_vol_size(self, vol_size, vol_size_in, vol_size_out, precision=0):
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
                return self.convert_float_to_decimal((vol_size * 1024.0**2), precision)
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

    def get_vol_size(self) -> None:
        """
        get_vol_size: method will get the total capacity and total used capacity and calculate per volume size and set self.vol_size global value.
        -------------

        Parameters:
        -----------
            Not required

        Global Variables:
        -----------------
            Not required

        Return:
            :- N/A
        """

        self.array_config_info()
        arra_size = int(self.created_config_info[self.array_name]["TotalarraycapacityMiB"]) - int(
            self.created_config_info[self.array_name]["TotalarrayusageMiB"]
        )

        space_to_use = arra_size - round(arra_size / 3)
        self.vol_size = round(space_to_use / self.volumes_count)
        logger.info("Volume size to create volumes is {self.vol_size}Mib")
        assert self.vol_size > 0, "No Space available in Array..."

    def set_back_date_time(self) -> None:

        """
        set_back_date_time: Method collects current date and time from VM and set back same date in Aletra 6K array
        ---------

        Parameters:
        -----------
            :- Not Required

        Return:
            :- None
        """

        array_set_back_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cmd = f"date --edit '{array_set_back_date}'"
        self.client.exec_cmd(cmd=cmd, retry=True)
        logger.info(f"Setting back actual array date and time {array_set_back_date}")
        print(f"{self.array_name}-INFO: Setting back actual array date and time {array_set_back_date}")

    def set_date_time(self, date_to_set) -> str:
        """
        set_date_time: Method will collect date to be modify and will set in Aletra 6K array
        ---------

        Parameters:
        -----------
            :- Not Required

        Return:
            replace_array_date :- Replaced date and time in str format
        """

        replace_array_date = re.sub("(.*)\.[0-9]+", r"\1", str(date_to_set))
        logger.info(f"Modifying Array date to {date_to_set}")
        print(f"{self.array_name}-INFO: Modifying Array date to {date_to_set}")
        # Executing command on array to set date and time
        cmd = f"date --edit '{replace_array_date}'"
        self.client.exec_cmd(cmd=cmd, retry=True)
        return replace_array_date

    def create_vol_coll(self, coll_name: str) -> str:
        """
        create_vol_coll: method will create volume collection
        ----------------

        Parameters:
        -----------
            coll_name :- Collection name

        Return:
            :- collection name
        """
        col_name = coll_name + "-" + str(self.vol_coll_prefix)
        cmd = f"volcoll --create {col_name}"
        self.client.exec_cmd(cmd=cmd)
        self.vol_coll_prefix += 1
        self.vol_coll_list.append(col_name)
        logger.info(f"volume collection name {col_name} created")
        return col_name

    def get_vol_names(self, count: int = 1) -> list:
        """
        get_vol_names: method will generate volume names based on count.
        --------------

        Parameters:
        -----------
            count :- how many volumes to be generate

        Return:
            :- volume names list
        """
        volume_names = list()
        for _ in range(count):
            volume_names.append(self.volume_name + str(self.vol_index))
            self.vol_index += 1
        logger.info(f"volume names {volume_names}")
        return volume_names

    def get_all_periodic_snaps(self) -> dict:
        """
        get_all_periodic_snaps: method will get all periodic snap shots
        -----------------------

        Parameters:
        -----------
            None

        Return:
            :- Periodic snap shots list
        """
        vol_with_periodic_snaps = {}
        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )
        cmd = f"snap --list --all --unmanaged"
        stdout = client.exec_cmd(cmd=cmd)
        if "INFO: No snapshot records" in stdout or not stdout:
            return vol_with_periodic_snaps

        for line in stdout.split("\n"):
            if re.search("------------.*|Volume.*|Name.*", line):
                continue
            search_obj = re.search("(pqa-.*volume-[0-9]+)\s(vol-coll.*\.[0-9]+)\s+[0-9]+\s", line)
            if search_obj:
                vol_with_periodic_snaps[search_obj.group(1)] = search_obj.group(2)
        client.close_connection()
        logger.info(f"Periodic snaps created in array to represented volumes{vol_with_periodic_snaps}")
        return vol_with_periodic_snaps

    def modify_retention_time(self):
        """
        modify_retention_time: method will modify retention time
        ---------------------

        Parameters:
        -----------
            None

        Return:
            :- None
        """
        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )
        periodic_snaps = self.get_all_periodic_snaps()
        step_val = 1
        choice_list = ["hours", "days", "weeks"]
        for vol, snap in periodic_snaps.items():
            self.created_config_info[self.array_name][vol].update({"totalPeriodicSnapshotsCount": 1})
            if step_val == 2:
                logger.info("Modifying retention time on snap {snap}")
                ttl = random.randint(1, 25)
                ttl_unit = random.choices(choice_list)[0]
                cmd = f"snap --edit {snap} --vol {vol} --ttl {ttl} --ttl_unit {ttl_unit}"
                stdout = client.exec_cmd(cmd=cmd)
                logger.info(f"CMD: {cmd}")
                print(f"{self.array_name}-INFO: {cmd}")
                step_val = 1
                self.created_config_info[self.array_name][vol]["snaps"].update(
                    {snap: {"snap_type": "Periodic", "retentionPeriodRange": str(ttl) + str(ttl_unit)}}
                )
                continue
            self.created_config_info[self.array_name][vol]["snaps"].update(
                {snap: {"snap_type": "Periodic", "retentionPeriodRange": None}}
            )
            step_val += 1

        client.close_connection()

    def update_vol_clone_info(self):
        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )
        total_vols = self.vols_to_remove + self.clones_to_remove
        for vol in self.vols_to_remove:
            cmd = f"vol --info {vol}"
            stdout = client.exec_cmd(cmd=cmd)
            for line in stdout.split("\n"):

                if "Serial number" in line:
                    s_no = line.split(": ")[1]
                    self.created_config_info[self.array_name][vol].update(
                        {
                            "volumeId": s_no,
                            "activityTrend": [{"timeStamp": None, "ioActivity": None}],
                            "ioActivity": None,
                            "array": self.array_name,
                            "volumeName": vol,
                            "volumeCreationAge": None,
                            "utilizedSpace": None,
                        }
                    )
                elif "Created" in line:
                    s_no = line.split(": ")[1]
                    c_date = re.search("(.*)\s+([0-9]+:[0-9]+:[0-9]+)", s_no)
                    converted_cre_date = datetime.datetime.strptime(c_date.group(1), "%b %d %Y").strftime("%Y-%m-%d")
                    converted_time = datetime.datetime.strptime(c_date.group(2), "%H:%M:%S")
                    converted_time = converted_time.strftime("%I:%M:%S %p")
                    creation_date_time = str(converted_cre_date) + " " + str(converted_time)
                    self.created_config_info[self.array_name][vol].update({"creationTime": creation_date_time})
                    break

            for clone in self.created_config_info[self.array_name][vol]["clones"]:
                cmd = f"vol --info {clone}"
                stdout = client.exec_cmd(cmd=cmd)
                for line in stdout.split("\n"):
                    if "Size" in line:
                        s_no = line.split(": ")[1]
                        size_bytes = self.format_vol_size(int(s_no), "MB", "B", precision=0)
                        self.created_config_info[self.array_name][vol]["clones"][clone].update(
                            {"totalSpace": size_bytes, "cloneName": clone, "utilizedSpace": None, "ioActivity": None}
                        )
                    elif "Thinly-provisioned" in line:
                        s_no = line.split(": ")[1]
                        if "No" in s_no:
                            self.created_config_info[self.array_name][vol]["clones"][clone].update(
                                {"provisionType": "thick"}
                            )
                        else:
                            self.created_config_info[self.array_name][vol]["clones"][clone].update(
                                {"provisionType": "thin"}
                            )
                    elif "Created" in line:
                        s_no = line.split(": ")[1]
                        c_date = re.search("(.*)\s+([0-9]+:[0-9]+:[0-9]+)", s_no)
                        converted_cre_date = datetime.datetime.strptime(c_date.group(1), "%b %d %Y").strftime(
                            "%Y-%m-%d"
                        )
                        converted_time = datetime.datetime.strptime(c_date.group(2), "%H:%M:%S")
                        converted_time = converted_time.strftime("%I:%M:%S %p")
                        creation_date_time = str(converted_cre_date) + " " + str(converted_time)
                        self.created_config_info[self.array_name][vol]["clones"][clone].update(
                            {"creationTime": creation_date_time}
                        )
                        break

        """
        if "Serial number" in line:
                s_no = line.split(": ")[1]
                self.created_config_info[self.array_name][clone].update(
                    {
                        "activityTrend": [{"timeStamp": None, "ioActivity": None}],
                        "ioActivity": None,
                        "array": self.array_name,
                        "cloneName": clone,
                        "volumeCreationAge": None,
                        "utilizedSpace": None,
                    }
                )
            
            
        """
        client.close_connection()

    def add_schedule_to_vol_coll(self) -> None:
        """
        add_schedule_to_vol_coll: method will add schedule to volume collection
        -------------------------

        Parameters:
        -----------
            None

        Return:
            :- None
        """
        cmd = "date"
        stdout = self.client.exec_cmd(cmd=cmd)
        min_to_change = re.search(".*[0-9]\s([0-9]+:[0-9]+):[0-9]+\s[A-Z]+.*", stdout).group(1).split(":")
        hour = min_to_change[0]
        mins = min_to_change[1]
        if int(mins) == 59:
            if hour == "00":
                hour = "01"
            elif hour == "23":
                hour = "00"
            elif "0" in hour[0]:
                if "9" in hour[1]:
                    hour = "10"
                else:
                    hour = "0" + str(int(hour[1]) + 1)
            schedule_at_time = hour + ":" + "01"
        elif int(mins) == "00":
            schedule_at_time = hour + ":" + "01"
        elif int(hour) == "00" and int(mins) == "00":
            schedule_at_time = "00:01"
        elif "0" in mins[0]:
            if "9" in mins[1]:
                schedule_at_time = hour + ":10"
            else:
                schedule_at_time = hour + ":0" + str(int(mins[1]) + 1)
        else:
            schedule_at_time = hour + ":" + str(int(mins) + 1)
        for coll in self.vol_coll_list:
            sch_name = coll + "-schedule-" + str(self.scheduler_index)
            logger.info(f"Adding schedule name {sch_name} to volume collection name {coll}")
            cmd = f"volcoll --addsched {coll} --schedule {sch_name} --repeat 1 --repeat_unit hours --at {schedule_at_time} --days all --retain 1"
            stdout = self.client.exec_cmd(cmd=cmd)
            logger.info(f"CMD: {cmd}")
            print(f"{self.array_name}-INFO: {cmd}")

    def vol_assoc_to_vol_coll(self, vol):
        """
        vol_assoc_to_vol_coll: method will associate volume to volume collection
        ---------------------

        Parameters:
        -----------
            vol:- volume name
        Return:
            :- None
        """
        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )
        if not self.vol_coll_name:
            self.vol_coll_name = self.create_vol_coll(coll_name="vol-coll-periodic-snaps")
        try:
            cmd = f"vol --assoc {vol} --volcoll {self.vol_coll_name}"
            output = client.exec_cmd(cmd=cmd)
        except Exception as error:
            if "has reached its maximum size" in error.args[0] or "Object exists" in error.args[0]:
                logger.info(
                    "{self.vol_coll_name} volume collection reached its maximum size. creating another volume collection."
                )
                print(
                    f"{self.vol_coll_name} volume collection reached its maximum size / already exist. creating another volume collection."
                )
                client = SshConnection(
                    hostname=self.array_info[self.array_name]["arrayip"],
                    username=self.array_cred.username,
                    password=self.array_cred.password,
                )
                self.vol_coll_name = self.create_vol_coll(coll_name="vol-coll-periodic-snaps")
                logger.info("{self.vol_coll_name} volume collection created")
                print(f"{self.vol_coll_name} volume collection created")
                cmd = f"vol --assoc {vol} --volcoll {self.vol_coll_name}"
                output = client.exec_cmd(cmd=cmd)

        self.vol_coll_vol_list.append(vol)
        client.close_connection()

    def get_vol_coll_count(self):
        cmd = "volcoll --list"
        output = self.client.exec_cmd(cmd=cmd)
        coll_count = []
        if "No volume collections" in output or not output:
            return coll_count

        for line in output.split("\n"):
            if "--------" in line or "Application" in line or "Name" in line:
                continue
            coll_num = int(re.sub("(.*-)([0-9]+)(\snone\s+.*)", r"\2", line))
            coll_count.append(coll_num)

        return coll_count

    def create_initiator_group(self, context) -> str:
        """
        create_initiator_group: method will create initiator group
        -----------------------

        Parameters:
        -----------
            context:- context object
        Return:
            :- None
        """

        initiator_iqn = context.array_info[self.array_name]["initiatoriqn"]
        initiator_ip = context.array_info[self.array_name]["initiatorip"]

        # Get initiator group names from array
        cmd = "initiatorgrp --list"
        std_out = self.client.exec_cmd(cmd=cmd)

        """
            Check provided initiator group as part of array or not
            if initiator group not created in array
                - create initiator group and add iqn and host IP to it
            if initiator already part of array than just return initiator group name
        """

        if self.initiator_grp_name not in std_out:
            cmd = f"initiatorgrp --create {self.initiator_grp_name}"
            self.client.exec_cmd(cmd=cmd)
            cmd = f"initiatorgrp --add_initiators {self.initiator_grp_name} --label medusa --initiator_name {initiator_iqn} --ipaddr {initiator_ip}"
            self.client.exec_cmd(cmd=cmd)
            logger.info("Initiator group {self.initiator_grp_name} created")
            return self.initiator_grp_name
        else:
            return self.initiator_grp_name

    def _snap_clone_create(
        self,
        vol_name: str = "",
        snap_count: int = 0,
        clone_create: bool = True,
        mounted: bool = True,
    ):
        """
        _snap_clone_create: method will create snapshot and its clone if clone-create True
        -------------------

        Parameters:
        -----------
            vol_name:- Volume name to create snap and its clone
            snap_count:- snapshot count per volume
            clone_create:- clone create True/False
            mounted:- True/False to mount clone
        Return:
            :- None
        """

        # Since running method in threads establishing ssh object seperately for each thread
        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )

        """
        Looping through snap count
            creating snap shot
            if clone create True
                checking snap index number is even or odd, not creating clones for every snap to avoid time complexity
                    if even creating clone and mounting clone based on mounted param value
        """
        clone_count = 0
        for ind, count in enumerate(range(snap_count)):
            snap_name = vol_name + "-snap-" + str(count)
            cmd = f"vol --snap {vol_name} --snapname {snap_name}"
            client.exec_cmd(cmd=cmd, retry=True)
            self.created_config_info[self.array_name][vol_name]["snaps"].update(
                {snap_name: {"snap_type": "Manual", "creation_date": self.modified_date}}
            )
            if clone_create:
                if ind % 2 == 0:
                    clone_name = snap_name + "-clone-" + str(count)
                    cmd = f"vol --clone {vol_name} --snapname {snap_name} --clonename {clone_name} --start_offline"
                    client.exec_cmd(cmd=cmd)
                    clone_count += 1
                    if not mounted:
                        cmd = f"vol --addacl {clone_name} --initiatorgrp {self.initiator_grp_name}"
                        self.client.exec_cmd(cmd=cmd)
                        self.created_config_info[self.array_name][vol_name]["clones"].update(
                            {clone_name: {"connected": "true"}}
                        )
                    self.created_config_info[self.array_name][vol_name]["clones"].update(
                        {clone_name: {"connected": "false"}}
                    )
                    self.clones_to_remove.append(clone_name)
        else:
            self.created_config_info[self.array_name][vol_name].update(
                {"totalAdhocSnapshotsCount": snap_count, "totalClonesCount": clone_count}
            )
            client.close_connection()

    def calculate_date(
        self, years: int = 0, months: int = 0, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0
    ):
        array_date = datetime.datetime.now()
        calculated_date = array_date - relativedelta(
            years=years, months=months, days=days, hours=hours, minutes=minutes, seconds=seconds
        )
        return calculated_date

    def _config_helper(self, count: int = 0, thick_count: int = 0, snap_count: int = 0) -> None:
        """
        _config_helper: method will create volume and generate seperate thread to create snap and clones per volume
        --------------

        Parameters:
        -----------
            count:- Volumes count
            thick_count:- Thick volumes count
            snap_count:- snaps count per volume
        Return:
            :- None
        """
        # Initiating new ssh object to reduce complexity of ssh connections
        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )

        # Generating volume name
        vol_names = self.get_vol_names(count=count)
        thread_list = []
        mounted = False
        snap_create = True
        snap_clone_create_count = 0

        """
        Looping through volume names
            :- if snap-clone-count 2 than creating snaps of volume, to reduce time complexity not going to create snaps and volumes for all volumes
                :- checking thick volume count based on count creating thick volumes with in volumes namens
                :- if index value of volume even than mounting volume, here also no need to mount all volumes
                :- if snap count is 0, adding those volumes to volume collection to create periodic snaps
                    :- else generating thread to create snaps and clones based on logic
        """

        for ind, vol in enumerate(vol_names):
            self.vol_size = random.randint(1, self.vol_size)
            self.size_in_bytes = self.format_vol_size(self.vol_size, "MB", "B", precision=0)
            if snap_clone_create_count == 2:
                snap_create = False
                snap_clone_create_count = 0
            self.created_config_info[self.array_name].update({vol: {}})

            if count == thick_count:
                cmd = f"vol --create {vol} --size {self.vol_size} --thinly_provisioned no --dedupe_enabled no"
                output = client.exec_cmd(cmd=cmd)
                print(f"{self.array_name}-INFO: Creating snaps and clones on {vol}...")
                self.vols_to_remove.append(vol)
                self.created_config_info[self.array_name][vol].update({"totalSpace": self.size_in_bytes})
                if ind % 2 == 0:
                    init_grp_name = self.create_initiator_group(context=self.context)
                    cmd = f"vol --addacl {vol} --initiatorgrp {init_grp_name}"
                    self.client.exec_cmd(cmd=cmd)
                    mounted = True
                    self.created_config_info[self.array_name][vol].update(
                        {"provisionType": "thick", "connected": "true"}
                    )
                else:
                    self.created_config_info[self.array_name][vol].update(
                        {"provisionType": "thick", "connected": "false"}
                    )
                if snap_count == 0:
                    self.created_config_info[self.array_name][vol].update({"snaps": {}})
                    self.created_config_info[self.array_name][vol].update({"clones": {}})
                    self.vol_assoc_to_vol_coll(vol=vol)
                    logger.info("Thick Volume {vol} associating to volume collection to create periodic snap shot")
                else:
                    self.created_config_info[self.array_name][vol].update({"snaps": {}})
                    self.created_config_info[self.array_name][vol].update({"clones": {}})
                    if snap_create:
                        logger.info("Volume {vol} creating with {snap_count} snaps and half of snap count clones")
                        thread = threading.Thread(target=self._snap_clone_create, args=(vol, snap_count, True, mounted))
                        thread_list.append(thread)
                        thread.start()
                    else:
                        snap_create = True
            else:
                cmd = f"vol --create {vol} --size {self.vol_size} --thinly_provisioned yes"
                client.exec_cmd(cmd=cmd)
                self.created_config_info[self.array_name][vol].update({"totalSpace": self.size_in_bytes})
                print(f"{self.array_name}-INFO: Creating snaps and clones on {vol}...")
                if ind % 2 == 0:
                    init_grp_name = self.create_initiator_group(context=self.context)
                    cmd = f"vol --addacl {vol} --initiatorgrp {init_grp_name}"
                    self.client.exec_cmd(cmd=cmd)
                    mounted = True
                    self.created_config_info[self.array_name][vol].update(
                        {"provisionType": "thin", "connected": "true"}
                    )
                else:
                    self.created_config_info[self.array_name][vol].update(
                        {"provisionType": "thin", "connected": "false"}
                    )
                self.vols_to_remove.append(vol)
                count -= 1
                if snap_count == 0:
                    self.created_config_info[self.array_name][vol].update({"snaps": {}})
                    self.created_config_info[self.array_name][vol].update({"clones": {}})
                    self.vol_assoc_to_vol_coll(vol=vol)
                    logger.info("Thin Volume {vol} associating to volume collection to create periodic snap shot")
                else:
                    self.created_config_info[self.array_name][vol].update({"snaps": {}})
                    self.created_config_info[self.array_name][vol].update({"clones": {}})
                    if snap_create:
                        logger.info("Volume {vol} creating with {snap_count} snaps and half of snap count clones")
                        thread = threading.Thread(target=self._snap_clone_create, args=(vol, snap_count, True, mounted))
                        thread_list.append(thread)
                        thread.start()
                    else:
                        snap_create = True

            mounted = False
            snap_clone_create_count += 1
        else:
            client.close_connection()

        # joining all threads
        for thr in thread_list:
            thr.join()

    def generate_config(
        self,
        array_name: str = "",
        data_set: list = [],
        pre_clean_up: bool = False,
    ) -> None:
        """
        generate_config: Method will generate the configuration based on data sets
        ---------------

        Parameters:
        -----------
            array_name:- Array name to create configuration
        Return:
        -------
            :- None
        """

        """
        Looping through the data set
            :- picking the frst data set
                :- generating the date to modify accordingly data set
                :- setting date 
                :- and calling config helper method with volume count and thick volume count and snap count
            
        """
        self.array_name = array_name
        self.volume_name = self.array_name + "-nimble-volume-"
        self.client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )
        if pre_clean_up:
            self.clear_config(array_name=self.array_name)
        else:
            print(f"{self.array_name}-INFO: Pre clean up recieved as a False")
            vol_list = self.get_all_volumes()
            print(f"{self.array_name}-INFO: Volumes presented in Array: {vol_list}")
            vol_numbers = []
            for vol in vol_list:
                print ("VOLUMES:",vol)
                vol_numbers.append(int(re.sub("(.*-volume-)([0-9]+)(-?.*)", r"\2", vol)))
            print ("VOL NUMBERS:", vol_numbers)
            self.vol_index = 1 if not vol_numbers else max(vol_numbers) + 1
            self.scheduler_index += 1
            print ("Coming here")
            col_count = self.get_vol_coll_count()
            print ("Coming here1")
            self.vol_coll_prefix = 1 if not col_count else max(col_count) + 1
            print(f"{self.array_name}-INFO: Array configuration started from volume index: {self.vol_index}")
            self.vol_coll_name = ""
        self.initiator_grp_name = self.array_name + "-pqa-test-initiator-grp"

        if data_set:
            for set in data_set:
                self.volumes_count += set[5]
        else:
            self.volumes_count = (
                random.randint(70, 150)
                if not self.context.array_config.totalvolumescount
                else self.context.array_config.totalvolumescount
            )

        self.thick_volumes_count = (
            round(self.volumes_count / 2)
            if self.context.array_config.thickvolumescount is None
            else self.context.array_config.thickvolumescount
        )

        self.get_vol_size()

        data_set = data_set if data_set else self.set_data_set()

        print("*********************************************")
        print(f"{self.array_name}-INFO: Creating Array configuration...")
        print(f"{self.array_name}- INFO: Array Name: {self.array_name}")
        print(f"Configuration Data Set: {data_set} ")
        print("*********************************************\n")

        for set in data_set:
            print(f"{self.array_name}-INFO: SET IS :", set)
            year = set[0]
            mon = set[1]
            hour = set[2]
            min = set[3]
            sec = set[4]
            vol_count = set[5]
            thick_vol_count = set[6]
            snap_count = set[7]
            logger.info("Picked data set {set}")
            date_modify = self.calculate_date(years=year, months=mon, hours=hour, minutes=min, seconds=sec)
            self.modified_date = self.set_date_time(date_to_set=date_modify)
            self._config_helper(vol_count, thick_vol_count, snap_count)

        # Date setting back to original date and time
        self.set_back_date_time()
        # Adding schedules to all volume collections
        self.add_schedule_to_vol_coll()
        # Sleeping for 65 sec to create periodic snaps
        time.sleep(65)
        # Dis associating volumes from volume collections so that all snaps become unmanaged and can modify retention time
        self.dis_assoc_vol(vol_list=self.vol_coll_vol_list)
        # Modifying retention time
        self.modify_retention_time()

        self.update_vol_clone_info()
        self.array_config_info()
        self.set_back_date_time()

        self.client.close_connection()

    def delete_clones_vols(self, vol_names: list = []) -> None:
        """
        _get_clones: is helper method and it will devide volumes and clones seperately and form a dictionary with vol and clone name and its staus
        ---------

        Parameters:
        -----------
            vol_names :- volume names to identify volumes and clones
                type:- list
                default value:- [] -> means, nothing will happen

        Return:
        -------
            if vol_names:
                type:- dictionary
                values:-
                    clones -> dict {"volname" : "online|offline"}
                    volumes -> dict {"clonename" : "online|offline"}
            else:
                clones -> dict {}
                volumes -> dict {}
        """

        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )
        clones = {}
        vols = {}
        for vol in vol_names:
            if self.array_name in vol:
                cmd = f"vol --delete {vol} --force"
                output = client.exec_cmd(cmd=cmd)
                continue
            else:
                cmd = f"vol --delete {vol} --force"
                output = client.exec_cmd(cmd=cmd)
            
            if "Clone: Yes" in output and "State: online" in output:
                clones[vol] = "online"
            elif "Clone: Yes" in output and "State: offline" in output:
                clones[vol] = "offline"

            if "Clone: No" in output and "State: online" in output:
                vols[vol] = "online"
            elif "Clone: No" in output and "State: offline" in output:
                vols[vol] = "offline"

        client.close_connection()
        return clones, vols

    def _get_initiator_group(self) -> list:
        """
        _get_initiator_group: is a helper method and it will list all initiator groups from array and return list of initiator groups
        ---------

        Parameters:
        -----------
            Not required

        Return:
        -------
            initiators_list:
                type:- list
        """
        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )
        cmd = "initiatorgrp --list"
        std_out = client.exec_cmd(cmd=cmd)
        initiators_list = []
        for line in std_out.split("\n"):
            if re.search("---------------.*|.*Number.*", line):
                continue
            init_search_obj = re.search("(.*)\s+[0-9]+.*", line)
            if init_search_obj:
                initiators_list.append(init_search_obj.group(1).replace(" ", ""))

        client.close_connection()
        return initiators_list

    def dis_assoc_vol(self, vol_list: list = []) -> None:
        """
        dis_assoc_vol: method will perform dis association volumes from volume collection
        -------------

        Parameters:
        -----------
            vol_list : Volume list

        Return:
        -------
            None
        """
        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )
        if not vol_list:
            for vol in self.vol_coll_vol_list:
                cmd = f"vol --dissoc {vol} --force"
                client.exec_cmd(cmd=cmd)
            else:
                client.close_connection()
        else:
            for vol in vol_list:
                cmd = f"vol --dissoc {vol} --force"
                client.exec_cmd(cmd=cmd)
            else:
                client.close_connection()

    def delete_script_created_clones(self) -> None:
        """
        delete_script_created_clones: method will delete all script created clones
        -----------------------------

        Parameters:
        -----------
            None

        Return:
        -------
            None
        """
        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )

        for clone in self.clones_to_remove:
            cmd = f"vol --delete {clone} --force"
            client.exec_cmd(cmd=cmd)
        else:
            client.close_connection()

    def delete_script_created_volumes(self) -> None:
        """
        delete_script_created_volumes: method will delete all script created volumes
        -----------------------------

        Parameters:
        -----------
            None

        Return:
        -------
            None
        """
        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )
        for vol in self.vols_to_remove:
            cmd = f"vol --delete {vol} --force"
            client.exec_cmd(cmd=cmd)
        else:
            client.close_connection()

    def delete_clones(self, clones: dict = {}) -> None:
        """
        delete_clones: method will delete all clones which is in array
        --------------

        Parameters:
        -----------
            clones:- clones dictionary along with clone name and status of clone

        Return:
        -------
            None
        """
        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )
        for clone in clones:
            if clones[clone] == "online":
                cmd = f"vol --offline {clone}"
                self.client.exec_cmd(cmd=cmd)
                cmd = f"vol --delete {clone}"
                self.client.exec_cmd(cmd=cmd)
            else:
                cmd = f"vol --delete {clone}"
                self.client.exec_cmd(cmd=cmd)
        client.close_connection()

    def delete_volumes(self, vols: dict = {}) -> None:
        """
        delete_volumes: method will delete all volumes which is in array
        --------------

        Parameters:
        -----------
            vols:- volumes dictionary along with volume name and status of volume

        Return:
        -------
            None
        """
        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )
        for vol in vols:
            if vols[vol] == "online":
                cmd = f"vol --offline {vol}"
                self.client.exec_cmd(cmd=cmd)
                cmd = f"vol --delete {vol}"
                self.client.exec_cmd(cmd=cmd)
            else:
                cmd = f"vol --delete {vol}"
                self.client.exec_cmd(cmd=cmd)
        client.close_connection()

    def vol_disassoc_del_vol_coll(self, volcoll: list = []) -> None:
        """
        vol_disassoc_del_vol_coll: method will dis associate all volumes and delete volume collections
        -------------------------

        Parameters:
        -----------
            volcoll:- volume collection list

        Return:
        -------
            None
        """
        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )
        for col in volcoll:
            cmd = f"volcoll --info {col}"
            output = client.exec_cmd(cmd=cmd)
            for line in output.split("\n"):
                if "Associated volumes: none" in line:
                    cmd = f"volcoll --delete {col}"
                    output = client.exec_cmd(cmd=cmd)
                    continue
                if "Associated volumes" in line:
                    vols = line.replace("Associated volumes: ", "").split(",")
                    for vol in vols:
                        cmd = f"vol --dissoc {vol}"
                        output = client.exec_cmd(cmd=cmd)
                    else:
                        cmd = f"volcoll --delete {col}"
                        output = client.exec_cmd(cmd=cmd)
        client.close_connection()

    def get_all_volumes(self, clone_delete: bool = False):

        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )

        vol_list = []
        cmd = "vol --list"
        output = client.exec_cmd(cmd=cmd)
        array_vol_list = output.split("\n")
        for line in array_vol_list:
            if re.search("^\s*$|---------------.*|Name.*|MiB.*", line):
                continue
            # pqa-2-sys1-nimble-volume-0      1000 Yes    N/A             0         0     100 default:/
            vol_search_obj = re.search("(.*)\s+[0-9]+\s+[Yes|No].*", line)

            if vol_search_obj:
                vol_clone = vol_search_obj.group(1).replace(" ", "")
                if self.array_name in vol_clone and "snap" in vol_clone:
                    if clone_delete:
                        clone_cmd = f"vol --delete {vol_clone} --force"
                        client.exec_cmd(cmd=clone_cmd)
                else:
                    vol_list.append(vol_clone)
        client.close_connection()
        return vol_list

    def clear_config(self, array_name: str = "", post: bool = False) -> None:
        """
        clear_config: Method will help to clean up array, list the all volumes, clones and initiator groups than will clear from array
        ---------

        Parameters:
        -----------
            :- Not Required

        Return:
            None
        """
        self.array_name = array_name
        client = SshConnection(
            hostname=self.array_info[self.array_name]["arrayip"],
            username=self.array_cred.username,
            password=self.array_cred.password,
        )
        logger.info(f"{self.array_name}-INFO: Clear config triggered on {self.array_name} ...")
        print(f"{self.array_name}-INFO: Clear config triggered on {self.array_name} ...")
        if post:
            print(f"{self.array_name}-INFO: Dis assoctiating config created volumes from volume collection")
            self.dis_assoc_vol()
            print(f"{self.array_name}-INFO: Deleting script created clones")
            self.delete_script_created_clones()
            print(f"{self.array_name}-INFO: Deleting script created volumes")
            self.delete_script_created_volumes()

        cmd = "volcoll --list"
        output = client.exec_cmd(cmd=cmd)
        volcoll = []
        for line in output.split("\n"):
            if re.search("------------.*|Volume Collection.*|Name.*", line):
                continue
            volcoll_search_obj = re.search("(.*)\s+[a-z]+\s+.*", line)
            if volcoll_search_obj:
                volcoll.append(volcoll_search_obj.group(1))
        print(f"{self.array_name}-INFO volume collections clean up started")
        self.vol_disassoc_del_vol_coll(volcoll=volcoll)
        print(f"{self.array_name}-INFO volume collections clean up done")

        print(f"{self.array_name}-INFO Non script created clones and volumes deletion started...")
        vol_list = self.get_all_volumes(clone_delete=True)
        clones, vols = self.delete_clones_vols(vol_names=vol_list)

        self.delete_clones(clones=clones)
        self.delete_volumes(vols=vols)
        print(f"{self.array_name}-INFO Non script created clones and volumes deletion completed...")
        init_list = self._get_initiator_group()
        logger.info(f"\n\t{init_list}")
        print(f"{self.array_name}-INFO: Initiator group list: {init_list} to remove")
        if init_list:
            for init_grp in init_list:
                cmd = f"initiatorgrp --delete {init_grp}"
                client.exec_cmd(cmd=cmd)
                logger.info("Initiator group {init_grp} clean up done successfully...")
                print(f"{self.array_name}-INFO: Initiator group {init_grp} clean up done successfully...")
        else:
            logger.info("No Inititator groups to remove")

        client.close_connection()

    def create_array_config(self, array_name: str = "", data_set: list = [], pre_clean_up: bool = True):
        """
        create_array_config: Method will create array config
        --------------------
        Parameters:
        -----------
            array_name:- Array name to configure
            pre_clean_up:- True/False - based on value will perform pre clean up

        Return:
            Dictionary along with created config
        """
        assert array_name, "Required one array name to trigger configuration"
        self.generate_config(array_name, data_set, pre_clean_up)
        #try:
        #    self.generate_config(array_name, data_set, pre_clean_up)
        #except Exception as error:
        #    if "Available space insufficient" in error.args[0]:
        #        # Error: ERROR: Failed to create volume. Available space insufficient for operation
        #        print(f"Array Configuration failed with error: {error.args}")
        #        print(
        #            "Please resolve the error and trigger config again with out preclean, it wil start from where exited..."
        #        )
        #    return

        print("*********************************************")
        print(f"{self.array_name}-INFO: Array Configuration completed on {self.array_name}")
        print("*********************************************\n")

        return self.created_config_info
