"""
A total of 80 regions are supported:
`az account list-locations -o table`

DSCC is going to support the listed Azure regions:
https://github.hpe.com/nimble-dcs/atlantia-inventory/blob/master/internal/domain/cloud/cloud_infrastructure.go#L44
"""

from enum import Enum


class AZRegion(Enum):
    # NORTH AMERICA
    EAST_US = "eastus"
    EAST_US_2 = "eastus2"
    WEST_US_2 = "westus2"
    WEST_US_3 = "westus3"
    CENTRAL_US = "centralus"
    SOUTH_CENTRAL_US = "southcentralus"
    CANADA_CENTRAL = "canadacentral"

    # EUROPE
    NORTH_EUROPE = "northeurope"
    WEST_EUROPE = "westeurope"
    SWEDEN_CENTRAL = "swedencentral"
    NORWAY_EAST = "norwayeast"
    UK_SOUTH = "uksouth"
    GERMANY_WEST_CENTRAL = "germanywestcentral"
    FRANCE_CENTRAL = "francecentral"
    POLAND_CENTRAL = "polandcentral"

    # ASIA
    SOUTH_EAST_ASIA = "southeastasia"
    KOREA_CENTRAL = "koreacentral"
    JAPAN_EAST = "japaneast"
    CENTRAL_INDIA = "centralindia"
    QATAR_CENTRAL = "qatarcentral"
    ASIA_PACIFIC = "asiapacific"
    UAE_NORTH = "uaenorth"

    # OCEANIA
    AUSTRALIA_EAST = "australiaeast"

    # AFRICA
    SOUTH_AFRICA_NORTH = "southafricanorth"


class AZZone(Enum):
    ZONE_1 = "1"
    ZONE_2 = "2"
    ZONE_3 = "3"
