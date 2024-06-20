from common import helpers
from lib.platform.aws.models.instance import Tag
from lib.platform.aws.ec2_manager import EC2Manager
from lib.platform.aws.aws_session import create_aws_session_manager

config = helpers.read_config()
aws_session_manager = create_aws_session_manager(config["testbed"]["AWS"])
ec2_manager = EC2Manager(aws_session_manager)
# Passing the tag key as "perf_test" as ec2 instances created for all Squid workflows have prefix
tag = Tag(Key=f"perf_test", Value="dummy")
ec2_manager.delete_running_ec2_instances_contains_tag(tag_substring=tag.Key)
