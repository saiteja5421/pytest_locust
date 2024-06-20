import json
import logging
from typing import Callable

import boto3

from lib.platform.aws.models.instance import Tag
from lib.platform.aws.client_config import ClientConfig

logger = logging.getLogger()


class IAMRolesAndPolicyManager:
    def __init__(
        self,
        aws_session: Callable[[], boto3.Session],
        aws_account_id="681961981209",
        policy_name="hpe-cam-backup-orchestration",
        role_name="hpe-cam-backup-orchestrator",
        endpoint_url: str = None,
        client_config: ClientConfig = None,
    ):
        self.get_session = aws_session
        self.aws_account_id = aws_account_id
        self.policy_name = policy_name
        self.role_name = role_name
        self.endpoint_url = endpoint_url
        self.client_config = client_config

    @property
    def iam_resource(self):
        return self.get_session().resource("iam", endpoint_url=self.endpoint_url, config=self.client_config)

    @property
    def iam_client(self):
        return self.get_session().client("iam", endpoint_url=self.endpoint_url, config=self.client_config)

    def get_existing_iam_policy_documet(self, aws_account_id: str, policy_name: str):
        read_policy = self.get_policy(aws_account_id=aws_account_id, policy_name=policy_name)
        logger.info(f"\n------ Reading Policy: {read_policy} ------\n")
        policy_json_document = read_policy.default_version.document
        logger.info("\n------ Printing Existing Policy ------\n")
        logger.info(f"    {policy_json_document}")
        """
        Policy is of the form:
        {'Version': '2012-10-17',
        'Statement': [{'Action': ['ec2:CreateSnapshot'],
        'Resource': ['arn:aws:ec2:::snapshot/*', 'arn:aws:ec2:::volume/*'],
        'Effect': 'Allow'},
        {'Action': ['ec2:DeleteSnapshot'],
        'Resource': ['arn:aws:ec2:::snapshot/hpe-*'],
        'Effect': 'Allow'},
        {'Action': ['ec2:CreateImage'],
        'Resource': ['arn:aws:ec2:::image/*', 'arn:aws:ec2:::instance/*'],
        'Effect': 'Allow'},
        {'Action': ['ec2:CreateTags', 'ec2:DeleteTags'],
        'Resource': ['arn:aws:ec2:::instance/*', 'arn:aws:ec2:::volume/*'],
        'Effect': 'Allow'},
        {'Action': ['ebs:ListSnapshotBlocks', 'ebs:ListChangedBlocks'],
        'Resource': ['arn:aws:ec2:::snapshot/*'],
        'Effect': 'Allow'}]}
        """
        return policy_json_document

    def edit_policy_document_effect(self, aws_account_id: str, policy_name: str, effect="Deny"):
        """We will update the ec2:CreateSnapshot Effect to "Deny" from "Allow" """
        updated_policy_document = self.get_existing_iam_policy_documet(
            aws_account_id=aws_account_id, policy_name=policy_name
        )
        updated_policy_document["Statement"][0]["Effect"] = effect
        logger.info(f"\n------ Showing the updated/edited Policy ------\n\t\t {updated_policy_document}\n\n")
        return updated_policy_document

    def get_policy(self, aws_account_id: str, policy_name: str):
        """This method will take the AWS Accout ID and the Policy Name as inputs

        Args:
            aws_account_id (str): AWS Account ID
            policy_name (str): Policy Name

        Returns:
            Returns AWS Policy Object
        """
        iam_policy = self.iam_resource.Policy(f"arn:aws:iam::{aws_account_id}:policy/{policy_name}")
        return iam_policy

    def detach_existing_role_from_policy(self, aws_account_id: str, role_name: str, policy_name: str):
        """Takes AWS Account ID, Role Name, and Policy Name as inputs
        and detaches the policy from its assigned role

        Args:
            aws_account_id (str): AWS Account ID
            role_name (str): Role Name
            policy_name (str): Policy Name associated with the role
        """

        iam_policy = self.get_policy(aws_account_id=aws_account_id, policy_name=policy_name)
        """ Detach the role from the IAM policy """
        logger.info(f"\n------ Detach Role: {role_name} and Delete Policy: {policy_name} ------\n")
        iam_policy.detach_role(RoleName=role_name)

    def delete_policy(self, aws_account_id: str, policy_name: str):
        """Takes AWS Account ID and Policy Name as inputs
        and deletes the policy

        Args:
            aws_account_id (str): AWS Account ID
            policy_name (str): Policy Name to be deleted
        """
        iam_policy = self.get_policy(aws_account_id=aws_account_id, policy_name=policy_name)
        """ Deleting the Policy """
        iam_policy.delete()

    def detach_existing_role_and_delete_policy(self, aws_account_id: str, role_name: str, policy_name: str):
        """This method will take the AWS Accout ID, Role Name, and the Policy Name as inputs
        and deletes the policy associated with the role.
        Args:
            aws_account_id (str): AWS Account ID
            role_name (str): Role Name
            policy_name (str): Policy Name associated with the role
        """
        self.detach_existing_role_from_policy(
            aws_account_id=aws_account_id, role_name=role_name, policy_name=policy_name
        )
        """ Deleting the Policy """
        self.delete_policy(aws_account_id=aws_account_id, policy_name=policy_name)

    def create_iam_policy(self, aws_account_id: str, policy_name: str, updated_policy):
        updated_policy = self.edit_policy_document_effect(aws_account_id=aws_account_id, policy_name=policy_name)
        create_new_policy = self.iam_client.create_policy(
            PolicyName=self.policy_name, PolicyDocument=json.dumps(updated_policy)
        )
        logger.info(f"\n------ creating policy: {create_new_policy} ------\n")

    def attach_existing_role_to_policy(self, aws_account_id: str, role_name: str, policy_name: str):
        """Takes AWS Account ID, Role Name, and Policy Name as inputs
        and attaches the policy to the specified role.

        Args:
            role_name (str): Role Name
            aws_account_id (str): AWS Account ID
            policy_name (str): Policy Name associated witht the role
        """
        self.iam_client.attach_role_policy(
            RoleName=role_name,
            PolicyArn=f"arn:aws:iam::{aws_account_id}:policy/{policy_name}",
        )

    def get_roles(self):
        response_roles = self.iam_client.list_roles()
        roles = [role["RoleName"] for role in response_roles["Roles"]]
        return roles

    def get_current_user(self):
        user = self.iam_resource.CurrentUser().arn
        return user

    def delete_all_oidc_providers(self):
        """Delete all OpenID Connect providers and verify if there are any stale entries after deletion"""
        oidc_providers = self.iam_client.list_open_id_connect_providers()["OpenIDConnectProviderList"]
        logger.info("Deleting OIDC providers...")
        for provider in oidc_providers:
            provider_arn = provider["Arn"]
            try:
                self.iam_client.delete_open_id_connect_provider(OpenIDConnectProviderArn=provider_arn)
                logger.info(f"Deleted OIDC with ARN {provider_arn} with success.")
            except Exception as error:
                logger.warning(f"Error while deleting OIDC provider {provider_arn}: {error}")
        oidc_providers_after_delete = self.iam_client.list_open_id_connect_providers()["OpenIDConnectProviderList"]
        assert (
            not oidc_providers_after_delete
        ), f"Some OIDC providers last after deletion. OIDC providers: {oidc_providers_after_delete}"

    def delete_iam_role(self, role_name):
        try:
            self.iam_client.delete_role(RoleName=role_name)
            logger.info(f"Deleted IAM role {role_name}")
        except Exception as error:
            logger.warning(f"Error while deleting IAM role {role_name}: {error}")

    def delete_iam_roles_with_prefix(self, prefix):
        roles = self.get_roles()
        for role in roles:
            if role.startswith(prefix):
                self.delete_iam_role(role)
        logger.info(f"All roles with prefix {prefix} deleted.")

    def get_oidc_list(self):
        oidc_connect_providers = self.iam_client.list_open_id_connect_providers()
        arn = [oidc["Arn"] for oidc in oidc_connect_providers["OpenIDConnectProviderList"]]
        return arn

    def get_oidc_tags_by_arn(self, arn: str) -> list[Tag]:
        response_oidc = self.iam_client.list_open_id_connect_provider_tags(
            OpenIDConnectProviderArn=arn,
        )
        return [Tag(**tag) for tag in response_oidc["Tags"]]

    def get_name_spaces(self, aws_account_id: str):
        name_spaces = self.iam_client.list_namespaces(AwsAccountId=aws_account_id)
        return name_spaces

    def detach_policy_from_role(self, role_name: str, policy_arn: str):
        logger.info(f"Detaching policy with ARN {policy_arn} from role {role_name}")
        self.iam_client.detach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
