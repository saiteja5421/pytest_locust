from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.common.enums.vm_details import VmInstanceDetails

allowed_instances_aws: list[CloudInstanceDetails] = [
    CloudInstanceDetails.R6I_LARGE,
    CloudInstanceDetails.M6I_XLARGE,
    CloudInstanceDetails.R6I_XLARGE,
    CloudInstanceDetails.C6I_2XLARGE,
    CloudInstanceDetails.R6I_2XLARGE,
    CloudInstanceDetails.C6I_4XLARGE,
    CloudInstanceDetails.M6I_4XLARGE,
    CloudInstanceDetails.R6I_4XLARGE,
    CloudInstanceDetails.C6I_8XLARGE,
    CloudInstanceDetails.M6I_8XLARGE,
    CloudInstanceDetails.R6I_8XLARGE,
    CloudInstanceDetails.C6I_12XLARGE,
    CloudInstanceDetails.M6I_12XLARGE,
    CloudInstanceDetails.R6I_12XLARGE,
    CloudInstanceDetails.C6I_16XLARGE,
    CloudInstanceDetails.M6I_16XLARGE,
    CloudInstanceDetails.R6I_16XLARGE,
    CloudInstanceDetails.C6I_24XLARGE,
    CloudInstanceDetails.M6I_24XLARGE,
    CloudInstanceDetails.R6I_24XLARGE,
    CloudInstanceDetails.C6I_32XLARGE,
    CloudInstanceDetails.M6I_32XLARGE,
    CloudInstanceDetails.R6I_32XLARGE,
]

allowed_instances_azure: list[CloudInstanceDetails] = [
    cld for cld in CloudInstanceDetails if isinstance(cld.value, VmInstanceDetails)
]

allowed_instances = allowed_instances_aws + allowed_instances_azure


def get_instance_details_by_name(name: str) -> CloudInstanceDetails:
    return next(filter(lambda x: name in x.value.instance_type, allowed_instances))


def is_allowed(wanted: CloudInstanceDetails, given: CloudInstanceDetails, strict_mode=False) -> bool:
    if not strict_mode:
        return 0 <= allowed_instances.index(given) - allowed_instances.index(wanted) <= 5
    else:
        return wanted == given
