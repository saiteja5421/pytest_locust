"""
Download and deploy Data Orchestrator OVA

E.g. CLI command:
    python deploy_ope_vm.py
        -oU "http://{URL}/HPE_Project_Atlas-1.0.0-2147.2-vcenter.ova"
        -oH "api-do-001"
        -vcenter "vcsa70-123.lab.nimblestorage.com"
        -u "administrator@vsphere.local"
        -p "<password>"
        -ds "ca29-oct12vc123-ds2"
        -dc "Atlas Cluster 4"
"""

import os
import atexit
import urllib3
import argparse
import requests
import subprocess
from time import time
from urllib.parse import quote
from waiting import wait, TimeoutExpired
from pyVim.connect import vim, SmartConnect, Disconnect

# Disable insecure warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


_ope_vm_deployment_timeout = 900

# Unset environmental proxy
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["no_proxy"] = ""


def download_ova(url):
    filename = url.split("/")[-1]
    command = f"wget -q --no-check-certificate {url} -O {filename}"
    response = subprocess.run(command.split())
    if response.returncode != 0:
        raise Exception(f"Failed to download OVA bundle. Command: '{command}'")
    return f"{os.getcwd()}/{filename}"


def get_ope_vm_ip_address(hostname, username, password, ope_vm_name):
    ope = None
    si = SmartConnect(
        host=hostname,
        user=username,
        pwd=password,
        port=int("443"),
        disableSslCertValidation=True,
    )
    atexit.register(Disconnect, si)
    content = si.RetrieveContent()
    vm = content.viewManager
    for c in vm.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True).view:
        if c.name == ope_vm_name:
            ope = c
            break
    if not ope:
        raise Exception(f"Failed to find deployed OPE VM '{ope_vm_name}'")

    print("Waiting for OPE guest OS IP address..")
    if wait(lambda: ope.guest.ipAddress is not None, timeout_seconds=900, sleep_seconds=5):
        return ope.guest.ipAddress


def deploy_ova(
    vcenter_hostname,
    vcenter_username,
    vcenter_password,
    datacenter,
    datastore,
    cluster,
    ope_hostname,
    ova_path,
):
    """
    Deploy OPE OVA into vCenter and return IPv4 address of it

    OVF Convertion: ovftool ./HPE_Project_Atlas-1.0.0-2147.3-vcenter.ova ./HPE_Project_Atlas-1.0.0-2147.3-vcenter.ovf
    Edit OVF - Remove Product, Vendor, VendorUrl
               sed -i  "/\bProduct\b\|\bVendor\b\|\bVendorUrl\b/d" HPE_Project_Atlas-1.0.0-2147.3-vcenter.ovf
    OVA Deploy: ovftool --name=raja-atlas-deploy --prop:"sys_:_hostname"="api-raja-do"  --powerOn  --noSSLVerify
                        --X:logToConsole -ds=ca29-oct12vc123-ds2 --acceptAllEulas  --noSSLVerify
                        --net:"Network - 1 (Management and Data)"="VM Network"
                        "./HPE_Project_Atlas-1.0.0-2147.3-vcenter.ovf"
                        "vi://{user}:{passwd}@{vcenter}/Datacenter/host/{cluster}/"
    """

    folder_path = os.path.dirname(ova_path)
    ova_file_name = os.path.basename(ova_path)
    (name_only, _) = os.path.splitext(ova_file_name)
    ovf_path = os.path.join(folder_path, name_only + ".ovf")

    # Extract OVA artifact
    print("Extracting OVA bundle")
    command = f"ovftool {ova_path} {ovf_path}"
    response = subprocess.run(command.split())
    if response.returncode != 0:
        raise Exception(f"Failed to extract OVA file. Command: {command}")

    # Remove unsupported elements by ovftool - 'Product, Vendor and VendorUrl'
    print("Removing unsupported elements from OVF")
    command = f"sed -i /\\bProduct\\b\|\\bVendor\\b\|\\bVendorUrl\\b/d {ovf_path}"
    response = subprocess.run(command.split())
    if response.returncode != 0:
        raise Exception(f"Failed to remove unsupported elements. Command: {command}")

    # Deploy OVF
    print("Deploying OVF")
    _vcenter_username = quote(vcenter_username)
    _vcenter_password = quote(vcenter_password)
    _vm_name = f"{name_only}-{int(time())}"
    command = [
        "ovftool",
        "--skipManifestCheck",
        "--noSSLVerify",
        "--acceptAllEulas",
        "--powerOn",
        "--X:logToConsole",
        "--net:Network - 1 (Management and Data)=VM Network",
        f"--prop:sys_:_hostname={ope_hostname}",
        f"-ds={datastore}",
        f"--name={_vm_name}",
        f"{ovf_path}",
        f"vi://{_vcenter_username}:{_vcenter_password}@{vcenter_hostname}/{datacenter}/host/{cluster}/",
    ]
    response = subprocess.run(command)
    if response.returncode != 0:
        raise Exception(f"Failed to deploy OVF. Command: {command}")
    print(f"OVF deployed to vcenter {vcenter_hostname}")

    # Remove extracted OVA files
    command = ["rm", "-f", f"{name_only}*"]
    res = subprocess.run(command)
    if res.returncode != 0:
        print("Failed to remove unnecessary files")

    print("Get OPE IP Address")
    ip = get_ope_vm_ip_address(vcenter_hostname, vcenter_username, vcenter_password, ope_vm_name=_vm_name)
    print(f"OPE IP Address: {ip}")

    return ip


def _wait_for_task(url, headers, timeout):
    def _return_condition():
        res = requests.get(url=url, headers=headers, verify=False)
        assert res.status_code == requests.codes.ok, f"Response: {res.text}"
        return res.json()["task"]["state"] == "Completed" and res.json()["task"]["status"] == "Ok"

    try:
        return wait(_return_condition, timeout_seconds=timeout, sleep_seconds=5)
    except TimeoutExpired:
        raise Exception("Failed to get task state as 'Completed'")


def _wait_for_https_service(ope_ip):
    def _check_get_request():
        print("Waiting for OPE HTTPS service..")
        try:
            res = requests.get(url=f"https://{ope_ip}/rest/atlas/v1/appliance", verify=False)
            assert res.status_code == requests.codes.unauthorized, f"Response: {res.text}"
            print("OPE REST API service is responding")
            return True
        except Exception as e:
            print(f"Service starting; Exception msg: {e}")
            return False

    wait(
        _check_get_request,
        timeout_seconds=_ope_vm_deployment_timeout,
        sleep_seconds=5,
    )


def first_run_wizard(ope_ip):
    # Get login token
    body = {
        "auth": {
            "identity": {
                "method": ["Password"],
                "password": {"user": {"name": "admin", "password": "admin"}},
            }
        }
    }
    headers = {"Content-Type": "application/json"}
    res = requests.post(
        url=f"https://{ope_ip}/rest/atlas/v2/login-sessions",
        json=body,
        verify=False,
        headers=headers,
    )
    assert res.status_code == requests.codes.ok, f"Response: {res.text}"

    # Update headers to have X-Auth-Token
    headers["X-Auth-Token"] = res.json()["token"]["id"]
    print(f"OPE login token: {res.json()['token']['id']}")

    # Get appliance detials
    res = requests.get(url=f"https://{ope_ip}/rest/atlas/v1/appliance", verify=False, headers=headers)
    assert res.status_code == requests.codes.ok, f"Response: {res.text}"

    # Update proxy
    payload = {
        "network": {
            "hostname": res.json()["interfaces"]["network"]["hostname"],
            "nameServers": res.json()["interfaces"]["network"]["nameServers"],
            "proxy": {
                "networkAddress": "http://web-proxy.corp.hpecorp.net",
                "port": 8080,
            },
        }
    }
    res = requests.patch(
        url=f"https://{ope_ip}/rest/atlas/v1/appliance",
        json=payload,
        headers=headers,
        verify=False,
    )
    assert res.status_code == requests.codes.accepted, f"Response: {res.text}"
    task_url = f"https://{ope_ip}{res.json()['task']}"
    print(f"Updating network proxy - Task: {task_url}")
    assert _wait_for_task(task_url, headers, timeout=_ope_vm_deployment_timeout)
    print("Updated network proxy")

    # Update completedSteps
    payload = {
        "firstRunWizard": {
            "completedSteps": 1,
            "totalSteps": 3,
            "status": "Ok",
            "state": "Running",
        }
    }
    res = requests.patch(
        url=f"https://{ope_ip}/rest/atlas/v1/appliance/first-run-wizard",
        json=payload,
        headers=headers,
        verify=False,
    )
    assert res.status_code == requests.codes.ok, f"Response: {res.text}"
    print("Updated completedSteps: 1")

    # Update datetime
    payload = {
        "dateTime": {"methodDateTimeSet": "Ntp", "timezone": "America/Denver"},
        "ntp": {
            "ntpServers": [
                {"networkAddress": "10.157.24.95"},
                {"networkAddress": "10.157.24.96"},
            ]
        },
    }
    res = requests.patch(
        url=f"https://{ope_ip}/rest/atlas/v1/appliance",
        json=payload,
        headers=headers,
        verify=False,
    )
    assert res.status_code == requests.codes.accepted, f"Response: {res.text}"
    task_url = f"https://{ope_ip}{res.json()['task']}"
    print(f"Updating dateTime - Task: {task_url}")
    assert _wait_for_task(task_url, headers, timeout=_ope_vm_deployment_timeout)
    print("Updated dateTime")

    # Update completedSteps
    payload = {
        "firstRunWizard": {
            "completedSteps": 2,
            "totalSteps": 3,
            "status": "Ok",
            "state": "Running",
        }
    }
    res = requests.patch(
        url=f"https://{ope_ip}/rest/atlas/v1/appliance/first-run-wizard",
        json=payload,
        headers=headers,
        verify=False,
    )
    assert res.status_code == requests.codes.ok, f"Response: {res.text}"
    print("Updated completedSteps: 2")

    # PUT dscc
    res = requests.put(
        url=f"https://{ope_ip}/rest/atlas/v1/appliance/dscc",
        headers=headers,
        verify=False,
    )
    assert res.status_code == requests.codes.ok, f"Response: {res.text}"
    print(f"SID: {res.json()['sid']}")

    return res.json()["sid"]


def main(
    ope_url,
    ope_hostname,
    vcenter_hostname,
    vcenter_username,
    vcenter_password,
    datastore,
    cluster,
    datacenter="Datacenter",
):
    print(f"Downloading file {ope_url}")
    ova_path = download_ova(ope_url)
    print(f"OVA file downloaded to {ova_path}")

    print(f"OVA Deployment started in {vcenter_hostname}")
    ope_ip = deploy_ova(
        vcenter_hostname,
        vcenter_username,
        vcenter_password,
        datacenter,
        datastore,
        cluster,
        ope_hostname,
        ova_path,
    )

    _wait_for_https_service(ope_ip)

    sid = first_run_wizard(ope_ip)
    print("=" * 80)
    print(f"OPE VM Successfully deployed. Use SID '{sid}' to activate")
    print("=" * 80)
    return sid


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CLI args for Deploy OPE OVA")

    parser.add_argument("-oU", "--ope-url", required=True, help="OPE OVA download URL")
    parser.add_argument("-oH", "--ope-hostname", required=True, help="Hostname of OPE")
    parser.add_argument("-vcenter", "--vcenter-hostname", required=True, help="vCenter IP or hostname")
    parser.add_argument("-u", "--vcenter-username", required=True, help="Vcenter username")
    parser.add_argument("-p", "--vcenter-password", required=True, help="Vcenter password")
    parser.add_argument("-ds", "--datastore", required=True, help="Datastore name in vCenter")
    parser.add_argument("-dc", "--cluster", required=True, help="Cluster name in vCenter")
    parser.add_argument(
        "--datacenter",
        required=False,
        default="Datacenter",
        help="Datacenter name in vCenter. default: Datacenter",
    )

    args = parser.parse_args()

    main(**args.__dict__)
