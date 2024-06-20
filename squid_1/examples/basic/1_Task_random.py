from locust import User, between, task

# Random execution of tasks
class MyUser(User):
    wait_time = between(5,10)
    @task
    def task1(self):
        print("Running task1")

    @task
    def task2(self):
        print("Running task2")

