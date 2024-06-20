from lib.platform.aws.models.base.pydantic_model import Base


class SecurityGroup(Base):
    GroupName: str
    GroupId: str
