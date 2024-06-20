from lib.dscc.data_panorama.inventory_manager.api.inventory_manager_api import InventoryManager
from lib.dscc.data_panorama.inventory_manager.models.inventory_manager import System, Array
from lib.dscc.data_panorama.consumption.models.volumes import VolumeActivity, ActivityTrendDetail, VolumesActivityTrend


def get_all_response_inventorysystem(func, limit=0, offset=0, **params):
    """
    Function to calculate and trigger multiple API/Array calls based on limit and offset where response will have list within list.
    Collected response will be unified into single dictionary and converted to corresponding Class object.
    Arguments:
        func        (R) - Variable to recieve array or API methods and reused
        limit: int  (O) - Limit =0, means retreive all the records. Value passed to limit, means retreive number of records equal to value passed.
        offset: int (O) - Default value of pageOffset is 0. Determines from which offset the data should be read from table.
        params:     (O) - set of query parameters required for func()

    """
    response_list = []
    items = []

    # Get total items using default api call
    result = func(**params)
    total = result.total
    dataclass_type = type(result)
    # dataclass_type = type(func(**params))
    if total != 0:
        if limit != 0:
            rem_items = limit
        else:
            rem_items = total

        # Decide number of function calls required to get the complete set of data keeping 1000 as the maximum value of limit/pagelimit
        while rem_items:
            if rem_items > 1000:
                limit = 1000
                rem_items = rem_items - limit
            elif rem_items < 10:
                limit = 10
                rem_items = 0
            else:
                limit = rem_items
                rem_items = rem_items - limit
            params["limit"] = limit
            params["offset"] = offset
            response_list.append(func(**params))
            offset += limit

    # Get list of parameters present as part of items dictionary
    # Get the variables of class VolumeActivity to build dictionary

    response_params = list(System.__dataclass_fields__keys())

    # Get the variables of class ActivityTrendDetail to build dictionary
    vars = list(Array.__dataclass_fields__keys())

    items = []
    for item in response_list:
        for val in item.items:
            temp_dict = {}
            for param in response_params:
                if param != "arrayInfo":
                    temp_dict[param] = val.__getattribute__(param)
                else:
                    activity_list = []
                    if val.__getattribute__(param) != None:
                        for iter in val.__getattribute__(param):
                            activity_dict = {}
                            for var in vars:
                                activity_dict[var] = iter.__getattribute__(var)
                            activity_list.append(activity_dict)
                    else:
                        activity_list = None
                    temp_dict[param] = activity_list
            items.append(temp_dict)

    # Compose dictionary by combining multiple response object
    response_dict = {"items": items, "pageLimit": 10, "pageOffset": 0, "total": total}

    # Convert the dictionary to object using models and return the object.
    # response_obj = type(response_list[0])(**response_dict)
    response_obj = dataclass_type(**response_dict)
    return response_obj


class InventoryManagerFunc(object):
    """
    Class related to Inventory Manager library functions.
    Functions present:
        get_systemids() - Function to get all the System IDs of a customer
        get_actual_arrayidlist_for_system() - Function to get arrayIDs for a system
        get_actual_system_location() - Function to get location details for a system
        get_actual_array_cost() - Function to get cost details for a array
    """

    def __init__(self, url: str, api_header: str) -> None:
        """
         __init__: Constructs all the necessary attributes for the InventoryManagerFunc object.

         -----------
         Parameters:
         -----------
             url :- url path eg: http://127.0.0.1:5002/api/v1
             type:- str
        -----------------
                     Arguments:
                     -----------------
         self.url :- Stores the user passed url
         self.inventorymanager = Object of InventoryManager class
        """

        self.url = url
        self.api_header = api_header
        self.inventorymanager = InventoryManager(self.url, self.api_header)

    def get_systemids(self) -> list:
        """
        Function to get all the System IDs of a customer
        Arguments: None
        Return argument: List of system IDs (list[system_id])
        """
        system_id = []
        inventory_manager = get_all_response_inventorysystem(self.inventorymanager.get_inventory_storage_systems)
        for item in inventory_manager.items:
            assert item.id != "", f"System ID is blank"
            system_id.append(item.id)
        return system_id

    def get_actual_arrayidlist_for_system(self, system_id: str) -> list:
        """
        Function to get arrayIDs for a system
        Arguments:
                system_id - system id to which arrays are associated
        Return argument:
                List of array IDs of a system (list[array_idlist])
        """
        array_idlist = []
        api_inventory_systems = get_all_response_inventorysystem(
            self.inventorymanager.get_inventory_storage_systems, arrayInfo=True
        )
        for item in api_inventory_systems.items:
            if item.id == system_id:
                for array_item in item.array:
                    array_idlist.append(array_item.id)
        return array_idlist

    def get_actual_system_location(self, system_id: str) -> dict:
        """
        Function to get location details for a system
        Arguments:
                system_id - system id for which location details are required
        Return argument:
                Dictionary of location details related to a system (dict{system_location})
        """
        system_location = {}
        vars = ["city", "postalCode", "state", "country"]
        api_inventory_systems = get_all_response_inventorysystem(self.inventorymanager.get_inventory_storage_systems)
        for item in api_inventory_systems.items:
            if item.id == system_id:
                for var in vars:
                    system_location[var] = item.__getattribute__(var)
        return system_location

    def get_actual_array_cost(self, system_id: str, array_id: str) -> dict:
        """
        Function to get cost details for a array
        Arguments:
                system_id - system id to which arrays are associated
                array_id - array id for which cost details are required
        Return argument:
                Dictionary of location details related to a system (dict{system_location})
        """
        array_cost = {}
        params = ["cost", "currency", "boughtAt", "monthsToDepreciate"]
        api_inventory_systems = get_all_response_inventorysystem(
            self.inventorymanager.get_inventory_storage_systems, arrayInfo=True
        )
        for item in api_inventory_systems.items:
            if item.id == system_id:
                for array_item in item.array:
                    if array_item.id == array_id:
                        for param in params:
                            array_cost[param] = array_item.__getattribute__(param)
        return array_cost
