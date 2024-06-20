import logging
import random
import string
from subprocess import TimeoutExpired
from typing import Callable

from lib.platform.aws.client_config import ClientConfig

import boto3
import botocore.exceptions as BotoException
from waiting import wait

logger = logging.getLogger()

length_random_str = 8
random_cluster_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=length_random_str))
eks_cluster_random_name = "eks-cluster-" + random_cluster_id


class EKSManager:
    def __init__(
        self, aws_session: Callable[[], boto3.Session], endpoint_url: str = None, client_config: ClientConfig = None
    ):
        self.get_session = aws_session
        self.endpoint_url = endpoint_url
        self.client_config = client_config

    @property
    def eks_resource(self):
        return self.get_session().resource("eks", endpoint_url=self.endpoint_url, config=self.client_config)

    @property
    def eks_client(self):
        return self.get_session().client("eks", endpoint_url=self.endpoint_url, config=self.client_config)

    def create_eks_cluster(
        self,
        role_arn: str,
        resources_vpc_config: dict,
        version: str = "1.25",
        eks_cluster_name: str = eks_cluster_random_name,
        delay_between_attempts: int = 30,
        max_attempts_count: int = 50,
    ) -> dict:
        """This function creates an EKS cluster and returns a description of the same.

        Args:
            role_arn (str):
            resources_vpc_config (dict): A dictionary comprising of Security group IDs and Subnet IDs. At least 2 subnet IDs should be present.
            version (str, optional): Desired version of Kubernetes to be used in the cluster. Defaults to "1.25".
            eks_cluster_name (str, optional): A name for the identification of the Cluster. A unique name will be assigned if not passed as an argument. Defaults to eks_cluster_random_name.
            delay_between_attempts (int, optional): Duration between two consecutive calls to gthe describe_cluster() method. Defaults to 30.
            max_attempts_count (int, optional): Maximum number of attempts of call to the describe_cluster() method. Defaults to 50.

        Raises:
            e: Catches a specific list of exceptions as mentioned by the boto3 library.
            err: Catches common exceptions that are not covered by the Boto3 list of exceptions

        Returns:
            dict: A description of the created EKS cluster.
        """
        try:
            logger.info(f"Creating EKS Cluster with name {eks_cluster_name} and Kubernetes Version {version}.")
            eks_cluster = self.eks_client.create_cluster(
                name=eks_cluster_name,
                version=version,
                roleArn=role_arn,
                resourcesVpcConfig=resources_vpc_config,
            )
            eks_waiter = self.eks_client.get_waiter("cluster_active")
            logger.info("Waiting for the EKS Cluster to be successfully created or error out.")
            eks_waiter.wait(
                name=eks_cluster_name,
                WaiterConfig={
                    "Delay": delay_between_attempts,
                    "MaxAttempts": max_attempts_count,
                },
            )
            return eks_cluster
        except (
            self.eks_client.exceptions.ResourceInUseException,
            self.eks_client.exceptions.ResourceLimitExceededException,
            self.eks_client.exceptions.InvalidParameterException,
            self.eks_client.exceptions.ClientException,
            self.eks_client.exceptions.ServerException,
            self.eks_client.exceptions.ServiceUnavailableException,
            self.eks_client.exceptions.UnsupportedAvailabilityZoneException,
        ) as e:
            logger.error("Cluster Creation Failed. Error Occurred.")
            logger.error(f"Currently, the first error encountered is '{e}'. There might be more!")
            raise e
        except Exception as err:
            raise err

    def create_aws_fargate_profile(
        self,
        fargate_profile_name: str,
        eks_cluster_name: str,
        pod_execution_role_arn: str,
        resource_type: str = "eks",
        private_subnets_list=[],
        fargate_selectors=[],
        client_resource_token="",
        tags: list() = [],
        delay_between_attempts: int = 10,
        max_attempts_count: int = 60,
    ) -> dict:
        """
        This Function Creates a Fargate Profile when its name and corresponding eks cluster name is passed.

        Args:
            fargate_profile_name (str): The name to be set for the fargate profile.
            eks_cluster_name (str): The name of the Amazon EKS cluster to apply the Fargate profile to.
            pod_execution_role_arn (str): The Amazon Resource Name (ARN) of the pod execution role to use for pods that
            match the selectors in the Fargate profile.
            private_subnets_list (list, optional): The IDs of subnets to launch the pods into. Defaults to [].
            fargate_selectors (list, optional): The selectors to match for pods to use this Fargate profile. Defaults
            to [].
            client_resource_token (str, optional): Unique, case-sensitive identifier to be provided while calling
            the function to ensure the idempotency of the request. Autopopulated if not passed as argument.
            Defaults to "".
            tags (list, optional): The metadata to apply to the Fargate profile to assist with categorization
            and organization. Each tag consists of a key and an optional value. Defaults to {}.
            delay_between_attempts (int, optional): Number of seconds of wait between each poll attempt. Defaults to 10
            max_attempts_count (int, optional): Number of maximum attempts that must be made. Defaults to 60

        Returns:
            dict: The full description of the Fargate Profile.
        """
        try:
            # tag_value = [dict(tag) for tag in tags]
            tag_spec = {"Resource Type ": resource_type, "Tags ": tags}
            logger.info(f"Creating Fargate Profile {fargate_profile_name}.")
            fargate_profile = self.eks_client.create_fargate_profile(
                fargateProfileName=fargate_profile_name,
                clusterName=eks_cluster_name,
                podExecutionRoleArn=pod_execution_role_arn,
                subnets=private_subnets_list,
                selectors=fargate_selectors,
                clientRequestToken=client_resource_token,
                tags=tag_spec,
            )
            eks_waiter = self.eks_client.get_waiter("fargate_profile_active")
            logger.info("Waiting for the Fargate profile to be successfully created or error out.")
            eks_waiter.wait(
                clusterName=eks_cluster_name,
                fargateProfileName=fargate_profile_name,
                WaiterConfig={
                    "Delay": delay_between_attempts,
                    "MaxAttempts": max_attempts_count,
                },
            )
            return fargate_profile
        except (
            BotoException.InvalidParameterException,
            BotoException.InvalidRequestException,
            BotoException.ClientException,
            BotoException.ServerException,
            BotoException.ResourceLimitExceededException,
            BotoException.UnsupportedAvailabilityZoneException,
        ) as e:
            logger.error(f"Currently, the first Error encountered is '{e}'. There might be more!")
        except Exception as err:
            raise err

    def describe_eks_cluster(self, eks_cluster_name: str) -> dict:
        """This function creates a description for the EKS Cluster whose name is passed as argument.

        Args:
            eks_cluster_name (str): Name of the cluster to describe

        Returns:
            dict: Full description of the specified cluster.
        """
        try:
            logger.info(f"Describing '{eks_cluster_name}' cluster")
            cluster_description = self.eks_client.describe_cluster(name=eks_cluster_name)
            return cluster_description
        except (
            BotoException.ResourceNotFoundException,
            BotoException.ClientException,
            BotoException.ServerException,
            BotoException.ServiceUnavailableException,
        ) as e:
            logger.error(f"Currently, the first Error encountered is '{e}'. There might be more!")

    def describe_eks_nodegroup(self, eks_cluster_name: str, node_group_name: str) -> dict:
        """This function creates a description for the nodegroups of the specified cluster.

        Args:
            eks_cluster_name (str): The name of the Amazon EKS cluster associated with the node group.
            node_group_name (str): Name of the nodegroup to describe.

        Returns:
            dict: Full description of the nodegroup.
        """
        try:
            logger.info(f"Describing EKS Nodegroup '{node_group_name}' for '{eks_cluster_name}' cluster")
            nodegroup_description = self.eks_client.describe_nodegroup(
                clusterName=eks_cluster_name, nodegroupName=node_group_name
            )
            return nodegroup_description
        except (
            BotoException.InvalidParameterException,
            BotoException.ResourceNotFoundException,
            BotoException.ClientException,
            BotoException.ServerException,
            BotoException.ServiceUnavailableException,
        ) as e:
            logger.error(f"Currently, the first Error encountered is '{e}'. There might be more!")

    def describe_fargate_profile(self, eks_cluster_name: str, fargate_profile_name: str) -> dict:
        """This function describes the fargate profile whose name is passed as an argument.

        Args:
            eks_cluster_name (str): The name of the Amazon EKS cluster associated with the Fargate profile.
            fargate_profile_name (str): The name of the fargate profile to be described.

        Returns:
            dict: Full description of the fargate profile whose name is passed.
        """
        try:
            logger.info(f"Describing Fargate Profile '{fargate_profile_name}' having cluster '{eks_cluster_name}'")
            fargate_description = self.eks_client.describe_fargate_profile(
                clusterName=eks_cluster_name, fargateProfileName=fargate_profile_name
            )
            return fargate_description
        except (
            BotoException.InvalidParameterException,
            BotoException.ClientException,
            BotoException.ServerException,
            BotoException.ResourceNotFoundException,
        ) as e:
            logger.error(f"Currently, the first Error encountered is '{e}'. There might be more!")

    def get_eks_clusters(
        self,
        max_result_value: int = 100,
        next_token_value: str = "",
        external_clusters: list = [],
    ) -> dict:
        """This function returns list of all EKS clusters in the Authenticated AWS Account in the specified region.

        Args:
            max_result_value (int, optional): Maximum number of EKS clusters returned by one function call.
            Takes a value between 1 & 100. Defaults to 100.
            next_token_value (str, optional): This is returned from the previous function call and is used to make
            additional calls to get list of remaining EKS clusters. Defaults to "".
            external_clusters (list, optional): Indicates whether external clusters are included in the returned list.
            Set it as ['all'] to return all connected clusters. Default value returns only AWS clusters. Defaults to [].

        Returns:
            dict: List of all clusters in the account in the specified region along with a nextToken string.
        """
        try:
            logger.info("Getting a list of all the EKS clusters present.")
            clusters = self.eks_client.list_clusters(
                maxResults=max_result_value,
                nextToken=next_token_value,
                include=external_clusters,
            )
            return clusters
        except (
            BotoException.InvalidParameterException,
            BotoException.ClientException,
            BotoException.ServerException,
            BotoException.ServiceUnavailableException,
        ) as e:
            logger.error(f"Currently, the first Error encountered is '{e}'. There might be more!")

    def get_eks_nodegroups(
        self,
        eks_cluster_name: str,
        max_result_value: int = 100,
        next_token_value: str = "",
    ) -> dict:
        """This function returns a list of all the nodegroups associated with the passed EKS cluster.

        Args:
            eks_cluster_name (str): The name of the Amazon EKS cluster whose nodegroups is to be listed.
            max_result_value (int, optional): Maximum number of EKS clusters returned by one funciton call.
            Takes a value between 1 & 100. Defaults to 100.
            next_token_value (str, optional): This is returned from the previous function call and is used to make
            additional calls to get list of remaining EKS clusters. Defaults to "".

        Returns:
            dict: List of all the nodegroups for the given EKS cluster along with nextToken string.
        """
        try:
            logger.info(f"Getting a list of all the nodegroups associated to '{eks_cluster_name}' cluster")
            nodegroups = self.eks_client.list_nodegroups(
                clusterName=eks_cluster_name,
                maxResults=max_result_value,
                nextToken=next_token_value,
            )
            return nodegroups
        except (
            self.eks_client.exceptions.InvalidParameterException,
            self.eks_client.exceptions.ClientException,
            self.eks_client.exceptions.ServerException,
            self.eks_client.exceptions.ServiceUnavailableException,
            self.eks_client.exceptions.ResourceNotFoundException,
        ) as e:
            logger.warning(f"Currently, the first Error encountered is '{e}'. There might be more!")

    def get_aws_fargate_profiles(
        self,
        eks_cluster_name: str,
        max_result_value: int = 100,
        next_token_value: str = "",
    ) -> dict:
        """This function lists the fargate profiles associated with the specified cluster in the authenticated AWS
          account in the specified region.

        Args:
            eks_cluster_name (str): Name of the EKS cluster Within which the fargate profiles are to be listed.
            max_result_value (int, optional): Maximum number of EKS clusters returned by one funciton call. Takes a
            value between 1 & 100. Defaults to 100.
            next_token_value (str, optional): This is returned from the previous function call and is used to make
            additional calls to get list of remaining EKS clusters. Defaults to "".

        Returns:
            dict: List of all the fargate profiles associated with the specified EKS cluster along with a nextToken
            string.
        """
        try:
            logger.info(f"Getting a list of Fargate Profiles having '{eks_cluster_name}' cluster")
            fargate_profiles = self.eks_client.list_fargate_profiles(
                clusterName=eks_cluster_name,
                maxResult=max_result_value,
                nextToken=next_token_value,
            )
            return fargate_profiles
        except (
            BotoException.InvalidParameterException,
            BotoException.ResourceNotFoundException,
            BotoException.ClientException,
            BotoException.ServerException,
        ) as e:
            logger.error(f"Currently, the first Error encountered is '{e}'. There might be more!")

    def delete_eks_cluster(self, eks_cluster_name: str, delay_between_attempts: int, max_attempts_count: int) -> dict:
        """This function deletes and returns the description of the specified EKS cluster.

        Args:
            eks_cluster_name (str): Name of the EKS cluster to be deleted.
            delay_between_attempts (int, optional): Number of seconds of wait between each poll attempt. Defaults to 30
            max_attempts_count (int, optional): Number of maximum attempts that must be made. Defaults to 40.

        Returns:
            dict: A full description of the EKS cluster deleted.
        """
        try:
            logger.info(f"Deleting cluster '{eks_cluster_name}'")
            deleted_cluster = self.eks_client.delete_cluster(name=eks_cluster_name)
            eks_waiter = self.eks_client.get_waiter("cluster_deleted")
            logger.info("Waiting for the EKS Clusters to be successfully deleted or error out.")
            eks_waiter.wait(
                name=eks_cluster_name,
                WaiterConfig={
                    "Delay": delay_between_attempts,
                    "MaxAttempts": max_attempts_count,
                },
            )
            return deleted_cluster

        except (
            BotoException.ResourceInUseException,
            BotoException.ResourceNotFoundException,
            BotoException.ClientException,
            BotoException.ServerException,
            BotoException.ServiceUnavailableException,
        ) as e:
            logger.warning(f"Currently, the first Error encountered is '{e}'. There might be more!")

    def delete_eks_nodegroup(
        self,
        eks_cluster_name: str,
        node_group_name: str,
        delay_between_attempts: int,
        max_attempts_count: int,
    ) -> dict:
        """This function deletes the mentioned nodegroup in the specified EKS cluster and returns the nodegroup's
        description.

        Args:
            eks_cluster_name (str): Name of the EKS cluster whose nodegroup is to be deleted.
            node_group_name (str): The nodegroup to be deleted.
            delay_between_attempts (int, optional): Number of seconds of wait between each poll attempt. Defaults to 30
            max_attempts_count (int, optional): Number of maximum attempts that must be made. Defaults to 40

        Returns:
            dict: Full description of the nodegroup deleted.
        """
        try:
            logger.info(f"Deleting eks nodegroup '{node_group_name}' of '{eks_cluster_name}' cluster")
            deleted_nodegroup = self.eks_client.delete_nodegroup(
                clusterName=eks_cluster_name, nodegroupName=node_group_name
            )
            eks_waiter = self.eks_client.get_waiter("nodegroup_deleted")
            logger.info("Waiting for the nodegroup to be successfully deleted or error out.")
            eks_waiter.wait(
                clusterName=eks_cluster_name,
                nodegroupName=node_group_name,
                WaiterConfig={
                    "Delay": delay_between_attempts,
                    "MaxAttempts": max_attempts_count,
                },
            )
            return deleted_nodegroup
        except (
            BotoException.ResourceInUseException,
            BotoException.ResourceNotFoundException,
            BotoException.InvalidParameterException,
            BotoException.ClientException,
            BotoException.ServerException,
            BotoException.ServiceUnavailableException,
        ) as e:
            logger.warning(f"Currently, the first Error encountered is '{e}'. There might be more!")

    def delete_aws_fargate_profile(
        self,
        eks_cluster_name: str,
        fargate_profile_name: str,
        delay_between_attempts: int,
        max_attempts_count: int,
    ) -> dict:
        """This function deleted and return a description of the specified fargate profile associated with the
        specified EKS cluster.

        Args:
            eks_cluster_name (str): Name of the EKS cluster associated with the fargate profile to be deleted.
            fargate_profile_name (str): Name of the fargate profile to be deleted.
            delay_between_attempts (int, optional): Number of seconds of wait between each poll attempt. Defaults to 30
            max_attempts_count (int, optional): Number of maximum attempts that must be made. Defaults to 60

        Returns:
            dict: Full Description of the deleted fargate profile.
        """
        try:
            logger.info(f"Deleting Fargate Profile '{fargate_profile_name}' associated to cluster '{eks_cluster_name}'")
            deleted_fargate_profile = self.eks_client.delete_fargate_profile(
                clusterName=eks_cluster_name, fargateProfileName=fargate_profile_name
            )
            eks_waiter = self.eks_client.get_waiter("fargate_profile_deleted")
            logger.info("Waiting for the Fargate profile to be successfully deleted or error out.")
            eks_waiter.wait(
                clusterName=eks_cluster_name,
                fargateProfileName=fargate_profile_name,
                WaiterConfig={
                    "Delay": delay_between_attempts,
                    "MaxAttempts": max_attempts_count,
                },
            )
            return deleted_fargate_profile
        except (
            BotoException.InvalidParameterException,
            BotoException.ClientException,
            BotoException.ServerException,
            BotoException.ResourceNotFoundException,
        ) as e:
            logger.warning(f"Currently, the first Error encountered is '{e}'. There might be more!")

    def close_client_connection(self):
        """
        This Function closes the Boto3 Session.

        """
        logger.info("Closing the Boto3 Session")
        self.eks_client.close()
        logger.info("Boto3 Session closed successfully.")

    def get_eks_addons(
        self,
        eks_cluster_name: str,
        max_result_value: int = 100,
        next_token_value: str = "",
    ) -> dict:
        """This function returns a list of all the addon associated with the passed EKS cluster.

        Args:
            eks_cluster_name (str): The name of the Amazon EKS cluster whose nodegroups is to be listed.
            max_result_value (int, optional): Maximum number of EKS clusters returned by one funciton call.
            Takes a value between 1 & 100. Defaults to 100.
            next_token_value (str, optional): This is returned from the previous function call and is used to make
            additional calls to get list of remaining EKS clusters. Defaults to "".

        Returns:
            dict: List of all the addon for the given EKS cluster along with nextToken string.
        """
        try:
            logger.info(f"Getting a list of all the addon associated to '{eks_cluster_name}' cluster")
            addons = self.eks_client.list_addons(
                clusterName=eks_cluster_name,
                maxResults=max_result_value,
                nextToken=next_token_value,
            )
            return addons
        except (
            BotoException.InvalidParameterException,
            BotoException.ClientException,
            BotoException.ServerException,
            BotoException.ServiceUnavailableException,
            BotoException.ResourceNotFoundException,
        ) as e:
            logger.warning(f"Currently, the first Error encountered is '{e}'. There might be more!")

    def wait_for_update_status(self, cluster_name, update_id, expected_status="Successful"):
        logger.info(f"Waiting for update state to be {expected_status}")
        minutes_to_wait = 15
        try:
            wait(
                lambda: self.eks_client.describe_update(name=cluster_name, updateId=update_id)["update"]["status"]
                == expected_status,
                timeout_seconds=minutes_to_wait * 60,
                sleep_seconds=5,
            )
        except TimeoutExpired as e:
            status = self.eks_client.describe_update(name=cluster_name, updateId=update_id)["update"]["status"]
            logger.error(
                f"Waited {minutes_to_wait} minutes for Update status {expected_status}, but it's still in status {status}"
            )
            raise e

    def wait_for_nodegroup_update_status(
        self,
        cluster_name,
        update_id,
        nodegroup_name,
        expected_status="Successful",
    ):
        """
        This method waits for the specified EKS nodegroup update to reach the expected status.

        Args:
          cluster_name (str): The name of the EKS cluster.
          update_id (str): The unique ID of the update to monitor.
          nodegroup_Name (str): The name of the EKS nodegroup associated with the update.
          expected_status (str, optional): The expected update status to wait for (default is "Successful").

        Raises:
          TimeoutExpired: If the specified timeout is reached before the update reaches the expected status.

        Returns:
            None
        """
        logger.info(f"Waiting for nodegroup update state to be {expected_status}")
        minutes_to_wait = 30
        try:
            wait(
                lambda: self.eks_client.describe_update(
                    name=cluster_name, updateId=update_id, nodegroupName=nodegroup_name
                )["update"]["status"]
                == expected_status,
                timeout_seconds=minutes_to_wait * 60,
                sleep_seconds=5,
            )
        except TimeoutExpired as e:
            status = self.eks_client.describe_update(name=cluster_name, updateId=update_id)["update"]["status"]
            logger.error(
                f"Waited {minutes_to_wait} minutes for Update status {expected_status}, but it's still in status {status}"
            )
            raise e
