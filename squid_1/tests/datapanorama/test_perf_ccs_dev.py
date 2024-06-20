from locust import HttpUser, between
from tests.datapanorama.task import RestApiResponseTime
from common import helpers


class LoadUser(HttpUser):
    """
    No of simultaneous users from single customer account and multiple users (20) access data panorama API for Bronze dataset and measure response time.

    Note: Bronze DataSet will be created in Array before runnning this Test.
        Bronze Dataset : 1 Customer and should be able to scale to 10 Customer, 5-10 Systems/Array (6k + 9k), 500-1k volumes , 500-1k snapshots,500-1k clones

    Args:
        HttpUser (_type_): 20 Users will be triggering the RestAPI Tasks Concurrently
    """

    wait_time = between(2, 4)
    tasks = [RestApiResponseTime]

    def on_start(self):
        static_token = ""
        self.headers = helpers.gen_token(static_token=static_token)
