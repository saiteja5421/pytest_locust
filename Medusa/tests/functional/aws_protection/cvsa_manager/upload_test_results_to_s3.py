"""
Script created for uploading cloud test results from FilePoc:
- upload test results from cluster to S3 bucket
"""
import logging
import os.path
from datetime import datetime, timedelta
from os import getenv

import boto3 as boto3

S3_BUCKET_NAME = "global-storagecentral-qa-testreports-us-west-2"
TEST_RESULT_PATH = "/Medusa/test_results/"
TEST_RESULTS_NAME = "cVSA_Manager_Cloud_tests.xml"
TEST_RESULTS_FILE = f"{TEST_RESULT_PATH}{TEST_RESULTS_NAME}"
AWS_REGION_1_NAME = getenv("AWS_REGION_ONE", "eu-west-1")

if not os.path.isfile(TEST_RESULTS_FILE):
    logging.error(f"Log file does not exist {TEST_RESULTS_FILE}")


def timestamp_test_results() -> str:
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    test_results_timestamped = f"{TEST_RESULT_PATH}cVSA_Manager_Cloud_tests_{timestamp}.xml"
    if os.path.isfile(TEST_RESULTS_FILE):
        os.rename(TEST_RESULTS_FILE, test_results_timestamped)
        return test_results_timestamped
    else:
        return TEST_RESULTS_FILE


def upload_file_to_bucket(file_path: str, bucket_name: str) -> None:
    boto_session = boto3.Session(region_name=AWS_REGION_1_NAME)
    s3_client = boto_session.client(service_name="s3")
    file_name = os.path.basename(file_path)
    try:
        with open(file_path, "rb") as file:
            s3_client.upload_fileobj(Fileobj=file, Bucket=bucket_name, Key=file_name)
            logging.info(f"Log uploaded {file} to {bucket_name}")
    except FileNotFoundError:
        logging.info(f"Log file not found {file_path}")


def delete_reports_older_than(days=7):
    date_past = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    s3_client = boto3.client(service_name="s3")
    response = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix="cVSA_Manager_Cloud_tests")
    filtered_objects = [
        obj["Key"] for obj in response["Contents"] if obj["LastModified"].strftime("%Y-%m-%d") <= date_past
    ]
    for obj_key in filtered_objects:
        logging.info(f"Deleting log file: {obj_key}")
        s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=obj_key)


new_test_report_name = timestamp_test_results()
upload_file_to_bucket(bucket_name=S3_BUCKET_NAME, file_path=new_test_report_name)
delete_reports_older_than()
