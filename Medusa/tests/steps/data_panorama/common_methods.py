import pandas as pd
import sqlalchemy
from enum import Enum


class PathType(Enum):
    volumes = "volumes"
    app_lineage = "app_lineage"


def get_path_params(db_name: str, table: str, params: list, num_of_records: int = 1) -> dict:
    """
    Method used to get random path parameters required for API calls. This method can be called directly by passing db_name, table_name and params required.
    In case of default values required for API calls use get_path_params_by_type()
    Args:
        db_name (str): use complete path(ex: /workspaces/panorama_mock_uploader/mock_tool/mock_db_2023-04-20_05-52-04.sqlite)
        table (str): name of the table from where data has to be picked
        params (list): list of parameters for which we need value

    Sample code to be used in test case:
      db_name = "/workspaces/panorama_mock_uploader/mock_tool/mock_db_2023-04-20_05-52-04.sqlite"
      table = "spark_volumes"
      params = ['volumeId', 'arrid', 'creationTime']
      params_dict = get_path_params(db_name, table, params)

    Returns:
        params_dict (dict): {'volumeId': '7c17dddef36f49f9813e82cc570e5846', 'arrid': 'd7b39cc9712e45f186093551bc6f6a9e'}
    """
    engine = sqlalchemy.create_engine("sqlite:///%s" % db_name, execution_options={"sqlite_raw_colnames": True})
    conn = engine.connect()
    df = pd.read_sql_table(table, con=conn)
    row = df[params].sample(n=num_of_records).to_dict("records")
    params_dict = row[0]
    return params_dict if num_of_records == 1 else row


def get_path_params_by_type(db_name: str, type: str, num_of_records: int = 1) -> dict:
    """Method used to get random path parameters required for API calls

    Args:
        db_name (str): use complete path(ex: /workspaces/panorama_mock_uploader/mock_tool/mock_db_2023-04-20_05-52-04.sqlite)
        type (str): volumes / app_lineage

    Returns:
        params_dict (dict): {'volumeId': '7c17dddef36f49f9813e82cc570e5846', 'arrid': 'd7b39cc9712e45f186093551bc6f6a9e'}
    """
    dict = {
        "volumes": {
            "table": "spark_vol_lastcollection",
            "params": ["volumeId", "storagesysid"],
        },
        "clones": {
            "table": "spark_clone_lastcollection",
            "params": ["cloneid", "system_id"],
        },
        "app_lineage": {
            "table": "spark_app_lastcollection",
            "params": ["volid", "storagesysid"],
        },
        "inventory": {"table": "spark_sys_lastcollection", "params": ["storagesysid"]},
        "volumesallcollections": {
            "table": "spark_vol_all_collection",
            "params": ["avgiops"],
        },
    }
    params_dict = get_path_params(
        db_name=db_name, table=dict[type]["table"], params=dict[type]["params"], num_of_records=num_of_records
    )
    return params_dict
