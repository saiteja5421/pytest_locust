# Publish result to testrail
Pass below parameters to pytest cli and it will publish the result to testrail
```
"--testrail",
"--tr-config=configs/data_panorama/pytest/pytest_testrun.ini",
"--tr-run-id=23827"
```
Note: test run id given here is sample. Check your test run id and pass it accordingly

# Publish to report portal
Pass --reportportal option to pytest cli then the result will be published to reportportal