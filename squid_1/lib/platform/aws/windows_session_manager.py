import base64

import logging
from lib.platform.aws.aws_factory import AWS

# Imports for connecting to Windows VM
import winrm
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

logger = logging.getLogger()


class WindowsSessionManager:
    def __init__(self) -> None:
        pass

    def decrypt_password(self, private_key_file_path: str, password_data) -> str:
        """Decrypts the password by using the key-pair used to create an EC2 instance.

        Args:
            private_key_file_path (str): path of the '.pem' or '.cer' key-pair file
            password_data (_type_): Data returned by method `aws.ec2.get_ec2_password_data()`

        Returns:
            str: Decrypted password
        """
        key_text: str = None
        with open(private_key_file_path, "r") as key_file:
            key_text = key_file.read()
        logger.info(f"key_text = {key_text}")

        key = RSA.importKey(key_text)
        cipher = PKCS1_v1_5.new(key)
        password = cipher.decrypt(base64.b64decode(password_data), None).decode("utf-8")
        return password

    def get_ec2_password(
        self,
        aws: AWS,
        ec2_instance,
        private_key_file_path: str,
    ) -> str:
        """Returns EC2 password using the private_key_file_path - '.pem' or '.cer' file

        Args:
            aws (AWS): AWS object
            ec2_instance (AWS EC2 instance): EC2 instance object from AWS
            private_key_file_path (str): path of the '.pem' or '.cer' key-pair file.

        Returns:
            str: EC2 password
        """
        password_data = aws.ec2.get_ec2_password_data(ec2_instance_id=ec2_instance.id)
        logger.info(f"EC2 Password Data = {password_data}")

        ec2_password = self.decrypt_password(
            private_key_file_path=private_key_file_path,
            password_data=password_data,
        )
        logger.info(f"Decrypted Password = {ec2_password}")

        return ec2_password

    def connect_to_windows_vm(
        self,
        aws: AWS,
        ec2_instance,
        private_key_file_path: str = None,
        user_name: str = "Administrator",
        password: str = None,
    ) -> winrm.Session:
        """Takes an EC2 instance details and returns the session object for successful connection

        Args:
            aws (AWS): AWS object
            ec2_instance (AWS EC2 instance): EC2 instance object from AWS
            private_key_file_path (str, optional): path of the '.pem' or '.cer' key-pair file.
            This parameter MUST be provided if password is not provided
            user_name (str, optional): Username of the EC2 instance. Defaults to "Administrator" for Windows VM.
            password (str, optional): Password of the EC2 instance. Defaults to None.

        Returns:
            winrm.Session: Session object can be used to run commands against the EC2 instance.
        """

        ec2_password: str = password
        if not password:
            ec2_password = self.get_ec2_password(
                aws=aws,
                ec2_instance=ec2_instance,
                private_key_file_path=private_key_file_path,
            )

        session = winrm.Session(ec2_instance.public_dns_name, auth=(user_name, ec2_password))
        return session
