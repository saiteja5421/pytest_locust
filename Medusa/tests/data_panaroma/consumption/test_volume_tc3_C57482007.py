# Standard libraries
import logging
from pathlib import Path
import pandas as pd


from pytest import fixture, mark

from tests.e2e.data_panorama.panorama_context import Context
from lib.dscc.data_panorama.consumption.api.volumes_api import VolumesInfo
from lib.dscc.data_panorama.consumption.models.volumes import VolumesConsumption
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser
from tests.steps.data_panorama.panaroma_common_steps import write_to_json


logger = logging.getLogger()


@fixture(scope="session")
def context():
    yield Context()
    # Test Clean up will be added later


# @mark.skip(reason="Blocked by cost design changes")
@mark.validated
@mark.order(1015)
def test_volume_tc3_C57482007(context: context):
    """
    The test case validates the customer is able to view volume consumption details between array and api calls.
    API validated is :

    curl --location 'http://CCS_DEV_URL/data-observability/v1alpha1/volumes-consumption' --header 'Authorization: Bearer TOKEN'


    Prerequisite: Data to be uploaded by data uploader service.
    """
    # Define data set for mock generator
    # To-Do: Function needs to be revisited, Need details of arguments to be passed

    aobj = ArrayConfigParser(context=context)
    # array_id_cost =[]
    # array_id_cost = get_arrayid_cost()
    array_obj = aobj.get_volume_consumption()
    write_to_json(
        df=pd.DataFrame([array_obj.to_dict()]),
        path=f"{aobj.steps_obj.json_path}/arr_{Path(__file__).stem}.json",
        sort_by="id",
    )
    
    """
    curl --location 'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/volumes-consumption' \
    --header 'Authorization: Bearer <token>'
    """
    volumes_info = VolumesInfo(context.cluster.panorama_url, context.api_header)
    api_obj = volumes_info.get_volumes_consumption()
    write_to_json(
        df=pd.DataFrame([api_obj.to_dict()]),
        path=f"{aobj.steps_obj.json_path}/api_{Path(__file__).stem}.json",
        sort_by="id",
    )

    # Validation of volume details from array and api calls matches
    # params = [param for param in dir(api_obj) if param not in dir(VolumesConsumption)]
    params = list(VolumesConsumption.__dataclass_fields__.keys())
    ignore_param = ["id", "resourceUri", "consoleUri", "name"]
    check_param = [element for element in params if element not in ignore_param]

    for param in check_param:
        if param in ["cost", "previousMonthCost", "currentMonthCost"]:
            assert int(api_obj.__getattribute__(param)) == int(
                array_obj.__getattribute__(param)
            ), f"Values not matching API: {api_obj.__getattribute__(param)} and Actual: {array_obj.__getattribute__(param)}"
        else:
            assert api_obj.__getattribute__(param) == array_obj.__getattribute__(
                param
            ), f"Values not matching API: {api_obj.__getattribute__(param)} and Actual: {array_obj.__getattribute__(param)}"
    logger.info("Test completed succesfully")
