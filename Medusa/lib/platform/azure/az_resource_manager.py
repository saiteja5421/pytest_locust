"""Documentation
https://learn.microsoft.com/en-us/python/api/azure-mgmt-resource/azure.mgmt.resource.resources.v2016_02_01.operations.resourcegroupsoperations?view=azure-python#azure-mgmt-resource-resources-v2016-02-01-operations-resourcegroupsoperations

https://learn.microsoft.com/en-us/python/api/azure-mgmt-resource/azure.mgmt.resource.subscriptions.v2016_06_01.operations.subscriptionsoperations?view=azure-python#azure-mgmt-resource-subscriptions-v2016-06-01-operations-subscriptionsoperations
"""

import logging
from typing import MutableMapping, Union, Any

from lib.common.enums.az_regions import AZRegion

from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import ResourceGroup
from azure.mgmt.resource.subscriptions.v2021_01_01 import SubscriptionClient
from azure.mgmt.resource.subscriptions.models import Location
from azure.mgmt.resource.templatespecs.models import TemplateSpecExpandKind, TemplateSpec
from azure.mgmt.resource.templatespecs import TemplateSpecsClient

from azure.core.exceptions import HttpResponseError

logger = logging.getLogger()


class AZResourceManager:
    def __init__(
        self,
        credential: Union[DefaultAzureCredential, ClientSecretCredential],
        subscription_id: str,
    ) -> None:
        self.resource_client = ResourceManagementClient(credential, subscription_id)
        self.subscription_client = SubscriptionClient(credential)
        self.template_spec_client = TemplateSpecsClient(credential, subscription_id)

    def get_resource_group_by_name(self, resource_group_name: str) -> ResourceGroup:
        """Get a Resource Group by name

        Args:
            resource_group_name (str): The Resource Group name

        Returns:
            ResourceGroup: The ResourceGroup object if found, None otherwise
        """
        resource_group: ResourceGroup = None

        try:
            resource_group = self.resource_client.resource_groups.get(resource_group_name=resource_group_name)
            logger.info(f"Resource Group found: {resource_group.name}")
        except HttpResponseError as error:
            logger.info(f"Error in GET call: {error.message}")

        return resource_group

    def create_or_update_resource_group(
        self, resource_group_name: str, location: AZRegion, tags: dict[str, str] = {}
    ) -> ResourceGroup:
        """Create or Update a Resource Group

        Args:
            resource_group_name (str): Resource Group name
            location (AZRegion): Resource Group location
            tags (dict[str, str], optional): A set of Tags to add to the Resource Group. Defaults to {}.

        Returns:
            ResourceGroup: The new or updated ResourceGroup if successful, None otherwise
        """
        resource_group: ResourceGroup = None
        resource_group_payload = ResourceGroup(location=location.value, tags=tags)

        try:
            resource_group = self.resource_client.resource_groups.create_or_update(
                resource_group_name=resource_group_name, parameters=resource_group_payload
            )
            logger.info(f"Resource Group {resource_group.name} created")
        except HttpResponseError as error:
            logger.info(f"Error in CREATE_OR_UPDATE call: {error.message}")

        return resource_group

    def delete_resource_group(self, resource_group_name: str) -> bool:
        """Delete a Resource Group

        Args:
            resource_group_name (str): The Resource Group name

        Returns:
            bool: True if the Resource Group was found and deleted, False otherwise
        """
        try:
            self.resource_client.resource_groups.begin_delete(resource_group_name=resource_group_name).result()
            logger.info(f"Resource Group {resource_group_name} deleted")
            return True
        except HttpResponseError as error:
            logger.info(f"Error in DELETE call: {error.message}")
            return False

    def get_all_resource_groups_list(self) -> list[ResourceGroup]:
        """Returns a list of all resource groups in the account

        Returns:
            list[ResourceGroup]: A list of resource groups
        """
        resource_groups_list = self.resource_client.resource_groups.list()
        resource_groups: list[ResourceGroup] = [resource_group for resource_group in resource_groups_list]
        logger.info(f"Fetched resource groups list is {resource_groups}")
        return resource_groups

    def get_all_locations(self, subscription_id: str) -> list[Location]:
        """Retrieves all the available locations (regions) in the provided subscription

        Args:
            subscription_id (str): Azure Account Subscription ID

        Returns:
            list[Location]: list of locations
        """
        locations = self.subscription_client.subscriptions.list_locations(subscription_id=subscription_id)
        # below line is failing wit error:
        # Bearer token authentication is not permitted for non-TLS protected (non-https) URLs.
        locations: list[Location] = [location.name for location in locations]
        logger.info(f"Retrieved locations are {locations}")
        return locations

    def get_arm_template(
        self, resource_group_name: str, template_spec_name: str, expand: TemplateSpecExpandKind = None
    ) -> TemplateSpec:
        """Get ARM Template

        Args:
            resource_group_name (str): Name of Resource Group
            template_spec_name (str): name of the Template Spec
            expand (TemplateSpecExpandKind, optional): Allows for expansion of additional Template Spec details. Defaults to None.

        Returns:
            arm_template (TemplateSpec): TemplateSpec object
        """
        arm_template = self.template_spec_client.template_specs.get(
            resource_group_name=resource_group_name, template_spec_name=template_spec_name, expand=expand
        )
        logger.info(f"Obtained ARM Template {template_spec_name} ({arm_template.id})")
        return arm_template

    def create_or_update_arm_template(
        self,
        resource_group_name: str,
        template_spec_name: str,
        description: str,
        display_name: str,
        location: AZRegion = AZRegion.EAST_US,
        tags: dict[str, str] = {},
        metadata: MutableMapping[str, Any] = None,
        content_type: Union[str, None] = "application/json",
    ) -> TemplateSpec:
        """Create or update ARM Template

        Args:
            resource_group_name (str): Name of Resource Group
            template_spec_name (str): Name of Template Spec
            description (str): Template Spec description
            display_name (str): Display name of Template Spec
            location (AZRegion, optional): Location of Template Spec. Defaults to AZRegion.EAST_US.value.
            tags (dict[str, str], optional): Tags of Template Spec. Defaults to {}.
            metadata (MutableMapping[str, Any], optional): Template Spec metadata. Defaults to None.
            content_type (Union[str, None], optional): Body parameter content-type. Defaults to "applicationjson".

        Returns:
            created_updated_template_spec (TemplateSpec): Newly created/updated ARM Template object
        """
        template_spec: TemplateSpec = TemplateSpec(
            location=location.value, tags=tags, description=description, display_name=display_name, metadata=metadata
        )
        created_updated_template_spec = self.template_spec_client.template_specs.create_or_update(
            resource_group_name=resource_group_name,
            template_spec_name=template_spec_name,
            template_spec=template_spec,
            content_type=content_type,
        )
        logger.info(f"Created/Updated ARM Template: {created_updated_template_spec.id}")
        return created_updated_template_spec

    def delete_arm_template(self, resource_group_name: str, template_spec_name: str) -> None:
        """Delete ARM Template

        Args:
            resource_group_name (str): Name of Resource Group
            template_spec_name (str): Name of Template Spec
        """
        self.template_spec_client.template_specs.delete(
            resource_group_name=resource_group_name, template_spec_name=template_spec_name
        )
        logger.info(f"Deleted ARM Template: {template_spec_name}")
