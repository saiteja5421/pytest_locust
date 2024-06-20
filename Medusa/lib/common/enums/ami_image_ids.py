from enum import Enum


class AMIImageIDs(Enum):
    # From: ec2_manager.py#97
    # "ami-04505e74c0741db8d" Id for Ubuntu (Free) - US East Region
    UBUNTU_US_EAST = "ami-04505e74c0741db8d"
    UBUNTU_US_EAST_1 = "ami-04505e74c0741db8d"
    UBUNTU_US_EAST_2 = "ami-02f3416038bdb17fb"
    UBUNTU_US_WEST_2 = "ami-0fcf52bcf5db7b003"
    AMAZON_LINUX_US_EAST_1 = "ami-05fa00d4c63e32376"
    AMAZON_LINUX_US_WEST_1 = "ami-0d9858aa3c6322f73"
    AMAZON_LINUX_US_WEST_2 = "ami-098e42ae54c764c35"
    REDHAT7_US_WEST = "ami-078a6a18fb73909b2"
    AMAZON_LINUX_CA_CENTRAL_1 = "ami-041a9937e9118f3f3"
    WINDOWS_SERVER_2022_BASE_US_WEST_2 = "ami-05cc83e573412838f"
