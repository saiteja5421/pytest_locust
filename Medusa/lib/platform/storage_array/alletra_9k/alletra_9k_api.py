from tests.e2e.data_panorama.panorama_context import Context
from lib.platform.storage_array.ssh_connection import SshConnection

from dateutil.relativedelta import relativedelta
import datetime
import time
import random
import re
import threading
import logging

logger = logging.getLogger()


class AlletraThreePar(object):
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
        self.alletra_9k_client: object = ""
        self.array_info = self.context.array_info
        self.array_name: str = ""
        self.config_dict_arr_name = ""
        self.array_cred = self.context.array_9K_cred
        self.volume_name: str = ""
        self.vol_index: int = 1
        self.vols_to_remove: list = []
        self.vv_set_prefix: int = 1
        self.vv_set_name: str = ""
        self.cpg_index: int = 1
        self.cpg_name: str = ""
        self.cpg: str = ""
        self.host_index: int = 1
        self.host_name: str = ""
        self.modified_date: str = ""
        self.voumes_date_data_set: list = []
        self.volumes_count = 0
        self.vol_size: int = 1
        self.vol_id = 2
        self.size_in_bytes: int = 1
        self.thick_volumes_count = (
            round(self.volumes_count / 2)
            if self.context.array_config.thickvolumescount is None
            else context.array_config.thickvolumescount
        )
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
        """
        check_key_config_dict: Method will check provided key exist in global dict or not,
                                - if not exist key will get added to global dict
        ----------------------

        Parameters:
            key* :- key name to check
                type:- str

        Return:
        -------
            None
        """
        if key not in self.created_config_info:
            self.created_config_info[key] = {}

    def array_config_info(self) -> None:
        """
        array_config_info: method will execute array info command and frame a dictionary each field as a key and represening value like below.
        -------------
        ---------------General----------------
        System Name         :             s012
        System Model        :   HPE_3PAR 7400c
        Serial Number       :          9900012
        System ID           :               12
        Number of Nodes     :                4
        Master Node         :                0
        Nodes Online        :          0,1,2,3
        Nodes in Cluster    :          0,1,2,3
        Cluster LED         :              Off
        Chunklet Size (MiB) :             1024
        Minimum PW length   :                6

        -----System Capacity (MiB)-----
        Total Capacity     :   10027008
        Allocated Capacity :    1038336
        Free Capacity      :    8988672
        Failed Capacity    :          0

        -----Remote_Syslog_Status------
        Active              :         0
        General Server      :   0.0.0.0
        General Connection  :      None
        Security Server     :   0.0.0.0
        Security Connection :      None

        --------System Descriptors--------
        Location    :
        Owner       :
        Contact     :
        Comment     :


        Parameters:
        -----------
            Not required

        Global Variables:
        -----------------
            Not required

        Return:
            :- N/A
        """
        logger.info("Fetched array info and constructed dictionary...")
        cmd = f"showsys -d"
        output = self.alletra_9k_client.exec_cmd(cmd=cmd)
        output = output.replace(" ", "").replace("(", "").replace(")", "")

        for field in output.split("\n"):
            if "---" in field or not field:
                continue
            spli_val = field.split(":")
            if not spli_val[1]:
                self.created_config_info[self.config_dict_arr_name].update({spli_val[0]: None})
            else:
                self.created_config_info[self.config_dict_arr_name].update({spli_val[0]: spli_val[1]})

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
        cmd = f"showspace -ha mag"
        output = self.alletra_9k_client.exec_cmd(cmd=cmd)
        for line in output.split("\n"):
            if "Estimated" in line or "RawFree" in line:
                continue
            size = re.sub("\s+", ":", line).split(":")
            array_free_size_mb = int(size[1])

        if array_free_size_mb < 100000:
            print("**************************************************************")
            print(
                f"{self.array_name}-INFO: Available sapce in array is: {array_free_size_mb}MB  \nCan not proceed with available space to generate configuration"
            )
            print(f"{self.array_name}-INFO: Skinpping configuration...")
            print("***************************************************************\n")

        array_free_size_gb = round(array_free_size_mb / 1024)
        array_free_size_gb = array_free_size_gb - round(array_free_size_gb / 2)

        self.vol_size = round(array_free_size_gb / self.volumes_count)
        logger.info(f"{self.config_dict_arr_name}-INFO: Volume size to create volumes is {self.vol_size} GB")
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
        cmd = f"date -s '{array_set_back_date}'"
        self.alletra_9k_client.exec_cmd(cmd=cmd, retry=True)
        logger.info(f"Setting back actual array date and time {array_set_back_date}")
        print(f"{self.config_dict_arr_name}-INFO: Setting back actual array date and time {array_set_back_date}")

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
        # client = SshConnection(
        #    hostname=self.array_name,
        #    username=self.array_cred.username,
        #    password=self.array_cred.password,
        # )

        replace_array_date = re.sub("(.*)\.[0-9]+", r"\1", str(date_to_set))
        logger.info(f"Modifying Array date to {date_to_set}")
        print(f"{self.config_dict_arr_name}-INFO: Modifying Array date to {date_to_set}")
        # Executing command on array to set date and time
        cmd = f"date -s '{replace_array_date}'"
        self.alletra_9k_client.exec_cmd(cmd=cmd, retry=True)
        return replace_array_date

    def calculate_date(self, years: int = 0, months: int = 0, days: int = 0, hours: int = 0, minutes: int = 0):
        """
        calculate_date: Method will calculate modified date
        --------------

        Parameters:
        -----------
            years :- year to change
            months :- Month number set date
            days :- day to set date
            hours :- hour to set date
            minutes :- minutes to set date
            seconds :- seconds to set date
        Return:
            calculated date :- calculated date and time in str format
        """
        array_date = datetime.datetime.now()
        calculated_date = array_date - relativedelta(
            years=years, months=months, days=days, hours=hours, minutes=minutes
        )
        return calculated_date

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

    def get_vv_sets(self):
        """
        get_vv_sets: Method will get all vvsets
        -----------

        Parameters:
        -----------
            None
        Return:
            vv set list :- vv set list
        """
        vv_set_list = []
        cmd = f"showvvset -csvtable"
        output = self.alletra_9k_client.exec_cmd(cmd=cmd)
        array_vv_set_list = output.split("\n")
        for line in array_vv_set_list:
            if re.search("Name|----.*|total|Rsvd", line):
                continue
            if re.match("[0-9]+", line):
                set = line.split(",")[1]
                vv_set_list.append(set)
        return vv_set_list

    def get_all_volumes(self):

        """
        get_all_volumes: Method will get all volumes
        ---------------

        Parameters:
        -----------
            None
        Return:
            volume list :- volume list
        """

        vol_list = {}
        cmd = "showvv -csvtable -showcols Id,Name"
        output = self.alletra_9k_client.exec_cmd(cmd=cmd)
        array_vol_list = output.split("\n")
        for line in array_vol_list:
            if re.search("Name|srdata|admin|----.*|total|Rsvd|snap|vvcopy|vvcp", line):
                continue
            if self.config_dict_arr_name in line:
                line = re.sub("\s+", "", line)
                vol_id = line.split(",")
                if "vvcp" in vol_id[1] or "vvcopy" in vol_id[1]:
                    continue
                vol_list[int(vol_id[0])] = vol_id[1]
        return vol_list

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

    def get_all_cpgs(self):
        """
        get_all_cpgs: Method will get all cpgs
        ------------

        Parameters:
        -----------
            None
        Return:
            cpgs list :- cpgs list
        """
        cpg_list = []
        cmd = "showcpg -csvtable -showcols Name"
        output = self.alletra_9k_client.exec_cmd(cmd=cmd)
        array_cpg_list = output.split("\n")
        for line in array_cpg_list:
            if re.search("Name|admin|----.*|total|Rsvd", line):
                continue

            if self.config_dict_arr_name in line:
                cpg_list.append(line)
        return cpg_list

    def create_cpg(self):
        """
        create_cpg: method will use to create cpg based on count
        ----------

        Parameters:
        -----------
            count:- number of cpgs
        Return:
            cpg list :- created cpgs list
        """
        cpg_list = []
        cmd = "setsys AllowR5OnNLDrives yes"
        self.alletra_9k_client.exec_cmd(cmd=cmd)
        raid_type = "r6"
        self.cpg_name = self.config_dict_arr_name + "-medusa-" + raid_type + "-cpg-" + str(self.cpg_index)
        cmd = f"createcpg -t {raid_type} -ha mag {self.cpg_name}"
        self.alletra_9k_client.exec_cmd(cmd=cmd)
        self.cpg_index += 1
        return self.cpg_name

    def get_host(self):
        """
        get_host: method will use to get hosts
        --------

        Parameters:
        -----------
            None
        Return:
            host list :- hosts list
        """
        cmd = "showhost -csvtable"
        output = self.alletra_9k_client.exec_cmd(cmd=cmd)
        host_list = []
        array_host_list = output.split("\n")
        for line in array_host_list:
            if re.search("Name|admin|----.*|total|Rsvd", line):
                continue

            if re.match("[0-9]+", line):
                host = line.split(",")[1]
                host_list.append(host)
        return host_list

    def create_host(self):
        """
        create_host: method will use to create host
        ------------

        Parameters:
        -----------
            None
        Return:
            host :- created host
        """
        host_list = self.get_host()
        hostname = self.config_dict_arr_name + "-medusa-host-1"
        host_wwns = set(self.array_info[self.config_dict_arr_name]["hostwwns"])
        join_wwn = ""
        for wwn in host_wwns:
            join_wwn = join_wwn + wwn + " "

        for host in host_list:
            cmd = f"removehost {host}"
            self.alletra_9k_client.exec_cmd(cmd=cmd)
        cmd = f"createhost {hostname} {join_wwn}"
        output = self.alletra_9k_client.exec_cmd(cmd=cmd)
        return hostname

    def get_vv_source_copy(self, client: object = "", vol: str = ""):
        """
        get_vv_source_copy: method will use to get vv copy source
        -------------------

        Parameters:
        -----------
            client :- ssh client object
            vol :- volume name to get source of volume
        Return:
            source vv list :- source vv list
        """
        cmd = f"showvv -p -type pcopy -showcols CopyOf {vol}"
        output = client.exec_cmd(cmd=cmd)
        copies = output.split("\n")
        copy_list = []
        while not copy_list:
            for copy in copies:
                if "vvcp" in copy:
                    copy_list.append(copy)
            cmd = f"showvv -p -type pcopy -showcols CopyOf {vol}"
            output = client.exec_cmd(cmd=cmd)
            copies = output.split("\n")
        return copy_list

    def get_cpg_vv_count(self, cpg_name: str = ""):
        cmd = f"showcpg -csvtable -showcols Name,VVs {cpg_name}"
        output = self.alletra_9k_client.exec_cmd(cmd=cmd)
        cpgs_count = output.split("\n")
        cpg_vol_count = ""
        for c_count in cpgs_count:
            if self.config_dict_arr_name in c_count:
                s_val = c_count.split(",")
                cpg_vol_count = s_val[1]
        return cpg_vol_count

    def create_vv_copy(self, vol: str = "", count: int = 0, copy_name: str = ""):
        """
        create_vv_copy: method will use to create vv copies
        ---------------

        Parameters:
        -----------
            vol :- volume name to create vv copy
            count :- number copies
            copy_name :- vv copy name, if vv copy name empty will create default name
        Return:
            None
        """
        count = random.randint(5, 10) if not count else count
        for ind in range(1, count):
            vv_copy_name = copy_name + str(ind) if copy_name else vol + "-vvcopy-" + str(ind)
            self.created_config_info[self.config_dict_arr_name][vol]["copies"].update({vv_copy_name: {}})

            cmd = f"createvv -tpvv -snp_cpg {self.cpg} {self.cpg} {vv_copy_name} {self.vol_size}g"
            output = self.alletra_9k_client.exec_cmd(cmd=cmd, err_exception=True)
            if "space" in output:
                print(f"{self.config_dict_arr_name}-INFO: Cpg has reached maximum SA or SD space, creating new cpg")
                self.cpg = self.create_cpg()
                cmd = f"createvv -tpvv -snp_cpg {self.cpg} {self.cpg} {vol} {self.vol_size}g"
                output = self.alletra_9k_client.exec_cmd(cmd=cmd)
            cmd = f"createvvcopy -p {vol} -s {vv_copy_name}"
            output = self.alletra_9k_client.exec_cmd(cmd=cmd)
            copies = self.get_vv_source_copy(client=self.alletra_9k_client, vol=vv_copy_name)
            self.created_config_info[self.config_dict_arr_name][vol]["copies"][vv_copy_name].update(
                {
                    "cloneName": vol,
                    "provisionType": "thin",
                    "utilizedSpace": None,
                    "totalSpace": self.size_in_bytes,
                    "creationTime": self.modified_date,
                    "connected": "false",
                    "ioActivity": None,
                }
            )
        logger.info(f"{self.config_dict_arr_name}-INFO: vv copies created successfully done on volume {vol}")
        self.created_config_info[self.config_dict_arr_name][vol].update({"totalClonesCount": count})

    def _snap_vv_copy_create(
        self,
        vol_name: str = "",
        snap_count: int = 0,
    ):
        """
        _snap_vv_copy_create: method will create snapshot and its copy
        -------------------

        Parameters:
        -----------
            vol_name:- Volume name to create snap and its clone
            snap_count:- snapshot count per volume
        Return:
            :- None
        """
        """
        Looping through snap count
            creating snap shot and than create some random vv copies
            
        """

        for ind, count in enumerate(range(snap_count)):
            snap_name = vol_name + "-snap-" + str(count)
            snap_type = random.choices(["-ro", " "])[0]
            exp = random.choices(["d", "h", "m"])[0]
            exp_num = random.randint(3, 8)
            cmd = f"createsv {snap_type} -exp {exp_num}{exp} {snap_name} {vol_name}"
            output = self.alletra_9k_client.exec_cmd(cmd=cmd, err_exception=True)

            if "Unknown" in output or "space" in output:
                print(f"{self.config_dict_arr_name}-INFO: Cpg has reached maximum SA or SD space, creating new cpg")
                self.cpg = self.create_cpg()
                cmd = f"createsv {snap_type} -exp {exp_num}{exp} {snap_name} {vol_name}"
                output = self.alletra_9k_client.exec_cmd(cmd=cmd)
            self.created_config_info[self.config_dict_arr_name][vol_name]["snaps"].update(
                {
                    snap_name: {
                        "snap_type": snap_type,
                        "retentionPeriodRange": exp + str(exp_num),
                        "creation_date": self.modified_date,
                    }
                }
            )
            copy_name = snap_name + "-vvcp-"
            copies_count = random.randint(0, 5)
            self.create_vv_copy(vol=vol_name, count=copies_count, copy_name=copy_name)
            logger.info(
                f"{self.config_dict_arr_name}-INFO: Snaps and vv copies created successfully done on volume {vol_name}"
            )
        self.created_config_info[self.config_dict_arr_name][vol_name].update({"totalAdhocSnapshotsCount": snap_count})

    def _config_helper(
        self,
        count: int = 0,
        reduce_vol_count: int = 0,
        snap_count: int = 0,
    ) -> None:
        """
        _config_helper: method will create volume and generate seperate thread to create snap and clones per volume
        --------------

        Parameters:
        -----------
            count:- Volumes count
            reduce_vol_count:- reduce volumes count
            snap_count:- snaps count per volume
        Return:
            :- None
        """
        # Generating volume name
        thread_list = []
        snap_create = True
        snap_create_count = 0
        """
        Looping through volume names
            :- if snap-create-count 2 than creating snaps of volume, to reduce time complexity not going to create snaps and volumes for all volumes
                :- checking thick volume count based on count creating thick volumes with in volumes namens
                :- if index value of volume even than mounting volume
                :- if snap count is 0, adding those volumes to create vv copies
                    :- else generating thread to create snaps and copies based on logic
        """

        vol_names = self.get_vol_names(count=count)
        for ind, vol in enumerate(vol_names):
            if snap_create_count == 2:
                snap_create = False
                snap_create_count = 0
            self.created_config_info[self.config_dict_arr_name].update({vol: {}})
            self.created_config_info[self.config_dict_arr_name][vol].update({"snaps": {}})
            self.created_config_info[self.config_dict_arr_name][vol].update({"copies": {}})
            # self.vol_size = random.randint(10, self.vol_size)
            if count == reduce_vol_count:
                cmd = f"createvv -tpvv -i {self.vol_id} -snp_cpg {self.cpg} {self.cpg} {vol} {self.vol_size}g"
                output = self.alletra_9k_client.exec_cmd(cmd=cmd, err_exception=True)
                self.vol_id += 1
                if "space" in output:
                    print(f"{self.config_dict_arr_name}-INFO: Cpg has reached maximum SA or SD space, creating new cpg")
                    self.cpg = self.create_cpg()
                    cmd = f"createvv -tpvv -i {self.vol_id} -snp_cpg {self.cpg} {self.cpg} {vol} {self.vol_size}g"
                    output = self.alletra_9k_client.exec_cmd(cmd=cmd)
                    self.vol_id += 1
                print(f"{self.config_dict_arr_name}-INFO: Creating snaps and vvcopies on {vol}...")
                self.created_config_info[self.config_dict_arr_name][vol].update(
                    {
                        "totalSpace": self.size_in_bytes,
                        "volumeName": vol,
                        "provisionType": "reduce",
                        "utilizedSpace": None,
                        "creationTime": self.modified_date,
                        "volumeCreationAge": None,
                        "ioActivity": None,
                        "volumeId" : self.vol_id,
                        "array": self.config_dict_arr_name,
                        "activityTrend": [{"timeStamp": None, "ioActivity": None}],
                    }
                )
                if ind % 2 == 0:
                    cmd = f"createvlun {vol} auto {self.host_name}"
                    self.alletra_9k_client.exec_cmd(cmd=cmd)
                    self.created_config_info[self.config_dict_arr_name][vol].update({"connected": "true"})
                else:
                    self.created_config_info[self.config_dict_arr_name][vol].update({"connected": "false"})
                if snap_count == 0:
                    logger.info(
                        f"{self.config_dict_arr_name}-INFO: creating some random online off line vv copies for vv {vol}"
                    )

                    print(
                        f"{self.config_dict_arr_name}-INFO: creating some random online off line vv copies for vv {vol}"
                    )
                    self.created_config_info[self.config_dict_arr_name][vol].update({"totalAdhocSnapshotsCount": 0})
                    thread = threading.Thread(target=self.create_vv_copy, args=(vol,))
                    thread_list.append(thread)
                    thread.start()
                    # self.create_vv_copy(vol=vol)
                else:
                    if snap_create:
                        logger.info(
                            f"{self.config_dict_arr_name}-INFO:creating {snap_count} snapshots and some random online off line vv copies for vv {vol}"
                        )
                        print(
                            f"{self.config_dict_arr_name}-INFO:creating {snap_count} snapshots and some random online off line vv copies for vv {vol}"
                        )
                        thread = threading.Thread(target=self._snap_vv_copy_create, args=(vol, snap_count))
                        thread_list.append(thread)
                        thread.start()
                        # self._snap_vv_copy_create(vol, snap_count)
                    else:
                        snap_create = True
            else:
                cmd = f"createvv -tpvv -i {self.vol_id} -snp_cpg {self.cpg} {self.cpg} {vol} {self.vol_size}g"
                output = self.alletra_9k_client.exec_cmd(cmd=cmd, err_exception=True)
                self.vol_id += 1
                if "space" in output:
                    print(f"{self.config_dict_arr_name}-INFO: Cpg has reached maximum SA or SD space, creating new cpg")
                    self.cpg = self.create_cpg()
                    cmd = f"createvv -tpvv -i {self.vol_id} -snp_cpg {self.cpg} {self.cpg} {vol} {self.vol_size}g"
                    self.vol_id += 1
                    output = self.alletra_9k_client.exec_cmd(cmd=cmd)

                count -= 1
                print(f"{self.config_dict_arr_name}-INFO: Creating snaps and vvcopies on {vol}...")
                self.created_config_info[self.config_dict_arr_name][vol].update(
                    {
                        "totalSpace": self.size_in_bytes,
                        "volumeName": vol,
                        "provisionType": "thin",
                        "utilizedSpace": None,
                        "creationTime": self.modified_date,
                        "volumeCreationAge": None,
                        "ioActivity": None,
                        "array": self.config_dict_arr_name,
                        "volumeId" : self.vol_id,
                        "activityTrend": [{"timeStamp": None, "ioActivity": None}],
                    }
                )
                if ind % 2 == 0:
                    cmd = f"createvlun {vol} auto {self.host_name}"
                    self.alletra_9k_client.exec_cmd(cmd=cmd)
                    self.created_config_info[self.config_dict_arr_name][vol].update({"connected": "true"})
                else:
                    self.created_config_info[self.config_dict_arr_name][vol].update({"connected": "false"})

                if snap_count == 0:
                    logger.info(f"creating some random online off line vv copies for vv {vol}")
                    print(
                        f"{self.config_dict_arr_name}-INFO: creating some random online off line vv copies for vv {vol}"
                    )
                    self.created_config_info[self.config_dict_arr_name][vol].update({"totalAdhocSnapshotsCount": 0})
                    thread = threading.Thread(target=self.create_vv_copy, args=(vol,))
                    thread_list.append(thread)
                    thread.start()
                    # self.create_vv_copy(vol=vol)
                else:
                    if snap_create:
                        logger.info("Volume {vol} creating with {snap_count} snaps and half of snap count clones")
                        print(f"Volume {vol} creating with {snap_count} snaps and half of snap count clones")
                        thread = threading.Thread(target=self._snap_vv_copy_create, args=(vol, snap_count))
                        thread_list.append(thread)
                        thread.start()
                        # self._snap_vv_copy_create(vol, snap_count)
                    else:
                        snap_create = True
            snap_create_count += 1
        for th in thread_list:
            th.join()

    def generate_config(self, array_name: str = "", data_set: list = [], pre_clean_up: bool = False) -> None:
        """
        generate_config: Method will generate the configuration based on data sets
        ---------------

        Parameters:
        -----------
            array_name:- Array name to create configuration
            data_set:- data sets to create volumes and snaps based on date and time
            pre_clean_up:- if pre clean up true cleaning up array else not cleaning
        Return:
        -------
            :- None
        """

        """
        Looping through the data set
            :- picking the frst data set
                :- generating the date to modify accordingly data set
                :- setting date 
                :- and calling config helper method with volume count and reduce volume count and snap count
            
        """
        self.array_name = array_name
        self.alletra_9k_client = SshConnection(
            hostname=self.array_name,
            username=self.array_cred.username,
            password=self.array_cred.password,
        )

        self.config_dict_arr_name = re.search("([a-z0-9]+)\.cxo.*", self.array_name)
        if self.config_dict_arr_name:
            self.config_dict_arr_name = self.config_dict_arr_name.group(1)

        self.check_key_config_dict(key=self.config_dict_arr_name)
        self.created_config_info[self.config_dict_arr_name].update({"device_type": "9k"})

        if pre_clean_up == True:
            self.clear_config(array_name=self.array_name)
            print(f"{self.config_dict_arr_name}-INFO: Clear config done")
        else:
            print(f"{self.config_dict_arr_name}-INFO: Pre clean up recieved as a False")
            vol_list = self.get_all_volumes()
            print(f"{self.config_dict_arr_name}-INFO: Volumes presented in Array: {vol_list}")
            vol_numbers = []
            vol_ids = []
            for vol in vol_list:
                if self.config_dict_arr_name in vol_list[vol]:
                    vol_numbers.append(int(re.sub("(.*-vv-)([0-9]+)(-?.*)", r"\2", vol_list[vol])))
                    vol_ids.append(vol)
            self.vol_index = 1 if not vol_numbers else int(max(vol_numbers)) + 1
            self.vol_id = 2 if not vol_ids else int(max(vol_ids)) + 1
            logger.info("VOL INDEX: ", self.vol_index)
            vv_set_list = self.get_vv_sets()
            vv_set_num = []
            for vol in vv_set_list:
                if self.config_dict_arr_name in vol:
                    vv_set_num.append(int(re.sub("(.*-vvset-)([0-9]+)(-?.*)", r"\2", vol)))
            self.vv_set_prefix = 1 if not vv_set_num else max(vv_set_num) + 1
            logger.info(
                f"{self.config_dict_arr_name}-INFO: Array configuration started from volume index: {self.vol_index}"
            )

            cpg_list = self.get_all_cpgs()
            cpg_set_num = []
            for cpg in cpg_list:
                if self.config_dict_arr_name in cpg:
                    cpg_set_num.append(int(re.sub("(.*-cpg-)([0-9]+)(-?.*)", r"\2", cpg)))
            self.cpg_index = 1 if not cpg_set_num else max(cpg_set_num) + 1

        self.host_name = self.create_host()
        self.volume_name = self.config_dict_arr_name + "-3par-vv-"

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
        self.size_in_bytes = self.format_vol_size(self.vol_size, "GB", "B", precision=0)

        self.cpg = self.create_cpg()

        print("*********************************************")
        print(f"{self.config_dict_arr_name}-INFO: Creating Array configuration...")
        print(f"{self.config_dict_arr_name}- INFO: Array Name: {self.config_dict_arr_name}")
        print(f"{self.config_dict_arr_name}-INFO: Configuration Data Set: {data_set} ")
        print("*********************************************\n")
        for set in data_set:
            print(f"{self.config_dict_arr_name}-INFO: Current Data Set:", set)
            year = set[0]
            mon = set[1]
            day = set[2]
            hour = set[3]
            min = set[4]
            vol_count = set[5]
            reduce_vol_count = set[6]
            snap_count = set[7]
            logger.info(f"{self.config_dict_arr_name}-INFO: Picked data set {set}")
            date_modify = self.calculate_date(years=year, months=mon, days=day, hours=hour, minutes=min)
            self.modified_date = self.set_date_time(date_to_set=date_modify)
            self._config_helper(vol_count, reduce_vol_count, snap_count)

        self.array_config_info()
        self.set_back_date_time()
        self.alletra_9k_client.close_connection()

    def clear_config(self, array_name: str = "", post: bool = False) -> None:
        """
        clear_config: Method will help to clean up array, list the all volumes, vv copies and  Hhosts than will clear from array
        ---------

        Parameters:
        -----------
            :- Not Required

        Return:
            None
        """
        if post:
            self.alletra_9k_client = SshConnection(
                hostname=self.array_name,
                username=self.array_cred.username,
                password=self.array_cred.password,
            )
        logger.info(f"Clear config triggered on {self.config_dict_arr_name} ...")
        print(f"{self.config_dict_arr_name}-INFO: Clear config triggered on {self.config_dict_arr_name} ...")
        cmd = f"removevlun -f -pat \* \* \*"
        self.alletra_9k_client.exec_cmd(cmd)
        while 1:
            cmd = f"removevv -f -cascade -pat \*"
            self.alletra_9k_client.exec_cmd(cmd)
            vv_list = self.get_all_volumes()
            if not len(vv_list):
                break
            time.sleep(5)
        self.alletra_9k_client.exec_cmd(cmd)
        cmd = f"removecpg -f -pat \*"
        self.alletra_9k_client.exec_cmd(cmd)
        vvsets = self.get_vv_sets()
        for vvset in vvsets:
            cmd = f"removevvset -f {vvset}"
            self.alletra_9k_client.exec_cmd(cmd)

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
        try:
            self.generate_config(array_name, data_set, pre_clean_up)
        except TypeError:
            pass
        print("*********************************************")
        print(f"# INFO: Array Configuration completed on {self.array_name}")
        print("*********************************************\n")

        # print(self.created_config_info)
        return self.created_config_info
