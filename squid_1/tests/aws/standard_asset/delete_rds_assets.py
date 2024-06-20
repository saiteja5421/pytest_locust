from lib.platform.aws.rds_manager import RDSManager
from common import helpers
from lib.platform.aws.models.instance import Tag
import logging

config = helpers.read_config()
rds = RDSManager(aws_config=config["testbed"]["AWS"])

logging.info(f"-----Delete RDS instance----")
rds.delete_db_instances_by_tag(Tag(Key="AtlantiaPSRRDSTest", Value="Test"))
