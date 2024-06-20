"""
This module contains GFRS Helper functions
"""
import logging

from lib.platform.host.models.file_hash import FileHashList

from lib.platform.aws_boto3.aws_factory import AWS

import tests.steps.aws_protection.gfrs.gfrs_aws_steps as GFRSAWSSteps
import tests.steps.aws_protection.gfrs.gfrs_backup_and_restore_steps as GFRSBRSteps

logger = logging.getLogger()


####################################################
def download_and_compare_restored_file_checksums(
    aws: AWS, csp_asset_id: str, target_location: str, initial_checksum_list: FileHashList
) -> str:
    """Download the tar from the "target_location" and compare with the provided FileHashList

    Args:
        aws (AWS): The AWS Account
        csp_asset_id (str): CSP Machine or Volume ID
        target_location (str): The "target_location" from GFRS Restore operation
        initial_checksum_list (FileHashList): The initial FileHashList checksums

    Returns:
        str: The AWS "bucket_name" that contains the restored files
    """
    logger.info(f"Taking checksum after restore for the CSP Asset {csp_asset_id}")
    bucket_name, s3_filename = GFRSBRSteps.get_bucket_and_s3_filename_from_restore_location(target_location)

    checksum_list_after_restore = GFRSAWSSteps.get_checksum_s3(
        aws=aws,
        bucket_name=bucket_name,
        filename=s3_filename,
    )

    logger.info(
        f"Comparing checksum before {initial_checksum_list} and after restore for the instance {checksum_list_after_restore}"
    )
    GFRSAWSSteps.compare_source_checksum_with_restored(
        source_list=initial_checksum_list,
        target_list=checksum_list_after_restore,
    )
    return bucket_name
