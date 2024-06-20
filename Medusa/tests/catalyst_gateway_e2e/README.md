# Catalyst Gateway e2e API Test Automation Framework

This repository consists of the framework layout for API testing. 

### Assumptions

It will assume that all the necessary pre-requisites like vCenters (multiple, and AD users), storage folders with vCenters, different regions/labs (rtp/etc) - good to have, and neccessary AWS accounts are in place and created beforehand. The automation will make use of those and do the read/write/delete operations. And Sandbox cluster with all the dependent microservices deployed and being up to date with latest code.

### TO DO

1. Fix failing test cases on Jenkins

# GitHub Repositories

1. [Cloud Backup](https://github.hpe.com/dcs-bristol/backup-cloud/tree/master/catalyst-gateway-manager)
2. [Onprem Backup](https://github.hpe.com/dcs-bristol/backup-on-prem)

# Test Plans

1. [Functional Test](https://confluence.eng.nimblestorage.com/pages/viewpage.action?pageId=190843612)
2. [E2E Test](https://confluence.eng.nimblestorage.com/display/WIQ/Mauritania+Catalyst+Gateway+Manager+Test+Plan)

### More to be added here

The folder structure is:

```
(bdd-CUy-gIYt-py3.8) ➜  catalyst-gw-e2e-api git:(master) ✗ tree -L 2                          
.
├── Dockerfile                                  --> To generate docker test image
├── Jenkinsfile                                 --> Configuration file for Jenkins CI job for e2e tests
├── Makefile                                    --> Makefile for ease of executing the test commands
├── README.md
├── README_BEFORE_CHANGING_VARIABLES_INI.md
├── chaos                                       --> Chaos test folder
│   ├── README.md
│   ├── health-http-fail-report.pdf
│   ├── health-http-pass-report.pdf
│   ├── health-http.yaml
│   ├── journal.json
│   └── terminate-pod.yaml
├── created_cluster_id.json
├── e2e-tests                                   --> E2E test folder
│   ├── __init__.py
│   ├── api                                     --> Script for common functions
│   ├── conftest.py
│   ├── enums
│   ├── library                                 --> Common libraries that will be used access like VCenter etc.
│   ├── models
│   ├── payloads                                --> Payload folder, to generate payloads based on CRUD operation
│   ├── schemas                                 --> JSON schema folder for assertion of responses
│   ├── test_data
│   ├── test_sanity                             --> Tests folder that holds sanity tests
│   ├── test_scripts                            --> Tests folder that holds all the tests 
│   └── utils                                   --> Utilities folder
├── k6-perf-tests                               --> Performance tests for CRUD end-points
│   ├── CRUD_workflow.js
│   ├── README.md
│   ├── backup_restore_workflow.js
│   ├── createLocalStore.js
│   ├── create_protectiongateway.js
│   ├── deleteCatalystVM.js
│   ├── delete_protectiongateway.js
│   ├── get_all_clusters.js
│   ├── jenkins-scripts
│   ├── lib.js
│   ├── list_protectiongateway.js
│   ├── modifyCatalystNic.js
│   ├── modify_local_store.js
│   ├── modify_nic.js
│   ├── payload_lib.js
│   └── testconfig.json
├── lint.sh                                     --> Lint script to check the Python linting
├── poetry.lock								      --> Set versions of libraries added by poetry
├── postman
│   └── atlas.postman_collection.json            --> Postman collection for manual api testing
├── pyproject.toml                              --> Poetry to add libraries and create virtual environment
├── pytest.ini                                  --> Configuration file for pytest specific
└── variables.ini                               --> Configuration file for product specific details

23 directories, 136 files


```

# Pre-Requisite

Prerequisites components are placed in variables.ini file. Components are described in README_BEFORE_CHANGING_VARIABLES_INI.md file.

# How to Get Auth Token for making CRUD calls?

[Reference](https://confluence.eng.nimblestorage.com/display/CDSDEVOPS/Functional+Tests+in+Sandbox)

DevOps team has made a service that when deployed on the respective clusters like the ATLASPOC, ATLASPOC2, SC-INT, will take the user provided details like the Username, Password, CID, and the URL of the micro-app and return the token, which can then be used for making further API calls. When the tests are executed from Jenkins, we need to make sure that the Jenkins job have access to the HPE LR1 network of the RTP lab for this to work.

Below is an example of the cURL command for getting the users auth token for ATLASPOC cluster:

Request
```
curl --location --request POST 'https://sc-retrieve-test-jwt.rtplab.nimblestorage.com/gettoken' \
--header 'Content-Type: application/json' \
--data '{
    "LOGIN_URL": "https://console-atlaspoc-app.qa.cds.hpe.com/login",
    "LOGIN_USER": "<MY-EMAIL>",
    "LOGIN_PASSWORD": "<MY-PASSWORD>",
    "CID": "<MY-CID>"
}'
```

_Note: CID - Customer ID, this is nothing but, `application_customer_id` field that one can get by inspecting the browser network tab when you on the URL: https://pavo.common.cloud.hpe.com/applications/my-apps, look for the API call https://pavo-user-api.common.cloud.hpe.com/ui-doorway/ui/v1/applications/provisions?provision_status=PROVISIONED - this API call will have the `application_customer_id` which needs to be filled in the above Request._

Response
```
{
    "currentUrl": "https://console-atlaspoc-app.qa.cds.hpe.com/",
    "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6Iml2RmVQWHlXd3RraVN0Y2J6eWVtQmZQODhQNCIsInBpLmF0bSI6IjFmN28ifQ.eyJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIiwiY2xpZW50X2lkIjoiODllYWQzMWYtM2E5Mi00ZjM3LTk4MGEtZDMyNGQ3ZDUzOGY2IiwiaXNzIjoiaHR0cHM6Ly9zc28uY29tbW9uLmNsb3VkLmhwZS5jb20iLCJhdWQiOiJhdWQiLCJsYXN0TmFtZSI6IlRlc3QiLCJzdWIiOiJjYXRhbHlzdC50ZXN0QG91dGxvb2suY29tIiwidXNlcl9jdHgiOiJiZjYwNTFhNDA1MTUxMWVjODY0MDIyY2ZiYzQ3ZmFhMSIsImF1dGhfc291cmNlIjoicDE0YyIsImdpdmVuTmFtZSI6IkNhdGFseXN0IiwiaWF0IjoxNjMxMDQwNDM2LCJleHAiOjE2MzEwNDc2MzZ9.SgVhVfqIRhfJOGmRMRpeWxLoIrT-Ec4SJPinQSXmxPGrOysewEsDB_Aw6gSbZrMTWe5EijqIJF4GjVfHx02GuRyGx70RH072cIWoJJJEe7NSIftLXcxR7dbQO7-0uGfkmuFvbOLlJQBeM7USBs1urDZ3SbI2frE0SNzAkJ1SLz8quZLffxlqvwVKxcW2BpZLpCIbIVeNVyOLGJf7LcrihWu0tuh_z17mgKXFNyZq8NIYjbIjTLZcFATQyN3z4LnhY8MAzyPidE8a5_-gI6or3_pxNolaRFxjOZD0AduxTZyROyHYB0zN5cqqLhz32UH8PQ-MTRJYQ3pET9sySu2R7Q"
}
```

# How to execute the tests?

1. Clone this repository and make sure you install the `poetry` using either `brew`, which is just `brew install poetry` or by referring to the [link](https://python-poetry.org/docs/) here. 
2. Once done, do `poetry install`, this command will install all the required dependencies. 
3. `poetry shell` to activate the virtual environment
4. And now, you can update the `variables.ini` files based on your testbed
5. Use `make help` to know the different tests that you can execute:
   1. `make lint` --> This will run the lint and ensure you are adhereing to the proper coding standards
   2. `make e2e-tests` --> This will execute the e2e tests
   3. `make docker-e2e-test` --> This will execute e2e tests in a docker container
   4. `make sanity-tests` --> This will execute the sanity tests
   5. `make docker-sanity-test` --> This will execute sanity tests in a docker container

The REST end-point where the server is running can be modified in the `variables.ini` file under the `e2e-tests` directory.

Execute `make help` or `make` to see all the available options for `make` command.

`make e2e-tests`, this will trigger the all the tests that are located in `test_scripts` folder.

If you don't want to execute the test suite and instead want to execute a particular test case, then make sure you are
in folder `Atlas-catayst-gw-e2e-api` and `@mark.dependency` annotation is commented, then execute the below command:

`pytest -sv e2e-tests/test_scripts/{file_name}.py`

It works for sanity tests respectively.

### Pushing to repo

**Execute the `make lint` to make sure the linting is proper and no issues exists before pushing the code the git repo.**

To make sure the code is formatted well, we use black with pre-commit package to ensure it. 
To install pre-commit and use it, please use:
```
poetry run pre-commit install
```
This will ensure that whenever you want to commit, black will check your code and show you the difference. 
If your file does not meet black requirements, please use:
```
poetry run black [file]
```

To update black hook to the latest version we should use command:
```
poetry run pre-commit autoupdate
```
### Test Coverage

To run coverage tests make sure that in `pytest.ini` file there is a parameter "--cov" added to "addopts" variable then execute below command.

`pytest -sv e2e-tests/test_scripts/{file_name}.py`

If you don't want to run coverage tests, remove the "--cov" parameter before running tests.

# Reporting

We will use [Report Portal](https://reportportal.io/) as our reporting tool, this will be in consistency with other teams in Storage Central (like Atlas). Deploy a docker instance of the report portal with below steps:

[Official Steps](https://reportportal.io/docs/Deploy-with-Docker) to download and run the docker instance of RP.
```
1. Download docker-compose YAML file
    curl https://raw.githubusercontent.com/reportportal/reportportal/master/docker-compose.yml -o docker-compose.yml

2. Spin up containers
    docker-compose -p reportportal up -d --force-recreate

3. Execute below command to view the containers are up and healthy
    docker ps -a

4. Go to below URL with credentials - user: superadmin, password: erebus
    http://localhost:8080/ui 
```

Required changes have been made in the `conftest.py` file to make use of the ReportPortal. Make use of `docstrings` to provide the steps on what the tests are performing so that these steps show up in the reportportal. Please do check the sample tests.

Example of a ReportPortal Tests look as [here](https://github.hpe.com/sachin-uplaonkar/catalyst-gw-e2e-api/commit/fde297f6af184f3e7c9399939c69a816b1f7cd30#commitcomment-25227)

#### Report Portal Details:

URL: http://10.226.67.255:8080
Project Name: e2e-api

Note: Do not configure to push test runs to this Report Portal when running the test locally on you dev environment.
This report portal is intended to use with Jenkins pipeline.

# Execute Tests in Docker

The `catalyst-gw-e2e-api` directory consists of the Dockerfile that helps in dockerizing the tests and making them run as a separate entity. The *IP* and the *PORT* fields are added as an environment variable here, update them as required. Once the proper service is deployed, a new variable URL will be added so that tests point to the service.

### Steps to build and run the tests

1. `cd` into the `catalyst-gw-e2e-api` directory
2. Run the command - `docker build --tag e2e-catalyst-gw-mgr:v1.0 .` to build the docker image for test
3. Once successfully built, execute the command - 
```
docker run --rm -e no_proxy=$no_proxy,127.0.0.1,localhost,.nimblestorage.com,10.0.0.0/8,192.0.0.0/8,172.0.0.0/8,10.226.67.255 e2e-catalyst-gw-mgr:v1.0 python -m pytest -sv --reportportal e2e-tests/test_scripts
```




A docker image from the above steps can be found using the command `docker images | grep catalyst`:

```
(bdd-CUy-gIYt-py3.8) ➜  catalyst-gw-e2e-api git:(master) ✗ docker images | grep catalyst                
e2e-catalyst-gw-mgr                  v1.0                                                    e87367482634   12 seconds ago   262MB

(bdd-CUy-gIYt-py3.8) ➜  catalyst-gw-e2e-api git:(master) ✗ docker run --rm -e no_proxy=$no_proxy,127.0.0.1,localhost,.nimblestorage.com,10.0.0.0/8,192.0.0.0/8,172.0.0.0/8,10.226.67.255 e2e-catalyst-gw-mgr:v1.0 python -m pytest -sv --reportportal e2e-tests/test_scripts

```


# How to connect to vCenter and verify the VM exists?

As part of e2e workflow, we need to verify the whether the Catalyst-GW VM is created in the specified vCenter. Add/update the corresponding vCenter details in the `variables.ini` file under the `[VCENTER1]` field, as indicated, one needs to provide the IP of the vCenter, username, password, and the VM which we are looking for. A sample run of the code looks like below. Here, we are extracting the necessary details like IP, MAC address and the Connected Status fields along with whether the VM is powered ON or not.


```
(bdd-CUy-gIYt-py3.8) ➜  catalyst-gw-e2e-api git:(master) ✗ python e2e-tests/library/vcenter_details.py
Getting all ESX hosts ...
Collecting portgroups on all hosts. This may take a while ...
        Host hiqa-tc20.lab.nimblestorage.com done.
        Host hiqa-tc21.lab.nimblestorage.com done.
        Host c3-nimdl360g10-250.lab.nimblestorage.com done.
        Host c3-nimdl360g10-252.lab.nimblestorage.com done.
        Host c3-nimdl360g10-251.lab.nimblestorage.com done.
        Portgroup collection complete.

Getting datastores ...

Name                  : Datastorea999-hiqa-20-21-vmfs-DS1-for-VM
URL                   : ds:///vmfs/volumes/605baa9d-0185f980-0f2f-08f1ea7dad1c/
Capacity              : 7.0TB GB
Free Space            : 7.0TB GB
Uncommitted           : 191.2GB GB
Provisioned           : 209.7GB GB
Hosts                 : 2
Virtual Machines      : 1
Virtual Machine Name  : HPE-Project-Atlas-2124.9-vcenter

Getting all VMs ...
Found VM: HPE-Project-Atlas-2124.9-vcenter(poweredOn)

IP Address: (str) [
   '172.21.203.221'
]
 MAC Address: 00:50:56:a9:2b:29
 Connected Status: True 


IP Address: (str) []
 MAC Address: 00:50:56:a9:cd:d1
 Connected Status: True 


IP Address: (str) []
 MAC Address: 00:50:56:a9:d3:7b
 Connected Status: True 



Summary: {
    "vm_name": [
        "HPE-Project-Atlas-2124.9-vcenter"
    ],
    "datastore": [
        "Datastorea999-hiqa-20-21-vmfs-DS1-for-VM"
    ],
    "power_status": [
        "poweredOn"
    ],
    "ip_address": [
        [
            "172.21.203.221"
        ],
        [],
        []
    ],
    "mac_address": [
        "00:50:56:a9:2b:29",
        "00:50:56:a9:cd:d1",
        "00:50:56:a9:d3:7b"
    ],
    "connected_status": [
        true,
        true,
        true
    ]
}
(bdd-CUy-gIYt-py3.8) ➜  catalyst-gw-e2e-api git:(master) ✗  
```


# Sanity Testing

This suite contains tests for key functionalities of ATLAS Catalyst that have a high probability of being patched/updated.

Pre-requisites for sanity tests are placed in `variables.ini` file under `[SANITY]` section.

To run this suite make sure you are in folder `Atlas-catayst-gw-e2e-api` and then execute the below command:

```pytest -sv e2e-tests/test_sanity```

To execute Sanity Tests in Docker, follow the instruction aforementioned with the exception in `docker run` command:

```
docker run --rm -e no_proxy=$no_proxy,127.0.0.1,localhost,.nimblestorage.com,10.0.0.0/8,192.0.0.0/8,172.0.0.0/8,10.226.67.255 e2e-catalyst-gw-mgr:v1.0 python -m pytest -slv --reportportal e2e-tests/test_sanity
```

To run sanity tests with `make` command, please refer to `How to execute the tests?` section of this document.

# Performance Testing

**SAMPLE TEST**

We will be using the [k6](https://k6.io) as our performance testing tool, this is a javascript based tool that support REST, gRPC, and various other methods which will be helpful in testing the performance of CRUD based operations. Please refer to the above document of k6. The folder `k6-perf-tests` consists of a sample test (of cluster manager) that is run in the docker container. K6 supports the execution of tests from various Amazon regions and provides a great Dashboard functionality. These features are available only in the paid version.

K6 allows us to replicate the actual production scenario as seen in the example below, here the we are selecting 100 users, who will join the application under test on a specified interval and at the same time ramping up the users as we usually see in the day to day life. We can also, restrict on the time taken for each request to be within the 500 ms as part of perf measure. There are alot of other evaluations available within the k6.

```
    stages: [
      { duration: "30s", target: 1 },
      { duration: "30s", target: 15 },
      { duration: "30s", target: 30 },
      { duration: "30s", target: 60 },
      { duration: "30s", target: 100 },
      { duration: "30s", target: 100 },
      { duration: "30s", target: 75 },
      { duration: "30s", target: 42 },
      { duration: "30s", target: 20 },
      { duration: "30s", target: 10 },
      { duration: "30s", target: 0 },
    ],
    thresholds: {
      "RTT": ["avg<500"]
```

# Chaos Testing

**SAMPLE TEST**

Chaos Testing is used to find the hidden dependencies and/or missed error handlings and to know how the app performance when an unexpected event occurs. The idea here is to randomly terminate some of the services and/or dependent services and see how the app performance. Here we are using [ChaosToolKit](https://chaostoolkit.org/) to perform the Chaos operations. The Chaos test can be found under the directory `tests/chaos`.

### Test set up

Cluster Manager REST service is dependent on the gRPC service which inturn depends on Database. gRPC service is also dependent on the Kafka queues to write into them. To perform a simple chaos test that basically distrupts the service of the gRPC service in meanwhile making a REST call to ensure the system responds follow the below steps to the setup and execution.

#### Steps to Run

1. Copy the `chaos/**` directory into the `ccs-dev` environment where the k8s-cluster-mgr repos are present 
2. Install the chaostoolkit using the command:
`pip install -U chaostoolkit chaostoolkit-kubernetes`
3. And execute the command `chaos run health-http.yaml`, the output if everything goes as expected will be as below:

```
$ chaos run health-http.yaml
[2021-05-28 16:42:44 INFO] Validating the experiment's syntax
[2021-05-28 16:42:45 INFO] Experiment looks valid
[2021-05-28 16:42:45 INFO] Running experiment: What happens if we terminate an instance of the gRPC application?
[2021-05-28 16:42:45 INFO] Steady-state strategy: default
[2021-05-28 16:42:45 INFO] Rollbacks strategy: default
[2021-05-28 16:42:45 INFO] Steady state hypothesis: The app is healthy
[2021-05-28 16:42:45 INFO] Probe: app-responds-to-requests
[2021-05-28 16:42:45 INFO] Steady state hypothesis is met!
[2021-05-28 16:42:45 INFO] Playing your experiment's method now...
[2021-05-28 16:42:45 INFO] Action: terminate-app-pod
[2021-05-28 16:42:45 INFO] Pausing after activity for 2s...
[2021-05-28 16:42:47 INFO] Steady state hypothesis: The app is healthy
[2021-05-28 16:42:47 INFO] Probe: app-responds-to-requests
[2021-05-28 16:42:47 INFO] Steady state hypothesis is met!
[2021-05-28 16:42:47 INFO] Let's rollback...
[2021-05-28 16:42:47 INFO] No declared rollbacks, let's move on.
[2021-05-28 16:42:47 INFO] Experiment ended with status: completed
```
4. Incase if something goes wrong and unexpected happens, the output looks like below:

```
$ chaos run health-http.yaml
[2021-05-28 16:47:38 INFO] Validating the experiment's syntax
[2021-05-28 16:47:38 INFO] Experiment looks valid
[2021-05-28 16:47:38 INFO] Running experiment: What happens if we terminate an instance of the gRPC application?
[2021-05-28 16:47:38 INFO] Steady-state strategy: default
[2021-05-28 16:47:38 INFO] Rollbacks strategy: default
[2021-05-28 16:47:38 INFO] Steady state hypothesis: The app is healthy
[2021-05-28 16:47:38 INFO] Probe: app-responds-to-requests
[2021-05-28 16:47:38 INFO] Steady state hypothesis is met!
[2021-05-28 16:47:38 INFO] Playing your experiment's method now...
[2021-05-28 16:47:38 INFO] Action: terminate-app-pod
[2021-05-28 16:47:38 INFO] Pausing after activity for 2s...
[2021-05-28 16:47:40 INFO] Steady state hypothesis: The app is healthy
[2021-05-28 16:47:40 INFO] Probe: app-responds-to-requests
[2021-05-28 16:47:43 ERROR]   => failed: activity took too long to complete
[2021-05-28 16:47:43 WARNING] Probe terminated unexpectedly, so its tolerance could not be validated
[2021-05-28 16:47:43 CRITICAL] Steady state probe 'app-responds-to-requests' is not in the given tolerance so failing this experiment
[2021-05-28 16:47:43 INFO] Experiment ended with status: deviated
[2021-05-28 16:47:43 INFO] The steady-state has deviated, a weakness may have been discovered 
```

# Gate/PR Checks

GitHub wired to have minimal validation before code goes into 'master' branch.
For now a gate check job [gate-run](https://10.226.69.107/job/gate-run/) gets triggered if the file changes within *qa_automation/Medusa/*** scope.

There are two hooks introduced.

1. For all PR's whose scope are within *Medusa/*** then job [gate-run](https://10.226.69.107/job/gate-run/) gets triggered. It does below validations

    - Service1 PQA dry run *"SERVICE_VERSION=service1 pytest tests/catalyst_gateway_e2e --collect-only"*
    - Service2 FQA dry run *"pytest -c configs/atlantia/pytest/pytest.ini tests/functional --collect-only"*
    - Service2 PQA dry run *"pytest -c configs/atlantia/pytest/pytest.ini tests/e2e --collect-only"*
    - Code formatter using *black* - Just checks *.py files and print its output, doesn't fail the test.

2. On demand request to run API Sanity test. If user wanted to run a live test for their change with SERVICE1 API Sanity against SCDEV01 then simply type a comment on the PR **"Test this change"**. Job [test-runner](https://10.226.69.107/job/test-runner/) listen for this text and triggers remote job [atlas-sanity-scdev01](http://dcs-jenkins.vlab.nimblestorage.com:8080/view/QA_AUTOMATION_API/job/atlas-sanity-scdev01/)
    - Runner: [test-runner](https://10.226.69.107/job/test-runner/)
    - Actual job: [atlas-sanity-scdev01](http://dcs-jenkins.vlab.nimblestorage.com:8080/view/QA_AUTOMATION_API/job/atlas-sanity-scdev01/)

    Result status gets posted once remote job gets completed.
