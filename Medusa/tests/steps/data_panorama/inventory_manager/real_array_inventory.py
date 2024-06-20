import logging
import pandas as pd
import sqlalchemy

from lib.dscc.data_panorama.inventory_manager.api.inventory_manager_api import (
    InventoryManager,
)

logger = logging.getLogger()


def form_df(db_path):
    """This Method creates a Dataframe out of the Cost Table from the Aggregated DB.

    Args:
        context: The Context Object

    Returns:
        A Dataframe of the cost table.
    """
    db_name = db_path
    table_name = "Cost_last_collection"
    engine = sqlalchemy.create_engine("sqlite:///%s" % db_name, execution_options={"sqlite_raw_colnames": True})
    df = pd.read_sql_table(table_name, engine)
    return df


def verify_inventory_locations(context, url, api_header):
    """This method takes location info of the arrays from API and Dataframe and compares them

    Args:
        context (Context): The Context Object
        url (string): v1alpha1 atlaspoc url
        api_header: header needed to be passed alongwith the URL
    """
    api_inventory_manager_obj = InventoryManager(context, url, api_header)
    api_inventory_manager_summary = api_inventory_manager_obj.get_inventory_storage_systems()
    array_dataframe = form_df(context.real_data_db_path)
    locations = array_dataframe["location"].to_list()
    for do in api_inventory_manager_summary.items:
        current_array = array_dataframe.loc[array_dataframe["id"] == do.id]
        arr_array_id = "".join(current_array["id"].to_list())
        logger.info(f"Checking for Array ID {arr_array_id}")
        # checking for single entry per array. (Logically its not possible to have duplicates, but still, to be on the
        # safer side)
        assert current_array.shape[0] == 1, f"Either No or Duplicate entries in the Database for {do.name}"

        api_array_id = do.id
        assert (
            api_array_id == arr_array_id
        ), f"Array - {do.name} not found. DO Api Aray ID - {api_array_id}, Fleet Api Array ID - {arr_array_id}"
        city_name = do.city
        state_name = do.state
        pincode = do.postalCode
        country_name = do.country
        api_array_location = f"{city_name}, {state_name} {pincode}, {country_name}"
        arr_array_location = "".join(current_array["location"].to_list())
        arr_array_name = "".join(current_array["name"].to_list())
        logger.info(f"DO - Location for Array {do.name} from the DO API - {api_array_location}")
        logger.info(f"Fleet - Location for Array {arr_array_name} from the Fleet API - {arr_array_location}")
        assert (
            api_array_location == arr_array_location
        ), f"Location Details mismatch. DO - {api_array_location}, Fleet - {arr_array_location}"
        locations.remove(api_array_location)
    assert len(locations) == 0, "Duplicate/Additional data present in the Fleet API response."


def verify_inventory_system_summary(context, url, api_header):
    """This method gets system summary from API and Dataframe and compares them.

    Args:
        context (Context): The Context Object
        url (string): v1alpha1 atlaspoc url
        api_header: header needed to be passed alongwith the URL
    """
    api_inventory_manager_obj = InventoryManager(context, url, api_header)
    api_inventory_manager_system_summary = api_inventory_manager_obj.get_inventory_storage_systems_summary()
    array_dataframe = form_df(context.real_data_db_path)
    arr_array_current_asset_value = round(array_dataframe["CurrentAssetValue"].sum(), 2)
    api_array_current_asset_value = round(api_inventory_manager_system_summary.cost, 2)
    logger.info(f"Current Asset Value in DO - {api_array_current_asset_value}")
    logger.info(f"Current Asset Value in Fleet - {arr_array_current_asset_value}")
    assert (
        arr_array_current_asset_value == api_array_current_asset_value
    ), f"Current Asset value Mismatch. DO - {api_array_current_asset_value}, Fleet - {arr_array_current_asset_value}"

    arr_num_systems = array_dataframe["id"].size
    api_num_systems = api_inventory_manager_system_summary.numSystems
    logger.info(f"Number of Systems in DO - {api_num_systems}")
    logger.info(f"Number of Systems in Fleet - {arr_num_systems}")
    assert (
        arr_num_systems == api_num_systems
    ), f"Number of systems mismatch. DO - {api_num_systems}, FLeet - {arr_num_systems}"

    arr_total_size_in_bytes = array_dataframe["totalSizeInBytes"].astype("int").sum()
    api_total_size_in_bytes = api_inventory_manager_system_summary.totalSizeInBytes
    logger.info(f"Total Size in Bytes in DO - {api_total_size_in_bytes}")
    logger.info(f"Totoal Size in Bytes in Fleet - {arr_total_size_in_bytes}")
    assert (
        arr_total_size_in_bytes == api_total_size_in_bytes
    ), f"Total Size in Bytes Mismatch. DO - {api_total_size_in_bytes}, Fleet - {arr_total_size_in_bytes}"

    arr_utilized_size_in_bytes = array_dataframe["utilizedSizeInBytes"].astype("int").sum()
    api_utilized_size_in_bytes = api_inventory_manager_system_summary.utilizedSizeInBytes
    logger.info(f"Utilized size in Bytes in DO - {api_utilized_size_in_bytes}")
    logger.info(f"Utilized size in Bytes in Fleet - {arr_utilized_size_in_bytes}")
    assert (
        arr_utilized_size_in_bytes == api_utilized_size_in_bytes
    ), f"Utilized Size in Bytes Mismatch. DO - {api_utilized_size_in_bytes}, Fleet - {arr_utilized_size_in_bytes}"


def verify_inventory_consumption(context, url, api_header):
    """This method gets System Consumption from API and Array and compares them.

    Args:
        context (Context): The Context Object
        url (string): v1alpha1 atlaspoc url
        api_header: header needed to be passed alongwith the URL
    """
    api_inventory_manager_obj = InventoryManager(context, url, api_header)
    api_inventory_manager_system_summary = api_inventory_manager_obj.get_inventory_storage_systems()
    array_dataframe = form_df(context.real_data_db_path)
    for array in api_inventory_manager_system_summary.items:
        logger.info(f"Checking for Array ID - {array.id}")
        current_array = array_dataframe.loc[array_dataframe["id"] == array.id]
        arr_total_size_in_bytes = current_array["totalSizeInBytes"].to_list()
        logger.info(f"DO total size in Bytes - {array.totalSizeInBytes}")
        logger.info(f"Fleet total size in Bytes - {arr_total_size_in_bytes[0]}")
        assert int(array.totalSizeInBytes) == int(
            arr_total_size_in_bytes[0]
        ), f"Total Size in Bytes did not match for {array.name}. DO {array.totalSizeInBytes}, Fleet {arr_total_size_in_bytes[0]}"
        # DO - {array.totalSizeInBytes}, Fleet - {arr_total_size_in_bytes}
        arr_utilized_size_in_bytes = current_array["utilizedSizeInBytes"].to_list()
        logger.info(f"DO utilized size in Bytes - {array.utilizedSizeInBytes}")
        logger.info(f"Fleet utilized size in Bytes - {arr_utilized_size_in_bytes[0]}")
        logger.info(
            f"The difference between the Fleet Utilized Size and DO Utilized Size is {int(arr_utilized_size_in_bytes[0]) - array.utilizedSizeInBytes}"
        )
        assert int(array.utilizedSizeInBytes) == int(
            arr_utilized_size_in_bytes[0]
        ), f"Utilized Size in Bytes did not match for {array.name}. DO {array.utilizedSizeInBytes}, Fleet {arr_utilized_size_in_bytes[0]}"
        # DO - {array.utilizedSizeInBytes}, Fleet - {arr_utilized_size_in_bytes}

        api_percentage_consumed = round(((array.utilizedSizeInBytes / array.totalSizeInBytes) * 100), 2)
        arr_percentage_consumed = round(
            ((int(arr_utilized_size_in_bytes[0]) / int(arr_total_size_in_bytes[0])) * 100), 2
        )
        logger.info(f"DO Percentage Utilized (Rounded to 2 decimal places) - {api_percentage_consumed}%")
        logger.info(f"Fleet Percentage Utilized (Round to 2 decimal places) - {arr_percentage_consumed}%")
        assert (
            api_percentage_consumed == arr_percentage_consumed
        ), f"Percentage Consumptipon Mismatch. DO - {api_percentage_consumed}, Fleet - {arr_percentage_consumed}"
