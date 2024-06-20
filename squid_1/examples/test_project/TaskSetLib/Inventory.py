import requests
from locust import SequentialTaskSet, task

from examples.test_project.CommonLib.UtilHelper import UtilHelper


class InventoryTest(SequentialTaskSet):
    
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

    @task
    def done(self):
        self.interrupt()