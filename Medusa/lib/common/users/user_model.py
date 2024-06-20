from dataclasses import dataclass


@dataclass
class APIClientCredential:
    api_client_id: str
    api_client_secret: str
    credential_name: str
    username: str
