import dataclasses
import os
import logging
from time import sleep
import requests
from json import JSONDecodeError
from requests import codes, Response, adapters
from tenacity import retry, stop_after_attempt, wait_fixed


timeout_in_millis = 5000
show_response = os.environ.get("show_response", "false")
delete_payload = {}
IPIFY_NUM_TRIES: int = 5
IPIFY_RESPONSE_BAD_GATEWAY: str = "Bad Gateway"

logger = logging.getLogger()
s = requests.Session()
s.mount("https://", adapters.HTTPAdapter(pool_connections=10, max_retries=3))


class Http403ForbiddenException(Exception):
    pass


@dataclasses.dataclass
class FailedRetryWithResponseException(Exception):
    response: Response


def raise_my_exception(retry_state):
    result = retry_state.outcome.result()

    # Raise specific 403 exception for others return the result
    if isinstance(result, Response) and result.status_code == codes.forbidden:
        raise FailedRetryWithResponseException(result)
    else:
        return result


def is_retry_needed(retry_state):
    needs_retry = False
    result = retry_state.outcome._result

    if isinstance(result, Response) and result.status_code == codes.forbidden:
        # For forbidden response
        needs_retry = True
        logger.debug("Server returned forbidden response. Retrying..")
    elif isinstance(
        retry_state.outcome._exception,
        (
            requests.exceptions.ProxyError,
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectionError,
        ),
    ):
        # For ProxyError OR socket timeouts
        needs_retry = True
        logger.debug("Proxy error occurred. Retrying..")
        logger.debug("Server returned forbidden response. Retrying..")
    elif (
        isinstance(result, Response)
        and result.status_code == codes.internal_server_error
        and "/data-services/v1beta1/async-operations" in result.request.url
    ):
        # Workaround till we get fix for SC-8356
        needs_retry = True
        logger.debug("SC-8356(Task service internal error) issue. Retrying..")
    elif (
        isinstance(result, Response)
        and result.status_code == codes.service_unavailable
        and "/data-services/v1beta1/async-operations" in result.request.url
    ):
        needs_retry = True
        logger.error("503 Error from tasks service")
    elif isinstance(result, Response) and result.status_code == codes.unauthorized and "Jwks" in result.text:
        needs_retry = True
        # Should retry on "Jwks doesn't have key to match kid or alg from Jwt"
        logger.error("401 Error, unauthorized -> Jwks doesn't have key to match kid or alg from Jwt")
    return needs_retry


def _log_request(method, uri, path, headers, payload=None):
    if headers.get("X-B3-TraceId") and headers.get("X-B3-SpanId"):
        logger.debug(f'Humio "x_b3_traceid"={headers["X-B3-TraceId"]} "x_b3_spanid"={headers["X-B3-SpanId"]}')
    if payload:
        logger.debug(f"URI {method} {uri}/{path}")
        logger.debug(f"Request Body {payload}")


def _log_response(response: Response):
    if response.status_code not in [codes.ok, codes.accepted, codes.no_content]:
        logger.debug(f"Status {response.status_code}")
        logger.debug(f"Response Headers {response.headers}")
        if "content-type" in response.headers and response.headers["content-type"] == "application/json":
            try:
                logger.debug(f"Response Body {response.json()}")
            except JSONDecodeError:
                logger.debug(f"Unable to parse response to JSON. Text Response Body {response.text}")
        else:
            logger.debug(f"Response Body: {response.text}")

        if "upstream connect error or disconnect" in response.text:
            logger.error(response.text)


@retry(
    retry=is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=raise_my_exception,
)
def get(uri, path, params="", headers={}, verify=False):
    """Send a GET request"""
    _log_request("GET", uri, path, headers)
    response = s.get(
        url=f"{uri}/{path}",
        headers=headers,
        params=params,
        timeout=timeout_in_millis,
        verify=verify,
    )
    _log_response(response)
    return response


@retry(
    retry=is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=raise_my_exception,
)
def post(uri, path, json_data="", params="", just_json="", headers={}, verify=False, auth=None):
    """Send a POST request"""
    _log_request("POST", uri, path, headers, json_data)
    response = s.post(
        url=f"{uri}/{path}",
        headers=headers,
        data=json_data,
        params=params,
        json=just_json,
        timeout=timeout_in_millis,
        verify=verify,
        auth=auth,
    )
    _log_response(response)
    return response


@retry(
    retry=is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=raise_my_exception,
)
def put(uri, path, json_data="", params="", just_json="", headers={}, verify=False):
    """Send a PUT request"""
    _log_request("PUT", uri, path, headers, json_data)
    response = s.put(
        url=f"{uri}/{path}",
        data=json_data,
        params=params,
        json=just_json,
        headers=headers,
        timeout=timeout_in_millis,
        verify=verify,
    )
    _log_response(response)
    return response


@retry(
    retry=is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=raise_my_exception,
)
def patch(uri, path, json_data="", params="", just_json="", headers={}, verify=False):
    """Send a PATCH request"""
    _log_request("PATCH", uri, path, headers, json_data)
    response = s.patch(
        url=f"{uri}/{path}",
        data=json_data,
        params=params,
        json=just_json,
        headers=headers,
        timeout=timeout_in_millis,
        verify=verify,
    )
    _log_response(response)
    return response


@retry(
    retry=is_retry_needed,
    stop=stop_after_attempt(10),
    wait=wait_fixed(5),
    retry_error_callback=raise_my_exception,
)
def delete(uri, path, headers={}, verify=False):
    _log_request("DELETE", uri, path, headers)
    response = s.delete(
        url=f"{uri}/{path}",
        headers=headers,
        data=delete_payload,
        timeout=timeout_in_millis,
        verify=verify,
    )
    _log_response(response)
    return response


def get_public_ip() -> str:
    # Occasionally, to call to "get("https://api.ipify.org").content.decode("utf8")"
    # returns "Bad Gateway" instead of an actual IP Address.
    # We'll make a few attempts to get an address
    # NOTE: updating the URL to: "https://api64.ipify.org".
    # "https://api.ipify.org" seems to be blocked, failing all Sanity Suites
    ip = ""

    for _ in range(IPIFY_NUM_TRIES):
        logger.info("Get public IP")
        ip = get("https://api64.ipify.org", path="").content.decode("utf8")
        if ip != IPIFY_RESPONSE_BAD_GATEWAY:
            break
        sleep(5)
    logger.info(f"Public IP from ipify: {ip}")
    return ip


def get_task_id_from_header(response: Response):
    """Returns task_id parsed from 'Location' header of the response object as per the new GLCP API compliance"""
    logger.info(f"task {response.headers}: {response.headers}")
    task_id = response.headers.get("Location")
    return task_id.split("/")[-1]
