"""
    TestRail ID:   	C57582331
    Deploy PSG to  content library

    TestRail ID: C57582335
    Deploy PSG with cluster id

    TestRail ID:   C57582334
    Deploy PSG with resource-pool

    TestRail ID:  C57582333
    Deploy PSG on folder

    TestRail ID:C57582336
    Deploy PSG with all options

    TestRail ID:C57582337
    Deploy PSG with invalid details

    TestRail ID: C57642255
    Deploy PSG with smaller vCPU and memory and perform backup and restore

    TestRail ID - C57597030	Create Cloud Protection store with valid GLCP location/region,
    but not registered with GLBR (e.g. Jakarta)

    TestRail ID - C57597032	Create Cloud store and provide location_id with Invalid characters
    and numeric and special characters

    TestRail ID - C57597029	Create Protection store with out providing region and location_id then check for the error message

"""

from pytest import fixture, mark
import logging
from lib.common.enums.azure_locations import AzureLocations
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    delete_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    validate_protection_store_gateway_vm_ok_state_and_station_id,
    validate_psgw_error_messages,
    verify_the_PSG_deployment_info_after_successfully_deployment,
)
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.protection_template_steps import (
    create_protection_template,
    assign_protection_template_to_vm,
    verify_cloud_protection_store_error,
)
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.models.error import Error
from requests import codes
from lib.common.enums.aws_regions import AwsStorageLocation
from tests.steps.vm_protection.backup_steps import (
    run_backup,
    restore_virtual_machine,
)
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from lib.common.error_messages import (
    ERROR_MESSAGE_CREATE_CLOUD_STORAGE_LOCATION_ID,
    ERROR_MESSAGE_CREATE_CLOUD_STORAGE_LOCATION_ID_AS_EMPTY,
    ERROR_MESSAGE_DEPLOY_PSG_ALL_HOSTID_CLUSTERID_RESOURCEPOOLID,
    ERROR_MESSAGE_DEPLOY_PSG_WITH_INVALD_CLUSTER_ID,
    ERROR_MESSAGE_DEPLOY_PSG_WITH_INVALD_CONTENT_LIB_DATASTORE_ID,
    ERROR_MESSAGE_DEPLOY_PSG_WITH_INVALD_FOLDER_ID,
    ERROR_MESSAGE_DEPLOY_PSG_WITH_INVALD_RESOURCE_POOL_ID,
)
from lib.common.enums.restore_type import RestoreType

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context(v_center_type="VCENTER1")
    yield test_context
    logger.info(f"\n{'Teardown Start'.center(40, '*')}")
    perform_cleanup(test_context, clean_vm=True)
    logger.info(f"\n{'Teardown Complete'.center(40, '*')}")


@mark.order(1800)
@mark.deploy
def test_deploy_psgw_with_minimum_size_and_ova_on_content_lib_ds(context, vm_deploy):
    """TestRail ID:   	C57582331
    Deploy PSG to  content library

    TestRail ID: C57642255
    Deploy PSG with smaller vCPU and memory and perform backup and restore
    """
    create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=1.0,
        max_cld_rtn_days=1,
        max_onprem_dly_prtctd_data=1.0,
        max_onprem_rtn_days=1,
        deploy_ova_on_content_lib_ds=True,
        add_data_interface=False,
    )
    validate_protection_store_gateway_vm(context)
    # Expected sizer fields for minimum sized psgw
    exp_sizer_fields = {
        "vCpu": 2,
        "ramInGiB": 16.0,
        "storageInTiB": 1,
    }
    verify_the_PSG_deployment_info_after_successfully_deployment(
        context,
        exp_sizer_fields,
        deploy_ova_on_content_lib_ds=True,
        verify_size=True,
    )
    validate_protection_store_gateway_vm_ok_state_and_station_id(context)
    create_protection_template(context, cloud_region=AzureLocations.AZURE_southafricanorth)
    assign_protection_template_to_vm(context)
    logger.info("Validating backup and restore with minimum sized PSGW. 2 vCPUs and 16Gib ram.")
    run_backup(context, backup_type=BackupTypeScheduleIDs.cloud)
    logger.info("Restorting VM from cloud backups")
    restore_virtual_machine(context, RestoreType.new, "cloud")
    logger.info("Restorting VM from cloud backups succeeded")
    logger.info(f"Run backup and restore successfully verified with smaller size. 2 vCPUs and 16Gib ram.")


@mark.order(1805)
@mark.deploy
def test_deploy_psgw_with_cluster_id(context):
    """TestRail ID: C57582335
    Deploy PSG with cluster id
    """
    create_protection_store_gateway_vm(
        context,
        deploy_with_cluster_id=True,
        add_data_interface=False,
    )
    validate_protection_store_gateway_vm(context)
    verify_the_PSG_deployment_info_after_successfully_deployment(
        context,
        deploy_with_cluster_id=True,
    )
    delete_protection_store_gateway_vm(context)


@mark.order(1810)
@mark.deploy
def test_deploy_psgw_with_resource_pool_id(context):
    """
    TestRail ID:   C57582334    Deploy PSG with resource-pool

    TestRail ID - C57597030	Create Cloud Protection store with valid GLCP location/region,
    but not registered with GLBR (e.g. Jakarta)

    TestRail ID - C57597032	Create Cloud store and provide location_id with Invalid characters
    and numeric and special characters

    TestRail ID - C57597029	Create Protection store with out providing region and location_id then check for the error message
    """
    create_protection_store_gateway_vm(
        context,
        deploy_with_resource_pools=True,
        add_data_interface=False,
    )
    validate_protection_store_gateway_vm(context)
    verify_the_PSG_deployment_info_after_successfully_deployment(
        context,
        deploy_with_resource_pools=True,
    )

    # Test case for validating the error message for storage locations.
    verify_cloud_protection_store_error(
        context,
        storage_location_id=AwsStorageLocation.AWS_AP_SOUTHEAST_3.value,
        error_message=ERROR_MESSAGE_CREATE_CLOUD_STORAGE_LOCATION_ID,
        response_code=codes.precondition_failed,
    )
    logger.info("successfully validated the error while creating cloud store with location not available for GLBR")

    verify_cloud_protection_store_error(
        context,
        storage_location_id="invalid123#@!",
        error_message=ERROR_MESSAGE_CREATE_CLOUD_STORAGE_LOCATION_ID,
        response_code=codes.precondition_failed,
    )
    logger.info("successfully validated the error while creating cloud store with invalid location")

    verify_cloud_protection_store_error(
        context,
        storage_location_id="",
        error_message=ERROR_MESSAGE_CREATE_CLOUD_STORAGE_LOCATION_ID_AS_EMPTY,
        response_code=codes.bad_request,
    )
    logger.info("successfully validated the error while creating cloud store with region as empty string")

    delete_protection_store_gateway_vm(context)


@mark.order(1815)
@mark.deploy
def test_deploy_psgw_with_folder_id(context):
    """TestRail ID:  C57582333
    Deploy PSG on folder
    """
    create_protection_store_gateway_vm(
        context,
        deploy_on_folder=True,
        add_data_interface=False,
    )
    validate_protection_store_gateway_vm(context)
    verify_the_PSG_deployment_info_after_successfully_deployment(context, deploy_on_folder=True)
    delete_protection_store_gateway_vm(context)


@mark.order(1820)
def test_deploy_psgw_with_all_options_and_validate_error_msg(context):
    """
    TestRail ID:C57582336
    Deploy PSG with all options
    """
    response = create_protection_store_gateway_vm(
        context,
        deploy_on_folder=True,
        deploy_with_cluster_id=True,
        deploy_with_resource_pools=True,
        deploy_ova_on_content_lib_ds=True,
        add_data_interface=False,
        return_response=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_DEPLOY_PSG_ALL_HOSTID_CLUSTERID_RESOURCEPOOLID,
    )


@mark.order(1825)
def test_deploy_psgw_with_invalid_ids_and_validate_error_msg(context):
    """TestRail ID:C57582337
    Deploy PSG with invalid details
    """
    # Deploy PSG with invalid hypervisor_cluster_id details
    hypervisor_cluster_id = context.hypervisor_cluster_id
    context.hypervisor_cluster_id = context.resources_pools_id
    response = create_protection_store_gateway_vm(
        context,
        deploy_with_cluster_id=True,
        add_data_interface=False,
        return_response=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.not_found,
        expected_error=ERROR_MESSAGE_DEPLOY_PSG_WITH_INVALD_CLUSTER_ID,
    )
    context.hypervisor_cluster_id = hypervisor_cluster_id

    #  Deploy PSG with invalid resources_pools_id details
    resources_pools_id = context.resources_pools_id
    context.resources_pools_id = context.hypervisor_cluster_id
    response = create_protection_store_gateway_vm(
        context,
        deploy_with_resource_pools=True,
        add_data_interface=False,
        return_response=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.not_found,
        expected_error=ERROR_MESSAGE_DEPLOY_PSG_WITH_INVALD_RESOURCE_POOL_ID,
    )
    context.resources_pools_id = resources_pools_id

    # Deploy PSG with invalid content_lib_datastore_id details
    content_lib_datastore_id = context.content_lib_datastore_id
    context.content_lib_datastore_id = context.hypervisor_cluster_id
    response = create_protection_store_gateway_vm(
        context,
        deploy_ova_on_content_lib_ds=True,
        add_data_interface=False,
        return_response=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.not_found,
        expected_error=ERROR_MESSAGE_DEPLOY_PSG_WITH_INVALD_CONTENT_LIB_DATASTORE_ID,
    )
    context.content_lib_datastore_id = content_lib_datastore_id

    # Deploy PSG with invalid hypervisor_folder_id details
    hypervisor_folder_id = context.hypervisor_folder_id
    context.hypervisor_folder_id = context.resources_pools_id
    response = create_protection_store_gateway_vm(
        context, add_data_interface=False, return_response=True, deploy_on_folder=True
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.not_found,
        expected_error=ERROR_MESSAGE_DEPLOY_PSG_WITH_INVALD_FOLDER_ID,
    )
    context.hypervisor_folder_id = hypervisor_folder_id
