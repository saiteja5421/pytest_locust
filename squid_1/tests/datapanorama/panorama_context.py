from typing import Union
import yaml
import logging

from dataclasses import dataclass
from common.users.user import ApiHeader

from common.enums.provided_users import ProvidedUser
from tests.datapanorama import panorama_context_models
from common.users import user_model

from utils.common_helpers import get_project_root

logger = logging.getLogger()


@dataclass
class Context:
    """
    A class to represent a Context data class.

    Usage:
    ------
        context = Context()
        context.varname

    Methods:
    --------
        set_cluster_section()
            :- based on cluster parameter value load data from yml file and construct cluster object using model file
        set_array_info_section()
            :- based on array_info parameter value load data from yml file and construct cluster object using model file
        set_array_cred_section()
            :- based on array_cred parameter value load data from yml file and construct cluster object using model file
        set_array_config_section()
            :- based on array_config parameter value load data from yml file and construct cluster object using model file
        set_provided_user_section()
            :- based on test_provided_user parameter value load data from yml file and construct cluster object using model file
        set_proxy_section()
            :- based on proxy parameter value load data from yml file and construct cluster object using model file

    Return:
    -------
        :- return Context object
    """

    def __init__(
        self,
        cluster=True,
        array_info=True,
        array_cred=True,
        array_config=True,
        test_provided_user=ProvidedUser.user_one,
        proxy=True,
        cxo_29_array=False,
        config_file="configs/data_panorama/panorama_variables.yml",
    ):
        """
        __init__: Constructs all the necessary attributes for the Context object.
        ---------

        Parameters:
        -----------
            cluster :- required cluster object or not while constructing object for Context
                type:- bool
                default Value:- True, means by default cluster object will get create in context
            array_info :- required array info object or not while constructing object for Context
                type:- bool
                default Value:- True, means by default array_info object will get create in context
            array_cred :- required array cred object or not while constructing object for Context
                type:- bool
                default Value:- True, means by default array_cred object will get create in context
            array_config :- required array config object or not while constructing object for Context
                type:- bool
                default Value:- True, means by default array_config object will get create in context
            array_config :- required to get user name object or not while constructing object for Context
                type:- str
                default Value:- ProvidedUser.user_one, means by default will pick user_one from yml file and
                                    -object will get create in context
            data_panorama_api :- required data panaroma API object or not while constructing object for Context
                type:- bool
                default Value:- True, means by default data_panorama_api object will get create in context
            proxy :- required proxy object or not while constructing object for Context
                type:- bool
                default Value:- True, means by default proxy object will get create in context


        Global Variables:
        -----------------
            self.config_dict:
                :- load yml file and construct objects for all fields which specified inside yml file
            self.snap_tool_path:
                :- snaptest IO tool path to copy in to remote host for running IO
            self.alletra_6k_created_config_info:
                :- after running config script framing dictionary for alletra 6k array with all configuration info
            self.alletra_9k_created_config_info:
                :- after running config script framing dictionary for alletra 9k array with all configuration info
            self.cluster:
                :- contains yml file cluster object
            self.array_info:
                :- contains yml file array info object
            self.array_config:
                :- contains yml file array config object
            self.array_cred:
                :- contains yml file array cred object
            self.user_provided:
                :- contains user object
            self.panorama_api:
                :- contains yml file data panaroma API object
            self.proxy:
                :- contains yml file proxy object

        """
        path_configs_service3 = get_project_root() / f"{config_file}"
        try:
            with open(path_configs_service3) as YFH:
                self.config_dict = yaml.load(YFH, Loader=yaml.FullLoader)
            logger.debug(f"Running tests against '{path_configs_service3}' config file")
        except:
            logger.info(f"Could not able to load '{path_configs_service3}' config file")
        self.snap_tool_path = get_project_root() / "lib/platform/resources/snaptest/snaptest"
        self.alletra_6k_created_config_info: dict = {}
        self.alletra_9k_created_config_info: dict = {}
        self.cluster: panorama_context_models.Cluster = self.set_cluster_section(cluster)
        self.user_provided: user_model.APIClientCredential = self.set_provided_user_section(test_provided_user)
        # This will have authentication header for user_provided
        if self.cluster.static_token:
            self.api_header = ApiHeader(
                api_credential=self.user_provided,
                oauth2_server=self.cluster.oauth2_server,
                static_token=self.cluster.static_token,
            )
        else:
            self.api_header = ApiHeader(api_credential=self.user_provided, oauth2_server=self.cluster.oauth2_server)
        self.array_info = self.set_array_info_section(array_info)
        self.array_config: panorama_context_models.ArrayConfig = self.set_array_config_section(array_config)
        self.array_6K_cred: panorama_context_models.ArrayCredentials = self.set_6K_array_cred_section(array_cred)
        self.array_9K_cred: panorama_context_models.ArrayCredentials = self.set_9K_array_cred_section(array_cred)
        self.proxy: panorama_context_models.Proxy = self.set_proxy_section(proxy)
        self.cxo_array: panorama_context_models.CXO_29_Array = self.set_cxo_29_array_section
        self.mock_collection_data = ""
        self.mock_vol_lastcoll = ""
        self.mock_snap_lastcoll = ""
        self.mock_clone_lastcoll = ""
        self.mock_vol_allcoll = ""
        self.mock_vol_usage_lastcoll = ""
        self.mock_clone_allcoll = ""
        self.mock_vol_perf_allcoll = ""
        self.mock_app_lastcoll = ""
        self.mock_snap_app_data = ""
        self.mock_clone_app_data = ""
        self.mock_sys_lastcoll = ""
        self.mock_total_snaps = ""
        self.mock_total_clones = ""
        self.mock_app_lastcoll_with_sys = ""
        self.cost_dict = ""
        self.mock_snap_all = ""
        self.mock_snap_usage = ""
        self.golden_db_path = f"tests/e2e/data_panorama/mock_data_generate/golden_db/ccs_pqa/mock_aggregated_db.sqlite"
        self.input_golden_db_path = f"tests/e2e/data_panorama/mock_data_generate/golden_db/ccs_pqa/mock_90_days.sqlite"
        self.real_data_db_path = f"lib/dscc/data_panorama/data_collector/out/aggregateddb.sqlite"

    def set_cluster_section(self, cluster):
        """
        set_cluster_section: Method will form a data object using "panaroma_context_models.py->Cluster"" model by reading self.config_dict["CLUSTER"]
        ---------

        Parameters:
            cluster* :- cluster
                type :- bool
        Return:
        -------
            if cluster True:
                Cluster data object
            else:
                None
        """
        if cluster:
            return panorama_context_models.Cluster(**self.config_dict["CLUSTER"])
        else:
            return None

    def set_array_info_section(self, array_info):
        """
        set_array_info_section: Method will return linked list of self.config_dict["ARRAY-INFO"]
        ---------

        Parameters:
            array_info* :- array_nfo
                type :- bool
        Return:
        -------
            if cluster True:
                array info dictionary
            else:
                None
        """
        if array_info:
            return self.config_dict["ARRAY-INFO"]
        else:
            return None

    def set_6K_array_cred_section(self, array_cred):
        """
        set_array_cred_section: Method will form a data object using "panaroma_context_models.py->ArrayConfig"" model by reading self.config_dict["ARRAY-CREDENTIALS"]
        ---------

        Parameters:
            array_cred* :- array_cred
                type :- bool
        Return:
        -------
            if array_cred True:
                array_cred data object
            else:
                None
        """
        if array_cred:
            return panorama_context_models.ArrayCredentials(**self.config_dict["6K-ARRAY-CREDENTIALS"])
        else:
            return None

    def set_9K_array_cred_section(self, array_cred):
        """
        set_array_cred_section: Method will form a data object using "panaroma_context_models.py->ArrayConfig"" model by reading self.config_dict["ARRAY-CREDENTIALS"]
        ---------

        Parameters:
            array_cred* :- array_cred
                type :- bool
        Return:
        -------
            if array_cred True:
                array_cred data object
            else:
                None
        """
        if array_cred:
            return panorama_context_models.ArrayCredentials(**self.config_dict["9K-ARRAY-CREDENTIALS"])
        else:
            return None

    def set_array_config_section(self, array_config):
        """
        set_array_config_section: Method will form a data object using "panaroma_context_models.py->ArrayConfig"" model by reading self.config_dict["ARRAY-CONFIG"]
        ---------

        Parameters:
            array_config* :- array_config
                type :- bool
        Return:
        -------
            if array_config True:
                array_config data object
            else:
                None
        """
        if array_config:
            return panorama_context_models.ArrayConfig(**self.config_dict["ARRAY-CONFIG"])
        else:
            return None

    def set_provided_user_section(self, test_provided_user):
        """
        set_provided_user_section: Method will form a data object using "panaroma_context_models.py->UserProvided"" model by reading self.config_dict[test_provided_user.value]
        ---------

        Parameters:
            test_provided_user* :- test_provided_user
                type :- bool
        Return:
        -------
            test_provided_user data object
        """
        return panorama_context_models.UserProvided(**self.config_dict[test_provided_user.value])

    def set_panorama_api_section(self, data_panorama_api):
        """
        set_panorama_api_section: Method will form a data object using "panaroma_context_models.py->PanoramaAPI"" model by reading self.config_dict["DATAPANORAMA-API"]
        ---------

        Parameters:
            data_panorama_api* :- data_panorama_api
                type :- bool
        Return:
        -------
            if data_panorama_api True:
                data_panorama_api data object
            else:
                None
        """
        if data_panorama_api:
            return panorama_context_models.PanoramaAPI(**self.config_dict["DATAPANORAMA-API"])
        else:
            return None

    def set_proxy_section(self, proxy):
        """
        set_proxy_section: Method will form a data object using "panaroma_context_models.py->PanoramaAPI"" model by reading self.config_dict["PROXY"]
        ---------

        Parameters:
            proxy* :- proxy
                type :- bool
        Return:
        -------
            if proxy True:
                proxy data object
            else:
                None
        """
        if proxy:
            return panorama_context_models.Proxy(**self.config_dict["PROXY"])
        else:
            return None

    def set_cxo_29_array_section(self, cxo_29_array: bool) -> Union[panorama_context_models.CXO_29_Array, None]:
        """The method will return an object of CXO_29_Array if cxo_29_array is 'True' else None

        Args:
            cxo_29_array (bool): True or False

        Returns:
            Union[panorama_context_models.CXO_29_Array, None]: Returns CXO_29_Array or None
        """
        if cxo_29_array:
            return panorama_context_models.CXO_29_Array(**self.config_dict["CX0_29_ARRAY"])
        else:
            return None
