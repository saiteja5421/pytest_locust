from locust import SequentialTaskSet, User, between, task

# Multiple task with interrupt . 
# If Interrupt is not there then the task from a single class will keep on execute
class CloudAccountMgr(SequentialTaskSet):
    @task
    def RegisterAccount(self):
        print("REgistering account")

    @task
    def DeletingAccount(self):
        print("Deleting account")

    @task
    def complete_execution(self):
        self.interrupt()

class InventoryManager(SequentialTaskSet):
    @task
    def GetEc2Instance(self):
        print("Get EC2 instance")

    @task
    def GetEBSVolume(self):
        print("Get EBS Volume")  

    @task
    def complete_execution(self):
        self.interrupt()

# Multiple task with interrupt
class MyUser(User):
    wait_time = between(1,2)
    tasks= { 
        CloudAccountMgr : 4,
        InventoryManager : 1
    }
    

