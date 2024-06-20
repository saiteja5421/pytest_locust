from locust import SequentialTaskSet, User, between, task

# This is SequentialTask example


class MyTasks(SequentialTaskSet):

    @task
    def select_product(self):
        print("Selecting the product")

    @task
    def order(self):
        print("Ordering the product")


class MyUser(User):
    wait_time = between(2, 3)
    tasks = [MyTasks]
