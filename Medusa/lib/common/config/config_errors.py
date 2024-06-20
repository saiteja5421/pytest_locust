from enum import Enum, auto


class ServiceType(Enum):
    service1 = auto()
    service2 = auto()


class ServiceNotSpecifiedError(Exception):
    def __init__(self):
        self.message = f"Service not specified! Service Version available: {ServiceType._member_names_}"
        super().__init__(self.message)


class WrongServiceSpecifiedError(Exception):
    def __init__(self, service: str):
        self.message = (
            f"Wrong service specified, we got: {service}! Service Version available: {ServiceType._member_names_}"
        )
        super().__init__(self.message)
