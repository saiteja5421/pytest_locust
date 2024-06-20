# TEST PLAN UPDATER

Script created for keeping cVSA manager test plan up to date.
After script is run the Test Scenarios on page below are updated accordingly to module doc strings from the top of tests
https://confluence.eng.nimblestorage.com/display/WIQ/cVSA+Manager+Test+Plan

## Prerequisite:
Local environment variable with personal access token for confluence
```shell
export CONFLUENCE_TOKEN="<confluence_token>"
```

Requirements:
```shell
pip install -r requirements
```

Working dir should be inside folder where update_test_plan.py is located
## Start application:

```shell
python update_test_plan.py
```