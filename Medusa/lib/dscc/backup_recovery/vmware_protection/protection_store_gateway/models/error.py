from dataclasses import dataclass

"""
Model related to TC30 - unable to pass parameter as string
due to comma in error message
"""


@dataclass(frozen=True)
class Error:
    message: str
