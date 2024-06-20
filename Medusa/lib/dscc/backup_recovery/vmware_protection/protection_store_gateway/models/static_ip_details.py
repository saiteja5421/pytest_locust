from dataclasses import dataclass


@dataclass(frozen=True)
class StaticIPDetails:
    """
    Static IP Details dataclass with network ip, network mask and network gateway information for TC30
    """

    network_ip: str
    network_mask: str
    network_gateway: str
