# Medusa Framework Quickstart Guide

## 1. Configuration virtual environment

Medusa Framework uses modules that don't come as part of standard library,
and it's recommend to install them in virtual environment, which is self-contained
directory tree that contains a Python installation for a particular version of Python,
plus a number of additional packages.

**Steps to create virtual environment:**

To create virtual environment, open terminal and navigate to Medusa directory
run indicated below command:

`python3 -m venv venv`,

where we invoke Python3 module `venv` to create virtual environment named `venv`

NOTE: The python version must be >= 3.9

**Activating virtual environment:**

To activate virtual environment, open terminal and navigate to Medusa directory and
run indicated below command:
* on Windows: `venv\Scripts\activate.bat`
* on Linux / Mac OSX: `. venv/bin/activate`

**Deactivating virtual environment:**

To deactivate virtual environment, open terminal and navigate to Medusa directory and
run command: `deactivate`

### 2. Dependencies

*** 2.1 Dependencies for RDS Oracle DB ***

To install and setup dependencies needed for RDS Oracle DB library.
NOTE: Expected to run as root user and `requirements_rds.sh` should already be an executable via 'chmod +x requirements_rds.sh'
run command: `./requirements_rds.sh`

*** 2.2 Dependencies for Medusa Framework ***

There are two types of requirements in Medusa Framework:
* developer oriented - `requirements_dev.txt` - which contains dependencies for developers 
like formatters, linters etc.
* project oriented - e.g. for Backup and Recovery: `requirements_backup_and_recovery.txt` - which contains dependencies that are required to 
execute code.
* project oriented - e.g. for RDS Backup and Recovery: `requirements_rds.txt` - which contains dependencies that are required to execute code for Maria DB and Oracle DB

**Installation guide:**

For installation, we will use built-in Python module named `pip3`.

To install dependencies, open terminal and navigate to Medusa directory, **activate your virtual
environment** and run commands:
* `pip3 install -r requirements_dev.txt`
* `pip3 install -r requirements_backup_and_recovery.txt` (Medusa for Backup and Recovery - S1, S2)
* `pip3 install -r requirements_rds.txt` (Medusa for RDS Mariadb & Oracle DB)

**Updating dependencies:**

To upgrade dependency change version in requirements.txt to version that you want to update, e.g.
`pytest==6.0.0` to `pytest==6.2.54`.

## 3. Using Docker image from Harbor Registry

As a part of our repository we are building Docker image for our tests, you can get it
from Harbor Registry.
Images are build for each commit to master in `qa_automation` with tag `latest`.

Images can be used in CI/CD on **SC-Jenkins** out of the box.

---
Full Backup and Restore testing container (dependencies and code):
```
sc-jenkins-preprod/medusa-backup-and-recovery
```

## 4. Global Variables

Global variables that are accessible in every file.
`import pytest` -> import pytest module
`pytest.is_filepoc` -> [bool] It parse CONFIG_FILE name for filepoc value.
`pytest.is_scdev01` -> [bool] It parse CONFIG_FILE name for scdev01 value.

## 5. Medusa design recording session
https://hpe-my.sharepoint.com/personal/vivek-vikas_baviskar_hpe_com/_layouts/15/stream.aspx?id=%2Fpersonal%2Fvivek%2Dvikas%5Fbaviskar%5Fhpe%5Fcom%2FDocuments%2FRecordings%2FMedusa%20framework%20design%2D20220512%5F150542%2DMeeting%20Recording%2Emp4&ga=1

## 6. Medusa framework design
![Medusa_jenkins](https://media.github.hpe.com/user/54977/files/4b2a8a89-e9e8-424d-8d2c-11c73f336ca5)

## 7. Medusa features 

![Medusa-flair](https://media.github.hpe.com/user/54977/files/7182f953-348f-437c-b40d-988aaa9be8d6)

## 8. How to run a test in Medusa
Assuming installation / dependencies setup steps (above) were done already.

NOTE: The python version must be >= 3.9

Refer to: https://confluence.eng.nimblestorage.com/display/WIQ/Functional+Tests+Execution

*** 8.1 Initialize Context & usage of .ini variables file ***

*** 8.1.1 Initialize / Update Context in the test file(s) that you want to run/debug ***
In the test file(s), use the appropriate Context() / SanityContext() that you want to use & initialize

*** 8.1.2 Update .ini variables file (Use the appropriate .ini file for Context/SanityContext) ***
Update one of the .ini variables files that will be used when running the test file/case.

Update the following sections with your dedicated credientials/information:
-   [CLUSTER] : Target cluster information
-   [USER-ONE] : API credentials for target DSCC Account / Cluster
-   [AWS] : Target AWS / CSP account information

Ex: In /Medusa/configs/atlantia/variables_regression_scdev01.ini , update the appropriate [AWS] section

*** 8.2 Set Environment Variables ***
Follow one of the methods bellow. If you experience issues when running/debugging the test, try another method.

*** 8.2.1 Set Environment Variables from the terminal ***
In the terminal, you can set the environment variables such as LOCALSTACK_URL, CONFIG_FILE, SERVICE_VERSION, ATLANTIA_ENV, etc.

Refer to https://confluence.eng.nimblestorage.com/display/WIQ/Functional+Tests+Execution#:~:text=Set%20these%20environment%20variables%3A 

*** 8.2.2 Set Environment Variables from the test file ***
In the test file, you can directly set the environment variables explained in Section 8.2.1, but within the context fixture or test function in the file.

*** 8.2.3 Set Environment Variables from the Medusa/lib/common/config/config_manager.py file ***
Directly update the line to point to the dedicated .ini variables file you just updated: 
config_file = os.environ.get("CONFIG_FILE")

*** 8.3 Run test file ***
In the VSCODE Terminal, enter the following for the dedicated test file/folder you want to run: pytest -sv /Medusa/tests/e2e/aws_protection/test_regression/backup_restore_1/test_TC56_backup_restore_terminate_instance.py

Refer to: https://confluence.eng.nimblestorage.com/display/WIQ/Functional+Tests+Execution#:~:text=Command%20to%20run%20tests%20from%20terminal

*** 8.4 Debug test file (run test file through debugger) ***

*** 8.4.1 Setup settings.json ***
In **Medusa/.vscode/settings.json** , update the full path of the directory of where you want to debug the test file. Can refer to the following:
{
    "python.testing.pytestArgs": [
        "/Medusa/tests/e2e/aws_protection/test_regression/backup_restore_1"
    ],
    "python.testing.unittestEnabled": false,
    "python.testing.pytestEnabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "[python]": {
        "editor.defaultFormatter": null,
        "editor.insertSpaces": true,
        "editor.tabSize": 4,
        "editor.formatOnSave": true
    },
    "editor.fontSize": 15,
    "editor.rulers": [
        120
    ],
    "workbench.colorCustomizations": {
        "editorRuler.foreground": "#ff4081"
    },
    "python.linting.flake8Enabled": true,
    "python.linting.enabled": true,
    "python.formatting.blackArgs": [
        "line-length 120"
    ],
}

Similarly to https://confluence.eng.nimblestorage.com/display/WIQ/Functional+Tests+Execution#:~:text=After%20that%2C%20copy%20the%20content%20below%20in%20the%20.vscode/settings.json%C2%A0file%20and%20update%20the%20path%20for%C2%A0python.testing.pytestArgs

*** 8.4.2 Run debugger for test file ***

-   Click on the "Testing" Icon (Looks like a Labratory Flask Symbol) on the left column in VSCODE ![image](https://media.github.hpe.com/user/50650/files/54aa5b85-c787-40cb-a872-affe88d8a09d)
-   Find the test file (after going through the directories) you want to debug
-   Click on the "Debug Test" Icon (Looks like a play button with a bug/insect) either for the test file or the test case(s) within that file on the right side of that test file ![image](https://media.github.hpe.com/user/50650/files/2cde6167-0906-4cc1-9f10-a3da1b71ae70)
-   NOTE: You can also run the debugger directly from the file you wish to run, by clicking on the same "Debug Test" Icon  found on the top right. Sometimes it runs into issues so using the previous method is suggested. ![image](https://media.github.hpe.com/user/50650/files/07283ddc-6065-494e-b122-745d615cbdce)


-   Find the test file (after going through the directories) you want to debug

## 9. Jenkins jobs for building Dockerimage
Currently there are 3 active Jenkins jobs which build Dockerimages. These images are used in running functional, sanity, and regression tests through our various Jenkins pipelines

| Jenkins Build | Dockerfile | Use|
| ------------- | ---------- | -- |
| [qa-medusa-framework](https://sc-jenkins.rtplab.nimblestorage.com/job/qa-medusa-framework/job/master/) | medusa_backup_and_recovery.Dockerfile | CCS-DEV pipeline for functional tests |
| [build-docker-image-atlantia](http://dcs-jenkins-cxo.vlab.nimblestorage.com:8080/job/build-docker-image-atlantia/) | medusa_backup_and_recovery.Dockerfile | PQA team for Sanity and Regression tests |
| [build-docker-image](http://dcs-jenkins-cxo.vlab.nimblestorage.com:8080/job/build-docker-image/) | Dockefile | Atlas E2E tests |
| [build-docker-image](http://dcs-jenkins-cxo.vlab.nimblestorage.com:8080/job/build-docker-image/) | gate_check.Dockerfile |Git Gate Check |
