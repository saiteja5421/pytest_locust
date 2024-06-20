import requests
from common import helpers

url = "https://scdev01-app.qa.cds.hpe.com/api/v1/csp-accounts?limit=400"

headers = helpers.gen_token()
response = requests.request("GET", url, headers=headers.authentication_header)
accounts = response.json()["items"]
"name".startswith("fake")
for acc in accounts:
    acc_name = acc["name"]

    if acc_name.startswith("fake"):
        url = f"https://scdev01-app.qa.cds.hpe.com/test/v1/nb-rest.cam/csp-accounts/{acc['id']}"
        response = requests.request("DELETE", url, headers=headers.authentication_header)
        print(response.text)
