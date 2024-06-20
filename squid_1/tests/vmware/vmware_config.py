from enum import Enum


class Paths:
    version1 = "v1"
    version1_beta1 = "v1beta1"
    version1_alpha1 = "v1alpha1"
    backup_recovery = "backup-recovery"
    hybrid_cloud = "hybrid-cloud"
    vcenter = f"/{hybrid_cloud}/{version1_beta1}/hypervisor-managers"
    datastores = f"/{hybrid_cloud}/{version1_beta1}/datastores"
    hypervisors = "hosts"
    hypervisor_hosts = f"/{hybrid_cloud}/{version1_beta1}/hypervisor-hosts"
    hypervisor_cluster = "hypervisor-clusters"
    protection_policies = f"/{backup_recovery}/{version1_beta1}/protection-policies"
    protection_jobs = f"/{backup_recovery}/{version1_beta1}/protection-jobs"
    virtual_machines = f"/{hybrid_cloud}/{version1_beta1}/virtual-machines"
    virtual_machines_backups = f"/{backup_recovery}/{version1_beta1}/virtual-machines"
    networks = "networks"
    ope = "data-orchestrators"
    protection_stores = f"/{backup_recovery}/{version1_beta1}/protection-stores"
    protection_store_gateways = f"/{backup_recovery}/{version1_beta1}/protection-store-gateways"
    protection_store_gateway_sizer = f"/{backup_recovery}/{version1_beta1}/protection-store-gateway-sizer"
    TASK_API = "/data-services/v1beta1/async-operations"


class ConfigPaths:
    CONFIG_FILE_PATH = "/workspaces/Squid/s1_vmware_config.yml"
    LOCUST_CONF_PATH = "/workspaces/Squid/tests/s1_locust.conf"


class VcenterDetails:
    vcenter_name = "vcsa67-124.vlab.nimblestorage.com"
    hypervisor_host_name = "c3-nimdl325g10-036.lab.nimblestorage.com"
    datastore_name = "Manual-psg-124"
    network_name = "VM Network"
    netmask = "255.255.0.0"
    gateway = "172.21.0.1"
    network_type = "STATIC"
    dns_ip = "10.157.24.201"


class AWSRegions:
    AWS_US_EAST_1 = "USA, North Virginia"
    AWS_US_EAST_2 = "USA, Ohio"
    AWS_US_WEST_1 = "USA, North California"
    AWS_US_WEST_2 = "USA, Oregon"
    AWS_CA_CENTRAL_1 = "Canada, Quebec"
    AWS_EU_CENTRAL_1 = "Germany, Frankfurt"
    AWS_EU_WEST_1 = "Ireland, Dublin"
    AWS_EU_WEST_2 = "United Kingdom, London"
    AWS_EU_WEST_3 = "France, Paris"
    AWS_EU_NORTH_1 = "Sweden, Stockholm"
    AWS_AP_NORTHEAST_1 = "Japan, Tokyo"
    AWS_AP_NORTHEAST_2 = "South Korea, Seoul"
    AWS_AP_NORTHEAST_3 = "Japan, Osaka"
    AWS_AP_SOUTHEAST_1 = "Singapore"
    AWS_AP_SOUTHEAST_2 = "Australia, Sydney"
    AWS_AP_SOUTH_1 = "India, Mumbai"
    any = "any"


class AwsStorageLocation(Enum):
    AWS_US_EAST_1 = "aws:us-east-1"
    AWS_US_EAST_2 = "aws:us-east-2"
    AWS_US_WEST_1 = "aws:us-west-1"
