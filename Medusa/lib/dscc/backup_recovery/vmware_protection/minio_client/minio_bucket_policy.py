import json


public_bucket_policy_payload = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetBucketLocation", "s3:ListBucket", "s3:ListBucketMultipartUploads"],
            "Resource": ["arn:aws:s3:::test-api-bucket"],
        },
        {
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": [
                "s3:DeleteObject",
                "s3:GetObject",
                "s3:ListMultipartUploadParts",
                "s3:PutObject",
                "s3:AbortMultipartUpload",
            ],
            "Resource": ["arn:aws:s3:::test-api-bucket/*"],
        },
    ],
}
