import requests
from locust import SequentialTaskSet, task

from examples.test_project.CommonLib.UtilHelper import UtilHelper


class CatalystGatewayTest(SequentialTaskSet):
    
    def on_start(self):
        self.proxies = {
            "http": "web-proxy.corp.hpecorp.net:8080",
            "https": "web-proxy.corp.hpecorp.net:8080",
        }
        response = UtilHelper.get_token(proxies = self.proxies)
        self.client.headers.update(
            {
                "Content-Type": "application/json",
                "authorization": f'Bearer {response.json()["token"]}',
            }
        )

    @task
    def get_catalyst_gateways(self):
        response = self.client.get("/api/v1/hypervisor-managers", proxies=self.proxies)
        assert response.status_code == requests.codes.ok

    @task
    def done(self):
        self.interrupt()

 