from enum import Enum


class AZAccounts(Enum):
    FIRST = 1  # assigned to context.azure_one
    SECOND = 2  # assigned to context.azure_two
    RANDOM = 3  # assigned to context.azure_one or context.azure_two
    BOTH = 4  # assigned to context.azure_one and context.azure_two


class AZRegionCount(Enum):
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
