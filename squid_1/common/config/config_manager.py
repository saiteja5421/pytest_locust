import logging
import os
import pickle

from configparser import ConfigParser, ExtendedInterpolation
from threading import Lock
from common.enums.provided_users import ProvidedUser
from utils.common_helpers import get_project_root
from utils.ip_utils import find_unused_ip_from_range
import yaml
from yaml.loader import SafeLoader

SERVICE_1_VERSION = "service1"
SERVICE_2_VERSION = "service2"

DEFAULT_SERVICE_VARS = "variables_template"

BASE_VARIABLES = "variables_base.ini"

logger = logging.getLogger()


class Singleton(type):
    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ConfigManager(metaclass=Singleton):

    def __init__(self):
        self.config = ConfigParser(interpolation=ExtendedInterpolation())
        self.config_path = os.environ.get("CONFIG_FILE_PATH")
        with open(f"{self.config_path}") as f:
            self.config = yaml.load(f, Loader=SafeLoader)

    def _deep_copy(self) -> ConfigParser:
        """deep copy config"""
        temp = pickle.dumps(self.config)
        new_config = pickle.loads(temp)
        return new_config

    @classmethod
    def get_config(cls) -> ConfigParser:
        instance = cls()
        config = instance._deep_copy()
        return config

    @classmethod
    def write_and_save_config(cls) -> None:
        instance = cls()
        with open(f"{instance.config_path}", "w") as configfile:
            instance.config.write(configfile)

    @classmethod
    def get_config_path(cls) -> str:
        instance = cls()
        return instance.config_path

    @classmethod
    def get_config_name(cls) -> str:
        instance = cls()
        return instance.config_name

    @classmethod
    def read_config_as_dict(cls) -> dict:
        """Read variables.ini given and return them as dictionary

        Returns:
            dict: variables ini sections will be stored as dictionary.
                  elements under each section will be dictionary key values.

        """

        instance = cls()
        config_as_dict = {}
        # Read a section such as CLUSTER,VDBENCH and etc
        for section in instance.config.sections():
            config_as_dict[section] = {}
            # Each element in section (like atlas-url element in CLUSTER section)
            for element in instance.config.options(section):
                # Some config file elements are separated by '-' ,
                # to convert them to class property we replace it with '_'.
                # For ex: atlantia-url in variables.ini will be atlantia_url in Cluster class(snake_case)
                snake_case_element = element.replace("-", "_")
                config_as_dict[section][snake_case_element] = instance.config.get(section, element)
        return config_as_dict

    @classmethod
    def check_and_update_unused_ip_for_psg(cls, config) -> None:
        """
        Updates unused IP for the user data fields 'name' and 'secondary_psgw_ip'
        """
        for user in ProvidedUser:
            # Todo: User object for S1 & S2 improved.
            if not user.value.startswith("USER"):
                continue
            key = f"TEST-DATA-FOR-{user.value}"
            instance = cls()
            user_data = instance.config[key]
            unused_ip = find_unused_ip_from_range(user_data["network"])
            if not unused_ip:
                raise Exception(f"Failed to find unused IP from '{user_data['network']}'")
            config.set(key, "network", unused_ip)
            config.set(key, "network_ip_range", user_data["network"])
            logger.info(f"Updated {key}.network = {unused_ip}")
            unused_ip = find_unused_ip_from_range(user_data["secondary_psgw_ip"], exclude_ip_list=[unused_ip])
            if not unused_ip:
                raise Exception(f"Failed to find unused IP from '{user_data['secondary_psgw_ip']}'")
            config.set(key, "secondary_psgw_ip", unused_ip)
            logger.info(f"Updated {key}.secondary_psgw_ip = {unused_ip}")
