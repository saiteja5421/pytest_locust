from locust import events, SequentialTaskSet, User, between, task

# For the whole test suite this will run only once


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("---- Start Load Test -----------")  # 1
    user_count = environment.parsed_options.num_users
    print(f"Number of users are {user_count}")


@events.test_stop.add_listener
def on_test_stop(**kwargs):  # 7
    print("---- Stop Load Test -----------")


class CloudAccountMgr(SequentialTaskSet):
    # for each taskset it will run start ,stop once
    def on_start(self):  # 3
        print("--- Cloud Account Manager Test start ---")

    def on_stop(self):  # 5
        print("--- Cloud Account Manager Test stopped ---")

    @task
    def RegisterAccount(self):  # tasks are running number 4
        print("Registering account")

    @task
    def DeletingAccount(self):
        print("Deleting account")

    @task
    def complete_execution(self):
        self.interrupt()


class MyUser(User):
    wait_time = between(1, 2)
    tasks = [CloudAccountMgr]

    # for each user start and stop will executed once
    def on_start(self):  # 2
        print(f"---- User test starts -------")

    def on_stop(self):  # 6
        print(f"---- User test completed -------")
