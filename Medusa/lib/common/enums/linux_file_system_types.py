from enum import Enum


class LinuxFileSystemTypes(Enum):
    XFS = "xfs"
    EXT2 = "ext2"
    EXT3 = "ext3"
    EXT4 = "ext4"
    BTRFS = "btrfs"
