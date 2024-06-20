"""Documentation
https://learn.microsoft.com/en-us/python/api/azure-mgmt-network/azure.mgmt.network.v2022_05_01.operations.networkinterfacesoperations?view=azure-python#azure-mgmt-network-v2022-05-01-operations-networkinterfacesoperations-begin-create-or-update
"""

import logging
from typing import Union

from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import (
    Subnet,
    VirtualNetwork,
    AddressSpace,
    NetworkInterface,
    NetworkInterfaceIPConfiguration,
    NetworkSecurityGroup,
    SubResource,
    SecurityRule,
    SecurityRuleProtocol,
    SecurityRuleAccess,
    SecurityRuleDirection,
    PublicIPAddress,
    IPAllocationMethod,
    PublicIPAddressSku,
    PublicIPAddressSkuName,
    RouteTable,
    Route,
    RouteNextHopType,
)
from azure.core.exceptions import HttpResponseError
from lib.common.enums.az_regions import AZRegion, AZZone

logger = logging.getLogger()


class AZNetworkManager:
    def __init__(
        self,
        credential: Union[DefaultAzureCredential, ClientSecretCredential],
        subscription_id: str,
    ) -> None:
        self.network_client = NetworkManagementClient(credential, subscription_id)

    def get_all_subnets_from_resource_group(self, resource_group_name: str, virtual_network_name: str) -> list[Subnet]:
        """Returns all the subnets from the provided resource group name

        Args:
            resource_group_name (str): Resource Group Name
            virtual_network_name (str): Virtual Network Name

        Returns:
            list[Subnet]: A list of Subnet object
        """
        subnets = self.network_client.subnets.list(
            resource_group_name=resource_group_name,
            virtual_network_name=virtual_network_name,
        )
        subnets: list[Subnet] = [subnet for subnet in subnets]
        logger.info(f"Subnets in RG {resource_group_name} are {subnets}")
        return subnets

    def get_subnet(self, resource_group_name: str, virtual_network_name: str, subnet_name: str) -> Subnet:
        """Get Subnet by name

        Args:
            resource_group_name (str): Resource Group name
            virtual_network_name (str): Virtual Network name
            subnet_name (str): Subnet name

        Returns:
            Subnet: The Subnet object if found, None otherwise
        """
        subnet: Subnet = None

        try:
            subnet = self.network_client.subnets.get(
                resource_group_name=resource_group_name,
                virtual_network_name=virtual_network_name,
                subnet_name=subnet_name,
            )
            logger.info(f"Subnet found in RG {resource_group_name} : {subnet.name}")
        except HttpResponseError as error:
            logger.info(f"Error in GET call: {error.message}")

        return subnet

    def get_virtual_network(
        self,
        resource_group_name: str,
        virtual_network_name: str,
    ) -> VirtualNetwork:
        """Returns the subnet found by the name provided

        Args:
            resource_group_name (str): Name of the resource group
            virtual_network_name (str): Name of the virtual network

        Returns:
            VirtualNetwork: VirtualNetwork object
        """
        virtual_network: VirtualNetwork = self.network_client.virtual_networks.get(
            resource_group_name=resource_group_name,
            virtual_network_name=virtual_network_name,
        )
        logger.info(f"Fetched virtual network is {virtual_network}")
        return virtual_network

    def get_all_virtual_networks(self, resource_group_name: str) -> list[VirtualNetwork]:
        """Returns the virtual network (VNet) found by the name provided

        Args:
            resource_group_name (str): Name of the resource group

        Returns:
            VirtualNetwork: VirtualNetwork object
        """
        virtual_networks = self.network_client.virtual_networks.list(resource_group_name=resource_group_name)
        virtual_networks: list[VirtualNetwork] = [virtual_network for virtual_network in virtual_networks]
        virtual_network_name = [virtual_network.name for virtual_network in virtual_networks]
        logger.info(f"Virtual Network in RG {resource_group_name} are {virtual_network_name}")
        return virtual_networks

    def get_network_interface(
        self,
        resource_group_name: str,
        network_interface_name: str,
    ) -> NetworkInterface:
        """Returns the subnet found by the name provided

        Args:
            resource_group_name (str): Name of the resource group
            network_interface_name (str): Name of the NIC

        Returns:
            NetworkInterface: NetworkInterface object
        """
        network_interface: NetworkInterface = self.network_client.network_interfaces.get(
            resource_group_name=resource_group_name,
            network_interface_name=network_interface_name,
        )
        logger.info(f"Fetched NIC is {network_interface}")
        return network_interface

    def create_virtual_network(
        self,
        resource_group_name: str,
        virtual_network_name: str,
        location: AZRegion,
        subnet_id: str = None,
        subnet_name: str = "automation-subnet",
        subnet_prefix: str = "10.0.0.0/24",
        address_prefixes: list[str] = ["10.0.0.0/16"],
    ) -> VirtualNetwork:
        """Creates a virtual network with the provided RG, Location, and Addresses

        Args:
            resource_group_name (str): Name of the resource group under which the VNet should be created
            virtual_network_name (str): name of the virtual network
            location (AZRegion): Region under which the VNet should reside
            subnet_id (str): ID of the subnet. Defaults to None
            MUST provide subnet_id if default values for subnet_name and subnet_prefix don't want to be used
            If subnet_id is provided, then subnet_name and subnet_prefix will not be used

            subnet_name (str, optional): Name of the subnet. Defaults to 'automation-subnet'
            subnet_prefix (str, optional): Subnet Address Prefix. Defaults to '10.0.0.0/24'
            address_prefixes (list[str], optional): IP Address Allocation. Defaults to ["10.0.0.0/16"].

        Returns:
            virtual_network (VirtualNetwork): created virtual network
        """
        if subnet_id:
            subnet_params = Subnet(id=subnet_id)
        else:
            subnet_params = Subnet(name=subnet_name, address_prefix=subnet_prefix)

        virtual_network_params = VirtualNetwork(
            location=location.value,
            address_space=AddressSpace(address_prefixes=address_prefixes),
            subnets=[subnet_params],
        )

        logger.info(f"Creating VNet {virtual_network_name}, address {address_prefixes} in {location.value}")
        virtual_network: VirtualNetwork = self.network_client.virtual_networks.begin_create_or_update(
            resource_group_name=resource_group_name,
            virtual_network_name=virtual_network_name,
            parameters=virtual_network_params,
        ).result()

        logger.info(f"Created virtual network is {virtual_network}")

        return virtual_network

    def delete_virtual_network(
        self,
        resource_group_name: str,
        virtual_network_name: str,
    ):
        """Deletes a Virtual Network

        Args:
            resource_group_name (str): Resource Group Name
            virtual_network_name (str): VNet Name
        """
        logger.info(f"Deleting Virtual Network {virtual_network_name}")
        self.network_client.virtual_networks.begin_delete(
            resource_group_name=resource_group_name,
            virtual_network_name=virtual_network_name,
        ).result()

    def create_network_interface(
        self,
        resource_group_name: str,
        network_interface_name: str,
        location: AZRegion,
        subnet_id: str,
        security_group_id: str = None,
        public_ip_address: PublicIPAddress = None,
    ) -> NetworkInterface:
        """Creates a Network Interface in the provided Resource Group and Subnet

        Args:
            resource_group_name (str): Name of the Resource Group
            network_interface_name (str): Name of the Network Interface
            location (AZRegion): Location under which the NIC should be created
            subnet_id (str): ID of the subnet to be used for NIC creation (address allocation)
            security_group_id (str, optional): ID of a Security Group.
            Uses the security group for the created NIC if provided. Defaults to 'None'
            public_ip_address (PublicIPAddress):If provided, assigns the Public IP Address to the NIC. Defaults to None

        Returns:
            NetworkInterface: NetworkInterface object
        """
        network_interface_params = NetworkInterface(
            location=location.value,
            ip_configurations=[
                NetworkInterfaceIPConfiguration(
                    name="ipconfig1",
                    subnet=SubResource(id=subnet_id),
                ),
            ],
        )

        if public_ip_address:
            network_interface_params.ip_configurations[0].public_ip_address = public_ip_address

        if security_group_id:
            network_security_group = NetworkSecurityGroup(id=security_group_id)
            network_interface_params.network_security_group = network_security_group

        logger.info(f"Creating NIC {network_interface_name} with Subnet {subnet_id} in {location.value}")
        network_interface: NetworkInterface = self.network_client.network_interfaces.begin_create_or_update(
            resource_group_name=resource_group_name,
            network_interface_name=network_interface_name,
            parameters=network_interface_params,
        ).result()

        logger.info(f"Created NIC is {network_interface}")
        return network_interface

    def delete_network_interface(
        self,
        resource_group_name: str,
        network_interface_name: str,
    ):
        """Deletes a Network Interface

        Args:
            resource_group_name (str): Resource Group Name
            network_interface_name (str): NIC Name
        """
        logger.info(f"Deleting NIC {network_interface_name}")
        self.network_client.network_interfaces.begin_delete(
            resource_group_name=resource_group_name,
            network_interface_name=network_interface_name,
        ).result()

    def get_all_security_groups(self, resource_group_name: str) -> list[NetworkSecurityGroup]:
        """Retrieves all the Network Security Groups present within the provided resource_group_name

        Args:
            resource_group_name (str): Name of the resource group

        Returns:
            list[NetworkSecurityGroup]: List of Network Security Groups
        """
        security_groups = self.network_client.network_security_groups.list(resource_group_name=resource_group_name)
        security_groups: list[NetworkSecurityGroup] = [security_group for security_group in security_groups]
        logger.info(f"Security Groups in RG {resource_group_name} are {security_groups}")
        return security_groups

    def create_security_group(
        self,
        resource_group_name: str,
        security_group_name: str,
        location: AZRegion,
        description: str = "SSH Security Group",
        sg_rule_name: str = "ssh-rg-rule",
        source_port_range: Union[int, str] = "*",
        destination_port_range: int = 22,
        access: SecurityRuleAccess = SecurityRuleAccess.ALLOW,
        direction: SecurityRuleDirection = SecurityRuleDirection.INBOUND,
        priority: int = 100,
    ) -> NetworkSecurityGroup:
        """Creates a network security group with the specified ports

        Args:
            resource_group_name (str): Resource Group Name
            security_group_name (str): Security Group Name
            location (AZRegion): Location under which the security group should be created
            description (str, optional): Security Group description. Defaults to "SSH Security Rule".
            sg_rule_name (str, optional): SG rule name. Defaults to "ssh-rg-rule".
            The name can be up to 80 characters long. It must begin with a word character,
            and it must end with a word character or with '_'. The name may contain word characters or '.', '-', '_'.

            source_port_range (Union[int, str], optional): source port number. Defaults to * as recommended by Azure.
            destination_port_range (int, optional): destination port number. Defaults to 22.
            access (SecurityRuleAccess, optional): Access of the SG rule. Defaults to SecurityRuleAccess.ALLOW.
            direction (SecurityRuleDirection, optional): Direction of the security group rule.
            Defaults to SecurityRuleDirection.INBOUND.
            priority (int, optional): Priority of the SG rule. Defaults to 100

        Returns:
            NetworkSecurityGroup: NetworkSecurityGroup object
        """
        security_rule = SecurityRule(
            name=sg_rule_name,
            description=description,
            protocol=SecurityRuleProtocol.TCP,
            source_port_range=source_port_range,
            destination_port_range=destination_port_range,
            access=access,
            direction=direction,
            source_address_prefix="*",
            destination_address_prefix="*",
            priority=priority,
        )

        network_security_group = NetworkSecurityGroup(location=location.value, security_rules=[security_rule])
        security_group: NetworkSecurityGroup = self.network_client.network_security_groups.begin_create_or_update(
            resource_group_name=resource_group_name,
            network_security_group_name=security_group_name,
            parameters=network_security_group,
        ).result()

        logger.info(f"Created Security Group is {security_group}")
        return security_group

    def delete_security_group(
        self,
        resource_group_name: str,
        security_group_name: str,
    ):
        """Deletes a security group

        Args:
            resource_group_name (str): Resource Group Name
            security_group_name (str): Security Group Name
        """
        logger.info(f"Deleting security group {security_group_name}")
        self.network_client.network_security_groups.begin_delete(
            resource_group_name=resource_group_name,
            network_security_group_name=security_group_name,
        ).result()

    def create_subnet(
        self,
        resource_group_name: str,
        virtual_network_name: str,
        subnet_name: str,
        address_prefixes: list[str] = ["10.0.0.0/24"],
    ):
        """Creates a subnet in the specified VNet

        Args:
            resource_group_name (str): Resource Group Name
            virtual_network_name (str): VNet name
            subnet_name (str): Subnet Name
            address_prefixes (list, optional): Subnet address prefixes. Defaults to ["10.0.0.0/24"].
        """
        subnet_parameters = Subnet(
            name=subnet_name,
            address_prefixes=address_prefixes,
        )

        subnet: Subnet = self.network_client.subnets.begin_create_or_update(
            resource_group_name=resource_group_name,
            virtual_network_name=virtual_network_name,
            subnet_name=subnet_name,
            subnet_parameters=subnet_parameters,
        ).result()

        logger.info(f"Created subnet is {subnet}")

    def delete_subnet(
        self,
        resource_group_name: str,
        virtual_network_name: str,
        subnet_name: str,
    ):
        """Deletes a subnet

        Args:
            resource_group_name (str): Resource Group name
            virtual_network_name (str): VNet name
            subnet_name (str): Subnet name
        """
        logger.info(f"Deleting subnet {subnet_name} in VNet {virtual_network_name}")
        self.network_client.subnets.begin_delete(
            resource_group_name=resource_group_name,
            virtual_network_name=virtual_network_name,
            subnet_name=subnet_name,
        ).result()

    def update_subnet_route_table(
        self,
        resource_group_name: str,
        virtual_network_name: str,
        subnet_name: str,
        route_table: RouteTable,
    ) -> Subnet:
        """Update the RouteTable of a Subnet

        Args:
            resource_group_name (str): Resource Group name
            virtual_network_name (str): Virtual Network name
            subnet_name (str): Subnet name
            route_table (RouteTable): The RouteTable to add to the Subnet

        Returns:
            Subnet: The updated Subnet object
        """
        subnet = self.get_subnet(
            resource_group_name=resource_group_name,
            virtual_network_name=virtual_network_name,
            subnet_name=subnet_name,
        )

        # The Subnet must already exist
        if not subnet:
            logger.info(f"Subnet must exist: {subnet_name}")
            return subnet

        subnet.route_table = route_table

        subnet = self.network_client.subnets.begin_create_or_update(
            resource_group_name=resource_group_name,
            virtual_network_name=virtual_network_name,
            subnet_name=subnet_name,
            subnet_parameters=subnet,
        ).result()

        logger.info(f"Updated Subnet {subnet.name} RouteTable")

        return subnet

    def get_all_public_ips(self, resource_group_name: str) -> list[PublicIPAddress]:
        """Retrieves all the Public IPs present within the provided resource_group_name

        Args:
            resource_group_name (str): Name of the resource group

        Returns:
            list[PublicIPAddress]: List of Public IPs
        """
        public_ips = self.network_client.public_ip_addresses.list(resource_group_name=resource_group_name)
        public_ips: list[PublicIPAddress] = [public_ip for public_ip in public_ips]
        logger.info(f"Public IPs in RG {resource_group_name} are {public_ips}")
        return public_ips

    def create_public_ip(
        self,
        resource_group_name: str,
        public_ip_address_name: str,
        location: AZRegion,
        az_zones: list[AZZone] = [AZZone.ZONE_1],
        sku_name: PublicIPAddressSkuName = PublicIPAddressSkuName.STANDARD,
        public_ip_allocation_method: IPAllocationMethod = IPAllocationMethod.STATIC,
    ) -> PublicIPAddress:
        """Creates a Public IP Address

        Args:
            resource_group_name (str): Resource Group name
            public_ip_address_name (str): Public IP Address name
            location (AZRegion): Location under which the Public IP should be created
            az_zones (list[AZZone]): Zones under which the Public IP should be created. Defaults to [AZZone.ZONE_1]
            NOTE: The zone of the Public IP and VM MUST be the same to work
            sku_name (PublicIPAddressSkuName): Name of SKU standard. Defaults to PublicIPAddressSkuName.STANDARD
            public_ip_allocation_method (IPAllocationMethod): Public IP Allocation method.
                                                              Defaults to IPAllocationMethod.STATIC

        Returns:
            PublicIPAddress: Created Public IP Address
        """
        zones = [zone.value for zone in az_zones]
        public_ip = PublicIPAddress(
            location=location.value,
            public_ip_allocation_method=public_ip_allocation_method,
            zones=zones,
            sku=PublicIPAddressSku(name=sku_name),
        )

        logger.info(f"Creating Public IP Address {public_ip_address_name}")
        public_ip_address: PublicIPAddress = self.network_client.public_ip_addresses.begin_create_or_update(
            resource_group_name=resource_group_name,
            public_ip_address_name=public_ip_address_name,
            parameters=public_ip,
        ).result()

        return public_ip_address

    def delete_public_ip_address(
        self,
        resource_group_name: str,
        public_ip_address_name: str,
    ):
        """Deletes Public IP Address by name

        Args:
            resource_group_name (str): Resource Group name
            public_ip_address_name (str): Public IP Address name
        """
        logger.info(f"Deleting Public IP Address {public_ip_address_name}")
        self.network_client.public_ip_addresses.begin_delete(
            resource_group_name=resource_group_name,
            public_ip_address_name=public_ip_address_name,
        ).result()
        logger.info(f"Deleted Public IP Address {public_ip_address_name}")

    def create_or_update_route_table(
        self,
        resource_group_name: str,
        route_table_name: str,
        location: AZRegion = AZRegion.EAST_US,
        tags: dict[str, str] = None,
        routes: list[Route] = [
            Route(
                name="pqa-default-route",
                type=None,
                address_prefix="10.0.0.0/16",
                next_hop_ip_address=None,
                next_hop_type=RouteNextHopType.VNET_LOCAL.value,
            )
        ],
        disable_bgp_route_propagation: bool = False,
    ) -> RouteTable:
        """Create or Update a Route Table

        Args:
            resource_group_name (str): The name of the resource group
            route_table_name (str): The name of the route table
            location (AZRegion, optional): Location of Route Table. Defaults to AZRegion.EAST_US.
            tags (dict[str, str], optional): Tags for Route Table. Defaults to None.
            routes (list[Routes], optional): Routes for Route Table or can pass list as None. Defaults to pre-defined Route parameters.
            disable_bgp_route_propagation (bool, optional): Propagation flag for Route Table. Defaults to False.

        Returns:
            route_table (RouteTable): Newly created or updated Route Table
        """
        route_table = RouteTable(
            id=route_table_name,
            location=location.value,
            tags=tags,
            routes=routes,
            disable_bgp_route_propagation=disable_bgp_route_propagation,
        )
        route_table = self.network_client.route_tables.begin_create_or_update(
            resource_group_name=resource_group_name,
            route_table_name=route_table_name,
            parameters=route_table,
        ).result()
        logger.info(f"Route Table {route_table_name} Created/Updated: {route_table.id}")
        return route_table

    def delete_route_table(
        self,
        resource_group_name: str,
        route_table_name: str,
    ) -> None:
        """Delete Route Table

        Args:
            resource_group_name (str): The name of the resource group
            route_table_name (str): The name of the route table
        """
        self.network_client.route_tables.begin_delete(
            resource_group_name=resource_group_name,
            route_table_name=route_table_name,
        ).result()
        logger.info(f"Route Table {route_table_name} was deleted")

    def get_route_table(self, resource_group_name: str, route_table_name: str) -> RouteTable:
        """Get Route Table

        Args:
            resource_group_name (str): The name of the resource group
            route_table_name (str): The name of the route table

        Returns:
            route_table (RouteTable): RouteTable that was obtained
        """
        route_table: RouteTable = self.network_client.route_tables.get(
            resource_group_name=resource_group_name,
            route_table_name=route_table_name,
        )
        logger.info(f"Route Table {route_table_name} was obtained: {route_table.id}")
        return route_table

    def get_route_in_route_table(self, resource_group_name: str, route_table_name: str, route_name: str) -> Route:
        """Get Route in Route Table

        Args:
            resource_group_name (str): Name of Resource Group
            route_table_name (str): Name of Route Table
            route_name (str): Name of Route

        Returns:
            route (Route): Route object in Route Table
        """
        route = self.network_client.routes.get(
            resource_group_name=resource_group_name,
            route_table_name=route_table_name,
            route_name=route_name,
        )
        logger.info(f"Obtained Route {route_name} ({route.id})")
        return route

    def create_or_update_route_in_route_table(
        self,
        resource_group_name: str,
        route_table_name: str,
        route_name: str,
        type: str = None,
        address_prefix: str = "10.0.0.0/16",
        next_hop_type: RouteNextHopType = RouteNextHopType.VNET_LOCAL,
        next_hop_ip_address: str = None,
        has_bgp_override: bool = None,
    ) -> Route:
        """Create or Update Route in Route Table

        NOTE: Can only create a Route within a Route Table

        Args:
            resource_group_name (str): Name of Resource Group
            route_table_name (str): Name of Route Table
            route_name (str): Name of Route
            type (str, optional): Type of resource. Defaults to None.
            address_prefix (str, optional): Destination CIDR to which the route applies. Defaults to "10.0.0.0/16".
            next_hop_type (RouteNextHopType, optional): Type of Azure hop the packet should be sent to. Defaults to RouteNextHopType.VNET_LOCAL.
            next_hop_ip_address (str, optional): IP address packets should be forwarded to. Only allowed in routes where the next hop type is VirtualAppliance. Defaults to None.
            has_bgp_override (bool, optional): Indication whether route overrides overlapping BGP routes regardless of LPM. Defaults to None.

        Returns:
            route (Route): Newly created or update Route object
        """
        route = self.network_client.routes.begin_create_or_update(
            resource_group_name=resource_group_name,
            route_table_name=route_table_name,
            route_name=route_name,
            route_parameters=Route(
                name=route_name,
                type=type,
                address_prefix=address_prefix,
                next_hop_type=next_hop_type.value,
                next_hop_ip_address=next_hop_ip_address,
                has_bgp_override=has_bgp_override,
            ),
        ).result()
        logger.info(f"Created / Updated Route {route_name} in Route Table {route_table_name}")
        return route

    def delete_route_from_route_table(self, resource_group_name: str, route_table_name: str, route_name: str) -> None:
        """Delete Route from Route Table

        Args:
            resource_group_name (str): Name of Resource Group
            route_table_name (str): Name of Route Table
            route_name (str): Name of Route
        """
        self.network_client.routes.begin_delete(
            resource_group_name=resource_group_name,
            route_table_name=route_table_name,
            route_name=route_name,
        ).result()
        logger.info(f"Deleted Route {route_name} from Route Table {route_table_name}")
