from locust import SequentialTaskSet, User, between, task

# This is Multiple Task example.
# But if one class starts executing ,it will keep execute. We need interrupt so that other class also may get chance to execute
class CloudAccountMgr(SequentialTaskSet):
    @task
    def RegisterAccount(self):
        print("Registering account")

    @task
    def DeletingAccount(self):
        print("Deleting account")

class InventoryManager(SequentialTaskSet):
    @task
    def GetEc2Instance(self):
        print("Get EC2 instance")

    @task
    def GetEBSVolume(self):
        print("Get EBS Volume")  

class MyUser(User):
    wait_time = between(1,2)
    tasks= [CloudAccountMgr,InventoryManager]
    

