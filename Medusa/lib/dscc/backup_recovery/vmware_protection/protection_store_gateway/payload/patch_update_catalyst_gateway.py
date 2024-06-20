from json import dumps


class PatchUpdateCatalystGateway:
    def __init__(
        self,
        datastoreId=None,
        methodDateTimeSet=None,
        timezone=None,
        utcDateTime=None,
        dns_networkAddress=None,
        ntp_networkAddress=None,
        username=None,
        password=None,
        networkAddress=None,
        port=None,
        proxy_address=None,
    ):
        self.datastoreId = datastoreId
        self.methodDateTimeSet = methodDateTimeSet
        self.timezone = timezone
        self.utcDateTime = utcDateTime
        self.dns_networkAddress = dns_networkAddress
        self.ntp_networkAddress = ntp_networkAddress
        self.username = username
        self.password = password
        self.networkAddress = networkAddress
        self.port = port
        self.proxy_address = proxy_address
        self.dateTime = False
        self.proxy = False
        self.payload = {}

    def update(self):
        if self.proxy_address is not None:
            self.payload.update({"proxy": {"networkAddress": self.proxy_address, "port": self.port}})
            self.proxy = True

        if self.datastoreId:
            self.payload.update({"datastores": [self.datastoreId]})

        if self.methodDateTimeSet:
            self.payload.update({"dateTime": {"methodDateTimeSet": self.methodDateTimeSet}})
            self.dateTime = True

        if self.timezone:
            if self.dateTime:
                self.payload["dateTime"].update({"timezone": self.timezone})
            else:
                self.payload.update({"dateTime": {"timezone": self.timezone}})
                self.dateTime = True

        if self.utcDateTime:
            if self.dateTime:
                self.payload["dateTime"].update({"utcDateTime": self.dateTime})
            else:
                self.payload.update({"dateTime": ({"utcDateTime": self.utcDateTime})})
                self.dateTime = True

        if self.dns_networkAddress:
            self.payload.update({"dns": [{"networkAddress": self.dns_networkAddress}]})

        if self.ntp_networkAddress:
            self.payload.update({"ntp": [{"networkAddress": self.ntp_networkAddress}]})

        if self.username:
            self.payload.update({"proxy": {"credentials": {"username": self.username}}})
            self.proxy = True

        if self.password:
            if self.proxy:
                self.payload["proxy"]["credentials"].update({"password": self.password})
            else:
                self.payload.update({"proxy": {"credentials": {"password": self.password}}})
                self.proxy = True

        if self.networkAddress:
            if self.proxy:
                self.payload["proxy"].update({"networkAddress": self.networkAddress})
            else:
                self.payload.update({"proxy": {"networkAddress": self.networkAddress}})
                self.proxy = True

        if self.port:
            if self.proxy:
                self.payload["proxy"].update({"port": self.port})
            else:
                self.payload.update({"proxy": {"port": self.port}})
                self.proxy = True

        return dumps(self.payload)
