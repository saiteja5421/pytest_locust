import boto3
from lib.common.config.config_manager import ConfigManager
import logging

config = ConfigManager.get_config()
aws_access_key = config["AWS"]["access_key"]
aws_secret_key = config["AWS"]["secret_key"]
region = config["AWS"]["region"]
bucket = config["AWS"]["bucket_name"]


def connect_to_s3(access_key, secret_key):
    session = boto3.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key)
    return session.resource(service_name="s3")


def get_bucket_size(bucket_name=bucket):
    try:
        s3 = connect_to_s3(access_key=aws_access_key, secret_key=aws_secret_key)
        bucket = s3.Bucket(bucket_name)
        total_size = 0

        for obj in bucket.objects.all():
            total_size += obj.size
            print("\n")
            print(f"Object Name             : {obj.key}")
            print(f"Object Size in Bytes    : {obj.size} Bytes")

        total_size_gb = total_size / 1024 / 1024 / 1024
        print(f'\nTotal size of Bucket "{bucket_name}" in GB : {total_size_gb}')

        return total_size_gb
    except Exception as e:
        logging.info(f"Got exception while connecting to AWS S3: {e}")


def get_all_buckets():
    try:
        s3 = connect_to_s3(access_key=aws_access_key, secret_key=aws_secret_key)
        buckets = s3.buckets.all()
        list_of_buckets = [bucket.name for bucket in buckets.all()]
        logging.info(f"Number of Buckets found: {len(list_of_buckets)}")
        message = f"Bucket list: {list_of_buckets}, Number of buckets: {len(list_of_buckets)}"
        return message
    except Exception as e:
        logging.info(f"Got exception while connecting to AWS S3: {e}")
