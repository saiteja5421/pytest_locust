class PatchUpdateCatalystGatewayNetwork:
    payload = {}

    def __init__(
        self,
        nic_id=None,
        gateway=None,
        network_address=None,
        network_type=None,
        subnet_mask=None,
    ):
        self.id = nic_id
        self.gateway = gateway
        self.network_address = network_address
        self.network_type = network_type
        self.subnet_mask = subnet_mask
        self.nic = False

    def update(self):
        if self.id:
            self.payload.update({"id": self.id})

        if self.gateway:
            self.payload.update({"nic": {"gateway": self.gateway}})
            self.nic = True

        if self.network_address:
            if self.nic:
                self.payload["nic"].update({"networkAddress": self.network_address})
            else:
                self.payload.update({"nic": {"networkAddress": self.network_address}})
                self.nic = True
        if self.network_type:
            if self.nic:
                self.payload["nic"].update({"networkType": self.network_type})
            else:
                self.payload.update({"nic": {"networkType": self.network_type}})
                self.nic = True

        if self.subnet_mask:
            if self.nic:
                self.payload["nic"].update({"subnetMask": self.subnet_mask})
            else:
                self.payload.update({"nic": {"subnetMask": self.subnet_mask}})
                self.nic = True

        return self.payload
