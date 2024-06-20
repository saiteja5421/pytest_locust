import logging
import os

from requests import get, post, Response

logger = logging.getLogger()


class VaultManager:
    def __init__(self):
        """Vault Manager class to obtaining secrets from Vault

        Environment variables required to use this class:
        VAULT_ADDR: address to Vault

        Environment variables partially required to use this class (at least one needs to be present):
        VAULT_TOKEN: if we use fixed token
        VAULT_ROLE: if we're obtaining token from Kubernetes"""
        self.__vault_url = os.getenv("VAULT_ADDR")
        self.url = f"{self.__vault_url}/v1"
        self.header = self.__set_headers()

    def get_secret(self, path: str) -> Response:
        """Method that doing a rest call to Vault with path
        specified by parameter to obtain secret that is stored in Vault.

        :param path: str - path to Vault secret

        :return: :class:`Response <Response>` object
        :rtype: requests.Response
        """
        return get(url=f"{self.url}{path}", headers=self.header)

    def __set_headers(self):
        """Internal method that should be used only by Vault Manager.

        Checking two other internal methods if either Kubernetes token or Fixed token is obtainable.
        If specific token(s) exist(s) then first is looking for Kubernetes Token, if this token is
        present then it is set, otherwise fixed_token.
        """
        if not self.__vault_url:
            raise ValueError("VAULT_ADDR is empty")
        kubernetes_token = self.__get_kubernetes_token_authentication()
        fixed_token = self.__get_fixed_token()
        if not (kubernetes_token or fixed_token):
            raise ValueError("TOKEN is not obtainable")
        else:
            return {"X-Vault-Token": kubernetes_token if kubernetes_token else fixed_token}

    def __get_kubernetes_token_authentication(self):
        """Internal method that should be used only by Vault Manager.

        Method looks into path where JWT token is stored, if path exists then using it as request body with
        VAULT_ROLE environment variable to send request to Vault to authenticate.
        If authenticated returns token.

        Returns token if token exists, None if token does not exist
        """
        logger.info("Attempt to obtain Kubernetes JWT")
        path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        if os.path.exists(path) and os.getenv('VAULT_ROLE'):
            logger.info(f"Path {path} exist, proceeding to obtaining JWT token with role {os.getenv('VAULT_ROLE')}")
            with open(path) as jwt_file:
                request_body = {
                    "role": os.getenv("VAULT_ROLE"),
                    "jwt": jwt_file.read()
                }
            return post(url=f"{self.url}/auth/kubernetes/login", json=request_body).json()['auth']['client_token']
        logger.info("Kubernetes JWT token does not exist")

    def __get_fixed_token(self):
        """Internal method that should be used only by Vault Manager.

        Method is looking for environment variable VAULT_TOKEN if is present

        Returns token if token exists, None if token does not exist
        """
        logger.info("Attempt to obtain Fixed Token from env variable VAULT_TOKEN")
        token = os.getenv("VAULT_TOKEN")
        if token is not None:
            logger.info("Fixed Token obtained")
            return token
        logger.info("Fixed Token does not exist")
