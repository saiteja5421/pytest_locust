import logging
from typing import Callable

import boto3
from botocore.exceptions import ClientError, WaiterError

from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.aws_boto3.models.parameter import Parameter
from lib.platform.aws_boto3.client_config import ClientConfig

logger = logging.getLogger()


class CloudFormationManager:
    def __init__(
        self, aws_session: Callable[[], boto3.Session], endpoint_url: str = None, client_config: ClientConfig = None
    ):
        self.get_session = aws_session
        self.endpoint_url = endpoint_url
        self.client_config = client_config

    @property
    def ec2_resource(self):
        return self.get_session().resource("cloudformation", endpoint_url=self.endpoint_url, config=self.client_config)

    @property
    def ec2_client(self):
        return self.get_session().client(
            "cloudformation",
            endpoint_url=self.endpoint_url,
            region_name=self.get_session().region_name,
            config=self.client_config,
        )

    """
    if using template_url, it should be a presigned URL
    (https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html)
    use -> s3_manager.create_s3_presigned_url()
    """

    def create_cf_stack(
        self,
        stack_name: str,
        template_body: str = None,
        template_url: str = None,
        capabilities=["CAPABILITY_NAMED_IAM"],
    ):
        stack = None
        waiter = self.ec2_client.get_waiter("stack_create_complete")

        if not template_url:
            stack = self.ec2_resource.create_stack(
                StackName=stack_name, TemplateBody=template_body, Capabilities=capabilities
            )
        else:
            # Is it possible for stack.stack_status to be ROLLBACK_COMPLETE without create_cf_stack() encountering a WaiterError
            # Try to create a stack either manually or through code and then try to create another stack and debug this step might add some error handling with try-catch
            stack = self.ec2_resource.create_stack(
                StackName=stack_name, TemplateURL=template_url, Capabilities=capabilities
            )
        try:
            waiter.wait(StackName=stack_name)
        except WaiterError as e:
            rolllback_status = "ROLLBACK_COMPLETE"
            if stack.stack_status == rolllback_status:
                return rolllback_status
            else:
                raise (e)

        logger.info(f" ----- Stack {stack} created ----- ")
        return stack

    """
    if using template_url, it should be a presigned URL
    (https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html)
    use -> s3_manager.create_s3_presigned_url()
    """

    def create_cf_stack_with_parameters(
        self,
        stack_name: str,
        parameters_list: list[Parameter] = None,
        template_body: str = None,
        template_url: str = None,
    ):
        waiter = self.ec2_client.get_waiter("stack_create_complete")
        parameters = [dict(parameter) for parameter in parameters_list]

        if not template_url:
            stack = self.ec2_resource.create_stack(
                StackName=stack_name, TemplateBody=template_body, Parameters=parameters
            )
            waiter.wait(StackName=stack_name)
            logger.info(f" ----- Stack {stack} created ----- ")
            return stack
        else:
            stack = self.ec2_resource.create_stack(
                StackName=stack_name, TemplateURL=template_url, Parameters=parameters
            )
            waiter.wait(StackName=stack_name)
            logger.info(f" ----- Stack {stack} created ----- ")
            return stack

    """
    if using template_url, it should be a presigned URL
    (https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html)
    use -> s3_manager.create_s3_presigned_url()
    """

    def create_cf_stack_with_tags(
        self,
        stack_name: str,
        tags_list: list[Tag] = None,
        template_body: str = None,
        template_url: str = None,
    ):
        waiter = self.ec2_client.get_waiter("stack_create_complete")
        tags = [dict(tag) for tag in tags_list]

        if not template_url:
            stack = self.ec2_resource.create_stack(StackName=stack_name, TemplateBody=template_body, Tags=tags)
            waiter.wait(StackName=stack_name)

            logger.info(f" ----- Stack {stack} created ----- ")
            return stack
        else:
            stack = self.ec2_resource.create_stack(StackName=stack_name, TemplateURL=template_url, Tags=tags)
            waiter.wait(StackName=stack_name)

            logger.info(f" ----- Stack {stack} created ----- ")
            return stack

    """
    if using template_url, it should be a presigned URL
    (https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html)
    use -> s3_manager.create_s3_presigned_url()
    """

    def create_cf_stack_with_parameters_and_tags(
        self,
        stack_name: str,
        parameters_list: list[Parameter] = None,
        tags_list: list[Tag] = None,
        template_body: str = None,
        template_url: str = None,
    ):
        waiter = self.ec2_client.get_waiter("stack_create_complete")
        if parameters_list:
            parameters = [dict(parameter) for parameter in parameters_list]
        else:
            parameters = []

        if tags_list:
            tags = [dict(tag) for tag in tags_list]
        else:
            tags = []

        if not template_url:
            stack = self.ec2_resource.create_stack(
                StackName=stack_name,
                TemplateBody=template_body,
                Parameters=parameters,
                Tags=tags,
            )
            waiter.wait(StackName=stack_name)
            logger.info(f" ----- Stack {stack} created ----- ")
            return stack
        else:
            stack = self.ec2_resource.create_stack(
                StackName=stack_name,
                TemplateURL=template_url,
                Parameters=parameters,
                Tags=tags,
            )
            waiter.wait(StackName=stack_name)
            logger.info(f" ----- Stack {stack} created ----- ")
            return stack

    def delete_cf_stack(self, stack_name):
        waiter = self.ec2_client.get_waiter("stack_delete_complete")

        logger.info(f" ----- Deleting stack {stack_name} ----- ")

        stack = self.ec2_resource.Stack(stack_name)
        stack.delete()
        waiter.wait(StackName=stack_name)
        logger.info(f" ----- Deleted stack {stack_name} ----- ")

    def get_cf_stack(self, stack_name: str):
        stack = None
        logger.info(f" ----- Getting stack {stack_name} ----- ")

        try:
            stacks = self.ec2_client.describe_stacks(StackName=stack_name)
            stack = stacks["Stacks"][0]
            logger.info(f" ----- Got stack {stack_name} ----- ")
        except ClientError:
            # thrown if the stack does not exist:
            # botocore.exceptions.ClientError: An error occurred (ValidationError) when calling the DescribeStacks operation: Stack with id {stack_name} does not exist
            logger.warning(f"Stack: '{stack_name}' was not found")

        return stack

    def get_stack_resources(self, stack_name):
        logger.info(f"Getting CFT stack {stack_name} resources...")
        return self.ec2_client.list_stack_resources(StackName=stack_name)
