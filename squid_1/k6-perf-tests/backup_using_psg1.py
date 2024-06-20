import requests
import json


def run_backup_brim1_psg1():
    url = "https://scint-app.qa.cds.hpe.com/api/v1/app-data-management-jobs/3e832238-1f2f-4afa-9c02-2d8d052a8e06/run"
    payload = json.dumps({
        "scheduleIds": [
            3,
            1,
            2
        ]
    })
    headers = {
        'Authorization': 'Bearer {{access_token}}',
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    return response
response = run_backup_brim1_psg1()
print(response.text)


def get_jwt_token():
    url = "https://sc-retrieve-test-jwt.rtplab.nimblestorage.com/gettoken"

    payload = json.dumps({
        "LOGIN_URL": "https://console-scint-app.qa.cds.hpe.com/login",
        "LOGIN_USER": "samselvaprabu@gmail.com",
        "LOGIN_PASSWORD": "nIM123bOLI#",
        "CID": "571ffed87a3f11ec93d1364dca07b5c4"
    })
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    return response


response = get_jwt_token()

print(response.text)
