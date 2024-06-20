"""
Register Array utility:
usage: register_array.py [-h] -a ARRAY_NAME -ac ACCOUNT_NAME -u USERNAME -p PASSWORD -sk SUBSCRIPTION_KEY -vc VCSA1,VCSA2,VCSA3 -ds DS1,DS2,DS3

mandatory arguments:
  -a    ARRAY_NAME             --array_name           Array or varray name
  -ac   ACCOUNT_NAME           --account_name         Company Account name example: HPE-Catalyst
  -u    USERNAME               --username             DSCC username
  -p    PASSWORD               --password             User DSCC password
  -vc   VCSA1,VCSA2,VCSA3      --vcenters             vCenter list that should be added to array. Comma , seperated
  -ds   DS1,DS2,DS3            --datastores            Add datastore (name:value:unit) list (comma , separator ) that should be created in the array
                                                      ex. ds-psgw:2:TiB,ds-vms:20:GiB,ds-test:7777:MiB
                                                      Datastores will be created on every vcenter
                                                      Datastore name validation: use only dash "-" ex. datastore-psgw-only                                                      

optional arguments:
  -sk   SUBSCRIPTION_KEY       --subscription-key     Array subscription key. If empty, will be generated

E.g. CLI command:
    python register_array.py
        -a "scj-array7777"
        -ac "HPE-Catalyst"
        -u "atlas_automation@hpe.com"
        -p "<password>"
        -sk "XUDHPBE6CYDO9XLZZT08"
        -vc "vcsa90-027.vlab.nimblestorage.com,vcsa90-127.vlab.nimblestorage.com,vcsa90-327.vlab.nimblestorage.com"
        -ds "ds-psgw:2:TiB,ds-vms:20:GiB,ds-test:7777:MiB"
"""

import json
import urllib3
import argparse
import subprocess
import re
import sys
import time
import os

from tests.steps.vm_protection.vmware_steps import VMwareSteps

lop = "/auto/share/bin/lop"
subscription_path = "/auto/share/spulumati"
subscription_file = "pavo_create_device.py"
subscription_script = f"{subscription_path}/{subscription_file}"
sys.path.insert(0, subscription_path)
cwd = os.getcwd()
sys.path.append(f"{cwd}/Atlas-catayst-gw-e2e-api/e2e-tests")
sys.path.append(f"{cwd}/e2e-tests")
from pavo_create_device import DeviceManagement
from lib.platform.storage_array.array_api import ArrayApi

# Disable insecure warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Management(DeviceManagement):
    def __init__(self, host, username, password, pcid=False):
        super(DeviceManagement, self).__init__(host, username, password, pcid)

    def get_pcid(self, account_name):
        pcid = ""
        data = {
            "id_token": self.token_json["id_token"],
        }
        response = self.post("/authn/v1/session", json=data)
        for account in response["accounts"]:
            if account["company_name"] == account_name:
                pcid = account["platform_customer_id"]
        return pcid

    def register_array(self, serial_number, subscription_key):
        url = "https://pavo-user-api.common.cloud.hpe.com/ui-doorway/ui/v1/devices"
        data = json.dumps(
            {
                "devices": [
                    {
                        "serial_number": serial_number,
                        "entitlement_id": subscription_key,
                        "app_category": "STORAGE",
                    }
                ]
            }
        )
        try:
            response = self.post(url, data=data)
        except Exception as e:
            raise Exception("FAILED - register array", e.response.text)

        assert response == "OK", response.text
        print(f"SUCCESS - Array serial {serial_number} registrated")


def get_array_controller(array_name):
    output = subprocess.Popen(
        f"{lop} con {array_name}",
        shell=True,
        universal_newlines=True,
        stdout=subprocess.PIPE,
    )
    controller = ""
    for line in output.stdout:
        if "Controller" in line:
            controller = line.split("Controller: ", 1)[1][:-1]

            con = subprocess.Popen(
                [lop, "con", controller],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=0,
            )
            con.stdin.write("root\n")
            con.stdin.flush()
            time.sleep(10)
            con.stdin.write("admin\n")
            con.stdin.flush()
            time.sleep(5)
            con.stdin.write("version\n")
            time.sleep(2)
            con.stdin.close()
            for line in con.stdout:
                if "Not on active controller" in line:
                    print(f"Not on active controller {controller}")
                    break
            else:
                break

    assert controller, "Array controller not found."
    print(f"Controller found: {controller}")
    return controller


def get_array_details(array_name, array_controller):
    con = subprocess.Popen(
        [lop, "con", array_controller],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=0,
    )
    con.stdin.write("array --list\n")
    time.sleep(15)
    con.stdin.flush()
    con.stdin.close()
    status = ""
    for line in con.stdout:
        if array_name in line and "reachable" in line:
            name, serial, model, version, status = line.split()
            break

    assert status == "reachable", f"Array {array_name} serial and model not found"
    if name == serial:
        model = "VM-LEGACY"
        print(f"VArray: model changed to {model}")
    print(f"Array details - name: {name}, serial:{serial}, model:{model}, version:{version}, status:{status}")
    return name, serial, model, version, status


def enable_ccd(array_controller):
    con = subprocess.Popen(
        [lop, "con", array_controller],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=0,
    )
    try:
        # CCD can be enabled on Gen-5 arrays by running below command
        con.stdin.write("group --edit --cloud_enabled yes\n")
        con.stdin.flush()
        con.stdin.write("group --info | grep cloud\n")
        con.stdin.flush()
        for line in con.stdout:
            if "cloud enabled: Yes" in line:
                print("CCD cloud_enabled flag updated with group cmd")
                break
    except Exception as e:
        print(f"Got exception while enabling ccc cloud flag with group cmd: {e}")

    try:
        # Command to manually set the Software subscription flag
        con.stdin.write(
            "psql sodb -U dbuser -c \"update scalars set current_value=true where name = 'software_subscription_enabled';\"\n"
        )
        con.stdin.flush()
        for line in con.stdout:
            if "UPDATE 1" in line:
                print("CCD cloud_enabled flag updated with psql cmd")
                break
    except Exception as e:
        print(f"Got exception while enabling ccd cloud flag with psql cmd: {e}")
    con.stdin.close()


def enable_iscsi_protocol(array_controller):
    con = subprocess.Popen(
        [lop, "con", array_controller],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=0,
    )
    try:
        con.stdin.write("nsgroup --edit --iscsi_enabled yes\n")
        con.stdin.flush()
        con.stdin.write("nsgroup --info |grep 'iSCSI enabled'\n")
        con.stdin.flush()
        for line in con.stdout:
            if "iSCSI enabled: Yes" in line:
                print("ISCSI enabled")
                break
    except Exception as e:
        print(f"Got exception while enabling iscsi: {e}")
    con.stdin.close()


def get_subscriton_key(serial, model, unassign=False):
    unassign_flag = ""
    if unassign:
        unassign_flag = " -u"

    con = subprocess.Popen(
        f"python3 {subscription_script} -n {serial} -p {model}{unassign_flag}",
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=0,
    )
    sub_key = ""
    pattern = re.compile(r"([A-Z0-9]{20})")
    for line in con.stdout:
        match = pattern.findall(line)
        if match:
            sub_key = match[0]
            print(f"Subscription key generated successful. {sub_key}")
    return sub_key


def parse_datastores(datastores):
    ds_list_parsed = []
    ds_list = datastores.split(",")
    for ds in ds_list:
        ds_splited = ds.split(":")
        if ds_splited[2] == "MiB":
            size = int(ds_splited[1]) * 1024**2
        elif ds_splited[2] == "GiB":
            size = int(ds_splited[1]) * 1024**3
        elif ds_splited[2] == "TiB":
            size = int(ds_splited[1]) * 1024**4
        ds_parsed = {"name": ds_splited[0], "size": size}
        ds_list_parsed.append(ds_parsed)
    assert len(ds_list_parsed) > 0, "No datastores parsed"
    return ds_list_parsed


def create_datastores(vcenters, array_name, model, datastores):
    datastores_list = parse_datastores(datastores)
    array_domain = "lab.nimblestorage.com"
    vcenter_username = "Administrator@VSPHERE.LOCAL"
    # read this password from environment variables currently this file we are not using so added empty string.
    vcenter_password = ""
    dedupe = True
    if model == "VM-LEGACY":
        array_domain = f"v{array_domain}"
        dedupe = False
    vcenters = vcenters.split(",")
    array_api = ArrayApi(
        array_address=f"{array_name}.{array_domain}",
        username=vcenter_username,
        password=vcenter_password,
    )
    array_api.array_integrate_vcenters(vcenters)
    print(f"Vcenters registrated {vcenters}")
    for vcenter in vcenters:
        vcs_name_short = vcenter.split(".")[0]
        array_api.set_vcenter(vcenter)
        hosts = array_api.get_datacenter_hosts()
        pool_id = array_api.get_datacenter_pool()
        protocol = array_api.get_array_protocol()
        for ds in datastores_list:
            vcenter_control = VMwareSteps(vcenter, username=vcenter_username, password=vcenter_password)
            task_id = array_api.create_datastore(
                f"{ds['name']}-{vcs_name_short}",
                ds["size"],
                dedupe,
                hosts,
                pool_id,
                protocol,
            )
            status = vcenter_control.wait_for_task(task_id)
            if status[0]:
                print(f"Datastore created {ds['name']} on {vcenter}")
            else:
                print(f"FAILED - Datastore create - {ds['name']} on {vcenter}. {status[1]}")


def main(array_name, account_name, username, password, subscription_key, vcenters, datastores):
    ctr = get_array_controller(array_name)
    _, serial, model, _, _ = get_array_details(array_name, ctr)
    enable_ccd(ctr)
    enable_iscsi_protocol(ctr)
    if not subscription_key:
        subscription_key = get_subscriton_key(serial, model, unassign=True)
    if not subscription_key:
        subscription_key = get_subscriton_key(serial, model)
    pavo_u = Management(host="pavo.common.cloud.hpe.com", username=username, password=password)
    pavo_u.login()
    pcid = pavo_u.get_pcid(account_name)
    pavo_u.load_account(pcid)
    pavo_u.register_array(serial, subscription_key)
    create_datastores(vcenters, array_name, model, datastores)


if __name__ == "__main__":
    # Argument declarations
    parser = argparse.ArgumentParser(description="CLI args for array onboarding")
    parser.add_argument("-a", "--array_name", required=True, help="Array name")
    parser.add_argument(
        "-ac",
        "--account_name",
        required=True,
        help="Company Account name example: HPE-Catalyst",
    )
    parser.add_argument("-u", "--username", required=True, help="DSCC usename")
    parser.add_argument("-p", "--password", required=True, help="DSCC password")
    parser.add_argument(
        "-sk",
        "--subscription-key",
        required=False,
        help="[Optional] Array subscription key. Leave empty to generate",
    )
    parser.add_argument(
        "-vc",
        "--vcenters",
        required=True,
        help="vCenter list that should be added to array. Comma , seperated",
    )
    parser.add_argument(
        "-ds",
        "--datastores",
        required=True,
        help="Add datastore (name:value:unit) list (comma , separator ) that should be created in the array",
    )
    args = parser.parse_args()
    main(**args.__dict__)
