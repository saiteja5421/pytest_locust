# We are planning to use the https://k6.io for doing the performance tests
# More details will be added as we go...

### https://k6.io/docs/getting-started/running-k6/ 

`docker run -i loadimpact/k6 run - <k6-perf-tests/get_all_clusters.js` 
`docker run -i loadimpact/k6 run --vus 10 --duration 30s - <k6-perf-tests/get_all_clusters.js`

# Test inputs are configurable

## Test inputs are captured in testconfig.json
### Pass testconfig.json as below

`k6 run -e TEST_CONFIG=testconfig.json test_content_library.js --insecure-skip-tls-verify`

# Test Config json 
## Common input

All the common input can be captured in common element.

## Test specific input

All the test specific inputs will be captured in element specific to test case. For ex: createProtectionGateway element is for create_protectiongateway.js file