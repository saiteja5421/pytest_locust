import json
import logging
import os
import time
import uuid
from tenacity import retry, stop_after_attempt, wait_fixed
import subprocess

# Imports for connecting to Windows VM
import winrm
from lib.common.common import is_retry_needed, raise_my_exception
from lib.common.enums.command_type import CommandType
from tests.e2e.aws_protection.context import Context
from lib.platform.host.vdbench_config_models import (
    BasicParameters,
    StorageDefinitions,
    WorkloadDefinitions,
    RunDefinitions,
)
from json import loads


from lib.platform.host.models.file_hash import FileHash, FileHashList

logger = logging.getLogger()


class WindowsIOManager:
    def __init__(self, session: winrm.Session) -> None:
        """Provide the session object to instantiate this object.

        Args:
            session (winrm.Session): Session returned by connect_to_windows_vm() method in WindowsSessionManager
        """
        self.session = session

    @retry(
        retry=is_retry_needed,
        stop=stop_after_attempt(10),
        wait=wait_fixed(5),
        retry_error_callback=raise_my_exception,
    )
    def run_cmd_on_win_vm(
        self,
        command: str,
        command_type: CommandType = CommandType.Powershell,
    ) -> str:
        """Runs the specified CMD | Powershell command

        Args:
            command (str): Command to be executed on the VM
            command_type (CommandType): CMD or Powershell. Defaults to Powershell.
        """

        if command_type == CommandType.Powershell:
            response = self.session.run_ps(command)
        else:  # Runs CMD commands
            response = self.session.run_cmd(command)

        assert (
            response.status_code == 0
        ), f"Command {command} failed with error {response.std_err}, error code = {response.status_code}"
        return response.std_out.decode("utf-8")

    def get_vm_hostname(self) -> str:
        """Returns the hostname of the VM

        Returns:
            str: hostname of the VM
        """
        command: str = "hostname"
        hostname = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        logger.info(f"Hostname = {hostname}")
        return hostname.strip()

    def setup_vdbench_in_windows_instance(
        self, context: Context, ec2_instance, ec2_key_pair: str, ec2_password: str, drive_letter: str = "C"
    ):
        """Setting up vdbench configuration in windows EC2 instance
            Installing java and openssh
            Copying vdbench executable to windows EC2 instance

        Args:
            context (Object): Context
            ec2_instance (Object): windows ec2 instance
            ec2_key_pair (str): EC2 Key pair
            ec2_password (str): EC2 password
            drive_letter (str): Drive where required softwares are installed.Default to "C" Drive
        """

        logger.info("Download and Install java in windows EC2 instance")
        self.install_java_in_windows_instance(drive_letter=drive_letter)

        logger.info("Download and Install openssh in windows instance")
        self.install_openssh_in_windows_using_powershell(drive_letter=drive_letter)

        logger.info("Copy vdbench executable in windows")
        self.copy_vdbench_executable_to_remote_host(
            ec2_instance=ec2_instance,
            username="Administrator",
            password=ec2_password,
            private_key_file_path=f"{ec2_key_pair}.pem",
            resources_directory=context.resources_directory,
            vdbench_archive=context.vdbench_archive,
            drive_letter=drive_letter,
        )

    def write_and_validate_data_vdbench(
        self,
        context: Context,
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

        Args:
            context (Context): Context object
            file_size (str): Size of each file
            file_count (int): Number of files need to be created
            dir_name (str): Source Directory name where files and dirs are generated
            depth (int): Depth of files/dirs
            width (int): Width of files/dirs
            devices (list[str]): List of disk drives where data needs to be generated
            source_drive (str): Disk drive where we install vdbench,java and openssh.Also where we store config file and execute vdbench
            validate (bool, optional): True for read operation and False for write operation. Defaults to False.

        Sample Usage: write_and_validate_data_vdbench(
        context=context,file_size="1g",file_count=2,dir_name="dir1",depth=1,
        width=2,devices=[DRIVE_LETTER],source_drive=DRIVE_LETTER,validate=True)
        """
        self.create_vdbench_config_file_for_generating_files_and_dirs(
            context=context,
            file_size=file_size,
            file_count=file_count,
            dir_name=dir_name,
            depth=depth,
            width=width,
            devices=devices,
            drive_letter=source_drive,
        )

        self.run_vdbench(
            context=context, drive_letter=source_drive, config_file=context.vdbench_config_file, validate=validate
        )

    def write_and_validate_data_vdbench_with_custom_config_file(
        self, context: Context, source_drive: str, remote_config_file: str, validate: bool = False
    ):
        """Write and validate data using vdbench with custom config file

            Args:
                context (Context): Context Object
                source_drive (str): Disk drive where we install vdbench,java and openssh.Also where we store config file and execute vdbench
                remote_config_file (str): vdbench config file name in windows instance
                validate (bool, optional): True for read operation and False for write operation. Defaults to False.
            Sample Usage:
                write_and_validate_data_vdbench_with_custom_config_file(
                context=context, source_drive=DRIVE_LETTER, remote_config_file=context.vdbench_config_file
        )
        """
        self.copy_vdbench_custom_config_file_to_ec2_instance(
            context, drive_letter=source_drive, config_file=remote_config_file
        )
        self.run_vdbench(context=context, drive_letter=source_drive, config_file=remote_config_file, validate=validate)

    def copy_vdbench_custom_config_file_to_ec2_instance(self, context: Context, drive_letter: str, config_file: str):
        """Copy vdbench custom config file to config file in windows ec2 instance

        Args:
            context (Context): Context object
            drive_letter (str): Drive where config file is stored
            config_file (str): vdbench config file in windows instance
        """
        file_path = context.vdbench_windows_custom_config_file
        with open(file_path) as f:
            content = f.read()
        self.create_vdbench_config_in_ec2_instance(
            context=context, content=content, drive_letter=drive_letter, config_file=config_file
        )

    def create_vdbench_config_file_for_generating_files_and_dirs(
        self,
        context: Context,
        file_size: str,
        file_count: int,
        dir_name: str,
        depth: int,
        width: int,
        devices: list[str],
        drive_letter: str,
    ):
        """Create vdbench config file for generating files and directories

        Args:
            context (Context): Context object
            file_size (str): Size of each file
            file_count (int): Number of files need to be created
            dir_name (str): Source Directory name where files and dirs are generated
            depth (int): Depth of files/dirs
            width (int): Width of files/dirs
            devices (list[str]): List of disk drives where data needs to be generated
            drive_letter (str): Disk drive where we create vdbench config file
        """
        config_file = context.vdbench_config_file
        basic_content = list()
        fsd_content = list()
        fwd_content = list()
        frd_content = list()
        for serial, device in enumerate(devices, start=1):
            config = {"basic": {}, "fsd": {}, "fwd": {}, "frd": {}}
            source_dir = f"{device}:\\{dir_name}"
            storage_definition = context.fsd % (serial, source_dir, depth, width, file_count, file_size)
            # Use backtick (`) to enclose variable $operation and $format since we are running vdbench in powershell
            workload_definition = context.fwd % (serial, serial, "`$operation`")
            run_definition = context.frd % (serial, "`$format`")
            if serial == 1:
                config["basic"].update(
                    loads(
                        BasicParameters(
                            comp_ratio=f"compratio={context.compratio}",
                            validate=f"validate={context.validate}",
                            dedup_ratio=f"dedupratio={context.dedupratio}",
                            dedup_unit=f"dedupunit={context.dedupunit}\n",
                        ).to_json()
                    )
                )
                config["fsd"].update(loads(StorageDefinitions(storage_definition=storage_definition).to_json()))
                config["fwd"].update(loads(WorkloadDefinitions(workload_definition=workload_definition).to_json()))
                config["frd"].update(loads(RunDefinitions(run_definition=run_definition).to_json()))
                basic_content.extend(list(config["basic"].values()))
                fsd_content.extend(list(config["fsd"].values()))
                fwd_content.extend(list(config["fwd"].values()))
                frd_content.extend(list(config["frd"].values()))
            else:
                config["fsd"].update(loads(StorageDefinitions(storage_definition=storage_definition).to_json()))
                config["fwd"].update(loads(WorkloadDefinitions(workload_definition=workload_definition).to_json()))
                config["frd"].update(loads(RunDefinitions(run_definition=run_definition).to_json()))
                fsd_content.extend(list(config["fsd"].values()))
                fwd_content.extend(list(config["fwd"].values()))
                frd_content.extend(list(config["frd"].values()))
        content = basic_content + fsd_content + fwd_content + frd_content
        content = ["\n" + line for line in content]
        content = "".join(content)
        logger.info(f"content {content}")
        self.create_vdbench_config_in_ec2_instance(
            context=context, content=content, drive_letter=drive_letter, config_file=config_file
        )

    def run_vdbench(self, context: Context, drive_letter: str, config_file: str, validate: bool):
        """run vdbench with config file

        Args:
            context (Context): Context Object
            drive_letter (str): Drive where vdbench is installed
            config_file (str): Vdbench config file name in windows instance
            validate (Bool): True for read operation and False for write operation
        """

        success_message = "Vdbench execution completed successfully"
        if validate:
            command: str = f"""
            Set-Location {drive_letter}:\\vdbench\\{context.vdbench_folder}
            .\\vdbench.bat -f {config_file} format=no operation=read
            """
        else:
            command: str = f"""
            Set-Location {drive_letter}:\\vdbench\\{context.vdbench_folder}
            .\\vdbench.bat -f {config_file} format=yes operation=write
            """
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        logger.info(f"response {response}")
        assert success_message in response, "Vdbench execution failed"

    def create_vdbench_config_in_ec2_instance(
        self, context: Context, content: str, drive_letter: str, config_file: str
    ):
        """Create vdbench config file in windows EC2 instance

        Args:
            context (Context): Context object
            content (str): Content for config file
            drive_letter (str): Drive where we store vdbench config file
            config_file (str): Config file name on windows EC2 instance.By default config file name is "config" which we defined in variables_base.ini file under vdbench section

        """

        config_file_path = f"vdbench\\{context.vdbench_folder}\\{config_file}"
        command: str = f"""
        Set-Location {drive_letter}:
        $content = "{content}"
        Set-Content -Path .\\{config_file_path} -Value $content
        """
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        logger.info(f"Response {response}")

    def download_java_executable_in_windows_instance(self, drive_letter: str):
        """Download java executable in windows EC2 instance

        Args:
            drive_letter (str): Drive where we download java executable file
        """

        command: str = f"""
        Set-Location {drive_letter}:
        mkdir vdbench
        $source = "https://download.oracle.com/java/19/latest/jdk-19_windows-x64_bin.exe"
        $destination = "{drive_letter}:\\vdbench\\java-installer.exe"
        $client = new-object System.Net.WebClient
        $cookie = "oraclelicense=accept-securebackup-cookie"
        $client.Headers.Add([System.Net.HttpRequestHeader]::Cookie, $cookie);
        $client.DownloadFile($source, $destination)
        """
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        logger.info(f"response {response}")

    def download_openssh_file_in_windows_instance(self, drive_letter: str = "C"):
        """Download openssh zip file in windows EC2 instance

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
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        logger.info(f"response {response}")

    def install_openssh_in_windows_using_powershell(self, drive_letter: str = "C"):
        """Install openssh in windws using powershell script

        Args:
            drive_letter (str): drive where we download openssh.Defaults to "C" Drive
        """
        self.download_openssh_file_in_windows_instance(drive_letter=drive_letter)
        self.install_openssh(drive_letter=drive_letter)

    def install_openssh(self, drive_letter: str = "C"):
        """Install openssh in windows instance

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
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        logger.info(f"response {response}")

    def install_java_in_windows_instance(self, drive_letter: str = "C"):
        """Install java in windows EC2 instance

        Args:
            drive_letter (str): Drive where we download java exe file.Defaults to "C" Drive
        """
        self.download_java_executable_in_windows_instance(drive_letter=drive_letter)
        self.install_java(drive_letter=drive_letter)
        self.check_java_version(drive_letter=drive_letter)

    def install_java(self, drive_letter: str = "C"):
        """Install java

        Args:
            drive_letter (str): Drive where we downloaded java exe file.Defaults to "C" Drive
        """

        command: str = f"""
        Set-Location {drive_letter}:\\vdbench
        Invoke-Expression '{drive_letter}:\\vdbench\\java-installer.exe /s INSTALLDIR={drive_letter}: INSTALL_SILENT=1 STATIC=0 AUTO_UPDATE=0 WEB_JAVA=1 WEB_JAVA_SECURITY_LEVEL=H WEB_ANALYTICS=0 EULA=0 REBOOT=0 NOSTARTMENU=0 SPONSORS=0 /L java-windows-x64.log'
        """
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        logger.info(f"response {response}")

        logger.info("Setting JAVA_HOME Environment variable")
        command: str = f"""
        set JAVA_HOME="{drive_letter}:";
        set PATH="%PATH%;%JAVA_HOME%\\bin";
        """
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.CMD)
        logger.info(f"response {response}")

    def check_java_version(self, drive_letter: str = "C"):
        """Check java version

        Args:
            drive_letter (str): Drive where we installed java.Defaults to "C" Drive
        """
        command: str = f"""
        Set-Location {drive_letter}:
        $cmd = Get-WmiObject -Class Win32_Product -Filter "Name like '%Java%'"    
        echo $cmd
        """
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        logger.info(f"response {response}")

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

        Args:
            ec2_instance (Object): EC2 instance object
            username (str): EC2 username
            password (str): EC2 password
            private_key_file_path (str): EC2 key pair file name
            drive_letter (str): drive where we store vdbench archive in windows instance.Defaults to "C" Drive
            resources_directory (str): Local resources directory where stored vdbench zip file
            vdbench_archive (str): vdbench archive name

        Example Command:
            /usr/bin/sshpass -p "X&?C&yMIdfDXSmF=zvDkYjAyw5T(.g?G" scp -o 'StrictHostKeyChecking no' -i ec2-key-73fe731c-3ed5-40ef-8569-4f8a4eef7b1e.pem -r /workspaces/qa_automation/Medusa/lib/platform/resources/vdbench/vdbench50407.zip Administrator@ec2-35-91-155-14.us-west-2.compute.amazonaws.com:D:\\java
        """

        vdbench_path = os.path.join(resources_directory, vdbench_archive)
        command: str = f"""
        /usr/bin/sshpass -p'{password}' scp -v -o 'StrictHostKeyChecking no' -i {private_key_file_path} -r {vdbench_path} {username}@{ec2_instance.public_dns_name}:{drive_letter}:\\vdbench
        """
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        logger.info(f"command {command}")
        logger.info(f"output {result.stdout}")
        logger.info(f"error {result.stderr}")
        command: str = f"""
        Set-Location {drive_letter}:
        Expand-Archive -Path "{drive_letter}:\\vdbench\\{vdbench_archive}" -DestinationPath "{drive_letter}:\\vdbench\\vdbench50407"
        """
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        logger.info(f"response {response}")

    def write_data_to_drive(self, drive_letter: str):
        """Creates a random file of 100 MB on the specified disk.

        Args:
            drive_letter (str): A letter that you would like to assign to the new drive, eg. D, E, F, etc.
        """

        logger.info(f"Creating a random file on drive {drive_letter}")
        file_name = f"{drive_letter}:\\myfile-{str(uuid.uuid4())}.txt"

        command: str = f"""
        Set-Location {drive_letter}:
        $out = new-object byte[] 107374182; (new-object Random).NextBytes($out); [IO.File]::WriteAllBytes("{file_name}", $out)
        """
        self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)

    def get_drive_data_checksum(self, drive_letter: str):
        """Returns FileHash of all the files in the specified drive

        Args:
            drive_letter (str): A letter that you would like to assign to the new drive, eg. D, E, F, etc.

        Returns:
            str: Returns FileHash object if there is only 1 File, else returns FileHashList object
        """

        command: str = f"""
            Set-Location {drive_letter}:
            Get-FileHash -Algorithm MD5 -Path (Get-ChildItem "{drive_letter}:" -Recurse) | ConvertTo-Json
            """
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        file_hash_json_response = json.loads(response)
        if type(file_hash_json_response) == dict:
            return FileHash.from_json(response)
        else:  # Iterate over the list and convert it into FileHash object
            hash_list = []
            for hash in file_hash_json_response:
                hash_list.append(FileHash.from_json(json.dumps(hash)))
            file_hash_list = FileHashList(hash_list)
            return file_hash_list

    def compare_checksums(self, source_vm_checksum, restored_vm_checksum):
        if isinstance(source_vm_checksum, FileHash) and isinstance(restored_vm_checksum, FileHash):
            assert (
                source_vm_checksum.hash == restored_vm_checksum.hash
            ), f"Source VM Checksum = {source_vm_checksum.hash} and Restored VM Checksum = {restored_vm_checksum.hash}"
        else:  # The object will be an instance of FileHashList
            for source_vm in source_vm_checksum.file_hashes:
                source_vm_file_path = source_vm.path
                restored_vm = [
                    res_vm for res_vm in restored_vm_checksum.file_hashes if res_vm.path == source_vm_file_path
                ][0]
                if restored_vm:
                    assert (
                        source_vm.hash == restored_vm.hash
                    ), f"Source VM Checksum = {source_vm.hash} and Restored VM Checksum = {restored_vm.hash}"

    def bring_disks_online(self):
        """Brings all the disks online which are in offline state."""

        command: str = """Get-Disk | Where-Object IsOffline -Eq $True | Set-Disk -IsOffline $False"""
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        logger.info(response)

    def get_offline_disk_number(self) -> str:
        """Returns the number of a OFFLINE disk -> an EBS volume which is not in offline and assigned a drive yet.

        NOTE: This method is currently assuming that there will only be 1 Offline disk at a given time.
        TODO: Improve to take into account multiple Offline disks.

        Returns:
            str: Disk Number
        """
        command: str = "Get-Disk | Where-Object OperationalStatus -Eq Offline | ConvertTo-Json"
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        json_response = json.loads(response)
        logger.info(f"Get-Disk response = {json_response}")

        disk_number = json_response["DiskNumber"]
        logger.info(f"Raw disk number = {disk_number}")
        return disk_number

    def get_raw_disk_number(self) -> str:
        """Returns the number of a RAW disk -> an EBS volume which is not formatted and assigned a drive yet.

        NOTE: This method is currently assuming that there will only be 1 RAW disk at a given time.
        TODO: Improve to take into account multiple RAW disks.

        Returns:
            str: Disk Number
        """
        command: str = "Get-Disk | Where-Object PartitionStyle -Eq RAW | ConvertTo-Json"
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        json_response = json.loads(response)
        logger.info(f"Get-Disk response = {json_response}")

        disk_number = json_response["DiskNumber"]
        logger.info(f"Raw disk number = {disk_number}")
        return disk_number

    def initialize_disk(self, disk_number: str):
        """Initializes a disk so that it can be partitioned and formatted

        Args:
            session (winrm.Session): Session returned by connect_to_windows_vm() method in WindowsSessionManager
            disk_number (str): disk_number returned by get_raw_disk_number() method
        """
        command: str = f"Initialize-Disk {disk_number}"
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        logger.info(response)

    def create_disk_partition(self, disk_number: str, drive_letter: str):
        """Creates a disk partition

        Args:
            disk_number (str): disk_number returned by get_raw_disk_number() method
            drive_letter (str): A letter that you would like to assign to the new drive, eg. D, E, F, etc.
        """
        command: str = f"New-Partition -DiskNumber {disk_number} -DriveLetter {drive_letter} -UseMaximumSize"
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        logger.info(response)

    def format_disk(self, drive_letter: str, file_system_format: str = "NTFS"):
        """Formats a disk to a specified format

        Args:
            drive_letter (str): Drive which has to be formatted, eg. D, E, F, etc.
            file_system_format (str, optional): NTFS, FAT32, etc. Defaults to NTFS
        """
        command: str = f"Format-Volume -DriveLetter {drive_letter} -FileSystem {file_system_format}"
        response = self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)
        logger.info(response)

    def initialize_and_format_disk(
        self,
        drive_letter: str,
        file_system_format: str = "NTFS",
    ):
        """Formats the specified disk and enabled deduplication

        Args:
            drive_letter (str): Drive on which dedupe job was started, eg. D, E, F, etc.
            file_system_format (str, optional): NTFS, FAT32, etc. Defaults to NTFS
        """
        self.bring_disks_online()
        disk_number = self.get_raw_disk_number()
        logger.info(disk_number)

        self.initialize_disk(disk_number=disk_number)
        time.sleep(5)  # Adding some sleep for disk to be initialized and ready
        self.create_disk_partition(disk_number=disk_number, drive_letter=drive_letter)
        self.format_disk(drive_letter=drive_letter, file_system_format=file_system_format)

    # NOTE: Restored EBS volume has "Read-Only" attribute set to 'True'
    # because of which, writing cannot be performed on the disk
    # until the "Read-Only" attribute is set to 'False'
    def clear_disk_read_only_attribute_and_bring_disk_online(self, disk_number: str):
        """Sets disk's "Read-Only" attribute to 'False'
        Args:
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

        self.run_cmd_on_win_vm(command=command.strip(), command_type=CommandType.Powershell)

        # Running script file created above
        logger.info(f"Clearing Read-Only Attribute for Disk: {disk_number}")
        command: str = """
            Set-Location C:
            diskpart /s .\\script.txt
        """

        self.run_cmd_on_win_vm(command=command, command_type=CommandType.Powershell)

        logger.info("Getting offline disk number")
        disk_number = self.get_offline_disk_number()
        logger.info(f"Offline disk number = {disk_number}")

        logger.info(f"Bringing disk online {disk_number}")
        self.bring_disks_online()
        logger.info(f"Disk: {disk_number} is now online!")
