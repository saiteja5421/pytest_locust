"""
This module contains File Based Recovery functions related to restoring and validating files and folders from S3 buckets
"""

import hashlib
import logging
from typing import Union
import requests
import zipfile
import subprocess
import os

from io import BytesIO

from lib.common.enums.task_status import TaskStatus
from lib.dscc.backup_recovery.aws_protection.gfrs.domain_models.gfrs_models import (
    LocationModel,
    PostRestoreCSPFileSystemInfoModel,
)
from lib.dscc.backup_recovery.aws_protection.gfrs.models.gfrs_error_response import GFRSErrorResponse
from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.host.models.file_hash import FileHash, FileHashList

from tests.steps.tasks import tasks
from tests.e2e.aws_protection.context import Context

from utils.timeout_manager import TimeoutManager

logger = logging.getLogger()


def restore_csp_instance_files_folders(
    context: Context,
    csp_instance_id: str,
    csp_backup_id: str,
    restore_info: PostRestoreCSPFileSystemInfoModel,
    response_code: int = requests.codes.accepted,
    wait_for_task: bool = True,
    expected_task_status: TaskStatus = TaskStatus.success,
) -> LocationModel:
    """Restores provided files and folders for an CSP Instance's Backup and waits for restore task to complete

    Args:
        context (Context): Context object
        csp_instance_id (str): CSP Machine instance ID
        csp_backup_id (str): CSP Machine's Backup ID from which files / folders need to be restored
        restore_info (PostRestoreCSPFileSystemInfo): PostRestoreCSPFileSystemInfo object
        response_code (int, optional): Expected response code. Defaults to requests.codes.accepted.
        wait_for_task (bool, optional): Wait for restore task to complete if set to True. Defaults to True.
        expected_task_status (TaskStatus, optional): The expected Task Status. Defaults to TaskStatus.success.

    Returns:
        tuple[str, str]: target_location (S3 bucket restore location) and task_id
    """
    logger.info(f"Restoring files and folders for CSP Machine {csp_instance_id}, backup {csp_backup_id}")
    location: Union[LocationModel, GFRSErrorResponse] = (
        context.gfrs_data_protection_manager.restore_csp_machine_instance_files_folders(
            csp_backup_id=csp_backup_id,
            restore_info=restore_info,
            response_code=response_code,
        )
    )

    if isinstance(location, GFRSErrorResponse):
        logger.error(f"Error Response: {location}")
        raise Exception(
            f"Error occurred while restoring files and folders for CSP Machine instance {csp_instance_id}, backup {csp_backup_id}"
        )

    logger.info(f"S3 Bucket Restore Target Location is {location.location}")
    logger.info(f"Task ID for restore is {location.task_id}")

    if wait_for_task:
        logger.info(
            f"Waiting for Files / Folders restore for CSP Machine {csp_instance_id}, backup {csp_backup_id} to complete"
        )
        restore_task_status: str = tasks.wait_for_task(
            task_id=location.task_id,
            user=context.user,
            timeout=TimeoutManager.standard_task_timeout,
        )

        assert (
            restore_task_status.upper() == expected_task_status.value
        ), f"GFR Restore for CSP Machine instance {csp_instance_id}, backup {csp_backup_id} failed"

    return location


def restore_csp_volume_files_folders(
    context: Context,
    csp_volume_id: str,
    csp_backup_id: str,
    restore_info: PostRestoreCSPFileSystemInfoModel,
    response_code: int = requests.codes.accepted,
    wait_for_task: bool = True,
) -> LocationModel:
    """Restores provided files and folders for an CSP Instance's Backup and waits for restore task to complete

    Args:
        context (Context): Context object
        csp_volume_id (str): CSP Volume ID
        csp_backup_id (str): CSP Volume's Backup ID from which files / folders need to be restored
        restore_info (PostRestoreCSPFileSystemInfo): PostRestoreCSPFileSystemInfo object
        response_code (int, optional): Expected response code. Defaults to requests.codes.accepted.
        wait_for_task (bool, optional): Wait for restore task to complete if set to True. Defaults to True.

    Returns:
        tuple[str, str]: target_location (S3 bucket restore location) and task_id
    """
    logger.info(f"Restoring files and folders for CSP Volume {csp_volume_id}, backup {csp_backup_id}")
    location: Union[LocationModel, GFRSErrorResponse] = (
        context.gfrs_data_protection_manager.restore_csp_volume_files_folders(
            csp_backup_id=csp_backup_id,
            restore_info=restore_info,
            response_code=response_code,
        )
    )

    if isinstance(location, GFRSErrorResponse):
        logger.error(f"Error Response: {location}")
        raise Exception(
            f"Error occurred while restoring files and folders for CSP Volume {csp_volume_id}, backup {csp_backup_id}"
        )

    logger.info(f"S3 Bucket Restore Target Location is {location.location}")
    logger.info(f"Task ID for restore is {location.task_id}")

    if wait_for_task:
        logger.info(
            f"Waiting for Files / Folders restore for CSP Volume {csp_volume_id}, backup {csp_backup_id} to complete"
        )
        refresh_task_status: str = tasks.wait_for_task(
            task_id=location.task_id,
            user=context.user,
            timeout=TimeoutManager.standard_task_timeout,
        )

        assert (
            refresh_task_status.upper() == TaskStatus.success.value
        ), f"GFR Restore for CSP Volume {csp_volume_id}, backup {csp_backup_id} failed"

    return location


# TODO
def validate_restored_files_system_info(
    context: Context,
    csp_source_file_id: str,
    csp_restored_file_id: str,
) -> bool:
    """Returns True or False based on validation of restored driveName / fileSystemType / mountPath etc.
    CSPIndexedFileSystemInfoModel object needs to be used
    NOTE: Need to get more information on this once we have more visibility

    Args:
        context (Context): _description_
        csp_source_file_id (str): _description_
        csp_restored_file_id (str): _description_

    Returns:
        bool: _description_
    """
    pass


# TODO
def validate_restored_files_and_folders_info(
    context: Context,
    csp_source_file_folder_id: str,
    csp_restored_file_folder_id: str,
) -> bool:
    """Returns True or False based on validation of restored fileType / absolutePath / sizeInBytes etc.
    CSPIndexedFilesAndFoldersInfo object needs to be used
    NOTE: Need to get more information on this once we have more visibility

    Args:
        context (Context): _description_
        csp_source_file_folder_id (str): _description_
        csp_restored_file_folder_id (str): _description_

    Returns:
        bool: _description_
    """
    pass


def read_restored_files_from_s3_bucket(aws: AWS, s3_url: str) -> FileHashList:
    """Reads data from S3 bucket of restored backups and returns FileHashList object
    NOTE: Need to get more information on how the files will be processed.
    As per current knowledge, the backed-up files / folders will be zipped and stored in customer's S3 bucket
    This is just an idea on the validation. We can improve this later once we have more visibility
    '#read_zip_file_data()' is added based on the above mentioned understanding

    Args:
        aws (AWS): AWS object
        s3_url (str): s3_url returned by GFRS '/restore-files' endpoint
        {
         "targetLocation": "https://s3.us-west-2.amazonaws.com/abc_corp_restore_bucket"
        }

    Returns:
        FileHashList: FileHasList object
    """
    s3_bucket_name = s3_url.replace("https://", "").split("/")[1]
    bucket_files = aws.s3.get_s3_object_keys(bucket_name=s3_bucket_name)
    file_hashes: list[FileHash] = []

    for bucket_file in bucket_files:
        buffered_data = aws.s3.read_bucket_object_data(bucket_name=s3_bucket_name, key=bucket_file)
        if ".zip" in bucket_file:
            file_hash_list = read_zip_file_data(buffered_data)
            file_hashes.extend(file_hash_list)
        else:
            buffered_data["Body"].read()
            file_hash_md5 = hashlib.md5(buffered_data["Body"]).hexdigest()
            file_hash = FileHash(algorithm="MD5", hash=file_hash_md5, path=bucket_file)
            file_hashes.append(file_hash)

    return FileHashList(file_hashes=file_hashes)


def read_zip_file_data(zip_file_buffered_data: BytesIO) -> list[FileHash]:
    """Reads bytes data of files inside a .zip file and returns a list of FileHash object

    Args:
        zip_file_buffered_data (BytesIO): data returned by method:
        aws.s3.read_bucket_object_data(bucket_name=s3_bucket_name, key=bucket_file)

    Returns:
        list[FileHash]: A list of FileHash object
    """
    file_hashes: list[FileHash] = []
    z = zipfile.ZipFile(zip_file_buffered_data)
    for file_name in z.namelist():
        file_info = z.getinfo(file_name)
        logger.info(f"File Info {file_info}")

        file_content = z.read(file_name)
        logger.info(f"File Content = {file_content}")

        logger.info(f"Generating file hash for file {file_name}")
        file_hash_md5 = hashlib.md5(file_content).hexdigest()
        logger.info(f"File {file_name}, FileHash = {file_hash_md5}")

        file_hash = FileHash(algorithm="MD5", hash=file_hash_md5, path=file_name)
        file_hashes.append(file_hash)

    return file_hashes


def download_and_unzip_from_s3(aws: AWS, bucket_name: str, s3_filename: str, target_filename: str) -> str:
    """Download an S3 bucket to filename, and unzip the contents

    Args:
        aws (AWS): AWS object
        bucket_name (str): The S3 bucket name
        s3_filename (str): The filename to download from the S3 bucket
        target_filename (str): The destination file. Any directories included must already exist.

    Returns:
        str: The path to where the S3 bucket files were extracted
    """
    if not os.path.exists(path=target_filename):
        aws.s3.download_object(bucket_name, s3_filename, target_filename)

    path, filename = os.path.split(target_filename)

    # remove ".tar.gz" from filename and use for "s3_bucket" name
    s3_dir = filename.split(".")[0]

    # create a directory "s3_bucket" under "path", to ensure no other files are captured with hash searching
    s3_path = f"{path}/{s3_dir}"
    # create directory
    output = subprocess.run(f"mkdir -p {s3_path}", shell=True, capture_output=True, text=True)

    output = subprocess.run(f"tar -xf {target_filename} -C {s3_path}", shell=True, capture_output=True, text=True)
    # assert operation was successful
    assert output.returncode == 0, f"tar extraction failed: {output.stderr}"

    return s3_path


def get_bucket_and_s3_filename_from_restore_location(s3_target_location: str) -> tuple[str, str]:
    """Return S3 Bucket Name and S3 Filename from the given 's3_target_location' returned from 'restore_csp_instance_files_folders()' and 'restore_csp_volume_files_folders'

    Args:
        s3_target_location (str): S3 bucket target location from 'restore_csp_instance_files_folders()' and 'restore_csp_volume_files_folders'

    Returns:
        tuple[str, str]: The S3 Bucket Name and S3 Filename values
    """
    # EX: https://hpe-3b734085-6a5b-594b-9b0c-902fc110f836.s3.us-west-2.amazonaws.com/restored_content/bc1a19da-823a-50e7-ae69-643720b1abc1/recovered_files_bddaf465-1bc7-4e01-bcc1-837777b15439_f33e7d3b-6786-4f40-875a-90f0f7e6b9a8_1689721491.tar.gz
    target_location_parts = s3_target_location.replace("https://", "").split("/")
    # from: hpe-3b734085-6a5b-594b-9b0c-902fc110f836.s3.us-west-2.amazonaws.com
    bucket_name = target_location_parts[0].split(".")[0]
    # join the remaining parts into the S3 filename
    s3_filename = "/".join(target_location_parts[1:])

    return bucket_name, s3_filename
