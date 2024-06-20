from enum import Enum
from itertools import chain

from lib.common.enums.ec2_instance_details import InstanceDetails
from lib.common.enums.vm_details import VmDetails

CloudInstanceDetails = Enum("CloudInstanceDetails", [(i.name, i.value) for i in chain(InstanceDetails, VmDetails)])
