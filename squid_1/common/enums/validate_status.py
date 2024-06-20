from enum import Enum


class CSPK8sValidateStatus(Enum):
    unvalidated = "UNVALIDATED"
    passed = "PASSED"
    failed = "FAILED"
    not_allowed = "VALIDATION_NOT_ALLOWED"
