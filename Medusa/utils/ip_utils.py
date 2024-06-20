import logging
import subprocess
import platform

from lib.dscc.backup_recovery.vmware_protection.common.custom_error_helper import UnusedIPNotFoundError

logger = logging.getLogger()


def ping(ip, log_stdout=False):
    """
    Runs ping command and returns True if it gets ICMP response else False

    ip str: IP address
    """
    os = platform.system()
    ping_command = f"ping {ip} -n 2 -w 1000".split() if platform.system() == "Windows" else f"ping {ip} -c2 -w2".split()
    ping_output = subprocess.run(ping_command, stdout=subprocess.PIPE, shell=True if os == "Windows" else False)
    if log_stdout:
        print(f"{ping_output.stdout.decode()}")
    return ping_output.returncode == 0


def find_unused_ip_from_range(ip_range, exclude_ip_list=None):
    """
    Performs ICMP check and returns unused one from the given range otherwise returns None.

    ip_range str: IP range. E.g. 172.21.4.51 - 56
    """
    if "-" not in ip_range:
        return None if ping(ip_range) else ip_range

    if exclude_ip_list is None:
        exclude_ip_list = []

    start_ip, end = ip_range.replace(" ", "").split("-")
    network, start = (".".join(start_ip.split(".")[0:3]), start_ip.split(".")[-1])
    for host in range(int(start), int(end) + 1):
        ip = f"{network}.{host}"

        if ip in exclude_ip_list:
            continue

        if not ping(ip):
            return ip

    return None


def get_unused_ip_for_network_interface(context, ip_range):
    used_ips = []
    response = context.catalyst_gateway.get_catalyst_gateways().json()
    psgws = response["items"]
    for psg in psgws:
        nics = psg["network"]["nics"]
        del nics[0]
        for nic in nics:
            used_ips.append(nic["networkAddress"])

    if "-" not in ip_range:
        logger.warning(
            "There is only one IP provided in context for network interface. Could possibly fail if IP is in use."
        )
        return ip_range
    start_ip, end = ip_range.replace(" ", "").split("-")
    network, start = (".".join(start_ip.split(".")[0:3]), start_ip.split(".")[-1])
    for host in range(int(start), int(end) + 1):
        ip = f"{network}.{host}"
        if ip in used_ips:
            continue
        else:
            return ip
    logger.debug(f"All IPs from range: {ip_range} are in use.")
    raise UnusedIPNotFoundError


if __name__ == "__main__":
    print(ping("172.21.4.51", log_stdout=True))
    print(ping("localhost", log_stdout=True))
    print(ping("255.255.0.0", log_stdout=True))
    print(find_unused_ip_from_range("172.21.4.51 - 56"))
    print(find_unused_ip_from_range("172.21.4.51 - 56", exclude_ip_list=["172.21.4.51"]))
    print(find_unused_ip_from_range("172.21.4.51"))
