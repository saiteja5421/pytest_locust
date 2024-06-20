from enum import Enum


class CspType(Enum):
    # Field used in csp-machine-instances and csp-accounts to differentiate AWS, Azure and MS365
    AWS = "AWS"
    AZURE = "AZURE"
    MS365 = "MS365"
