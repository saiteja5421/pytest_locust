from enum import Enum


class ValidationStatus(Enum):
    passed = "PASSED"
    failed = "FAILED"
    unvalidated = "UNVALIDATED"
