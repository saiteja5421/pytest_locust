import json
import requests
from locust import events, SequentialTaskSet, task, constant, HttpUser

count = 1

class InventoryTest(SequentialTaskSet):
    """
    Locust script demo
    which uses Atlas service 1 - Inventory related get api requests.
    It also fetch token in on_start
    """
    
    def on_start(self):
        self.proxies = {
            "http": "web-proxy.corp.hpecorp.net:8080",
            "https": "web-proxy.corp.hpecorp.net:8080",
        }
        url = "https://sc-retrieve-test-jwt.rtplab.nimblestorage.com/gettoken"
        payload = json.dumps(
            {
                "LOGIN_URL": "https://console-atlaspoc-app.qa.cds.hpe.com/login",
                "LOGIN_USER": "give_login_user"
                "LOGIN_PASSWORD": "give_login_password",
                "CID": "cc70fa14050711ec86e042f66599af17",
            }
        )
        headers = {"Content-Type": "application/json"}

        response = requests.request("POST", url, headers=headers, data=payload)
        self.client.headers.update(
            {
                "Content-Type": "application/json",
                "authorization": f'Bearer {response.json()["token"]}',
            }
        )

    @task
    def get_virtual_machines(self):
        response = self.client.get("/api/v1/virtual-machines", proxies=self.proxies)
        assert response.status_code == requests.codes.ok

    @task
    def get_catalyst_gateways(self):
        response = self.client.get("/api/v1/hypervisor-managers", proxies=self.proxies)
        assert response.status_code == requests.codes.ok

    @task
    def get_protection_policies(self):
        response = self.client.get("/api/v1/protection-policies", proxies=self.proxies)
        assert response.status_code == requests.codes.ok

    @task
    def get_data_orchestrator(self):
        response = self.client.get(
            "/api/v1/app-data-management-engines", proxies=self.proxies
        )
        assert response.status_code == requests.codes.ok

    @task
    def get_protection_jobs(self):
        response = self.client.get("/api/v1/protection-jobs", proxies=self.proxies)
        assert response.status_code == requests.codes.ok


class LocustDemo(HttpUser):
    wait_time = constant(1)
 
    host = "https://atlaspoc-app.qa.cds.hpe.com"
    tasks = [InventoryTest]

    @events.request.add_listener
    def on_request(context, **kwargs):
        if context:
            print(f'Context --> {context["username"]}')
        else:
            print("No context -> {count}")
            count =  count+1