# from concurrent.futures.process import _threads_wakeups
import sys

from locust import events,HttpUser, SequentialTaskSet, between, task

from examples.test_project.CommonLib.UserLoader import UserLoader
from examples.test_project.CommonLib.UtilHelper import UtilHelper

@events.test_start.add_listener
def on_test_start(**kwargs):
    UserLoader.load_users()

class CatalystGatewayTasks(SequentialTaskSet):

    def on_start(self):
        header = self.user.get_header()
        print(f"{header}")
        self.client.headers.update(header)
        # TODO: Check whether the token is valid or about to be expired. 
        # If about to be expired then create new token

    @task
    def get_catalyst_gateway(self):
        print("Get catalyst gateway")
        proxies = {
                    'http': 'http://web-proxy.corp.hpecorp.net:8080',
                    'https': 'http://web-proxy.corp.hpecorp.net:8080',
                }
        # print(f"Locust host {self.locust.host}")
        with self.client.get('/api/v1/catalyst-gateways',proxies=proxies, catch_response=True) as response:
            print(f"response status code is {response.status_code}")
            print(f"response is {response.text}")
            # if (response.text['items']):
                
            print("Wait")
            this_function_name = sys._getframe(  ).f_code.co_name
            print(this_function_name)
            if(response.status_code == 200):
                response.success()
            else:
                response.failure(f"Unable to get response for get_catalyst_gateway")
        print("get catalsyst")
        
    @task
    def on_completion(self):
        self.interrupt()

class TestUser(HttpUser):
    '''
        Create multiple user from data/test_data.csv
        Login with that user and execute the tasks
    '''
    wait_time = between(3,5)
    tasks =[CatalystGatewayTasks]
    
    def __init__(self, parent):
        super(TestUser,self).__init__(parent)
        self.user_attr = {}
    
    def set_header(self, header):
        self.user_attr['header'] = header
        print(self.user_attr['header'])
    
    def get_header(self):
        return self.user_attr['header']

    def on_start(self):
        self.user_attr = UserLoader.get_user()
        
        print(f"User name is {self.user_attr['username']}")
        print(f"Password is {self.user_attr['password']}")

        response = UtilHelper.get_token(self.user_attr)
        print(f'Token is {response.json()["token"]}')
        header = (
            {
                "Content-Type": "application/json",
                "authorization": f'Bearer {response.json()["token"]}',
            }
        )
        self.set_header(header)



        