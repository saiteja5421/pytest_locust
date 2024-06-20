import logging
import json

logger = logging.getLogger(__name__)

def generate_psg_payload(psgw_name, vcenter_id, host_id, network_name, network_ip, netmask, gateway, network_type, dns_ip, datastore_id):
    """generates psg payload

    Args:
        psgw_name (str): name of the psg
        vcenter_id (str): ID of vcenter on which psg needs to deploy
        host_id (str): host id of vcenter
        network_name (str): network name of vcenter
        network_ip (str): network address for psg
        netmask (str): subnet mask for psg
        gateway (str): gateway address
        network_type (str): network type example-'STATIC'
        dns_ip (str): dns address
        datastore_id (str): datastore id to deploy PSG.

    Returns:
        json: returns payload for create psg.
    """
    override_cpu = 0
    override_ram_gib = 0
    maxInCloudDailyProtectedDataInTiB = 1.0
    maxInCloudRetentionDays  = 1
    maxOnPremDailyProtectedDataInTiB = 1.0
    maxOnPremRetentionDays = 1
    override_storage_tib = 0
    payload = {
        "name": psgw_name,
        "hypervisorManagerId": vcenter_id,
        "vmConfig": {
        "hostId": host_id,
        "maxInCloudDailyProtectedDataInTiB": maxInCloudDailyProtectedDataInTiB,
        "maxInCloudRetentionDays": maxInCloudRetentionDays,
        "maxOnPremDailyProtectedDataInTiB": maxOnPremDailyProtectedDataInTiB,
        "maxOnPremRetentionDays": maxOnPremRetentionDays,
            "network": {
                "name": network_name,
                "networkAddress": network_ip,
                "subnetMask": netmask,
                "gateway": gateway,
                "networkType": network_type,
                "dns": [
                    {
                        "networkAddress": dns_ip
                    }
                ]
            },
            "override": {
                "cpu": override_cpu,
                "ramInGiB": override_ram_gib,
                "storageInTiB": override_storage_tib
            },
            "datastoreIds": [
                datastore_id
            ]
        }
    }
    psg_payload = json.dumps(payload, indent=4)
    return psg_payload

def generate_payload_for_nic_creation( nic_ip, network_name, network_type, subnet, gateway=""):
    """" return payload to create nic

    Args:
        nic_ip (str): network_address to create nic
        network_name (str): network_name 
        network_type (str): network type example-'STATIC'
        subnet (str): subnet mask for Data1
        gateway (str, optional): gateway address. Defaults to "".

    Returns:
        json: return payload to create nic
    """
    payload = {
        "nic": {
            "networkAddress": nic_ip,
            "networkName": network_name,
            "networkType": network_type,
            "subnetMask": subnet,
            "gateway": gateway
            }
    }
    
    create_nic_payload = json.dumps(payload, indent=4)
    return create_nic_payload



