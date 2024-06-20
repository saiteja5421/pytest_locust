import json
import logging
import random
import string
from lib.dscc.backup_recovery.vmware_protection.protection_store import get_psg_id_from_response
from tests.vmware.vmware_config import AwsStorageLocation
from lib.dscc.backup_recovery.vmware_protection import protection_store_gateway

logger = logging.getLogger(__name__)


def generate_protection_store_payload(psgw_name, type, cloud_region=AwsStorageLocation.AWS_US_WEST_1):
    """This will return payload either (cloud/on premises) of the protection store based on type.

    Args:
        psgw_name (string): to create local/cloud store under this psg.
        type (string): Type of protection store(ON_PREMISES,CLOUD).
        storageLocationId (string, optional): regions where you want to create schedules. Defaults to AwsStorageLocation.AWS_EU_WEST_1.

    Returns:
        str : return payload for creating local/cloud protection store

    """

    protection_store_name_suffix = "".join(random.choice(string.ascii_letters) for _ in range(3))
    protection_store_name = f"{psgw_name.split('#')[0]}_{protection_store_name_suffix}"
    psgw_response = protection_store_gateway.get_psg()
    psgw_id = get_psg_id_from_response(psgw_name, psgw_response)
    if type == "CLOUD":
        protection_store_payload = {
            "displayName": f"CLOUD_{protection_store_name}",
            "protectionStoreType": "CLOUD",
            "storageLocationId": cloud_region.value,
            "storageSystemId": psgw_id,
        }
    elif type == "ON_PREMISES":
        protection_store_payload = {
            "displayName": f"ON_PREMISES_{protection_store_name}",
            "protectionStoreType": "ON_PREMISES",
            "storageSystemId": psgw_id,
        }
    else:
        raise Exception("parameter(type) passed other than 'CLOUD'/'ON_PREMISES'")

    logger.info(f"Protection store creation payload: {protection_store_payload}")
    protection_store_payload = json.dumps(protection_store_payload, indent=4)
    return protection_store_payload
