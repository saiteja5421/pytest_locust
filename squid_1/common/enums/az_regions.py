"""
A total of 80 regions are supported:
`az account list-locations -o table`

Add more as needed
"""

from enum import Enum


class AZRegion(Enum):
    EAST_US = "eastus"
    EAST_US_2 = "eastus2"
    WEST_US = "westus"
    WEST_US_2 = "westus2"
    WEST_US_3 = "westus3"
    CENTRAL_US = "centralus"
    NORTH_EUROPE = "northeurope"
    SWEDEN_CENTRAL = "swedencentral"
    UK_SOUTH = "uksouth"
    POLAND_CENTRAL = "polandcentral"
    SWITZERLAND_NORTH = "switzerlandnorth"
    CENTRAL_INDIA = "centralindia"
    ASIA_PACIFIC = "asiapacific"
    AUSTRALIA = "australia"
    EUROPE = "europe"
    SOUTH_AFRICA = "southafrica"


class AZZone(Enum):
    ZONE_1 = "1"
    ZONE_2 = "2"
    ZONE_3 = "3"
