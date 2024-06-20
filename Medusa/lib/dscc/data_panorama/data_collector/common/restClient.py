from math import ceil
import requests
import time

# import logging

# import data_collector.common.restClient as restClinet
# from tests.data_collector.dt1_collectdata import headers

# logger = logging.getLogger()


def get(url, headers, body=None):
    retry_count = 5
    while retry_count > 0:
        try:
            # timeout(<connectionTimeout> ,  <ResponseTimeout>) in seconds
            response = requests.get(url=url, data=body, headers=headers, timeout=(15, 60))
            response.raise_for_status()  # Raise an exception if the status is not 200
            # Do something with the response
            return response
            # break  # Exit the loop if successful
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            retry_count -= 1
            if retry_count == 0:
                # logger.error(f"Failed to get API response after 3 retries. url - {url}")
                print(f"Failed to get API response after 3 retries. url - {url}")
                # break
                exit()
            else:
                print(f"Retrying {retry_count} more time(s) in 5 seconds. url - {url}")
                time.sleep(5)


def post(url, headers, payload):
    retry_count = 3
    while retry_count > 0:
        try:
            # timeout(<connectionTimeout> ,  <ResponseTimeout>) in seconds
            response = requests.post(url=url, data=payload, headers=headers, timeout=(15, 60))
            response.raise_for_status()  # Raise an exception if the status is not 200
            # Do something with the response
            return response
            # break  # Exit the loop if successful
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            retry_count -= 1
            if retry_count == 0:
                print("Failed to post API data after 3 retries.")
                exit()
            else:
                print(f"Retrying {retry_count} more time(s) in 5 seconds.")
                time.sleep(5)


def get_paginated_response(resource_url, headers, limit=50):
    """
    Get page by page response.
    Note: Fleet API has issue with paging response thus duplicates are occuring. So use get_all_response
    """
    all_data = []
    # total_limit = 0
    num_resources = 0
    offset = 0
    while True:
        limits_url = f"{resource_url}?limit={limit}&offset={offset}"
        # params = {"limit": limit, "offset": offset}
        response = get(url=limits_url, headers=headers)
        resource = response.json()
        if not resource["items"]:
            break
        num_resources += len(resource["items"])
        all_data.extend(resource["items"])
        # total_limit = total_limit + limit
        # if total_limit < resource['total']:
        offset += limit
    return all_data


def get_all_response(resource_url, headers, sort_by="id", get_list=True):
    """
    Get all response irrespective of page limit
    """
    all_data = []
    response = get(url=resource_url, headers=headers)
    if response.status_code == 200:
        data = response.json()

    limit = data["total"]
    # limit = 500
    for i in range(ceil(limit / 500)):
        offset = 500 * i
        # url_limit_1000 = f'https://scdev01-app.qa.cds.hpe.com/api/v1/storage-systems/device-type2/0074a8774a94dbbe7c000000000000000000000001/volumes/0674a8774a94dbbe7c000000000000000000000012/snapshots?sort=id+desc&limit=500&offset={offset}'
        # limits_url = url_limit_1000
        # limits_url = f"{resource_url}?limit={limit}&offset=0"
        limits_url = f"{resource_url}?sort={sort_by}+desc&limit=500&offset={offset}"
        response = get(url=limits_url, headers=headers)
        if get_list == False:
            return response
        resource = response.json()
        all_data.extend(resource["items"])

    return all_data
