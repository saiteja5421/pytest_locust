# Squid
A Locust based Performance Testing Tool

## Squid Docker file and env file 
1. Squid.Dockerfile will prepare development environment for performance testing.
2. Squid uses locust perf framework (It is a python based).
3. Squid.env file contains required environment variable to execute perftest.
4. Copy paste it and create .env file with the parameters given there.
5. Squid should be executed from qa_automation folder as it also uses Medusa libraries.

# Proxy settings.

Proxy is not taken from environment variable, in your task class set the proxy like below
and call it in self.client.<get/post>
```
# inside your class add proxies property
proxies = {
        'http': 'http://web-proxy.corp.hpecorp.net:8080',
        'https': 'http://web-proxy.corp.hpecorp.net:8080',
    }

# inside your task when make rest calls use proxies.
with self.client.get(
            config.Paths.PROTECTION_JOBS, proxies=self.proxies, headers=self.headers, catch_response=True
        ) as response:
```


