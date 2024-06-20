import os
import pandas as pd
import sqlalchemy
import lib.dscc.data_panorama.data_collector.common.utils as utils
import lib.dscc.data_panorama.data_collector.common.restClient as restClinet

yaml_config = utils.read_yaml()
cluster = yaml_config["ACCOUNT"]["Cluster"]
# get JWT token
print("Getting jwt token")
jwt_token = utils.getBearerToken()
print("Got jwt token")

# set headers and URLs
headers = {"content-type": "application/json", "Authorization": f"{jwt_token}"}
baseurl = f"https://{cluster}/data-observability/v1alpha1/"
fleetbaseurl = f"https://{cluster}/api/v1/"
Inventory_storage_systems_url = f"{baseurl}inventory-storage-systems?array-info=true"

# get db connection
path_out = "lib/dscc/data_panorama/data_collector/out"
if os.path.exists(path_out) == False:
    os.mkdir(path_out)
db_path = f"{path_out}/aggregateddb.sqlite"
engine = sqlalchemy.create_engine("sqlite:///%s" % db_path, execution_options={"sqlite_raw_colnames": True})
conn = engine.connect()


# read db
def _get_table_data_from_db(table_name, conn):
    table_df = pd.read_sql_query(f"SELECT * from {table_name}", conn)
    return table_df


def _get_systems_info_from_db(storagesysid, table_name, conn):
    systems_df = _get_table_data_from_db(table_name, conn)
    filtered_df = systems_df[systems_df.storagesysid.isin([storagesysid])]
    # if filtered_df['devicetype'].iloc[0] == 'deviceType1':
    return (filtered_df["storagesysusablecapacity"].iloc[0], filtered_df["storagesystotalused"].iloc[0])


# get cis data from data orchestrator
def _get_cis_data_from_DO(Inventory_storage_systems_url, headers):
    response = restClinet.get(url=Inventory_storage_systems_url, headers=headers)
    inventory_storage_sys = response.json()
    return inventory_storage_sys


def _calculate_remaining_cost(row):
    if row["monthsToDepreciate"] == 0:
        return row["purchaseCost"]
    elif row["no_months_elapsed"] >= row["monthsToDepreciate"]:
        return 0
    else:
        return row["purchaseCost"] - row["elapsed_array_cost"]


def _cal_system_size(item, totalSysCapacity, usedSysCapacity):
    selected_fields = {"id", "name", "type", "purchaseCost"}
    array_df = {key: item[key] for key in item.keys() & selected_fields}

    # use values from fleet response
    array_df["totalSizeInBytes"] = totalSysCapacity
    array_df["utilizedSizeInBytes"] = usedSysCapacity

    # Calculate total_size_in_gib & tib
    array_df["totalSizeInGib"] = int(array_df["totalSizeInBytes"]) / (1024 * 1024 * 1024)
    array_df["totalSizeInTib"] = int(array_df["totalSizeInBytes"]) / (1024 * 1024 * 1024 * 1024)

    # Calculate total_size_in_gib & tib
    array_df["utilizedSizeInGib"] = int(array_df["utilizedSizeInBytes"]) / (1024 * 1024 * 1024)
    array_df["utilizedSizeInTib"] = int(array_df["utilizedSizeInBytes"]) / (1024 * 1024 * 1024 * 1024)
    return array_df


def _calculate_cost(array_df):
    if pd.api.types.is_string_dtype(array_df["boughtAt"]):
        array_df["boughtAt"] = pd.to_datetime(array_df["boughtAt"], utc=True)

    # Calculate the current date as a tz-aware Timestamp (UTC timezone)
    today = pd.Timestamp.utcnow()

    # Function to calculate the number of months between two dates
    def _calculate_months_between(bought_at):
        return (today.year - bought_at.year) * 12 + (today.month - bought_at.month)

    # Calculate the number of months between today and 'boughtAt' for each entry
    array_df["no_months_elapsed"] = array_df["boughtAt"].apply(_calculate_months_between) + 1

    # Calculate dep_per_month
    array_df["dep_per_month"] = array_df["purchaseCost"] / array_df["monthsToDepreciate"]

    # Calculate elapsed_array_cost
    mask = array_df["no_months_elapsed"] < array_df["monthsToDepreciate"]
    array_df["elapsed_array_cost"] = 0
    array_df.loc[mask, "elapsed_array_cost"] = array_df["no_months_elapsed"] * array_df["dep_per_month"]
    array_df["remaining_cost"] = array_df.apply(_calculate_remaining_cost, axis=1)
    array_df["per_gb_cost"] = array_df["dep_per_month"] / array_df["usable_capacity_bytes"] / (1024 * 1024 * 1024)
    return array_df


def getCISData():
    # fetchin DO invertory for CIS data
    inventory_storage_sys = _get_cis_data_from_DO(Inventory_storage_systems_url, headers)
    return inventory_storage_sys


def calc_cost_from_cis_array(inventory_storage_sys, engine=engine, conn=conn):
    systems_df = pd.DataFrame()
    for item in inventory_storage_sys["items"]:
        if item["arrayInfo"] is not None:
            # get system capacity from db collected from fleet
            totalSysCapacity, usedSysCapacity = _get_systems_info_from_db(item["id"], "system_last_collection", conn)

            nim_array_df = _cal_system_size(item, totalSysCapacity, usedSysCapacity)

            nim_df = pd.DataFrame(item["arrayInfo"])
            nim_df["usage"] = int(usedSysCapacity)
            nim_df["usable_capacity_bytes"] = int(totalSysCapacity)

            # calculate cost based on CIS and Fleet data
            nim_withCost_df = _calculate_cost(nim_df)

            nim_array_df["elapsedSystemCost"] = nim_withCost_df["elapsed_array_cost"].sum()
            nim_array_df["CurrentAssetValue"] = item["purchaseCost"] - nim_array_df["elapsedSystemCost"]
            nim_array_df["cost_per_gb"] = nim_withCost_df["dep_per_month"].sum() / nim_array_df["totalSizeInGib"]
            nim_array_df["noOfArrays"] = len(item["arrayInfo"])
            nim_array_df["location"] = f"{item['city']}, {item['state']} {item['postalCode']}, {item['country']}"
            systems_df = pd.concat([systems_df, pd.DataFrame(nim_array_df, index=[0])], ignore_index=True)

        else:
            totalSysCapacity, usedSysCapacity = _get_systems_info_from_db(item["id"], "system_last_collection", conn)
            selected_fields = {"id", "name", "type", "purchaseCost", "customerId"}
            primera_array_df = {key: item[key] for key in item.keys() & selected_fields}

            # using capacity from fleet response
            item["usable_capacity_bytes"] = int(totalSysCapacity)
            item["usage"] = int(usedSysCapacity)
            primera_array_df = _cal_system_size(item, totalSysCapacity, usedSysCapacity)

            pri_df = pd.DataFrame(item, index=[0])
            pri_withCost_df = _calculate_cost(pri_df)
            primera_array_df["elapsedSystemCost"] = pri_withCost_df["elapsed_array_cost"]
            primera_array_df["CurrentAssetValue"] = pri_withCost_df["remaining_cost"]
            primera_array_df["cost_per_gb"] = pri_withCost_df["per_gb_cost"]
            primera_array_df["noOfArrays"] = "N/A"
            primera_array_df["location"] = f"{item['city']}, {item['state']} {item['postalCode']}, {item['country']}"
            systems_df = pd.concat([systems_df, pd.DataFrame(primera_array_df, index=[0])], ignore_index=True)

    systems_df["consumption"] = round((systems_df["utilizedSizeInTib"] / systems_df["totalSizeInTib"]) * 100)

    systems_df.to_sql("Cost_last_collection", engine, if_exists="replace", index=False)


def getCISCostCalculationdata():
    inventory_storage_sys = getCISData()
    calc_cost_from_cis_array(inventory_storage_sys)


# getCISCostCalculationdata()
