from lib.platform.aws_boto3.models.base.pydantic_model import Base


class Parameter(Base):
    ParameterKey: str
    ParameterValue: str
