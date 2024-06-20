"""
Test Case ID C57482018
Test Description - TC13:- To verify customer is able to view thick and thin provisioned volumes
"""

# Standard libraries
import logging
import time
from pytest import mark, fixture

# Steps
from lib.dscc.data_panorama.consumption.api.volumes_api import VolumesInfo
from tests.steps.data_panorama.consumption.wastage_steps import WastageVolumes
from lib.dscc.data_panorama.consumption.models.volumes import ActivityTrendDetail
from tests.steps.data_panorama.panaroma_common_steps import PanaromaCommonSteps
from tests.steps.data_panorama.consumption.array_consumption_steps import ArrayConfigParser

# Tests
from tests.e2e.data_panorama.panorama_context import Context

logger = logging.getLogger()
logging.getLogger("py4j").setLevel(logging.WARNING) #To remove unnecessary logs

@fixture(scope="session")
def context():
    test_context = Context()
    yield test_context


def vol_type(arr_spark, provisiontype):
    """
    Function to find the volume count based on provision type from the data generator.
    This is the expected data for later comparison.
    Argument: provisiontype - Receives the volume provision type "Thin/Thick"
    Return - Returns the volume count
    """
    volume_count: int = 0
    tc_vol_activity_trend_expected = arr_spark.get_volumes_activity_trend(provisionType=provisiontype)

    for record in tc_vol_activity_trend_expected.items:
        if record.provisionType == provisiontype.capitalize():
            volume_count += 1

    return volume_count


@mark.validated
@mark.order(1065)
def test_volume_tc13_C57482018(context: context):
    """
    Test Description:
        TC13 - To verify customer is able to view thick and thin provisioned volumes
    Test ID: C57482018
    curl cmd:
        curl --location 'http://pqa-backup-lb.pqaftc.hpe.com/data-observability/v1alpha1/volumes-activity-trend?filter=provisionType%20eq%20Thin' --header {TOKEN}
    """
    logger.info("Start of test case")
    logger.info("PQA Testing -> Consumption -> Volumes -> TC13_C57482018")

    arr_spark = ArrayConfigParser(context=context)

    # To get expected thin and thick volume count from data generator
    expected_thin_vol_count = vol_type(arr_spark, "Thin")
    print("array_thin=", expected_thin_vol_count, "\n")

    expected_thick_vol_count = vol_type(arr_spark, "Thick")
    print("array_thick=", expected_thick_vol_count, "\n")

    """
    Call the required library to get list of thin and thick volumes
    """
    volumes_activity = VolumesInfo(context.cluster.url, api_header=context.api_header)

    api_thinvolume_type = volumes_activity.get_volumes_activity_trend(filter = "provisionType eq Thin")
    api_thinvolume_count = api_thinvolume_type.total
    print("api_thin=", api_thinvolume_count)

    api_thickvolume_type = volumes_activity.get_volumes_activity_trend(filter = "provisionType eq Thick")
    api_thickvolume_count = api_thickvolume_type.total
    print("api_thick=", api_thickvolume_count)

    # Verification steps

    assert (
        expected_thin_vol_count == api_thinvolume_count
    ), "Expected count of thin provision volumes and count returned by API doesn't match"
    assert (
        expected_thick_vol_count == api_thickvolume_count
    ), "Expected count of thick provision volumes and count returned by API doesn't match"
    logger.info("Test Completed Successfully")
