from aenum import Enum, NoAlias


class NetworkInterfaceType(Enum, settings=NoAlias):
    mgmt_only = "MGMT"
    mgmt_and_data = "MGMT"
    data1 = "DATA"
    data2 = "DATA"
