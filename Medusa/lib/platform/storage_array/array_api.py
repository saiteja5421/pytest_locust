import logging
from json import dumps
from requests import codes
from lib.common.common import get, post


class ArrayApi:
    def __init__(self, array_address, username, password, vcenter_address=""):
        """
        vcenter_address: ex. vcsa70-027.vlab.nimblestorage.com -> optional, its needed to call HPE plugin api
        array_address: ex. cxo-array29.lab.nimblestorage.com
        username: array username
        password: array password
        """
        self.logger = logging.getLogger()
        self.array_api = f"https://{array_address}"
        self.port = "5392"
        self.username = username
        self.password = password
        self.api_session = "api/vsphere/v1/vsphere_sessions"
        self.api_gmd_token = "api/GmdProxy/v1/tokens"
        self.api_datastore = "api/vsphere/v1/datastores"
        self.api_add_vcenter = "rest/appserver/create"
        self.api_add_web = "rest/vcenterregisterextension/web"
        self.api_add_vasa = "rest/vcenterregisterextension/vasa"
        self.api_hosts = "api/vsphere/v1/hosts"
        self.api_pools = "v1/pools"
        self.api_group = "v1/groups/detail?fields=name%2Caccess_protocol_list"
        self.headers = {"Content-Type": "application/json", "Host": array_address}
        self.array_gmd_token = self.get_gmd_token()
        if vcenter_address:
            self.set_vcenter(vcenter_address)

    def set_vcenter(self, vcenter_address):
        self.vcenter = vcenter_address
        self.vcenter_sdk = f"https://{vcenter_address}/sdk"
        self.session_id = self.generate_session_token()

    def get_gmd_token(self):
        token_id: str = ""
        payload = {"data": {"username": "admin", "password": "admin"}}
        response = post(
            self.array_api,
            self.api_gmd_token,
            json_data=dumps(payload),
            headers=self.headers,
        )
        assert response.status_code == codes.created, "Array Gmd token id generation failed"
        token_id = response.json()["data"]["session_token"]
        self.headers["X-Auth-Token"] = token_id
        self.logger.info("Array Gmd token id generated")
        return token_id

    def generate_session_token(self):
        session_id: str = ""
        payload = {
            "hostname": self.vcenter,
            "username": self.username,
            "password": self.password,
        }
        response = post(
            self.array_api,
            self.api_session,
            json_data=dumps(payload),
            headers=self.headers,
        )
        assert response.status_code == codes.ok, "Array session id generation failed"
        session_id = response.json()["data"]["session"].split(";").pop(0)
        self.logger.info("Array session id generated")
        return session_id

    def get_datastore(self, datastore_id):
        params = {
            "vCenterUrl": self.vcenter_sdk,
            "vCenterSessionId": self.session_id,
            "datastore_type": "VMFS",
        }
        path = f"{self.api_datastore}/Datastore:{datastore_id}"
        return get(self.array_api, path, params=params, headers=self.headers)

    def register_vcenter(self, vcenter):
        payload = {
            "hostname": vcenter,
            "name": vcenter,
            "password": self.password,
            "port": "443",
            "username": self.username,
            "subnetlabel": "mgmt-data",
            "serverid": None,
        }
        response = post(
            self.array_api,
            self.api_add_vcenter,
            json_data=dumps(payload),
            headers=self.headers,
        )
        if "already exists" in response.text:
            self.logger.info(f"Vcenter {vcenter} already exists")
            return
        assert response.status_code == codes.ok, f"vCenter {vcenter} not added to array response {response.text}"
        server_id = response.json()["serverId"]
        assert server_id, "Server id not found"
        self.logger.info(f"Vcenter {vcenter} added to array")
        return server_id

    def get_datastore_usage(self, datastore_id):
        """Get compressed datastore usage"""
        datastore_usage = 0
        datastore = self.get_datastore(datastore_id)
        assert datastore.status_code == codes.ok, f"Get datastore {datastore_id} usage failed"
        datastore_usage = datastore.json()["data"]["vol_usage_mapped"]
        self.logger.info(f"Datastore {datastore_id} usage:{datastore_usage}")
        return int(datastore_usage)

    def array_integrate_vcenters(self, vcenters):
        """Intagrate vcenter list with array. It will create array group"""
        for vcenter in vcenters:
            server_id = self.register_vcenter(vcenter)
            if server_id:
                self.register_web_extension(server_id)
                self.register_vasa_extension(server_id)

    def register_web_extension(self, server_id):
        payload = {"serverid": server_id}
        response = post(
            self.array_api,
            self.api_add_web,
            json_data=dumps(payload),
            headers=self.headers,
        )
        assert response.status_code == codes.ok, "Web extesnion not added"
        self.logger.info("Web extension added")

    def register_vasa_extension(self, server_id):
        payload = {"serverid": server_id}
        response = post(
            self.array_api,
            self.api_add_vasa,
            json_data=dumps(payload),
            headers=self.headers,
        )
        assert response.status_code == codes.ok, "Vasa extesnion not added"
        self.logger.info("Vasa extension added")

    def get_datacenter_hosts(self):
        params = {"vCenterUrl": self.vcenter_sdk, "vCenterSessionId": self.session_id}
        response_hosts = get(self.array_api, self.api_hosts, params=params, headers=self.headers)
        hosts = []
        for host in response_hosts.json()["data"]:
            name = host["id"]
            response = get(
                self.array_api,
                f"{self.api_hosts}/{name}",
                params=params,
                headers=self.headers,
            )
            host_system = {"name": name, "version": response.json()["data"]["version"]}
            hosts.append(host_system)
        self.logger.info(f"Hosts: {hosts}")
        return hosts

    def get_datacenter_pool(self):
        response = get(f"{self.array_api}:{self.port}", self.api_pools, headers=self.headers)
        assert response.status_code == codes.ok, "Datacenter pool not found"
        pool_id = response.json()["data"][0]["id"]
        assert pool_id, "Pool id not found"
        self.logger.info(f"Pool id found: {pool_id}")
        return pool_id

    def get_array_protocol(self):
        response = get(f"{self.array_api}:{self.port}", self.api_group, headers=self.headers)
        assert response.status_code == codes.ok, "Datacenter group not found"
        protocols = response.json()["data"][0]["access_protocol_list"]
        if "iscsi" in protocols:
            protocol = "iscsi"
        else:
            protocol = response.json()["data"][0]["access_protocol_list"][0]
        assert protocol, "Protocol not found"
        self.logger.info(f"Protocol found: {protocol}")
        return protocol

    def create_datastore(self, name, size, dedupe, hosts, pool_id, protocol):
        host_systems = []
        for host in hosts:
            host_system = {"moref": host["name"], "version": host["version"]}
            host_systems.append(host_system)

        payload = {
            "name": name,
            "type": "VMFS",
            "thinly_provisioned": True,
            "size": size,
            "protection_type": "NONE",
            "limit": 100,
            "volume_collection_app_sync_type": "none",
            "vmfs_block_size_mb": 1,
            "vmfs_version": 6,
            "performance_policy_id": "031b24a221ee5d0b63000000000000000000000014",
            "performance_policy_name": "VMware ESX 5",
            "pool_id": pool_id,
            "pool_name": "default",
            "use_chap": False,
            "protocol": protocol,
            "accessible": False,
            "request_initiator_per_ip": False,
            "dedupe_enabled": dedupe,
            "dedupe_override": False,
            "use_group_scope_target": True,
            "limit_iops": -1,
            "limit_iops_unlimited": True,
            "limit_mbps": -1,
            "limit_mbps_unlimited": True,
            "extended": False,
            "has_offline_volume": False,
            "has_demoted_volume": False,
            "has_deduped_blocks": False,
            "host_systems": host_systems,
            "protection_schedules": [
                {
                    "name": "Schedule-new",
                    "period": 1,
                    "period_unit": "hours",
                    "at_time": 28800,
                    "until_time": 72000,
                    "days": "monday,tuesday,wednesday,thursday,friday,saturday,sunday",
                    "num_retain": 48,
                    "disable_appsync": True,
                    "replicate_every": 0,
                    "num_retain_replica": 0,
                    "repl_alert_thres": 0,
                }
            ],
        }
        params = {"vCenterUrl": self.vcenter_sdk, "vCenterSessionId": self.session_id}
        response = post(
            self.array_api,
            self.api_datastore,
            params=params,
            json_data=dumps(payload),
            headers=self.headers,
        )
        assert response.status_code == codes.accepted, f"FAILED - Create datastore - {response.text}"
        self.logger.info("Create datastore in progress")
        task_id = response.json()["data"]["value"]
        return task_id
