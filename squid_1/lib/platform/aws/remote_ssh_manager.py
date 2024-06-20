import time
import paramiko
import http.client
import urllib.parse
import logging

from common.enums.linux_file_system_types import LinuxFileSystemTypes
from common import helpers

logger = logging.getLogger()


class RemoteConnect:
    def __init__(
        self,
        instance_dns_name,
        username,
        key_filename=None,
        pkey=None,
        sock=True,
        window_size=None,
        packet_size=None,
    ):
        config = helpers.read_config()
        self.proxy_uri = config["proxy"]["proxy_uri"]
        self.port: int = 22
        self.host = instance_dns_name
        self.username = username
        logger.info("Create paramiko SSHClient")
        self.client: paramiko = paramiko.SSHClient()
        logger.info("Client created.")
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.sock = None
        if sock:
            self.sock = self.set_sock_tunnel()

        logger.info(
            f"RemoteConnect: hostname={self.host}, port={self.port}, username={self.username}, \
            key_filename={key_filename}, sock={self.sock}, pkey={pkey}, \
            window_size={window_size}, packet_size={packet_size}, proxy={self.proxy_uri}"
        )

        try:
            logger.info("Paramiko client connecting")
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                key_filename=key_filename,
                pkey=pkey,
                sock=self.sock,
                banner_timeout=200,
            )
        except Exception as e:
            logger.warn(f"Paramiko client connection Failed. {e=}")
            raise e

        logger.info("Paramiko client connected")

        tr = self.client.get_transport()
        if packet_size:
            tr.default_max_packet_size = packet_size
        if window_size:
            tr.default_window_size = window_size

        logger.info("Opening paramiko client sftp")
        self.sftp = self.client.open_sftp()
        logger.info("Paramiko client sftp opened")

    def set_sock_tunnel(self):
        """Connect to the server specified

        Returns:
            obj: connection object
        """
        logger.info(f"Starting proxy connection to {self.proxy_uri}...")
        self.url = urllib.parse.urlparse(self.proxy_uri)
        self.http_con = http.client.HTTPConnection(self.url.hostname, self.url.port)
        self.http_con.set_tunnel(self.host, self.port)
        self.http_con.connect()
        logger.info("Proxy connected.")
        return self.http_con.sock

    def check_command(self, command: str, retry_count: int = 0):
        """Check whether the command exits or not

        Args:
            command (str): Command to be executed
            retry_count (int, optional): Number of command retries. Defaults to 0.

        Returns:
            Bool: Return True if command exists else return False
        """
        for i in range(retry_count + 1):
            stdin, stdout, stderr = self.client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                return True
        return False

    def execute_command(self, command: str, super_user=True, check_status=True, readline=False, retry_count: int = 0):
        """Excute command on a ec2 instance

        Args:
            command (str): Command to be executed
            retry_count (int): Number of command retries

        Returns:
            list: output of the command
        """
        command = f"sudo {command}" if super_user else command

        for i in range(retry_count + 1):
            stdin, stdout, stderr = self.client.exec_command(command)
            # recv_exit_status() will wait for the command completion
            logger.info(stdin)
            exit_status = stdout.channel.recv_exit_status()
            if check_status:
                logger.info(f"Exit Status: {exit_status}")
                if exit_status == 0:
                    return self._delete_newline_char(stdout, readline)
                else:
                    logger.info("Failed to execute command on ec2 instance")
                    logger.info(stderr)
                    if i == retry_count:
                        logger.debug(f"Failed to execute command on ec2 instance after {retry_count} retry attempts!")
                        raise Exception(
                            f"Failed to execute command {command} on ec2 instance ; stdout: {stdout.read()}"
                        )
                    else:
                        logger.info(f"Failed to execute command {command} on ec2 instance ; stdout: {stdout.read()}")
                        logger.info(f"Retrying {i} . . .")
                        time.sleep(2)
                        continue

            else:
                return self._delete_newline_char(stdout, readline)

    def copy_file(self, local_path: str, remote_path: str):
        """Copy a file from local server to ec2 instance

        eg: copy_file("/root/test.log", "/home/ec2-user/test.log")
        Remember to include filename in the remote_path as well

        Args:
            local_path (str): Absolute path of local file
            remote_path (str): Absolute path of remote file

        """
        try:
            self.sftp.put(local_path, remote_path)
        except (IOError, OSError) as e:
            logger.debug(f"Exeception while copying file to ec2 instance:: {e}")
            raise e

    def change_directory(self, path="."):
        """To change the working directory for file transfers
           By  default this will change working directory to user's home directory

        Args:
            path (str, optional): Absolute path to set working directory. Defaults to '.'.

        """
        try:
            self.sftp.chdir(path)
        except IOError as e:
            logger.debug(f"Exeception while changing directory:: {e}")
            raise e

    def get_current_working_directory(self, path="."):
        """Get current working directory. By default this will return user's home directory.

        Args:
            path (str, optional): Absolute path to change directory. Defaults to '.'.

        Returns:
            str: current working directory
        """
        try:
            self.change_directory(path)
            dir_path = self.sftp.getcwd()
            return dir_path
        except IOError as e:
            logger.debug(f"Exeception while getting current working directory:: {e}")
            raise e

    def _delete_newline_char(self, stdout, readline):
        """Format the output from exec_command

        Args:
            stdout (obj): stdout object retured by exec_command()

        Returns:
            list: command output
        """
        lines = []
        if readline:
            while True:
                lines.append(stdout.readline())
                if stdout.channel.exit_status_ready():
                    break
        else:
            lines = stdout.readlines()
        return [line.strip("\n") for line in lines]

    def close_connection(self):
        """
        Close ssh and sftp connections
        """
        try:
            logger.info("SFTP - closing")
            self.sftp.close()
            logger.info("SFTP -  closed")
        except Exception as e_close:
            logger.warn(f"SFTP connection closing {e_close=}")
        try:
            logger.info("paramiko client -  closing")
            self.client.close()
            logger.info("paramiko client -  closed")
        except Exception as e_close:
            logger.warn(f"Paramiko client closing {e_close=}")
        # closing connection need time to close
        time.sleep(60)

    def write_data_to_remote_file(self, remote_file: str, content: list[str], mode="a"):
        try:
            file = self.sftp.file(remote_file, mode, -1)
            for line in content:
                file.write(line)
                file.flush()
            return True
        except Exception as e:
            logger.error("Fail to write data to the remote file, Please check the error message below.")
            logger.debug(e)
            return False

    def sftp_exists(self, remote_path: str):
        # Works for files and directories.
        try:
            self.sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def check_for_string_in_stdout(self, stdout: list[str], query_list: list[str]):
        for query in query_list:
            for line in stdout:
                if query in line:
                    return True
        else:
            return False

    def format_volume_and_mount(
        self, file_system_device: str, file_system_type: LinuxFileSystemTypes, mount_point: str
    ):
        """Format and mount an attached EBS volume.

        Args:
            file_system_device (str): The attached EBS Volume device (i.e. /dev/xvdh)
            file_system_type (LinuxFileSystemTypes): The File System Type to format (i.e. xfs, ext3, ext4)
            mount_point (str): The directory to mount the attached EBS Volume (it's encouraged to specifiy a directory starting with /mnt)
        """

        # make file system on EBS block device | xfs, ext3, ext4
        command = f"mkfs -t {file_system_type.value} {file_system_device}"
        logger.info(f"creating file system on device: {command}")
        output = self.execute_command(command=command, super_user=True)
        logger.info(output)

        # create directory to mount EBS volume onto
        command = f"mkdir -p {mount_point}"
        logger.info(f"create mount point directory: {command}")
        output = self.execute_command(command=command, super_user=True)
        logger.info(output)

        # mount the EBS volume to /ebs_volume direcory
        command = f"mount {file_system_device} {mount_point}"
        logger.info(f"mount device to mount point: {command}")
        output = self.execute_command(command=command, super_user=True)
        logger.info(output)

        # open access to the mounted volume
        command = f"chmod 777 {mount_point}"
        logger.info(f"chmod mount point: {command}")
        output = self.execute_command(command=command, super_user=True)
        logger.info(output)
