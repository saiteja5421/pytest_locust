from enum import Enum

# Reference: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connection-prereqs.html


class EC2Username(Enum):
    """
    Example image names:
    - amzn2-ami-kernel-5.10-hvm-2.0.20220912.1-x86_64-gp2
    - suse-sles-15-sp4-v20220722-hvm-ssd-x86_64
    - RHEL-8.6.0_HVM-20220503-x86_64-2-Hourly2-GP2
    - ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-20220912
    - debian-11-amd64-20220503-998
    - CentOS-7-2111-20220825_1.x86_64-d9a3032a-921c-4c6d-b150-bde168105e42
    - Windows_Server-2022-English-Full-Base-2022.09.14
    """

    AMZN2 = "ec2-user"
    SUSE = "ec2-user"
    RHEL = "ec2-user"
    UBUNTU = "ubuntu"
    DEBIAN = "admin"
    FEDORA = "fedora"
    CENTOS = "centos"
    ORACLE = "ec2-user"
    BITNAMI = "bitnami"
    WINDOWS = "Administrator"
    EC2User = "ec2-user"

    @classmethod
    def get_ec2_username(cls, ec2_instance) -> str:
        """Takes an EC2 instance and returns its username

        Args:
            ec2_instance : Object returned by ec2_manager.get_ec2_instance_by_id()

        Returns:
            str: EC2 VM username
        """
        image_name: str = ec2_instance.image.name.lower()

        if "amzn2" in image_name:
            return cls.AMZN2.value
        elif "suse" in image_name:
            return cls.SUSE.value
        elif "rhel" in image_name:
            return cls.RHEL.value
        elif "ubuntu" in image_name:
            return cls.UBUNTU.value
        elif "bitnami" in image_name:
            return cls.BITNAMI.value
        elif "debian" in image_name:
            return cls.DEBIAN.value
        elif "centos" in image_name:
            return cls.CENTOS.value
        elif "fedora" in image_name:
            return cls.FEDORA.value
        elif "supportedimages ol" in image_name:
            return cls.ORACLE.value
        elif "windows" in image_name:
            return cls.WINDOWS.value
        else:
            return cls.EC2User.value
