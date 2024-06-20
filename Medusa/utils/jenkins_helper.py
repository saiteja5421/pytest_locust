import os
import requests


JENKINS_USER = "admin"
JENKINS_API_TOKEN = "11f8933612b0fa57d97e49f25970aacc45"


def update_build_description(description):
    """Updates Jenkins given build"""
    JENKINS_HOST = os.environ.get("JENKINS_URL")
    BUILD_URL = os.environ.get("BUILD_URL")
    auth = (JENKINS_USER, JENKINS_API_TOKEN)
    job_url = f"{BUILD_URL}/configSubmit"

    # Get Crumb token
    crumb_url = f'{JENKINS_HOST}crumbIssuer/api/xml?xpath=concat(//crumbRequestField,":",//crumb)'
    response = requests.get(crumb_url, auth=auth)
    if response.status_code != requests.codes.OK:
        print(f"Failed to get Crumb token. Got {response.status_code} and response is {response.text}")
        return False
    crumb_token = response.text.split(":")[1]

    # Update current build description
    headers = {"Jenkins-Crumb": crumb_token, "Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "displayName": "",
        "description": description,
        "core:apply": "",
        "json": f'{{"displayName":"", "description":"{description}", "core:apply": "", "Jenkins-Crumb": "{crumb_token}"}}',
        "Submit": "Save",
    }
    response = requests.post(job_url, auth=auth, data=payload, headers=headers)
    if response.status_code != requests.codes.OK:
        print(f"Failed to update description. Got {response.status_code} and response is {response.text}")
        return False
    return True
