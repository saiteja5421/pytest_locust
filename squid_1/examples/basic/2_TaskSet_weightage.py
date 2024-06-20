from locust import TaskSet, User, between, task

#Tasks with weightage
class MyTasks(TaskSet):
    @task(4)
    def view(self):
        print("Running view")

    @task(1)
    def order(self):
        print("Running order")

class MyUser(User):
    wait_time = between(5,10)
    tasks= [MyTasks]
    

