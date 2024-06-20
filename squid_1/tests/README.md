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