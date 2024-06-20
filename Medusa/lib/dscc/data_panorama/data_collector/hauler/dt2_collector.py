import json
import logging
import uuid
import pandas as pd

# import dt2_collection_tables as dt2coll
import common.restClient as restClinet
import common.utils as utils
from threading import Thread

yaml_config = utils.read_yaml()
cluster = yaml_config["ACCOUNT"]["Cluster"]

logger = logging.getLogger()

logger.info("Getting jwt token")
jwt_token = utils.getBearerToken()
logger.info("Got jwt token")
headers = {"content-type": "application/json", "Authorization": f"{jwt_token}"}
baseurl = f"https://{cluster}/api/v1"

# Initialize empty lists/arrays for storing data
all_volumes = {}
all_snapshots = {}
all_volume_collections = {}
all_storagepools = {}
all_volume_performace = []
all_volume_vluns = {}
dt2_collection = {}
dt2_arrays = {}
customerId = ""

collectionStartTime = utils.getDatetimeInUTC()


def dt2_collect_array_data(mock_dir):
    # Retrieve volumes and snapshots for each array and volume
    dt2_sys_urls, dt2_arrays = get_dt2_systems()
    # dt2coll.generate_dt2_system_table(dt2_arrays)
    for array in dt2_arrays:
        array_id = array["id"]

        # Retrieve volumes for current array
        dt2_vol_url, volumes = get_dt2_array_volumes(dt2_sys_urls, array_id)

        # Retrieve storagePools for current array
        get_dt2_storagePools(dt2_sys_urls, array_id)

        # Retrieve volume-collections for current array
        get_dt2_volumeCollections(dt2_sys_urls, array_id)

        # Retrieve snapshots for each volume
        threads = []
        for volume in volumes["items"]:
            volume_id = volume["id"]
            logger.info(f"getting volume snapshot details for volume ID - {volume_id}")
            t1 = Thread(
                target=get_dt2_snapshots,
                args=(
                    dt2_vol_url,
                    volume_id,
                ),
            )
            t2 = Thread(
                target=get_dt2_volume_performance_stats,
                args=(
                    dt2_vol_url,
                    volume_id,
                ),
            )

            # Add the threads to the list of threads
            threads.append(t1)
            threads.append(t2)

        # Start the threads to perform GET operations on different endpoints for each volume in parallel
        for t in threads:
            t.start()

        # Wait for all threads to finish
        for t in threads:
            t.join()

            # get_dt2_snapshots(dt2_vol_url, volume_id)

            # # Retrieve volume-performance for current volume
            # get_dt2_volume_performance_stats(dt2_vol_url, volume_id)
    dt2_consolidate_response_json(mock_dir)


def get_dt2_volume_performance_stats(dt2_vol_url, volume_id):
    logger.info(f"get perf stats for the volume - {volume_id}")
    dt2_vol_perf_url = f"{dt2_vol_url}/{volume_id}/performance-statistics"
    volumes_performance_response = restClinet.get(dt2_vol_perf_url, headers=headers)
    volume_performace = volumes_performance_response.json()
    volume_performace["volumeId"] = volume_id
    global all_volume_performace
    all_volume_performace.append(volume_performace)
    logger.info(f"got the perf stats for the volume - {volume_id}")


def get_dt2_snapshots(dt2_vol_url, volume_id):
    logger.info(f"get volumeSnapshots for the volume - {volume_id}")
    dt2_snap_url = f"{dt2_vol_url}/{volume_id}/snapshots"
    all_data = restClinet.get_all_response(dt2_snap_url, headers, sort_by="id")
    logger.info(f"got the volumeSnapshots for the volume - {volume_id}")
    global all_snapshots
    if all_data:
        all_snapshots[volume_id] = all_data


def get_dt2_volumeCollections(dt2_sys_urls, array_id):
    logger.info(f"get the volume-collections for the array - {array_id}")
    dt2_volume_collections_url = f"{dt2_sys_urls}/{array_id}/volume-collections"
    volume_collections_response = restClinet.get(dt2_volume_collections_url, headers=headers)
    volume_collections = volume_collections_response.json()
    global all_volume_collections
    all_volume_collections[array_id] = volume_collections["items"]
    logger.info(f"got the volume-collections for the array - {array_id}")


def get_dt2_storagePools(dt2_sys_urls, array_id):
    logger.info(f"get storagepools for the array - {array_id}")
    dt2_storagepool_url = f"{dt2_sys_urls}/{array_id}/storage-pools"
    storagepool_response = restClinet.get(dt2_storagepool_url, headers=headers)
    storagepools = storagepool_response.json()
    global all_storagepools
    all_storagepools[array_id] = storagepools["items"]
    logger.info(f"got storagepools for the array - {array_id}")


def get_dt2_array_volumes(dt2_sys_urls, array_id):
    logger.info(f"get on all volumes for the array - {array_id}")
    dt2_vol_url = f"{dt2_sys_urls}/{array_id}/volumes"
    volumes_response = restClinet.get(dt2_vol_url, headers=headers)
    volumes = volumes_response.json()
    global all_volumes
    all_volumes[array_id] = volumes["items"]
    logger.info(f"got the volumes for the array - {array_id}")
    return dt2_vol_url, volumes


def get_dt2_systems():
    logger.info("Querying dt2 SS")
    dt2_sys_urls = f"{baseurl}/storage-systems/device-type2"
    dt2_systems = restClinet.get(dt2_sys_urls, headers=headers)
    logger.info("got dt2 SS")
    global dt2_arrays, customerId
    dt2_arrays = dt2_systems.json().get("items")
    if (len(dt2_arrays) != 0) and (customerId is not None):
        customerId = dt2_arrays[0]["customerId"]
    return dt2_sys_urls, dt2_arrays


def dt2_consolidate_response_json(out_path):
    dt2_collection["Version"] = "1.0"
    dt2_collection["PlatformCustomerID"] = customerId
    dt2_collection["CollectionID"] = collectionId
    dt2_collection["Region"] = awsRegion
    dt2_collection["ApplicationCustomerID"] = customerId
    dt2_collection["ApplicationInstanceID"] = customerId
    dt2_collection["CollectionTrigger"] = "Planned"
    dt2_collection["CollectionStartTime"] = collectionStartTime
    dt2_collection["CollectionEndTime"] = collectionEndTime
    dt2_collection["DeviceType"] = "deviceType2"
    dt2_collection["HaulerType"] = "Fleet"
    dt2_collection["CollectionType"] = "Inventory"
    dt2_collection["Systems"] = dt2_arrays
    dt2_collection["StoragePools"] = all_storagepools
    dt2_collection["Volumes"] = all_volumes
    dt2_collection["Snapshots"] = all_snapshots
    dt2_collection["VolumePerformance"] = all_volume_performace
    dt2_collection["VolumeCollections"] = all_volume_collections

    # Write consolidated dt2_json
    # utils.replace_customer_id(dt2_collection, customerId)

    with open(f"{out_path}/dt2_collection-1.json", "w") as f:
        json.dump(dt2_collection, f)


# def dt2_create_collection_tables():
#     dt2coll.generate_dt2_system_table(dt2_arrays)
#     dt2coll.generate_dt2_storagepools_table(all_storagepools)
#     dt2coll.generate_dt2_volumecollections_table(all_volume_collections)
#     dt2coll.generate_dt2_volumes_table(all_volumes)
#     dt2coll.generate_dt2_snapshots_table(all_snapshots)
#     dt2coll.generate_dt2_volume_performace_table(all_volume_performace)


# dt2_collect_array_data()
collectionEndTime = utils.getDatetimeInUTC()
collectionId = uuid.uuid4().hex[:32]
awsRegion = "us-west-2"
# dt2_consolidate_response_json()
# dt2_create_collection_tables()
