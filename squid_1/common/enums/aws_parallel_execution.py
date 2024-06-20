from enum import Enum


class aws_accounts(Enum):
    first = 1  # assigned to context.aws_one
    second = 2  # assigned to context.aws_one
    random = 3  # assigned to context.aws_one
    both = 4  # assigned to context.aws_one and context.aws_two


class regions_count(Enum):
    one = 1
    two = 2
    three = 3
