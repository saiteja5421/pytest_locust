from enum import Enum


# K8s cluster registration status values
class CSPK8sClusterRegistrationStatus(Enum):
    REGISTERED = "REGISTERED"
    NOT_REGISTERED = "NOT_REGISTERED"
    UNREGISTERED = "UNREGISTERED"
