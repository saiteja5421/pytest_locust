import yaml
import lib.dscc.data_panorama.data_collector.common.restClient as restClinet
import datetime
import os


def read_yaml():
    with open(os.getenv("DATA_COLLECTOR_CONF"), "r") as file:
        acc_config = yaml.safe_load(file)
    return acc_config


def getAccessToken():
    url = f"https://sso.common.cloud.hpe.com/as/token.oauth2"
    yaml_config = read_yaml()
    body = f"grant_type=client_credentials&client_id={yaml_config['ACCOUNT']['client_id']}&client_secret={yaml_config['ACCOUNT']['client_secret']}"
    headers = {"content-type": "application/x-www-form-urlencoded"}
    resp = restClinet.post(url=url, payload=body, headers=headers)
    data = resp.json()
    return data["access_token"]


def getBearerToken():
    return f"Bearer {getAccessToken()}"
    # token='eyJhbGciOiJSUzI1NiIsImtpZCI6IlRFak8tZEJPbThxUDlqRUlxdVE5aXVKX09HTSIsInBpLmF0bSI6ImRlejAifQ.eyJjbGllbnRfaWQiOiI2ZDNkY2YzNS0yZDkwLTRlNjMtOTdmNC1hZWViYThiODAwMmUiLCJpc3MiOiJodHRwczovL3Nzby5jb21tb24uY2xvdWQuaHBlLmNvbSIsImF1ZCI6ImV4dGVybmFsX2FwaSIsInN1YiI6Im1haGFudGVzaC5jaGluaXdhckBocGUuY29tIiwidXNlcl9jdHgiOiJlNGEwMmE4NDkwOTgxMWVjYjgwZGQyNWUzMmQzYjRmNyIsImF1dGhfc291cmNlIjoiY2NzX3Rva2VuX21hbmFnZW1lbnQiLCJwbGF0Zm9ybV9jdXN0b21lcl9pZCI6IjhjZWU1ZDVjOGQ0ZjExZWM5MmMwMjY5NGYyZTRlMzg4IiwiaWF0IjoxNjgyMzkxODczLCJhcHBsaWNhdGlvbl9pbnN0YW5jZV9pZCI6IjM1OTUzZTg4LWQ0ZDgtNDA3Ni1iMzIxLWY2N2M5YWM0ZDJiZCIsImV4cCI6MTY4MjM5OTA3M30.V53SeTGM0t7m8OMKc_4YJLTDfSRA8e4cGRfYSbnysrjqzqRqsdTTQb9Tkp0EfID9NUEunA3U5YNi_JpE2eASCwEEi0FjabYNa2xqovFc0SQvlVImIW9AbalKIVNrPQ0d_D2mhsJ83QyKi0bf3JWf22NEbhhEchCNGrmNlcEbs5vU977r6vDrXkgW3ccxMRA9BGvNbYeVaS5zc_SIJVbCLKSX1jbsWVqAYcz2azQ7yZi4oN8OngzLAMX5t6wg-4PdhCof0dCWDtnmkScGN2f-JoAJkYUUQLKpsEUR5i_Cvq5ooVIy53IlPbEy6ci_w1U8cWo1CJBOSnbd6G-qjRrs0A'
    # return f'Bearer {token}'


def getDatetimeInUTC():
    dt = datetime.datetime.now(datetime.timezone.utc)
    dt = dt.strftime("%Y-%m-%d %H:%M:%S.%f %z %Z")
    return dt


def replace_customer_id(mydict, new_customer_id):
    if isinstance(mydict, dict):
        for key, value in mydict.items():
            if key == "customerId":
                mydict[key] = new_customer_id
            elif isinstance(value, (dict, list)):
                replace_customer_id(value, new_customer_id)
    elif isinstance(mydict, list):
        for item in mydict:
            replace_customer_id(item, new_customer_id)
