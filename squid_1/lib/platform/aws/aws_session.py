import os
from lib.platform.aws.aws_session_manager import AWSSessionManager
from lib.platform.aws.aws_factory import AWS


def create_aws_session_manager(aws_config):
    """
    Creates aws session manager using AWSSessionManager from Medusa
    Args:
        aws_config (dict): aws_config is section in testbed->AWS in config.yml file

    Returns:
        Object: Return aws session manager object
    """
    region = aws_config["region"]
    access_key = os.environ.get("AWS_ACCESS_KEY")
    secret_key = os.environ.get("AWS_SECRET_KEY")
    if not access_key:
        access_key = aws_config["accesskey"]

    if not secret_key:
        secret_key = aws_config["secretkey"]

    aws_session_manager: AWSSessionManager = AWSSessionManager(
        region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key
    )

    def aws_session():
        return aws_session_manager.aws_session

    return aws_session


def aws(aws_config):
    """
    Returns aws session object using AWS class (aws_factory) from Medusa
    Args:
        aws_config (dict): aws_config is section in testbed->AWS in config.yml file

    Returns:
        Object: Return aws session as callable object
    """
    region = aws_config["region"]
    access_key = os.environ.get("AWS_ACCESS_KEY")
    secret_key = os.environ.get("AWS_SECRET_KEY")
    if not access_key:
        access_key = aws_config["accesskey"]

    if not secret_key:
        secret_key = aws_config["secretkey"]

    aws: AWS = AWS(region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key, role_arn=None)

    return aws
