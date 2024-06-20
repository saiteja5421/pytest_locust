from lib.platform.aws.models.base.pydantic_model import Base


class Parameter(Base):
    ParameterKey: str
    ParameterValue: str
