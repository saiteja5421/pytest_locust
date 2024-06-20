import os
from locust import HttpUser, SequentialTaskSet, between, task

class Regres(SequentialTaskSet):
    
    proxies = {
                    'http': 'http://web-proxy.corp.hpecorp.net:8080',
                    'https': 'http://web-proxy.corp.hpecorp.net:8080',
                }

    @task
    def get_user(self):
        
        # print(f"Locust host {self.locust.host}")
        print(os.getenv('LOCUST_HOST'))
        with self.client.get('/api/users?page=2',proxies=self.proxies, catch_response=True) as response:
            print(f"response status code is {response.status_code}")
            print(f"response status code is {response.text}")
            if response.status_code != 200:
                response.failure("Failed to get all user, StatusCode: " + str(response.status_code))
            else:
                if "data" in response.text:
                    response.success() # this will send success to locust UI portal
                else:
                    response.failure("Failed to get user data, Text: " + response.text) # this will send failure to locust UI portal

    @task
    def create_user(self):
        data = {
            "name": "morpheus",
            "job": "leader"
        }
        with self.client.post("/api/users",proxies=self.proxies, json=data ) as response:
            print(response.status_code)
            print(response.text)

 
class MyUser(HttpUser):
    wait_time = between(2,5)
    tasks = [Regres]

    def on_start(self):
        print(f"hostname is {self.host}")