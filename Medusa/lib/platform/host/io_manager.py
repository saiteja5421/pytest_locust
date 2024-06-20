import time
from lib.platform.aws_boto3.remote_ssh_manager import RemoteConnect
from tests.e2e.aws_protection.context import Context
from utils.size_conversion import str_gb_to_mb
import logging
import os
import re
from packaging import version as pver

logger = logging.getLogger()


class IOManager:
    def __init__(self, context: Context, client: RemoteConnect):
        """
        Class contains methods to run dd and vdbench workload on a EC2 instance (Linux)
        Provides support for generating checksum using cksum module and cksum validation.

        Args:
            client (RemoteConnect): Paramiko client object of the EC2 instance.
        """

        self.client = client
        self.vdbench_custom_config_file = context.vdbench_custom_config_file
        self.vdbench_directory = context.vdbench_directory
        self.resources = context.resources_directory
        self.vdbench_archive = context.vdbench_archive
        self.java_build = "1.8.0"
        self.dmcore = context.dmcore
        self.home_directory = f"/home/{client.username}"
        self.archive = os.path.join(self.home_directory, self.vdbench_archive)
        self.dmcore_directory, self.dmcore_filename = os.path.split(self.dmcore)

    def get_devices(self) -> list[str]:
        # Information on EC2 block devices:
        # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/block-device-mapping-concepts.html
        devices = self.client.execute_command("lsblk --output KNAME -n")

        devices = [
            device
            for device in devices
            # Skipping xvda, which is a root volume by default.
            if ((len(device) < 5 and not device.endswith("a")) or (len(device) > 5 and len(device) < 8))
            and not device.endswith("0n1")
            and not device.endswith("14")  # device names on Ubuntu and Debian xvda14 and xvda15 which are boot devices
            and not device.endswith("15")
            and not device.endswith("127")
            and not device.endswith("128")
            and not device.startswith("sda")  # Azure linux
            and not device.startswith("sdb")  # Azure linux
            and not device.startswith("sr0")  # Azure linux
            and not device.startswith("loop")  # Azure Ubuntu
            and not device.startswith("dm-")  # Azure RHEL and Oracle
            and not device.startswith("fd0")  # Azure CentOS
        ]
        return devices

    def execute_dd_command(self, fill: str, device: str, block_size: int, count: int, seek: int = None) -> None:
        """
            Method to execute the dd command in the EC2 instance with the  given parameters.
        Args:
            fill (str): Value should be 'urandom' or 'zero'
            device (str): block device eg: xvdb
            block_size (int): block size (512, 4k, 1M etc.)
            count (int): Number of block
            seek (int): Block address to start the write process.
        """
        # Limitation: Successful dd command execution will not return any stdout.
        # Exception will be thrown if the command did not executed successfully.
        # TODO Add a retry mechanism.
        self.client.execute_command(f"dd if=/dev/{fill} of=/dev/{device} bs={block_size} count={count} oflag=direct")

    def clean_disks(self, devices: list[str]) -> None:
        for device in devices:
            # Fill volume with zero
            command = f"dd if=/dev/zero of=/dev/{device} bs=16M count=120 && sync"
            self.client.execute_command(command)
        logger.info("Device cleanup completed successfully")

    def get_volume_size(self, device):
        stdout = self.client.execute_command(f"lsblk -no SIZE /dev/{device}")
        # Get volume size in GB and convert to MB
        # eg: 8G -> 8 -> 8 * 1024 = 8096
        return str_gb_to_mb(stdout[0])

    def create_vdbench_config_in_ec2_instance(self, remote_file: str, content: list[str]):
        remote_directory, remote_filename = os.path.split(remote_file)
        if not self.client.sftp_exists(os.path.join(remote_directory, remote_filename)):
            self.client.execute_command(f"mkdir -p {remote_directory}")
        success = self.client.write_data_to_remote_file(remote_file=remote_file, content=content, mode="w")
        if not success:
            raise IOError("Writing vdbench config to the remote ec2 instance failed.")

    def generate_checksum(self, file_path: str) -> str:
        """Generates checksum using 'cksum' utility for a given remote file.

        eg: cksum /dev/xvdb returns 3633963874

        Args:
            file_path (str): Absolute remote file path (linux only)

        Returns:
            str: checksum
        """
        if self.client.sftp_exists(file_path):
            stdout = self.client.execute_command(f"cksum {file_path}")
            name = os.path.split(file_path)[-1]
            assert self.client.check_for_string_in_stdout(stdout, [name])
            checksum, size, name = stdout[-1].strip().split(" ")
            logger.info(f"Checksum generated successfully for the file {name}  - size {size} in bytes")
            return checksum
        else:
            raise FileNotFoundError("Remote file does not exists, Checksum generation failed.")

    def copy_vdbench_executable_to_remote_host(self):
        if not self.client.sftp_exists(self.home_directory):
            self.client.execute_command(f"mkdir -p {self.home_directory}")
        self.client.copy_file(
            os.path.join(self.resources, self.vdbench_archive),
            self.archive,
        )
        self.client.change_directory(self.home_directory)

    def install_java_in_remote_host(self):
        # Debian and Ubuntu
        if self.client.check_command("command -v apt-get"):
            self.client.execute_command("apt-get update")
            stdout = self.client.execute_command("apt-get -y install default-jdk")
            stdout = self.client.execute_command("java --version")
            assert self.client.check_for_string_in_stdout(
                stdout,
                ["openjdk"],
            )
            stdout = self.client.execute_command("apt-get -y install unzip")
            stdout = self.client.execute_command("which unzip")
            assert self.client.check_for_string_in_stdout(
                stdout,
                ["/usr/bin/unzip"],
            )
            stdout = self.client.execute_command(f"unzip -o {self.archive}")
            assert self.client.check_for_string_in_stdout(stdout, ["example5", "Nothing to do"])
        elif self.client.check_command("command -v yum"):
            # Amazon and Red Hat
            # On Amazon Linux and Suse -> yum install java-1.8.0-openjdk --assumeyes fails with:
            # Error: Unable to find a match: java-1.8.0-openjdk
            # Below command will list all the available java packages from which we are installing the first one
            # output example
            # [
            #     "Updating Subscription Management repositories.",
            #     "Unable to read consumer identity",
            #     "",
            #     "This system is not registered with an entitlement server. You can use subscription-manager to register.",
            #     "",
            #     "Last metadata expiration check: 0:02:10 ago on Wed 10 May 2023 08:50:36 PM UTC.",
            #     "Available Packages",
            #     "java-1.8.0-openjdk.x86_64             1:1.8.0.372.b07-2.el9 rhel-9-appstream-rhui-rpms",
            #     "java-1.8.0-openjdk-demo.x86_64        1:1.8.0.372.b07-2.el9 rhel-9-appstream-rhui-rpms",
            #     ...,
            # ]
            stdout = self.client.execute_command("yum list java*")
            logger.info(stdout)

            min_java_ver = pver.parse("1.6.999")
            java_versions = [java_version.split(" ")[0].strip() for java_version in stdout if "java" in java_version]
            java_version = [
                ver
                for ver in java_versions
                if (jv := re.search(r"\d.\d.\d", ver)) and pver.parse(jv[0]) >= min_java_ver
            ][0]
            logger.info(f"Java Version to be installed is {java_version}")

            stdout = self.client.execute_command(f"yum install {java_version} --assumeyes")
            assert self.client.check_for_string_in_stdout(stdout, ["Complete", "Nothing to do"])
            stdout = self.client.execute_command("yum install unzip --assumeyes")
            assert self.client.check_for_string_in_stdout(
                stdout,
                ["Complete", "Nothing to do"],
            )
            stdout = self.client.execute_command(f"unzip -o {self.archive}")
            assert self.client.check_for_string_in_stdout(stdout, ["example5", "Nothing to do"])
        else:
            # Suse
            stdout = self.client.execute_command("zypper search-packages openjdk-devel")
            logger.info(stdout)

            # output example
            # [
            #     "Refreshing service 'Basesystem_Module_x86_64'.",
            #     "Loading repository data...",
            #     "Reading installed packages...",
            #     "",
            #     "S | Name                     | Summary                            | Type",
            #     "S | Name                     | Summary                            | Type",
            #     "--+--------------------------+------------------------------------+--------",
            #     "  | java-1_8_0-openjdk-devel | OpenJDK 8 Development Environment  | package",
            #     "  | java-11-openjdk-devel    | OpenJDK 11 Development Environment | package",
            #     "  | java-17-openjdk-devel    | OpenJDK 17 Development Environment | package",
            # ]

            # java_versions = [java_version for java_version in stdout if "java" in java_version]
            # java_version = java_versions[0].split("|")[1].strip()
            # logger.info(f"Java Version to be installed is {java_version}")

            java_version = "java-11-openjdk-devel"
            stdout = self.client.execute_command(f"zypper --non-interactive install {java_version}")
            assert self.client.check_for_string_in_stdout(
                stdout, ["done", "update-alternatives", f"Installing: {java_version}", "Nothing to do"]
            )
            stdout = self.client.execute_command("zypper --non-interactive install unzip")
            assert self.client.check_for_string_in_stdout(
                stdout,
                ["Complete", "Nothing to do"],
            )
            stdout = self.client.execute_command(f"unzip -o {self.archive}")
            assert self.client.check_for_string_in_stdout(stdout, ["example5", "Nothing to do"])

    def copy_vdbench_custom_config_file_to_remote_host(self):
        """
        Copy Vdbench custom config file to the EC2 instance (Linux)
        """
        self.client.change_directory(self.home_directory)
        self.client.copy_file(
            os.path.join(self.vdbench_custom_config_file),
            self.vdbench_custom_config_file,
        )

    def get_vdbench_logs():
        # TODO Copy logs files from the remote machine to the test run directory for analysis.
        pass

    def copy_dmcore_binary_to_remote_host(self):
        """
        Copy dmcore binary file to the EC2 instance (Linux)
        """
        if not self.client.sftp_exists(self.dmcore):
            self.client.copy_file(self.dmcore, os.path.join(self.home_directory, self.dmcore_filename))
            time.sleep(5)
            command = f"chmod +x {self.dmcore_filename}"  # this line we added
            stdout = self.client.execute_command(command)
            for line in stdout:
                logger.info(line)
            # Need to add wait time for copy dmcore to complete as it may lead to errors when running dmcore later
            time.sleep(40)
            stdout = self.client.execute_command("ls -al")
            logger.info(stdout)
            stdout = self.client.execute_command("du -sh")
            logger.info(stdout)

    def run_dmcore(
        self,
        percentage_to_fill: int = 80,
        block_size: str = "4k",
        compression_ratio=4,
        compression_method=4,
        offset=0,
        validation=False,
        change_block_percentage: int = 20,
    ):
        """Run dmcore with given specifications, compression ratio and compression method is set to 4 by default.
        This will help us get around 4:1 dedupe ratio in store once applicance.
        Use offset to do the incremental backup

        Args:
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
        for device in self.get_devices():
            success = self.run_dm_core_on_custom_drive(
                device=device,
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
        device: str,
        percentage_to_fill: int = 80,
        block_size: str = "4k",
        compression_ratio=4,
        compression_method=4,
        offset=0,
        validation=False,
        change_block_percentage: int = 20,
        export_file_name: str = None,
    ):
        """Run dmcore with given specifications, compression ratio and compression method is set to 4 by default.
        This will help us get around 4:1 dedupe ratio in store once applicance.
        Use offset to do the incremental backup

        Args:
            device (str): volume on which the data has to be written. Eg. xvda, xvdh, etc.
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
        self.client.change_directory(self.home_directory)
        command: str = ""
        success = False
        # Convert size from GB to MB and type integer
        size = int((self.get_volume_size(device) / 100) * percentage_to_fill)

        export_file_name = export_file_name if export_file_name else f"/dev/{device}"

        if not validation:
            # Data write command
            command = f"./{self.dmcore_filename} Command=Write DMExecSet=Nas DMVerificationMode=MD5 ExportFileName={export_file_name} WriteT={size}m seed=1 WriteI={block_size} Offset={str(offset)} CompressionRatio={str(compression_ratio)} CompressionMethod={str(compression_method)} InternalBlockChange=50 TotalBlockChange={total_block_change}"
        else:
            # Data Read and validate command
            command = f"./{self.dmcore_filename} Command=Read DMExecSet=Nas ImportFileName={export_file_name} ReadT={size}m ReadI={block_size}  Validation=1"
        # time.sleep(10)
        stdout = self.client.execute_command(command=command, retry_count=5)
        # time.sleep(20)
        for line in stdout:
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
