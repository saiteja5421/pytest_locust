from lib.platform.aws_boto3.models.base.pydantic_model import Base


class SecurityGroup(Base):
    GroupName: str
    GroupId: str
