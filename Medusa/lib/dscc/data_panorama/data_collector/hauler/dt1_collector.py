import json
import uuid
import pandas as pd

# import dt1_collection_tables as dt1coll
import common.restClient as restClient
import common.utils as utils
import multiprocessing as mp
import logging
from threading import Thread

# from tests.data_collector.common.restClient import get_paginated_response

yaml_config = utils.read_yaml()
cluster = yaml_config["ACCOUNT"]["Cluster"]
logger = logging.getLogger()

# Initialize empty lists/arrays for storing data
all_volumes = {}
all_snapshots = {}
all_applicationsets = {}
all_capacity_summary = []
all_volume_performace = []
all_volume_vluns = {}
dt1_collection = {}
dt1_eoc_collection = {}
dt1_arrays = {}
customerId = ""


logger.info("Getting jwt token")
jwt_token = utils.getBearerToken()
logger.info("Got jwt token")
headers = {"content-type": "application/json", "Authorization": f"{jwt_token}"}
baseurl = f"https://{cluster}/api/v1"

collectionStartTime = utils.getDatetimeInUTC()


def dt1_collect_array_data(mock_dir):
    # Retrieve volumes and snapshots for each array and volume
    dt1_sys_urls = f"{baseurl}/storage-systems/device-type1"
    dt1_all_arrays = get_dt1_arrays(dt1_sys_urls)
    for array in dt1_all_arrays:
        array_id = array["id"]

        # Retrieve volumes for current array
        dt1_vol_url = f"{dt1_sys_urls}/{array_id}/volumes"
        volumes = get_dt1_array_volumes(dt1_vol_url, array_id)

        # Retrieve capacity-summary for current array
        get_dt1_capacity_summary(dt1_sys_urls, array_id)

        # Retrieve Application-sets for current array
        get_dt1_application_sets(dt1_sys_urls, array_id)

        threads = []
        for volume in volumes:
            volume_id = volume["id"]

            # Create a new thread to perform GET operations on different endpoints for the volume in parallel
            t1 = Thread(
                target=get_dt1_snapshots,
                args=(
                    dt1_vol_url,
                    volume_id,
                ),
            )
            t2 = Thread(
                target=get_dt1_volume_performance_stats,
                args=(
                    dt1_vol_url,
                    volume_id,
                ),
            )
            t3 = Thread(
                target=get_dt1_vluns,
                args=(
                    dt1_vol_url,
                    volume_id,
                ),
            )

            # Add the threads to the list of threads
            threads.append(t1)
            threads.append(t2)
            threads.append(t3)
        # Start the threads to perform GET operations on different endpoints for each volume in parallel
        for t in threads:
            t.start()

        # Wait for all threads to finish
        for t in threads:
            t.join()

            # # Retrieve snapshots for each volume
            # get_dt1_snapshots(dt1_vol_url, volume_id)

            # # # Retrieve volume-performance for current volume
            # get_dt1_volume_performance_stats(dt1_vol_url, volume_id)

            # # # Retrieve vlun information for current volume
            # get_dt1_vluns(dt1_vol_url, volume_id)
    dt1_consolidate_response_json(mock_dir)


def get_dt1_vluns(dt1_vol_url, volume_id):
    logger.info(f"get the vluns for the volume - {volume_id}")
    dt1_vol_vlun_url = f"{dt1_vol_url}/{volume_id}/vluns"
    volumes_vlun_response = restClient.get(url=dt1_vol_vlun_url, headers=headers)
    vlun_summary = volumes_vlun_response.json()
    global all_volume_vluns
    if len(vlun_summary["items"]):
        all_volume_vluns[volume_id] = vlun_summary
    logger.info(f"got the vluns for the volume - {volume_id}")


def get_dt1_volume_performance_stats(dt1_vol_url, volume_id):
    logger.info(f"get perf stats for the volume - {volume_id}")
    dt1_vol_perf_url = f"{dt1_vol_url}/{volume_id}/performance-statistics"
    volumes_performance_response = restClient.get(url=dt1_vol_perf_url, headers=headers)
    volume_performace = volumes_performance_response.json()
    volume_performace["volumeId"] = volume_id
    global all_volume_performace
    all_volume_performace.append(volume_performace)
    logger.info(f"got the perf stats for the volume - {volume_id}")


def get_dt1_snapshots(dt1_vol_url, volume_id):
    logger.info(f"get volumeSnapshots for the volume - {volume_id}")
    dt1_snap_url = f"{dt1_vol_url}/{volume_id}/snapshots"
    snapshots = restClient.get_all_response(dt1_snap_url, headers, sort_by="creationTime")
    # snapshots_response = restClient.get(url=dt1_snap_url, headers=headers)
    # snapshots = snapshots_response.json()
    global all_snapshots
    # only volumes having snapshots are considered
    if len(snapshots):
        all_snapshots[volume_id] = snapshots
    logger.info(f"got the volumeSnapshots for the volume - {volume_id}")


def get_dt1_application_sets(dt1_sys_urls, array_id):
    logger.info(f"get the application sets for the array - {array_id}")
    dt1_applicationsets_url = f"{dt1_sys_urls}/{array_id}/applicationsets"
    applicationsets_response = restClient.get(url=dt1_applicationsets_url, headers=headers)
    applicationsets = applicationsets_response.json()
    global all_applicationsets
    all_applicationsets[array_id] = applicationsets["items"]
    logger.info(f"got the application sets for the array - {array_id}")


def get_dt1_capacity_summary(dt1_sys_urls, array_id):
    logger.info(f"get capacity summary for the array - {array_id}")
    dt1_cap_summary_url = f"{dt1_sys_urls}/{array_id}/capacity-summary"
    capacity_summary_response = restClient.get(url=dt1_cap_summary_url, headers=headers)
    capacity_summary = capacity_summary_response.json()
    global all_capacity_summary
    all_capacity_summary.append(capacity_summary)
    logger.info(f"got capacity summary for the array - {array_id}")


def get_dt1_array_volumes(dt1_vol_url, array_id):
    logger.info(f"get on all volumes for the array - {array_id}")
    # dt1_vol_url=f"{dt1_sys_urls}/{array_id}/volumes"
    volumes = restClient.get_all_response(dt1_vol_url, headers, sort_by="creationTime")

    # volumes_response = restClient.get(url=dt1_vol_url, headers=headers)
    # volumes = volumes_response.json()
    global all_volumes
    all_volumes[array_id] = volumes
    logger.info(f"got the volumes for the array - {array_id}")
    return volumes


def get_dt1_arrays(dt1_sys_urls):
    logger.info("Querying dt1 SS")

    dt1_systems = restClient.get(url=dt1_sys_urls, headers=headers)
    logger.info("got dt1 SS")
    global dt1_arrays
    dt1_arrays = dt1_systems.json().get("items")
    dt1_all_arrays = dt1_arrays
    global customerId
    if (len(dt1_all_arrays) != 0) and (customerId is not None):
        customerId = dt1_all_arrays[0]["customerId"]
    return dt1_all_arrays


def dt1_consolidate_response_json(out_path):
    dt1_collection["Version"] = "1.0"
    dt1_collection["PlatformCustomerID"] = customerId
    dt1_collection["CollectionID"] = collectionId
    dt1_collection["Region"] = awsRegion
    dt1_collection["ApplicationCustomerID"] = customerId
    dt1_collection["ApplicationInstanceID"] = customerId
    dt1_collection["CollectionTrigger"] = "Planned"
    dt1_collection["CollectionStartTime"] = collectionStartTime
    dt1_collection["CollectionEndTime"] = collectionEndTime
    dt1_collection["DeviceType"] = "deviceType1"
    dt1_collection["HaulerType"] = "Fleet"
    dt1_collection["CollectionType"] = "Inventory"
    dt1_collection["Systems"] = dt1_arrays
    dt1_collection["SystemCapacity"] = all_capacity_summary
    dt1_collection["Volumes"] = all_volumes
    dt1_collection["Snapshots"] = all_snapshots
    dt1_collection["Vluns"] = all_volume_vluns
    dt1_collection["VolumePerformance"] = all_volume_performace
    dt1_collection["Applicationsets"] = all_applicationsets

    # modify customerID as per ccs-dev
    # Note: this step not required for real array data
    # utils.replace_customer_id(dt1_collection, customerId)
    # Write consolidated dt1_json
    with open(f"{out_path}/dt1_collection-1.json", "w") as f:
        json.dump(dt1_collection, f)


def generate_dt1_eoc_collection():
    dt1_eoc_collection["collectionId"] = collectionId
    awsRegion = "us-west-2"
    dt1_eoc_collection["Version"] = "1.0"
    dt1_eoc_collection["PlatformCustomerID"] = customerId
    dt1_eoc_collection["CollectionID"] = collectionId
    dt1_eoc_collection["Region"] = awsRegion
    dt1_eoc_collection["ApplicationCustomerID"] = customerId
    dt1_eoc_collection["ApplicationInstanceID"] = customerId
    dt1_eoc_collection["CollectionTrigger"] = "Planned"
    dt1_eoc_collection["CollectionStartTime"] = collectionStartTime
    dt1_eoc_collection["CollectionEndTime"] = collectionEndTime
    dt1_eoc_collection["DeviceType"] = "deviceType1"
    dt1_eoc_collection["HaulerType"] = "Fleet"
    dt1_eoc_collection["CollectionType"] = "EOC"
    dt1_eoc_collection["DeviceTypeUploadStatus"] = {"deviceType1": "Success"}

    with open("dt1_eoc_collection-1.json", "w") as f:
        json.dump(dt1_eoc_collection, f)


# def dt1_create_collection_tables():
#     dt1coll.generate_dt1_system_table(dt1_arrays)
#     dt1coll.generate_dt1_capacity_summary_table(all_capacity_summary)
#     dt1coll.generate_dt1_applicationsets_table(all_applicationsets)
#     dt1coll.generate_dt1_volumes_table(all_volumes)
#     dt1coll.generate_dt1_snapshots_table(all_snapshots)
#     dt1coll.generate_dt1_vluns_table(all_volume_vluns)
#     dt1coll.generate_dt1_volume_performace_table(all_volume_performace)


# dt1_collect_array_data()
collectionEndTime = utils.getDatetimeInUTC()
collectionId = uuid.uuid4().hex[:32]
awsRegion = "us-west-2"
# dt1_consolidate_response_json()
# generate_dt1_eoc_collection()
# dt1_create_collection_tables()

# Create a new thread to perform GET operations on different endpoints for the volume in parallel
#     t1 = threading.Thread(target=get_dt1_snapshots, args=(dt1_vol_url,volume_id,))
#     t2 = threading.Thread(target=get_dt1_volume_performance_stats, args=(dt1_vol_url,volume_id,))
#     t3 = threading.Thread(target=get_dt1_vluns, args=(dt1_vol_url,volume_id,))

#     # Add the threads to the list of threads
#     threads.append(t1)
#     threads.append(t2)
#     threads.append(t3)
# # Start the threads to perform GET operations on different endpoints for each volume in parallel
# for t in threads:
#     t.start()

# # Wait for all threads to finish
# for t in threads:
#     t.join()
