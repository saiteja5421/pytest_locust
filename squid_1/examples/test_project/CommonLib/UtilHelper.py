import json
import requests

class UtilHelper():

    @staticmethod
    def get_token(user_attr):
            url = "https://sc-retrieve-test-jwt.rtplab.nimblestorage.com/gettoken"
            payload = json.dumps(
                {
                    "LOGIN_URL": "https://console-scdev01-app.qa.cds.hpe.com/login",
                    "LOGIN_USER": user_attr["username"],
                    "LOGIN_PASSWORD": user_attr["password"],
                    "CID": "98238538805411ec8db89af28c4e9299",
                }
            )
            headers = {"Content-Type": "application/json"}

            response = requests.request("POST", url, headers=headers, data=payload)
            return response