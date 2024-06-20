"""
Upgrade Data Orchestrator utility:

usage: update_data_orchestrator.py [-h] -r RPM_URL -i DO_ADDRESS -c CLUSTER -u USERNAME -p PASSWORD
                                        -cid CUSTOMER_ID [-t JWT_SERVER] [-f FORCE]

CLI args for Data Orchestrator Update

mandatory arguments:

  -r RPM_URL, --rpm-url RPM_URL
                        Provide rpm file http path
  -i DO_ADDRESS, --do-address DO_ADDRESS
                        IPV4 Address of the Data Orchestrator
  -c CLUSTER, --cluster CLUSTER
                        Cluster where the Data Orchestrator is deployed: atlaspoc or atlaspoc2 or scint
  -u USERNAME, --username USERNAME
                        DSCC usename
  -p PASSWORD, --password PASSWORD
                        DSCC password
  -cid CUSTOMER_ID, --customer-id CUSTOMER_ID
                        Application customer ID for the user account

optional arguments:

  -t JWT_SERVER, --jwt-server JWT_SERVER
                        Input Playwright JWT server address
  -f FORCE, --force FORCE
                        To force the upgrade process
E.g. CLI command:
    python update_data_orchestrator.py
        -r "http://{URL}/HPE_Project_Atlas-1.0.1-2149.4.el7.noarch.rpm"
        -i "172.21.3.57"
        -c "atlaspoc2"
        -u "atlas_automation@hpe.com"
        -p "Atl@s2021"
        -cid "20469d0022fa11ec96df6a63b91175ec"
        -t "https://cxo-lin-136.cxo.storage.hpecorp.net:9000/gettoken"
        -f "False"
"""

import json
import urllib3
import argparse
import requests
from time import sleep


# Disable insecure warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_ope_vm_upgrade_timeout = 900


def get_dscc_token(jwt_server, cluster, username, password, customer_id):
    login_url = f"https://console-{cluster}-app.qa.cds.hpe.com/login"
    payload = json.dumps(
        {
            "LOGIN_URL": login_url,
            "LOGIN_USER": username,
            "LOGIN_PASSWORD": password,
            "CID": customer_id,
        }
    )
    headers = {"Content-Type": "application/json"}
    # Generating JWT token for the DSCC B&R portal
    response = requests.post(jwt_server, headers=headers, data=payload, verify=False)
    assert response.status_code == requests.codes.ok
    print(f"POST {jwt_server}:{response.status_code} ==>", response.content)
    try:
        token = response.json()["token"]
        return token
    except KeyError:
        print(f"Failed to retrieve the token from jwt server: {response.text}")
        exit(1)


def get_do_token(totp, do_address):
    url = f"https://{do_address}/rest/atlas/v2/login-sessions"
    headers = {"Content-Type": "application/json"}
    payload = json.dumps(
        {
            "auth": {
                "identity": {
                    "method": ["Totp"],
                    "totp": {"user": {"name": "admin", "passcode": totp}},
                }
            }
        }
    )
    # Generating login token for the Data Orchestrator using do RestAPIs specs.
    response = requests.post(url, headers=headers, data=payload, verify=False)
    assert response.status_code == requests.codes.ok
    print(f"POST {url}:{response.status_code} ==>", response.content)
    try:
        content = response.json()
        return content["token"]["id"]
    except KeyError:
        print(f"Failed to get the login token for data orchestrator: {response.text}")
        exit(1)


def get_do_totp(dscc_token, ope_uuid, cluster):
    url = f"https://{cluster}-app.qa.cds.hpe.com/api/v1/app-data-management-engines/{ope_uuid}/generate-totp"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {dscc_token}",
    }
    try:
        # Requesting One time password to login to DO
        response = requests.post(url, headers=headers, data={})
        assert response.status_code == requests.codes.created
        print(f"POST {url}:{response.status_code}", response.content)
        content = response.json()
        totp = content["totp"]
        expiry = int(content["expiresInSeconds"])
        # Regenerating TOTP when the generated TOTP is valid less than 10 seconds
        while expiry < 10:
            totp, expiry = get_do_totp(dscc_token, ope_uuid, cluster)
        return (totp, expiry)
    except KeyError:
        print(f"Failed to get the data orchestrator login token: {response.text}")
        exit(1)


def upload_rpm_to_do(do_address, rpm_url, filename, headers):
    url = f"https://{do_address}/rest/atlas/v1/software-packages"
    payload = json.dumps({"fileUrl": rpm_url, "name": filename})
    # Uploading the rpm file using the http share path
    response = requests.post(url, headers=headers, data=payload, verify=False)
    assert response.status_code == requests.codes.accepted
    print(f"POST {url}:{response.status_code} ==>", response.content)
    task_id = response.json()["task"].split("/")[-1]
    return task_id


def initiate_do_upgrade(software_package_id, do_address, headers, force):
    url = f"https://{do_address}/rest/atlas/v1/appliance/upgrade"
    payload = json.dumps(
        {
            "softwarePackageId": software_package_id,
            "autoRevertOnUpgradeFailure": False,
            "takeVmSnapshotBeforeUpgrade": False,
            "force": force,
        }
    )
    # Initiating the upgrade process with the software package id aquired after uploading the rpm file
    response = requests.put(url, headers=headers, data=payload, verify=False)
    assert response.status_code == requests.codes.accepted, response.text
    print(f"PUT {url}:{response.status_code} ==>", response.content)
    try:
        task_id = response.json()["task"].split("/")[-1]
        return task_id
    except Exception:
        print(f"Failed to initiate the upgrade task. {response.text}")
        exit(1)


def wait_for_task(task_id, do_address, headers, return_software_package_id=False):
    url = f"https://{do_address}/rest/atlas/v1/tasks/{task_id}"
    # Getting detailed task information
    response = requests.get(url, headers=headers, verify=False)
    assert response.status_code == requests.codes.ok
    print(f"GET {url}:{response.status_code} ==>", response.content)
    content = response.json()["task"]
    timeout = _ope_vm_upgrade_timeout
    # Polling for the task completion and timeout set to 15 minutes.
    while content["completedPercentage"] < 100 and timeout > 0:
        timeout -= 30
        print(f"{content['name']} - {content['completedPercentage']}% Completed")
        try:
            response = requests.get(url, headers=headers, verify=False)
            print(f"Task Status [{response.status_code}] ==>", response.content)
            if response.status_code != requests.codes.ok:
                # Data Orchestrator goes for a reboot during the upgrade process. 500 or 502 is expected.
                print("Waiting for Data orchestrator to respond...")
                sleep(60)
                continue
            content = response.json()["task"]
            sleep(30)
        except ConnectionRefusedError:
            sleep(60)
            continue
    if timeout < 1:
        raise TimeoutError(f"Task {task_id} failed to complete under 15 minutes")
    if content["status"] == "Ok":
        if return_software_package_id:
            return (True, content["associatedResource"][-1]["id"]) if content["state"] == "Completed" else (False, None)
        else:
            return True if content["state"] == "Completed" and content["status"] == "Ok" else False
    elif content["status"] == "Error":
        print(f'ERROR: {content["error"]["details"]}')
        exit(1)
    else:
        print(f'{content["status"]}: {response.text}')
        exit(1)


def get_do_uuid(do_address, dscc_token, cluster):
    do_uuid: str = ""
    url = f"https://{cluster}-app.qa.cds.hpe.com/api/v1/app-data-management-engines"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {dscc_token}",
    }
    response = requests.get(url, headers=headers, verify=False)
    assert response.status_code == requests.codes.ok, response.text
    try:
        items = response.json()
        for item in items["items"]:
            for nic in item["interfaces"]["network"]["nic"]:
                if nic["networkAddress"] == do_address:
                    do_uuid = item["id"]
                    break
            if do_uuid:
                break
        else:
            print(
                f'Data orchestrator with IP "{do_address}" not found in "{cluster}" cluster. +'
                "\nPlease check the IP and cluster details provided!!!"
            )
            exit(1)
        return do_uuid
    except Exception as e:
        print("ERROR: Failed to get the data orchestrator UUID:", e)
        exit(1)


def main(rpm_url, do_address, cluster, username, password, customer_id, jwt_server, force):
    filename = rpm_url.split("/")[-1]
    dscc_token = get_dscc_token(jwt_server, cluster, username, password, customer_id)
    do_uuid = get_do_uuid(do_address, dscc_token, cluster)
    totp = get_do_totp(dscc_token, do_uuid, cluster)[0]
    do_token = get_do_token(totp, do_address)
    headers = {"Content-Type": "application/json", "X-Auth-Token": do_token}
    task_id = upload_rpm_to_do(do_address, rpm_url, filename, headers)
    success, software_package_id = wait_for_task(task_id, do_address, headers, return_software_package_id=True)
    if success:
        task_id = initiate_do_upgrade(software_package_id, do_address, headers, json.loads(force.lower()))
        success = wait_for_task(task_id, do_address, headers)
        if success:
            print(f"Successfully upgraded Data Orchestrator {do_address} using the rpm file {filename}. Cheers!!")
        else:
            print("Data Orchestrator upgrade failed due to an exception!!")
            exit(1)


if __name__ == "__main__":
    # Argument declarations
    parser = argparse.ArgumentParser(description="CLI args for Data Orchestrator Update")
    parser.add_argument("-r", "--rpm-url", required=True, help="Provide rpm file http path")
    parser.add_argument(
        "-i",
        "--do-address",
        required=True,
        help="IPV4 Address of the Data Orchestrator",
    )
    parser.add_argument(
        "-c",
        "--cluster",
        required=True,
        help="Cluster where the Data Orchestrator is deployed: atlaspoc or atlaspoc2 or scint",
    )
    parser.add_argument("-u", "--username", required=True, help="DSCC usename")
    parser.add_argument("-p", "--password", required=True, help="DSCC password")
    parser.add_argument(
        "-cid",
        "--customer-id",
        required=True,
        help="Application customer ID for the user account",
    )
    parser.add_argument(
        "-t",
        "--jwt-server",
        required=False,
        default="http://atlast-qa-node-001.vlab.nimblestorage.com/gettoken",
        help="Input Playwright JWT server address",
    )
    parser.add_argument(
        "-f",
        "--force",
        required=False,
        default=False,
        help="To force the upgrade process",
    )

    args = parser.parse_args()
    main(**args.__dict__)
