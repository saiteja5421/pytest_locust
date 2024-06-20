import json
import logging
import uuid
from lib.common.enums.command_type import AZCommandType
from lib.platform.azure.azure_factory import Azure
from lib.platform.host.models.file_hash import FileHashList


logger = logging.getLogger()


def get_raw_disk_number(
    azure: Azure,
    resource_group_name: str,
    vm_name: str,
) -> int:
    """Returns raw disk number which is attached to a Windows VM

    Args:
        azure (Azure): Azure Factory object
        resource_group_name (str): Resource Group Name
        vm_name (str): Name of the VM

    Returns:
        (int): Disk Number of the disk which is attached to the VM
    """
    command: str = """
    Import-Module Storage
    Get-Disk | Where-Object PartitionStyle -Eq RAW | ConvertTo-Json
    """
    result = azure.az_vm_manager.run_command_on_vm(
        resource_group_name=resource_group_name,
        vm_name=vm_name,
        script=[command],
        command_id=AZCommandType.POWERSHELL,
    )

    # Returns a response with a little distorted JSON because some of the output is truncated
    # Getting substring of the response and adding '{' to fix JSON format and getting the disk number
    raw_disk_data_index = result.value[0].message.find("CimSystemProperties")
    raw_disk_data = "{" + f""""{result.value[0].message[raw_disk_data_index:]}"""
    logger.info(f"Raw disk data {raw_disk_data}")
    raw_disk_json = json.loads(raw_disk_data)
    disk_number = raw_disk_json["DiskNumber"]
    return disk_number


def initialize_disk(
    azure: Azure,
    resource_group_name: str,
    vm_name: str,
    disk_number: int,
):
    """Initializes raw disk attached to windows VM

    Args:
        azure (Azure): Azure Factory object
        resource_group_name (str): Resource Group Name
        vm_name (str): Name of the VM
        disk_number (int): Raw disk number
    """
    command: str = f"""
    Import-Module Storage
    Initialize-Disk {disk_number}
    """
    result = azure.az_vm_manager.run_command_on_vm(
        resource_group_name=resource_group_name,
        vm_name=vm_name,
        script=[command],
        command_id=AZCommandType.POWERSHELL,
    )
    logger.info(f"Raw Disk {disk_number} initialized {result.value[0].message}")


def partition_disk(
    azure: Azure,
    resource_group_name: str,
    vm_name: str,
    disk_number: int,
    drive_letter: str = "F",
):
    """Partitions raw disk attached to the VM and assigns specified letter to the partition

    Args:
        azure (Azure): Azure Factory object
        resource_group_name (str): Resource Group Name
        vm_name (str): Name of the VM
        disk_number (int): Raw disk number
        drive_letter (str, optional): Drive letter to be assigned to the partitioned disk. Defaults to "F".
        Letters D (Temporary Storage) and E (DVD Drive) are already in use
    """
    command: str = f"""
    Import-Module Storage
    New-Partition -DiskNumber {disk_number} -DriveLetter {drive_letter} -UseMaximumSize
    """
    result = azure.az_vm_manager.run_command_on_vm(
        resource_group_name=resource_group_name,
        vm_name=vm_name,
        script=[command],
        command_id=AZCommandType.POWERSHELL,
    )
    logger.info(f"Raw Disk {disk_number} partitioned and assigned letter {drive_letter} {result.value[0].message}")


def format_disk(
    azure: Azure,
    resource_group_name: str,
    vm_name: str,
    drive_letter: str = "F",
    file_system_format: str = "NTFS",
):
    """Formats disk attached to the VM

    Args:
        azure (Azure): Azure Factory object
        resource_group_name (str): Resource Group Name
        vm_name (str): Name of the VM
        drive_letter (str, optional): Drive letter to be formatted. Defaults to "F".
        file_system_format (str, optional): NTFS, FAT32, etc. Defaults to NTFS
    """
    command: str = f"""
    Import-Module Storage
    Format-Volume -DriveLetter {drive_letter} -FileSystem {file_system_format}
    """
    result = azure.az_vm_manager.run_command_on_vm(
        resource_group_name=resource_group_name,
        vm_name=vm_name,
        script=[command],
        command_id=AZCommandType.POWERSHELL,
    )
    logger.info(f"Drive {drive_letter} formatted and ready for use: {result.value[0].message}")


def initialize_and_format_disk(
    azure: Azure,
    resource_group_name: str,
    vm_name: str,
    drive_letter: str = "F",
    file_system_format: str = "NTFS",
):
    """Initializes and formats disk

    Args:
        azure (Azure): Azure Factory object
        resource_group_name (str): Resource Group Name
        vm_name (str): Name of the VM
        drive_letter (str, optional): Drive letter to be formatted. Defaults to "F".
        file_system_format (str, optional): NTFS, FAT32, etc. Defaults to NTFS
    """
    disk_number = get_raw_disk_number(
        azure=azure,
        resource_group_name=resource_group_name,
        vm_name=vm_name,
    )

    initialize_disk(
        azure=azure,
        resource_group_name=resource_group_name,
        vm_name=vm_name,
        disk_number=disk_number,
    )

    partition_disk(
        azure=azure,
        resource_group_name=resource_group_name,
        vm_name=vm_name,
        disk_number=disk_number,
        drive_letter=drive_letter,
    )

    format_disk(
        azure=azure,
        resource_group_name=resource_group_name,
        vm_name=vm_name,
        drive_letter=drive_letter,
        file_system_format=file_system_format,
    )


def write_data_to_disk(
    azure: Azure,
    resource_group_name: str,
    vm_name: str,
    drive_letter: str = "F",
    drive_path: str = "",
):
    """Writes data to the specified drive at the specified path in that drive

    Args:
        azure (Azure): Azure Factory object
        resource_group_name (str): Resource Group Name
        vm_name (str): Name of the VM
        drive_letter (str, optional): Drive letter on which data has to be written. Defaults to "F".
        drive_path (str, optional): Path in the specified drive where data should be written. Defaults to "".
    """
    file_name = f"myfile-{str(uuid.uuid4())}.txt"
    file_name_path = f"{drive_letter}:{drive_path[2:]}\\{file_name}"

    command: str = f"""
    Import-Module Microsoft.PowerShell.Utility
    $out = new-object byte[] 1048576; (new-object Random).NextBytes($out); [IO.File]::WriteAllBytes("{file_name_path}", $out)
    """
    result = azure.az_vm_manager.run_command_on_vm(
        resource_group_name=resource_group_name,
        vm_name=vm_name,
        script=[command],
        command_id=AZCommandType.POWERSHELL,
    )
    logger.info(f"Data written: {file_name_path}, {result.value[0].message}")


def get_drive_data_checksum(
    azure: Azure,
    resource_group_name: str,
    vm_name: str,
    drive_letter: str = "F",
) -> FileHashList:
    """Get checksum of the specified drive

    Args:
        azure (Azure): Azure Factory object
        resource_group_name (str): Resource Group Name
        vm_name (str): Name of the VM
        drive_letter (str, optional): Drive letter on which data has to be written. Defaults to "F".

    Returns:
        FileHashList: FileHashList with checksum
    """
    command: str = f"""
    Import-Module Microsoft.PowerShell.Utility
    Get-ChildItem -Path "{drive_letter}:" -Recurse| Get-FileHash -Algorithm SHA256 | ConvertTo-Json
    """
    result = azure.az_vm_manager.run_command_on_vm(
        resource_group_name=resource_group_name,
        vm_name=vm_name,
        script=[command],
        command_id=AZCommandType.POWERSHELL,
    )
    logger.info(f"Drive data checksum: {result.value[0].message}")

    file_hash_list: FileHashList = FileHashList([])
    file_hash_list.parse_sha256_windows(result.value[0].message)
    return file_hash_list
