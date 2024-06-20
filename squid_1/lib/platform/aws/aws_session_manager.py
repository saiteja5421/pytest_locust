import boto3


class AWSSessionManager:
    def __init__(
        self,
        region_name: str,
        profile_name: str = "default",
        aws_access_key_id: str = None,
        aws_secret_access_key: str = None,
        role_arn: str = None,
    ):
        self.region_name = region_name
        self.profile_name = profile_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.role_arn = role_arn
        self.aws_session_token = None

    def __repr__(self):
        return f"{vars(self)}"

    @property
    def aws_session(self) -> boto3.Session:
        if self.role_arn:
            self._load_credentials_from_role()
            return boto3.Session(
                region_name=self.region_name,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                aws_session_token=self.aws_session_token,
            )
        elif self.aws_access_key_id and self.aws_secret_access_key:
            return boto3.Session(
                region_name=self.region_name,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
            )
        else:
            return boto3.Session(region_name=self.region_name, profile_name=self.profile_name)

    @property
    def localstack_session(self) -> boto3.Session:
        return boto3.Session(
            region_name=self.region_name,
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )

    def _load_credentials_from_role(self):
        sts_client = boto3.client("sts")
        assumed_role_object = sts_client.assume_role(RoleArn=self.role_arn, RoleSessionName="role_session")
        credentials = assumed_role_object["Credentials"]
        self.aws_access_key_id = credentials["AccessKeyId"]
        self.aws_secret_access_key = credentials["SecretAccessKey"]
        self.aws_session_token = credentials["SessionToken"]
