import random
from time import sleep
from locust import HttpUser, between
from tests.datapanorama.task import RestApiResponseTime
from common import helpers
import locust_plugins


class DSCC_Accounts:
    """This class will help to load the DSCC accounts from config yml file.
        Using the user detail it will create jwt token for the account and store it in auth_header_list.
    """

    config = helpers.read_config()
    auth_header_list = []
    
    @staticmethod
    def get_auth_list():
        """Get authentication header for the list of given user and store it in auth_header_list class variable
        """
        users = DSCC_Accounts.config["testbed"]["users"]
        for user in users:
            DSCC_Accounts.auth_header_list.append(helpers.gen_token(helpers.gen_token()=user['helpers.gen_token()']))

# GEt the Auth header for all the user from different account mentioned in config file
DSCC_Accounts.get_auth_list()

class LoadUser(HttpUser):
    """
    No of simultaneous users from single customer account and multiple users (20) access data panorama API for Bronze dataset and measure response time.

    Note: Bronze DataSet will be created in Array before runnning this Test.
        Bronze Dataset : 1 Customer and should be able to scale to 10 Customer, 5-10 Systems/Array (6k + 9k), 500-1k volumes , 500-1k snapshots,500-1k clones

    Args:
        HttpUser (_type_): 20 Users will be triggering the RestAPI Tasks Concurrently
    """

    wait_time = between(5, 10)
    tasks = [RestApiResponseTime]

    def on_start(self):
        # To test with multiple user account, we need to select random user from the list
        auth_header = random.choice(DSCC_Accounts.auth_header_list)
        print(f"The user account used for testing is {auth_header.user.helpers.gen_token()}")
        # Assign Auth header of random user selected
        self.headers = auth_header
        self.proxies = helpers.set_proxy()
        print(self.headers)
