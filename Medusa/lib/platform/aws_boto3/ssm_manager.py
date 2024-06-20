import json
import logging
import os
import subprocess
import time
import uuid
from typing import Callable

import boto3
from waiting import wait, TimeoutExpired

from lib.common.config.config_manager import ConfigManager
from lib.common.enums.linux_file_system_types import LinuxFileSystemTypes
from lib.common.enums.ssm_command_type import SSMCommandType
from lib.platform.aws_boto3.models.instance import Instance
from lib.platform.host.models.file_hash import FileHash, FileHashList
from lib.platform.host.vdbench_config_models import (
    BasicParameters,
    RunDefinitions,
    StorageDefinitions,
    WorkloadDefinitions,
)
from lib.platform.aws_boto3.client_config import ClientConfig
from utils.size_conversion import str_gb_to_mb

logger = logging.getLogger()


# NOTE: Working with SSM Agent: https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-install-ssm-win.html
# https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent-status-and-restart.html


class SSMManager:
    def __init__(
        self, aws_session: Callable[[], boto3.Session], endpoint_url: str = None, client_config: ClientConfig = None
    ):
        self.get_session = aws_session
        self.config = ConfigManager.get_config()
        self.vdbench_config = self.config["VDBENCH"]
        self.dmcore_config = self.config["DMCORE"]
        self.endpoint_url = endpoint_url
        self.client_config = client_config

    @property
    def ssm_client(self):
        return self.get_session().client("ssm", endpoint_url=self.endpoint_url, config=self.client_config)

    def get_instance_ssm_information(self, ec2_instance_id: str):
        """Describes all the instances are managed by SSM
        supported version: windows, linux

        Args:
            instance_id (str): EC2 Instance Id

        Returns:
            _type_: Response of describe_instance_information method which contains instances associated with SSM
        """
        response = self.ssm_client.describe_instance_information(
            InstanceInformationFilterList=[
                {"key": "InstanceIds", "valueSet": [ec2_instance_id]},
            ]
        )
        logger.info(response)
        return response

    def run_command(
        self,
        ec2_instance_id: str,
        command: str,
        command_type: SSMCommandType = SSMCommandType.WINDOWS,
    ):
        """Runs a command on the specified EC2 instance
        supported version: windows, linux

        Args:
            ec2_instance_id (str): AWS EC2 instance ID
            command (str): Command to run on the EC2 instance. Make sure to properly escape characters like '\' etc.
            command_type (SSMCommandType, optional): WINDOWS | LINUX. Defaults to WINDOWS

        Returns:
            Any: Command Output
        """

        self.wait_for_ssm_information_update(ec2_instance_id=ec2_instance_id)

        response = self.ssm_client.send_command(
            InstanceIds=[ec2_instance_id],
            DocumentName=command_type.value,
            Parameters={"commands": [command]},
        )

        command_id = response["Command"]["CommandId"]

        logger.info(f"Waiting for {command} to be executed")
        waiter = self.ssm_client.get_waiter("command_executed")
        # default timeout waiter values:
        # WaiterConfig (dict) –
        # A dictionary that provides parameters to control waiting behavior.
        #   Delay (integer) – The amount of time in seconds to wait between attempts. Default: 5
        #   MaxAttempts (integer) – The maximum number of attempts to be made. Default: 20
        # We increase default values, we have had timeouts occur while the command is still "InProgress"
        waiter.wait(
            CommandId=command_id,
            InstanceId=ec2_instance_id,
            WaiterConfig={"Delay": 10, "MaxAttempts": 40},
        )

        # after the command has completed - invoke to get the output
        output = self.invoke_command(ec2_instance_id=ec2_instance_id, command_id=command_id)
        logger.info(f"OUTPUT = {output}")
        return output

    def invoke_command(self, ec2_instance_id: str, command_id: str):
        """Invokes the command run by ssm "send_command" method
        supported version: windows, linux

        Args:
            command_id (str): Command ID returned by the "send_command" method
        """
        output = self.ssm_client.get_command_invocation(
            CommandId=command_id,
            InstanceId=ec2_instance_id,
        )
        return output

    # The Complex Regression test "test_windows_EC2_restore_cloud_backup" started failing: 2023-09-20 16:05:25
    # The failure is a timeout waiting for the Restored EC2 instance to appear in the "InstanceInformationList".
    # Manual testing has revealed that it can take over 20 minutes now for the Restored instance to show in the list.
    # The "AmazonSSMRoleForInstancesQuickSetup" role is successfully applied to the Restored Instance, and is seen in AWS UI.
    # The Source EC2 continues to appears in the "InstanceInformationList" within 5 minutes.
    def wait_for_ssm_information_update(self, ec2_instance_id: str, timeout: int = 2400, sleep: int = 30):
        """Wait for ssm information to update
        supported version: windows, linux

        Args:
            ec2_instance_id (str): EC2 instance id
            timeout (int) : Max time in seconds to wait for ssm information to get update. Default to 2400
            sleep (int) : Interval time in seconds.Default to 30
        """
        try:
            wait(
                lambda: self.get_instance_ssm_information(ec2_instance_id=ec2_instance_id)["InstanceInformationList"]
                != [],
                timeout_seconds=timeout,
                sleep_seconds=sleep,
            )
        except TimeoutExpired as e:
            response = self.get_instance_ssm_information(ec2_instance_id=ec2_instance_id)
            logger.info(f"Timeout waiting for {ec2_instance_id} SSM information update: {response}")
            raise e

    def compare_checksums(self, source_vm_checksum, restored_vm_checksum):
        """compare source and restored checksum
        supported version: windows, linux

        Args:
            source_vm_checksum: Checksum of source
            restored_vm_checksum : Checksum of restore
        """
        if isinstance(source_vm_checksum, FileHash) and isinstance(restored_vm_checksum, FileHash):
            assert (
                source_vm_checksum.hash == restored_vm_checksum.hash
            ), f"Source VM Checksum = {source_vm_checksum.hash} does not match Restored VM Checksum = {restored_vm_checksum.hash}"
        else:  # The object will be an instance of FileHashList
            for source_vm in source_vm_checksum.file_hashes:
                source_vm_file_path = source_vm.path
                restored_vm = [
                    res_vm for res_vm in restored_vm_checksum.file_hashes if res_vm.path == source_vm_file_path
                ][0]
                if restored_vm:
                    assert (
                        source_vm.hash == restored_vm.hash
                    ), f"Source VM Checksum = {source_vm.hash} does not match Restored VM Checksum = {restored_vm.hash}"

    def initialize_and_format_disk(
        self,
        ec2_instance_id: str,
        drive_letter: str,
        file_system_format: str = "NTFS",
    ):
        """Initializes and Formats the specified drive
        supported version: windows

        Args:
            ec2_instance_id (str): AWS EC2 instance ID
            drive_letter (str): Drive Letter to Initialize and Format
            file_system_format (str, optional): NTFS, FAT32, etc. Defaults to NTFS
        """
        self.bring_disks_online(ec2_instance_id=ec2_instance_id)
        disk_number = self.get_raw_disk_number(ec2_instance_id=ec2_instance_id)
        logger.info(f"Disk Number: {disk_number}")

        self.initialize_disk(ec2_instance_id=ec2_instance_id, disk_number=disk_number)
        time.sleep(5)  # Adding some sleep for disk to be initialized and ready
        self.create_disk_partition(
            ec2_instance_id=ec2_instance_id,
            disk_number=disk_number,
            drive_letter=drive_letter,
        )
        self.format_disk(
            ec2_instance_id=ec2_instance_id,
            drive_letter=drive_letter,
            file_system_format=file_system_format,
        )

    def bring_disks_online(self, ec2_instance_id: str):
        """Brings all the disks online which are in offline state.
        supported version: windows

        Args:
            ec2_instance_id (str): AWS EC2 instance ID
        """

        command: str = """Get-Disk | Where-Object IsOffline -Eq $True | Set-Disk -IsOffline $False"""
        logger.info(f"PS Command: {command}")
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(response)

    def get_raw_disk_number(self, ec2_instance_id: str) -> str:
        """Returns the number of a RAW disk -> an EBS volume which is not formatted and assigned a drive letter yet.
        supported version: windows

        NOTE: This method is currently assuming that there will only be 1 RAW disk at a given time.
        TODO: Improve to take into account multiple RAW disks.

        Args:
            ec2_instance_id (str): AWS EC2 instance ID

        Returns:
            str: Disk Number
        """
        command: str = "Get-Disk | Where-Object PartitionStyle -Eq RAW | ConvertTo-Json"
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        json_response = json.loads(response["StandardOutputContent"])
        logger.info(f"Get-Disk response = {json_response}")

        disk_number = json_response["DiskNumber"]
        logger.info(f"Raw disk number = {disk_number}")
        return disk_number

    def initialize_disk(self, ec2_instance_id: str, disk_number: str):
        """Initializes a disk so that it can be partitioned and formatted
        supported version: windows

        Args:
            ec2_instance_id (str): AWS EC2 instance ID
            disk_number (str): disk_number returned by get_raw_disk_number() method
        """
        command: str = f"Initialize-Disk {disk_number}"
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(response)

    def create_disk_partition(self, ec2_instance_id: str, disk_number: str, drive_letter: str):
        """Creates a disk partition
        supported version: windows

        Args:
            ec2_instance_id (str): AWS EC2 instance ID
            disk_number (str): disk_number returned by get_raw_disk_number() method
            drive_letter (str): A letter that you would like to assign to the new drive, eg. D, E, F, etc.
        """
        command: str = f"New-Partition -DiskNumber {disk_number} -DriveLetter {drive_letter} -UseMaximumSize"
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(response)

    def format_disk(self, ec2_instance_id: str, drive_letter: str, file_system_format: str = "NTFS"):
        """Formats a disk to a specified format
        supported version: windows

        Args:
            ec2_instance_id (str): AWS EC2 instance ID
            drive_letter (str): Drive which has to be formatted, eg. D, E, F, etc.
            file_system_format (str, optional): NTFS, FAT32, etc. Defaults to NTFS
        """
        command: str = f"Format-Volume -DriveLetter {drive_letter} -FileSystem {file_system_format}"
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(response)

    def create_subfolders_in_windows(self, ec2_instance_id: str, drive_letter: str) -> str:
        """Creates sub folders on the specified drive.
        supported version: windows

        Args:
            ec2_instance_id (str): AWS EC2 instance ID
            drive_letter (str): Drive under which user would like to create folders
        Returns:
            Folder path created on the drive
        """
        folder1 = '{"$_\F1"}'
        folder2 = '{"$_\F2"}'
        folder3 = '{"$_\F3"}'
        logger.info(f"Creating sub folders on drive {drive_letter}")
        command: str = f"""
            Set-Location {drive_letter}:
            (New-Item -Type Directory -Force `
            -Path (1 -replace '^', 'E').ForEach({folder1}).ForEach({folder2}).ForEach({folder3})) -join"`n";"""
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        folder_path = response["StandardOutputContent"]
        logger.info(f"folder_path: {folder_path}")
        return folder_path[:-2]

    def create_jpeg_file_in_windows(self, ec2_instance_id: str, drive_path: str):
        """Creates a jpeg file on the specified drive path.
        supported version: windows

        Args:
            ec2_instance_id (str): AWS EC2 instance ID
            drive_path (str): Drive path where user would like to create jpeg file
        Returns:
            jpeg file created
        """

        logger.info(f"Creating JPEG file on drive {drive_path}")
        file_name = "testjpegfile.jpeg"
        file_name_path = f"{drive_path}" + f"\\{file_name}"
        command: str = f"""
            [Reflection.Assembly]::LoadWithPartialName("System.Drawing")
            $filename= "{file_name_path}"
            $bmp = new-object System.Drawing.Bitmap 250,61 
            $font = new-object System.Drawing.Font Consolas,24 
            $brushBg= [System.Drawing.Brushes]::Yellow
            $brushFg= [System.Drawing.Brushes]::Black
            $graphics= [System.Drawing.Graphics]::FromImage($bmp) 
            $graphics.FillRectangle($brushBg,0,0,$bmp.Width,$bmp.Height) 
            $graphics.DrawString('Hello World',$font,$brushFg,10,10) 
            $graphics.Dispose() 
            $bmp.Save($filename)
            """

        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(response)
        return file_name

    def write_data_to_drive(self, ec2_instance_id: str, drive_letter: str, drive_path: str = ""):
        """Creates a random file of 100 MB on the specified disk.
        supported version: windows

        Args:
            ec2_instance_id (str): AWS EC2 instance ID
            drive_letter (str): A letter that you would like to assign to the new drive, eg. D, E, F, etc.
        """

        logger.info(f"Creating a random file on drive {drive_letter}")
        file_name = f"myfile-{str(uuid.uuid4())}.txt"
        file_name_path = f"{drive_letter}:{drive_path[2:]}\\myfile-{str(uuid.uuid4())}.txt"

        command: str = f"""
        $out = new-object byte[] 107374182; (new-object Random).NextBytes($out); [IO.File]::WriteAllBytes("{file_name_path}", $out)
            """
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(response)
        return file_name

    def get_drive_data_checksum(self, ec2_instance_id: str, path: str):
        """Returns FileHash of all the files in the specified drive
        supported version: windows

        Args:
            ec2_instance_id (str): AWS EC2 instance ID
            path (str): path to folder or file localization

        Returns:
            str: Returns FileHashList object
        """

        command: str = f"""
            Get-ChildItem -Path "{path}" -Recurse| Get-FileHash -Algorithm SHA256 | ConvertTo-Json
            """
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(response)
        file_hash_list: FileHashList = FileHashList([])
        file_hash_list.parse_sha256_windows(response["StandardOutputContent"])
        return file_hash_list

    # NOTE: Restored EBS volume has "Read-Only" attribute set to 'True'
    # because of which, writing cannot be performed on the disk
    # until the "Read-Only" attribute is set to 'False'
    def clear_disk_read_only_attribute_and_bring_disk_online(self, ec2_instance_id: str, disk_number: str):
        """Sets the disk "Read-Only" attribute to 'False'
        supported version: windows

        Args:
            ec2_instance_id (str): AWS EC2 instance ID
            disk_number (str): Number of the disk which needs the "Read-Only" attribute to be set to 'False'

        # REFERENCE: https://www.online-tech-tips.com/windows-10/how-to-fix-media-is-write-protected-in-windows/
        """

        # Creating a script file in C: drive
        logger.info(f"Writing script file to clear Read-Only Attribute for Disk: {disk_number}")
        command: str = f"""
            Set-Location C:

            $value = @"\nselect disk {disk_number}\nattributes disk clear readonly\n"@

            New-Item "script.txt" -ItemType File -Value $value
        """
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(response)

        # Running script file created above
        logger.info(f"Clearing Read-Only Attribute for Disk: {disk_number}")
        command: str = """
            Set-Location C:
            diskpart /s .\\script.txt
        """
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(response)

        logger.info("Getting offline disk number")
        disk_number = self.get_offline_disk_number(ec2_instance_id=ec2_instance_id)
        logger.info(f"Offline disk number = {disk_number}")

        logger.info(f"Bringing disk online {disk_number}")
        self.bring_disks_online(ec2_instance_id=ec2_instance_id)
        logger.info(f"Disk: {disk_number} is now online!")

    def get_offline_disk_number(self, ec2_instance_id: str) -> str:
        """Returns the number of a OFFLINE disk -> an EBS volume which is not in offline and assigned a drive yet.
        supported version: windows

        NOTE: This method is currently assuming that there will only be 1 Offline disk at a given time.
        TODO: Improve to take into account multiple Offline disks.

        Args:
            ec2_instance_id (str): AWS EC2 instance ID

        Returns:
            str: Disk Number
        """
        command: str = "Get-Disk | Where-Object OperationalStatus -Eq Offline | ConvertTo-Json"
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(response)

        json_response = json.loads(response["StandardOutputContent"])
        logger.info(f"Get-Disk response = {json_response}")

        disk_number = json_response["DiskNumber"]
        logger.info(f"Raw disk number = {disk_number}")
        return disk_number

    def download_java_executable_in_windows_instance(self, ec2_instance_id: str, drive_letter: str):
        """Download java executable in windows EC2 instance
        supported version: windows

        Args:
            drive_letter (str): Drive where we download java executable file
        """
        command: str = f"""
        Set-Location {drive_letter}:
        mkdir vdbench
        $source = "https://download.oracle.com/java/17/latest/jdk-17_windows-x64_bin.msi"
        $destination = "{drive_letter}:\\vdbench\\java-installer.msi"
        $client = new-object System.Net.WebClient
        $cookie = "oraclelicense=accept-securebackup-cookie"
        $client.Headers.Add([System.Net.HttpRequestHeader]::Cookie, $cookie);
        $client.DownloadFile($source, $destination)
        """
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(f"response {response}")

    def install_java(self, ec2_instance_id: str, drive_letter: str = "C"):
        """Install java
        supported version: windows

        Args:
            drive_letter (str): Drive where we downloaded java exe file.Defaults to "C" Drive
        """
        command: str = f"""
        Set-Location {drive_letter}:\\vdbench
        msiexec.exe /i "{drive_letter}:\\vdbench\\java-installer.msi" /q /norestart
        """

        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(f"response {response}")

        command: str = f"""
        Set-Location {drive_letter}:\\vdbench

        $value = '[Environment]::SetEnvironmentVariable("JAVA_HOME",  "C:\\Program Files\\Java\\jdk-17", "Machine")'

        Add-Content -Path "java_home.ps1" -Value $value
        """

        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(f"response {response}")

        command: str = f"""
        Set-Location {drive_letter}:\\vdbench

        $value = '[System.Environment]::SetEnvironmentVariable("PATH", $Env:Path + ";C:\\Program Files\\Java\\jdk-17\\bin", "Machine")'

        Add-Content -Path "java_home.ps1" -Value $value
        """

        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(f"response {response}")

        command: str = f"""
        Set-Location {drive_letter}:\\vdbench
        .\\java_home.ps1
        """
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(f"response {response}")

    def check_java_version(self, ec2_instance_id: str, drive_letter: str = "C"):
        """Check java version
        supported version: windows

        Args:
            drive_letter (str): Drive where we installed java.Defaults to "C" Drive
        """
        command: str = f"""
        Set-Location {drive_letter}:
        $cmd = Get-WmiObject -Class Win32_Product -Filter "Name like '%Java%'"
        echo $cmd
        """
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(f"response {response}")
        assert "Java" in response["StandardOutputContent"], f"Java not installed, {response['StandardOutputContent']}"

    def install_java_in_windows_instance(self, ec2_instance_id: str, drive_letter: str = "C"):
        """Install java in windows EC2 instance
        supported version: windows

        Args:
            drive_letter (str): Drive where we download java exe file.Defaults to "C" Drive
        """
        self.download_java_executable_in_windows_instance(ec2_instance_id=ec2_instance_id, drive_letter=drive_letter)
        self.install_java(ec2_instance_id=ec2_instance_id, drive_letter=drive_letter)
        self.check_java_version(ec2_instance_id=ec2_instance_id, drive_letter=drive_letter)

    def download_openssh_file_in_windows_instance(self, ec2_instance_id: str, drive_letter: str = "C"):
        """Download openssh zip file in windows EC2 instance
        supported version: windows

        Args:
            drive_letter (str): Drive where we download openssh file.Defaults to C Drive
        """

        command: str = f"""
        Set-Location {drive_letter}:
        $source = "https://github.com/PowerShell/Win32-OpenSSH/releases/download/v9.2.0.0p1-Beta/OpenSSH-Win32.zip"
        $destination = "{drive_letter}:\\vdbench\\OpenSSH-Win32.zip"
        $client = new-object System.Net.WebClient
        $cookie = "oraclelicense=accept-securebackup-cookie"
        $client.Headers.Add([System.Net.HttpRequestHeader]::Cookie, $cookie);
        $client.DownloadFile($source, $destination)
        Expand-Archive -Path "{drive_letter}:\\vdbench\\OpenSSH-Win32.zip" -DestinationPath "{drive_letter}:\\vdbench"
        """
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(f"response {response}")

    def install_openssh(self, ec2_instance_id: str, drive_letter: str = "C"):
        """Install openssh in windows instance
        supported version: windows

        Args:
            drive_letter (str): drive where we downloaded openssh.Defaults to "C" Drive
        """

        command: str = f"""
        Set-Location {drive_letter}:
        powershell -ExecutionPolicy Bypass -File {drive_letter}:\\vdbench\\OpenSSH-Win32\\install-sshd.ps1
        Start-Service sshd
        Set-Service -Name sshd -StartupType 'Automatic'
        if (!(Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue | Select-Object Name, Enabled)) {{
        Write-Output "Firewall Rule 'OpenSSH-Server-In-TCP' does not exist, creating it..."
        New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
        }} else {{
            Write-Output "Firewall rule 'OpenSSH-Server-In-TCP' has been created and exists."
        }}
        """
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(f"response {response}")

    def install_openssh_in_windows_using_powershell(self, ec2_instance_id: str, drive_letter: str = "C"):
        """Install openssh in Windows using powershell script
        supported version: windows

        Args:
            drive_letter (str): drive where we download openssh.Defaults to "C" Drive
        """
        self.download_openssh_file_in_windows_instance(ec2_instance_id=ec2_instance_id, drive_letter=drive_letter)
        self.install_openssh(ec2_instance_id=ec2_instance_id, drive_letter=drive_letter)

    def copy_vdbench_executable_to_remote_host(
        self,
        ec2_instance,
        username: str,
        password: str,
        private_key_file_path: str,
        resources_directory: str,
        vdbench_archive: str,
        drive_letter: str = "C",
    ):
        """Copy vdbench executable from local to windows EC2 instance
        supported version: windows

        Args:
            ec2_instance (Object): EC2 instance object
            username (str): EC2 username
            password (str): EC2 password
            private_key_file_path (str): EC2 key pair file name
            drive_letter (str): drive where we store vdbench archive in windows instance.Defaults to "C" Drive
            resources_directory (str): Local resources directory where stored vdbench zip file
            vdbench_archive (str): vdbench archive name

        Example Command:
            sshpass -p "X&?C&yMIdfDXSmF=zvDkYjAyw5T(.g?G" scp -o 'StrictHostKeyChecking no' -i ec2-key-73fe731c-3ed5-40ef-8569-4f8a4eef7b1e.pem -r /workspaces/qa_automation/Medusa/lib/platform/resources/vdbench/vdbench50407.zip Administrator@ec2-35-91-155-14.us-west-2.compute.amazonaws.com:D:\\java
        """

        vdbench_path = os.path.join(resources_directory, vdbench_archive)
        command: str = f"""
        sshpass -p'{password}' scp -v -o 'StrictHostKeyChecking no' -i {private_key_file_path} -r {vdbench_path} {username}@{ec2_instance.public_dns_name}:{drive_letter}:\\vdbench
        """
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        logger.info(f"command {command}")
        logger.info(f"output {result.stdout}")
        logger.info(f"error {result.stderr}")
        command: str = f"""
        Set-Location {drive_letter}:
        Expand-Archive -Path "{drive_letter}:\\vdbench\\{vdbench_archive}" -DestinationPath "{drive_letter}:\\vdbench\\vdbench50407"
        """
        response = self.run_command(ec2_instance_id=ec2_instance.id, command=command)
        logger.info(f"response {response}")

    def setup_vdbench_in_windows_instance(
        self,
        ec2_instance,
        ec2_key_pair: str,
        ec2_password: str,
        drive_letter: str = "C",
    ):
        """Setting up vdbench configuration in windows EC2 instance
            Installing java and openssh
            Copying vdbench executable to windows EC2 instance
            supported version: windows

        Args:
            ec2_instance (Object): windows ec2 instance
            ec2_key_pair (str): EC2 Key pair
            ec2_password (str): EC2 password
            drive_letter (str): Drive where required softwares are installed.Default to "C" Drive
        """

        logger.info("Download and Install java in windows EC2 instance")
        self.install_java_in_windows_instance(ec2_instance_id=ec2_instance.id, drive_letter=drive_letter)

        logger.info("Download and Install openssh in windows instance")
        self.install_openssh_in_windows_using_powershell(ec2_instance_id=ec2_instance.id, drive_letter=drive_letter)

        logger.info("Copy vdbench executable in windows")
        self.copy_vdbench_executable_to_remote_host(
            ec2_instance=ec2_instance,
            username="Administrator",
            password=ec2_password,
            private_key_file_path=f"{ec2_key_pair}.pem",
            resources_directory=self.vdbench_config["resources-directory"],
            vdbench_archive=self.vdbench_config["vdbench-archive"],
            drive_letter=drive_letter,
        )

    def create_vdbench_config_in_ec2_instance(
        self,
        ec2_instance_id: str,
        content: str,
        drive_letter: str,
        config_file: str,
    ):
        """Create vdbench config file in windows EC2 instance
        supported version: windows

        Args:
            content (str): Content for config file
            drive_letter (str): Drive where we store vdbench config file
            config_file (str): Config file name on windows EC2 instance.By default config file name is "config" which we defined in variables_base.ini file under vdbench section

        """

        config_file_path = f"vdbench\\{self.vdbench_config['vdbench-folder']}\\{config_file}"
        command: str = f"""
        Set-Location {drive_letter}:
        $content = "{content}"
        Set-Content -Path .\\{config_file_path} -Value $content
        """
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        logger.info(f"Response {response}")

    def create_vdbench_config_file_for_generating_files_and_dirs(
        self,
        ec2_instance_id: str,
        file_size: str,
        file_count: int,
        dir_name: str,
        depth: int,
        width: int,
        devices: list[str],
        drive_letter: str,
    ):
        """Create vdbench config file for generating files and directories
        supported version: windows

        Args:
            file_size (str): Size of each file
            file_count (int): Number of files need to be created
            dir_name (str): Source Directory name where files and dirs are generated
            depth (int): Depth of files/dirs
            width (int): Width of files/dirs
            devices (list[str]): List of disk drives where data needs to be generated
            drive_letter (str): Disk drive where we create vdbench config file
        """
        config_file = self.vdbench_config["vdbench-config-file"]
        fsd = self.vdbench_config["fsd"]
        fwd = self.vdbench_config["fwd"]
        frd = self.vdbench_config["frd"]
        basic_content = list()
        fsd_content = list()
        fwd_content = list()
        frd_content = list()
        for serial, device in enumerate(devices, start=1):
            config = {"basic": {}, "fsd": {}, "fwd": {}, "frd": {}}
            source_dir = f"{device}:\\{dir_name}"
            storage_definition = fsd % (
                serial,
                source_dir,
                depth,
                width,
                file_count,
                file_size,
            )
            # Use backtick (`) to enclose variable $operation and $format since we are running vdbench in powershell
            workload_definition = fwd % (serial, serial, "`$operation`")
            run_definition = frd % (serial, "`$format`")
            if serial == 1:
                config["basic"].update(
                    json.loads(
                        BasicParameters(
                            comp_ratio=f"compratio={self.vdbench_config['compratio']}",
                            validate=f"validate={self.vdbench_config['validate']}",
                            dedup_ratio=f"dedupratio={self.vdbench_config['validate']}",
                            dedup_unit=f"dedupunit={self.vdbench_config['dedupunit']}\n",
                        ).to_json()
                    )
                )
                config["fsd"].update(json.loads(StorageDefinitions(storage_definition=storage_definition).to_json()))
                config["fwd"].update(json.loads(WorkloadDefinitions(workload_definition=workload_definition).to_json()))
                config["frd"].update(json.loads(RunDefinitions(run_definition=run_definition).to_json()))
                basic_content.extend(list(config["basic"].values()))
                fsd_content.extend(list(config["fsd"].values()))
                fwd_content.extend(list(config["fwd"].values()))
                frd_content.extend(list(config["frd"].values()))
            else:
                config["fsd"].update(json.loads(StorageDefinitions(storage_definition=storage_definition).to_json()))
                config["fwd"].update(json.loads(WorkloadDefinitions(workload_definition=workload_definition).to_json()))
                config["frd"].update(json.loads(RunDefinitions(run_definition=run_definition).to_json()))
                fsd_content.extend(list(config["fsd"].values()))
                fwd_content.extend(list(config["fwd"].values()))
                frd_content.extend(list(config["frd"].values()))
        content = basic_content + fsd_content + fwd_content + frd_content
        content = ["\n" + line for line in content]
        content = "".join(content)
        logger.info(f"content {content}")
        self.create_vdbench_config_in_ec2_instance(
            ec2_instance_id=ec2_instance_id,
            content=content,
            drive_letter=drive_letter,
            config_file=config_file,
        )

    def run_vdbench(self, ec2_instance_id: str, drive_letter: str, config_file: str, validate: bool):
        """run vdbench with config file
        supported version: windows

        Args:
            drive_letter (str): Drive where vdbench is installed
            config_file (str): Vdbench config file name in windows instance
            validate (Bool): True for read operation and False for write operation
        """

        success_message = "Vdbench execution completed successfully"
        if validate:
            command: str = f"""
            Set-Location {drive_letter}:\\vdbench\\{self.vdbench_config["vdbench-folder"]}
            $env:PATH = "C:\\Program Files\\Java\\jdk-17\\bin;$env:PATH"
            Invoke-Expression -Command ".\\vdbench.bat -f {config_file} format=no operation=read"
            """
        else:
            command: str = f"""
            Set-Location {drive_letter}:\\vdbench\\{self.vdbench_config["vdbench-folder"]}
            $env:PATH = "C:\\Program Files\\Java\\jdk-17\\bin;$env:PATH"
            Invoke-Expression -Command ".\\vdbench.bat -f {config_file} format=yes operation=write"
            """
        response = self.run_command(ec2_instance_id=ec2_instance_id, command=command)
        standard_output = response["StandardOutputContent"]
        print(standard_output)
        logger.info(f"response {response}")
        assert success_message in standard_output, f"Vdbench execution failed, {standard_output}"

    def write_and_validate_data_vdbench(
        self,
        ec2_instance_id: str,
        file_size: str,
        file_count: int,
        dir_name: str,
        depth: int,
        width: int,
        devices: list[str],
        source_drive: str,
        validate: bool = False,
    ):
        """Write and Validate data using vdbench
        supported version: windows

        Args:
            file_size (str): Size of each file
            file_count (int): Number of files need to be created
            dir_name (str): Source Directory name where files and dirs are generated
            depth (int): Depth of files/dirs
            width (int): Width of files/dirs
            devices (list[str]): List of disk drives where data needs to be generated
            source_drive (str): Disk drive where we install vdbench,java and openssh.Also where we store config file and execute vdbench
            validate (bool, optional): True for read operation and False for write operation. Defaults to False.

        Sample Usage: write_and_validate_data_vdbench(
        file_size="1g",file_count=2,dir_name="dir1",depth=1,
        width=2,devices=[DRIVE_LETTER],source_drive=DRIVE_LETTER,validate=True)
        """
        self.create_vdbench_config_file_for_generating_files_and_dirs(
            ec2_instance_id=ec2_instance_id,
            file_size=file_size,
            file_count=file_count,
            dir_name=dir_name,
            depth=depth,
            width=width,
            devices=devices,
            drive_letter=source_drive,
        )

        self.run_vdbench(
            ec2_instance_id=ec2_instance_id,
            drive_letter=source_drive,
            config_file=self.vdbench_config["vdbench-config-file"],
            validate=validate,
        )

    def copy_vdbench_custom_config_file_to_ec2_instance(
        self,
        ec2_instance_id: str,
        drive_letter: str,
        config_file: str,
    ):
        """Copy vdbench custom config file to config file in windows ec2 instance
        supported version: windows

        Args:
            drive_letter (str): Drive where config file is stored
            config_file (str): vdbench config file in windows instance
        """
        file_path = self.vdbench_config["vdbench_windows_custom_config_file"]
        with open(file_path) as f:
            content = f.read()
        self.create_vdbench_config_in_ec2_instance(
            ec2_instance_id=ec2_instance_id,
            content=content,
            drive_letter=drive_letter,
            config_file=config_file,
        )

    def write_and_validate_data_vdbench_with_custom_config_file(
        self,
        ec2_instance_id: str,
        source_drive: str,
        remote_config_file: str,
        validate: bool = False,
    ):
        """Write and validate data using vdbench with custom config file
        supported version: windows

            Args:
                source_drive (str): Disk drive where we install vdbench,java and openssh.Also where we store config file and execute vdbench
                remote_config_file (str): vdbench config file name in windows instance
                validate (bool, optional): True for read operation and False for write operation. Defaults to False.
            Sample Usage:
                write_and_validate_data_vdbench_with_custom_config_file(
                source_drive=DRIVE_LETTER, remote_config_file=vdbench_config_file
        )
        """
        self.copy_vdbench_custom_config_file_to_ec2_instance(
            ec2_instance_id=ec2_instance_id,
            drive_letter=source_drive,
            config_file=remote_config_file,
        )
        self.run_vdbench(
            ec2_instance_id=ec2_instance_id,
            drive_letter=source_drive,
            config_file=remote_config_file,
            validate=validate,
        )

    def check_command(
        self,
        ec2_instance_id: str,
        command: str,
        command_type: SSMCommandType = SSMCommandType.LINUX,
    ) -> bool:
        """Check whether the command exits or not
        supported version: linux

        Args:
            ec2_instance_id (str): AWS EC2 instance ID
            command (str): Command to run on the EC2 instance. Make sure to properly escape characters like '\' etc.
            command_type (SSMCommandType, optional): Linux . Defaults to AWS-RunShellScript.LINUX.value

        Returns:
            Bool: Return True if command exists else return False
        """

        ssm_check_command = self.ssm_client.send_command(
            InstanceIds=[ec2_instance_id],
            DocumentName=command_type,
            DocumentVersion="1",
            Parameters={"commands": [command]},
        )

        ssm_check_command_id = ssm_check_command["Command"]["CommandId"]

        # Verify the command exist
        response = self.ssm_client.list_commands(CommandId=ssm_check_command_id)
        if "Commands" in response and response["Commands"]:
            command_status = response["Commands"][0]["Status"]
            if command_status == "Success":
                return True
        return False

    def get_devices(self, ec2_instance_id: str, command_type: SSMCommandType.LINUX) -> list[str]:
        # Information on EC2 block devices:
        # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/block-device-mapping-concepts.html
        command = "lsblk --output KNAME -n"
        output = self.run_command(
            ec2_instance_id=ec2_instance_id,
            command=command,
            command_type=command_type,
        )
        devices = output["StandardOutputContent"].split("\n")
        # To remove null value in the response
        device_list = [device for device in devices if device]
        devices = [
            device
            for device in device_list
            # Skipping xvda, which is a root volume by default.
            if (len(device) < 5 and not device.endswith("a"))
            or (len(device) > 5 and len(device) < 8)
            and not device.endswith("0n1")
            and not device.endswith("14")  # device names on Ubuntu and Debian xvda14 and xvda15 which are boot devices
            and not device.endswith("15")
            and not device.endswith("127")
            and not device.endswith("128")
        ]
        return devices

    def get_volume_size(self, ec2_instance_id: str, command_type: SSMCommandType.LINUX, device: str):
        command = f"lsblk -no SIZE /dev/{device}"
        stdout = self.run_command(
            ec2_instance_id=ec2_instance_id,
            command=command,
            command_type=command_type,
        )
        # Get volume size in GB and convert to MB
        # eg: 8G -> 8 -> 8 * 1024 = 8096
        return str_gb_to_mb(stdout["StandardOutputContent"])

    def run_dmcore(
        self,
        ec2_instance_id: str,
        user_name: str,
        command_type: SSMCommandType = SSMCommandType.LINUX,
        percentage_to_fill: int = 80,
        block_size: str = "4k",
        compression_ratio=4,
        compression_method=4,
        offset=0,
        validation=False,
        change_block_percentage: int = 20,
    ) -> bool:
        """Run dmcore with given specifications, compression ratio and compression method is set to 4 by default.
        This will help us get around 4:1 dedupe ratio in store once appliance.
        Use offset to do the incremental backup

        supported version : Linux

        Args:
            ec2_instance_id (str): AWS EC2 ID on which data has to be written or validated
            user_name (str): ec2 user name to be used to determine the home directory
            command_type (SSMCommandType, optional): LINUX. Defaults to LINUX for AWS-RunShellScript
            percentage_to_fill (int, optional): Defaults to 80.
            block_size (str, optional): Defaults to "4k".
            compression_ratio (int, optional): Defaults to 4.
            compression_method (int, optional): Defaults to 4.
            offset (int, optional): Defaults to 0.
            validation (bool, optional): Defaults to True.
            change_block_percentage (int, optional): Defaults to 20

        Returns:
            bool : True for operation success else False
        """
        success = False
        for device in self.get_devices(ec2_instance_id, command_type):
            success = self.run_dm_core_on_custom_drive(
                ec2_instance_id=ec2_instance_id,
                user_name=user_name,
                device=device,
                command_type=command_type,
                percentage_to_fill=percentage_to_fill,
                block_size=block_size,
                compression_ratio=compression_ratio,
                compression_method=compression_method,
                offset=offset,
                validation=validation,
                change_block_percentage=change_block_percentage,
            )
        logger.info(f"Dmcore success value is {success}")
        return success

    def run_dm_core_on_custom_drive(
        self,
        user_name: str,
        ec2_instance_id: str,
        device: str,
        command_type: SSMCommandType = SSMCommandType.LINUX,
        percentage_to_fill: int = 80,
        block_size: str = "4k",
        compression_ratio=4,
        compression_method=4,
        offset=0,
        validation=False,
        change_block_percentage: int = 20,
        export_file_name: str = None,
    ) -> bool:
        """Run dmcore with given specifications, compression ratio and compression method is set to 4 by default.
        This will help us get around 4:1 dedupe ratio in store once appliance.
        Use offset to do the incremental backup

        Args:
            user_name (str): ec2 user name to be used to determine the home directory
            ec2_instance_id (str): AWS EC2 ID on which data has to be written or validated
            device (str): volume on which the data has to be written. Eg. xvda, xvdh, etc.
            command_type (SSMCommandType): command type to be used to execute in linux
            percentage_to_fill (int, optional): Defaults to 80.
            block_size (str, optional): Defaults to "4k".
            compression_ratio (int, optional): Defaults to 4.
            compression_method (int, optional): Defaults to 4.
            offset (int, optional): Defaults to 0.
            validation (bool, optional): Defaults to True.
            change_block_percentage (int, optional): Defaults to 20
            export_file_name (str, option): Provide a value if data is supposed to be written to a file system.
                                            Defaults to None

        Returns:
            bool : True for operation success else False
        """
        total_block_change = int((change_block_percentage * 100) / 50)
        command: str = ""
        success = False
        # Convert size from GB to MB and type integer
        size = int((self.get_volume_size(ec2_instance_id, command_type, device) / 100) * percentage_to_fill)

        export_file_name = export_file_name if export_file_name else f"/dev/{device}"

        if not validation:
            # Data write command
            command = f"./dmcore Command=Write DMExecSet=Nas DMVerificationMode=MD5 ExportFileName={export_file_name} WriteT={size}m seed=1 WriteI={block_size} Offset={str(offset)} CompressionRatio={str(compression_ratio)} CompressionMethod={str(compression_method)} InternalBlockChange=50 TotalBlockChange={total_block_change}"
        else:
            # Data Read and validate command
            command = f"./dmcore Command=Read DMExecSet=Nas ImportFileName={export_file_name} ReadT={size}m ReadI={block_size}  Validation=1"
        # AWS session manager default login /usr/bin will change the directory and execute
        combined_command = f"cd /home/{user_name} && {command}"
        stdout = self.run_command(
            ec2_instance_id=ec2_instance_id,
            command_type=command_type,
            command=combined_command,
        )
        logger.info(stdout)
        time.sleep(10)
        for line in stdout["StandardOutputContent"].split("\n"):
            logger.info(line)
            if 'ReturnMessage="Success"' in line:
                success = True
                break
            elif 'ReturnMessage="Error"' in line:
                logger.error(stdout)
                break
        else:
            success = False

        logger.info(f"Dmcore success value is {success}")
        return success

    def copy_file_to_ec2_instance(
        self,
        local_file_path: str,
        remote_file_path: str,
        key_name: str,
        user_name: str,
        ec2_instance_address: str,
    ) -> int:
        """Function copy file to remote EC2 instance using secure copy.

        Args:
            local_file_path (str): relative file path of the file in local machine.
            remote_file_path (str): absolute path of the file in the remote machine.
            key_name (str): key pair name associated with the EC2 instance.
            user_name (str): username for the EC2 instance to use.
            ec2_instance_address (str): public dns name or IP address of the EC2 instance.

        Note:
        Failure message is sent to the logger.
        scp is agnostic, file at the remote will be replaced if already exists. No exception is raised.

        Returns:
            int: return code as 0 or 1. 0 indicates a successful copy, 1 indicates a failure.
        """
        subprocess.run(f"chmod 400 {key_name}.pem", shell=True, capture_output=True, text=True)

        command = f"scp -o 'StrictHostKeyChecking no' -i '{key_name}.pem' -r {local_file_path} {user_name}@{ec2_instance_address}:{remote_file_path}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 1:
            logger.error(f"Copy file {local_file_path} to EC2 instance failed!")
            logger.error(result.stderr)
        return result.returncode

    def copy_dmcore_to_linux_ec2_instance(self, ec2_instance: Instance, user_name: str):
        """Method copies the dmcore binary located in the lib/platform/resources/dmcore/dmcore
        to remote Linux machine's home directory /home/<username>/dmcore and set execution permission.
        Make sure to keep the .pem key in the current working directory for the function to work.

        Args:
            ec2_instance (str): EC2 instance ID to copy the dmcore binary.
            user_name (str): EC2 Linux user name to determine the home directory
        """
        local_file_path = self.dmcore_config["binary"]
        remote_file_path = f"/home/{user_name}/dmcore"
        # Command uses secure copy to transfer the file from local to the remote EC2 instance using pem key.
        return_code = self.copy_file_to_ec2_instance(
            user_name=user_name,
            key_name=ec2_instance.key_name,
            ec2_instance_address=ec2_instance.public_dns_name,
            local_file_path=local_file_path,
            remote_file_path=remote_file_path,
        )
        if return_code != 0:
            assert False, "Copy DMCore failed!, Please check error message for more information."
        # Linux command to set execution permission for the dmcore binary
        command = f"chmod +x /home/{user_name}/dmcore"
        # Execute the linux command
        self.run_command(
            ec2_instance_id=ec2_instance.id,
            command=command,
            command_type=SSMCommandType.LINUX,
        )

    def format_volume_and_mount(
        self,
        file_system_device: str,
        file_system_type: LinuxFileSystemTypes,
        ec2_instance_id: str,
        mount_point: str,
        partition_number: str = "1",
        command_type: SSMCommandType = SSMCommandType.LINUX,
    ):
        """Create partition, Format and mount an attached EBS volume.
        supported version : Linux

        Args:
            file_system_device (str): The attached EBS Volume device (i.e. /dev/xvdh)
            file_system_type (LinuxFileSystemTypes): The File System Type to format (i.e. xfs, ext3, ext4)
            ec2_instance_id (str): AWS EC2 ID of the attache volume to be partitioned,create file system and mount
            mount_point (str): The directory to mount the attached EBS Volume (it's encouraged to specifiy a directory starting with /mnt)
            partition_number: (str): Partition number should be in range of [1 to 4]. default to 1
            command_type (SSMCommandType): command type to be used to execute in linux
        """
        # create partition
        command = f"""
        echo -e '\nn\np\n{partition_number}\n\n\nw' | fdisk {file_system_device}
        """
        logger.info(f"Create partition : {command}")
        output = self.run_command(
            ec2_instance_id=ec2_instance_id,
            command_type=command_type,
            command=command,
        )
        logger.info(output)
        file_system_device = file_system_device + partition_number

        # make file system on EBS block device | xfs, ext3, ext4
        command = f"sudo mkfs -t {file_system_type.value} {file_system_device}"
        logger.info(f"Creating file system on device: {command}")
        output = self.run_command(
            ec2_instance_id=ec2_instance_id,
            command_type=command_type,
            command=command,
        )
        logger.info(output)

        # create directory to mount EBS volume onto
        command = f"sudo mkdir -p {mount_point}"
        logger.info(f"Create mount point directory: {command}")
        output = self.run_command(
            ec2_instance_id=ec2_instance_id,
            command_type=command_type,
            command=command,
        )
        logger.info(output)

        # mount the EBS volume to /ebs_volume directory
        command = f"sudo mount {file_system_device} {mount_point}"
        logger.info(f"mount device to mount point: {command}")
        output = self.run_command(
            ec2_instance_id=ec2_instance_id,
            command_type=command_type,
            command=command,
        )
        logger.info(output)

    def disable_selinux(
        self,
        ec2_instance_id: str,
    ):
        """disable the selinux for redhat and suse
        supported version : Linux
        NOTE# observed selinux is available only in redhat and suse linux flavors
        Args:
            ec2_instance_id (str): AWS EC2 ID on which data has to be written or validated
        """

        command = "sudo setenforce 0 && sudo sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config"
        logger.info(f"disable the selinux: {command}")
        output = self.run_command(
            ec2_instance_id=ec2_instance_id,
            command_type=SSMCommandType.LINUX,
            command=command,
        )
        logger.info(output)

    def start_service(
        self,
        ec2_instance_id: str,
        service_name: str,
        command_type: SSMCommandType = SSMCommandType.LINUX,
    ):
        """Start provided linux service
        supported version : Linux

        Args:
            ec2_instance_id (str): AWS EC2 ID on which data has to be written or validated
            service_name (str): linux service name such as amazon-ssm-agent
            command_type (SSMCommandType): command type to be used to execute in linux
        """

        # start linux service
        command = f"sudo systemctl start {service_name}"
        logger.info(f"start linux {service_name} service: {command}")
        output = self.run_command(
            ec2_instance_id=ec2_instance_id,
            command_type=command_type,
            command=command,
        )
        logger.info(output)

    def stop_service(
        self,
        ec2_instance_id: str,
        service_name: str,
        command_type: SSMCommandType = SSMCommandType.LINUX,
    ):
        """Stop provided linux service
        supported version : Linux

        Args:
            ec2_instance_id (str): AWS EC2 ID on which data has to be written or validated
            service_name (str): linux service name such as amazon-ssm-agent
            command_type (SSMCommandType): command type to be used to execute in linux
        """

        # stop linux service
        command = f"sudo systemctl stop {service_name}"
        logger.info(f"stop linux {service_name} service: {command}")
        output = self.run_command(
            ec2_instance_id=ec2_instance_id,
            command_type=command_type,
            command=command,
        )
        logger.info(output)
