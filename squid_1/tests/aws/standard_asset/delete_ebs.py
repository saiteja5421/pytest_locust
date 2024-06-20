from common import helpers
from lib.platform.aws.models.instance import Tag
from lib.platform.aws.ebs_manager import EBSManager
from lib.platform.aws.aws_session import create_aws_session_manager

config = helpers.read_config()
aws_session_manager = create_aws_session_manager(config["testbed"]["AWS"])
ebs_manager = EBSManager(aws_session_manager)
ebs_list = ebs_manager.get_all_volumes()
for volume in ebs_list:
    ebs_manager.delete_volume(volume_id=volume.id)
