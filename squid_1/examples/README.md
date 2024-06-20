# Execute locust 
## Execute locust test. Once initiated open localhost:8089 in browser and executed it
locust -f api_test/get_user -u 1 -r 1

## This command will run the test case for 20 seconds in headless mode (no need to run from browser)
locust -f api_test/get_user -u 1 -r 1 -t 30s --headless

## To run using config.yml 
locust --config=api_test/config.yml

## To enable debugging locust script in vscode, add below configuration in launch.json
```
{
            "name": "Locust: Current File",
            "type": "python",
            "request": "launch",
            "module": "locust",
            "args": [
                "-f",
                "${file}",
                "--headless",
                "--config=Squid/tests/locust.conf"
            ],
            "console": "integratedTerminal",
            "gevent": true
        },
```

## To Enable debug with conf.yml (where the host and user details are captured)

