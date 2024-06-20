from requests import codes, Response

from lib.common.common import get
from lib.common.config.config_manager import ConfigManager
from lib.common.users.user import User
from lib.dscc.audit.models.audit_events import AuditEventList


class AuditEvents:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.common_services_api = config["COMMON-SERVICES-API"]
        self.dscc = config["CLUSTER"]
        self.url = f"{self.dscc['url']}/api/{self.dscc['version']}"
        self.audit_events = self.common_services_api["audit-events"]

    # https://pages.github.hpe.com/nimble-dcs/storage-api/docs/#get-/api/v1/audit-events
    def get_audit_events(
        self, limit: int = 100, offset: int = 0, sort: str = "occurredAt", order: str = "desc", filter: str = ""
    ) -> AuditEventList:
        response: Response = get(
            self.url,
            path=self.audit_events,
            headers=self.user.authentication_header,
            params={"limit": limit, "offset": offset, "sort": f"{sort} {order}", "filter": filter},
        )
        assert response.status_code == codes.ok
        return AuditEventList.from_json(response.text)
