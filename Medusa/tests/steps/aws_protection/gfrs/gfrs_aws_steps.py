"""
This module contains functions related to generating and comparing checksum values
"""

import logging
import subprocess
from sys import platform

from lib.common.enums.os import OS

from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.host.io_manager import IOManager
from lib.platform.host.models.file_hash import FileHashList

from tests.e2e.aws_protection.context import Context

from tests.steps.aws_protection.common_steps import connect_to_ec2_instance
from tests.steps.aws_protection.gfrs.gfrs_backup_and_restore_steps import download_and_unzip_from_s3

logger = logging.getLogger()


def get_checksum_ec2(
    context: Context,
    aws: AWS,
    ec2_instance_id: str,
    path: str,
    key_file: str = None,
    os: OS = OS.LINUX,
    scrub_path: str = None,
) -> FileHashList:
    """
    It will prepare FileHashList from given folder on ec2 instance.

    Args:
        context (Context): Atlantia context object
        aws (AWS): AWS object for given account and region
        ec2_instance_id (str): ec2 instance Id from AWS
        path (str): path to a file or folder
        key_file (str, optional): SSH private key to ec2. Defaults to None.
        os (OS, optional): WINDOWS or LINUX. Defaults to OS.LINUX.
        scrub_path (str, optional): FileHash from Windows and Linux may contain path data that will not be present in the restored FileHash.
          if a value is provided, it will be removed from any FileHash.path values. Defaults to None.

    Returns:
        FileHashList: list of FileHash from given path
    """
    logger.info(f"Get ec2 checksum started: {ec2_instance_id=}, {os=}, {path=}")
    checksum_list: FileHashList = FileHashList([])

    if os == OS.WINDOWS:
        checksum_list = aws.ssm.get_drive_data_checksum(ec2_instance_id=ec2_instance_id, path=path)
        # The Indexed Files will restore with forward-slash.  We need to convert any \\ to / in returned FileHash.path
        for filehash in checksum_list.file_hashes:
            filehash.path = filehash.path.replace("\\", "/")

    elif os == OS.LINUX:
        client = connect_to_ec2_instance(
            context=context,
            aws=aws,
            account_id=context.csp_account_id_aws_one,
            ec2_instance_id=ec2_instance_id,
            key_file=key_file,
        )
        io_manager = IOManager(context=context, client=client)
        logger.info(f"Remote connection started to {ec2_instance_id}")

        std_out = io_manager.client.execute_command(command=f"find {path} -type f -exec sha256sum {{}} \\;")
        logger.info(f"Command output {std_out}")
        checksum_list.parse_sha256_unix(std_out)
        client.close_connection()

    # For Window, source FileHash will likely have a Drive letter, whereas the restore FileHash will not
    # For Linux, source FileHash may contain a mount path, whereas the restore FileHash will not
    # If the optional parameter "scrub_path" has a value, remove that value from all FileHash.path entries
    if scrub_path:
        for filehash in checksum_list.file_hashes:
            filehash.path = filehash.path.replace(scrub_path, "")

    logger.info(f"Get ec2 checksum finished: {ec2_instance_id=}, {os=}, {path=}, {checksum_list=}")
    return checksum_list


def get_checksum_local(path: str) -> FileHashList:
    """
    It will calculate FileHashList from given path.
    It should automatically check operation system and choose the appropriate code to generate checksum.

    Args:
        path (str): path to a file or folder

    Returns:
        FileHashList: list of FileHash from given path
    """
    logger.info(f"Get local checksum started: {path=}")
    checksum_list: FileHashList = FileHashList([])

    if OS.LINUX.value in platform:
        output = subprocess.run(
            f"find {path} -type f -exec sha256sum {{}} \\;", shell=True, capture_output=True, text=True
        )

    elif OS.MAC.value in platform:
        output = subprocess.run(
            f"find {path} -type f -exec shasum -a 256 {{}} \\;", shell=True, capture_output=True, text=True
        )
    elif OS.WINDOWS.value in platform:
        output = subprocess.run(
            [
                "powershell",
                "-Command",
                f'Get-ChildItem -Path "{path}" -Recurse| Get-FileHash -Algorithm SHA256 | ConvertTo-Json',
            ],
            shell=True,
            capture_output=True,
            text=True,
        )

    # "output" is a "CompletedProcess" object
    cmd_output = output.stdout
    logger.info(f"Command output: {cmd_output}")

    if OS.LINUX.value in platform or OS.MAC.value in platform:
        checksum_list.parse_sha256_unix_subprocess(cmd_output)
    elif OS.WINDOWS.value in platform:
        # TODO needs to be tested, since the stdout here is from a different process than "ssm_client"
        checksum_list.parse_sha256_windows(cmd_output)
    logger.info(f"Get local checksum finished: {path=}, {checksum_list.file_hashes=}")
    return checksum_list


def get_checksum_s3(aws: AWS, bucket_name: str, filename: str) -> FileHashList:
    """
    Downloads a file from S3, unzips it, and builds a FileHashList from the unzipped folder.

    Args:
        aws (AWS): AWS object for given account and region
        bucket_name (str): S3 bucket name
        filename (str): filename to download from S3

    Returns:
        FileHashList: list of FileHash from given path
    """
    logger.info(f"Get s3 checksum started: {bucket_name=}, {filename=}")

    # The destination file needs to be downloaded to a directory that already exists on the test system.  We'll use "/tmp"
    # The "filename" will have directories included, since the S3 path within the Bucket is something like:
    # "restored_content/bc1a19da-823a-50e7-ae69-643720b1abc1/recovered_files_bddaf465-1bc7-4e01-bcc1-837777b15439_f33e7d3b-6786-4f40-875a-90f0f7e6b9a8_1689721491.tar.gz"
    # --> grab the last item
    gz_file = filename.split("/")[-1]
    dest_filename = f"/tmp/{gz_file}"

    path = download_and_unzip_from_s3(aws, bucket_name, filename, dest_filename)
    checksum = get_checksum_local(path)

    # the "path" returned needs to be removed from each FileHash in the "checksum"
    # Backup files such as:
    #   FileHash(algorithm='SHA256', hash='664ad437ca59c2c5695d33e1e81ff9124e93c745e0be06dee6ebda11be8c1be3', path='/dir1/vdb.1_1.dir/vdb_f0000.file')
    # after restore will appear as:
    #   FileHash(algorithm='SHA256', hash='664ad437ca59c2c5695d33e1e81ff9124e93c745e0be06dee6ebda11be8c1be3', path='/tmp/s3_bucket/dir1/vdb.1_1.dir/vdb_f0000.file')
    for filehash in checksum.file_hashes:
        filehash.path = filehash.path.replace(path, "")

    # delete the downloaded file and extracted files
    subprocess.run(f"rm {dest_filename}", shell=True, capture_output=True, text=True)
    subprocess.run(f"rm -r {path}", shell=True, capture_output=True, text=True)

    logger.info(f"Get s3 checksum finished: {bucket_name=}, {filename=}, {checksum.file_hashes=}")
    return checksum


def compare_source_checksum_with_restored(source_list: FileHashList, target_list: FileHashList):
    """
    Checks whether two FileHashList have the same order and params value.

    Args:
        source_list (FileHashList): source list of FileHash
        target_list (FileHashList): target list of FileHash
    """

    def _get_hash_item(hash_item_path: str):
        for item in target_list.file_hashes:
            if item.path in hash_item_path or hash_item_path in item.path:
                return item

    # The source and target lists may not have their FileHash members in a matching order.
    # This is a function of the 2 methods used to get the Before and After FileHashLists.
    #
    # In addition, Windows restores can place an extra file (.dat)
    #
    # Therefore:
    # a) assert each member of the Source FileHashList has a matching entry in the Target FileHashList
    #
    # FileHash values are hexadecimal values - so Uppercase and Lowercase values are equal.
    # Windows returns Uppercase, Linux returns lowercase.  We will .upper() the hash values.
    for source_item in source_list.file_hashes:
        target_item = _get_hash_item(source_item.path)
        assert target_item, f"FileHash for path {source_item.path} was not found in target list"
        assert (
            source_item.hash.upper() == target_item.hash.upper()
        ), f"FileHash values do not match: {source_item.hash} vs {target_item.hash}"

    logger.info(f"Checksum compare PASSED {source_list}, {target_list}")
