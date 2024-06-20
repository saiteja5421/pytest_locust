

from locust import HttpUser, constant

from examples.test_project.TaskSetLib.Inventory import InventoryTest
from examples.test_project.TaskSetLib.ProtectionGateway import CatalystGatewayTest


class LocustDemo(HttpUser):
    wait_time = constant(1)
    host = "https://atlaspoc-app.qa.cds.hpe.com"
    # Tasks from InventoryTest and CatalystGatewayTest will be triggered.
    # Failed Request and successful request will be added into list via events
    # When the program is over the success and failure list will be captured in csv files.
    tasks = [InventoryTest,CatalystGatewayTest]