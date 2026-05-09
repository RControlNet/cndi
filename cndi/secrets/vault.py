import logging
import os

from cndi.annotations import Component, ConditionalRendering
from cndi.autoconfiguration.configure import AutoConfigurationProviders
from cndi.consts import RCN_ENABLE_VAULT_PROVIDER
from cndi.env import getContextEnvironment, getContextEnvironments, RCN_ENVS_CONFIG, \
    reload_envs

logger = logging.getLogger(__name__)
VAULT_PROVIDER_PREFIX = "vault://"

@Component
@ConditionalRendering(callback=lambda x: getContextEnvironment(RCN_ENABLE_VAULT_PROVIDER, defaultValue=False, castFunc=bool))
class VaultSecretProvider:
    def __init__(self):
        try:
            import hvac
            vault_addr = getContextEnvironment("secrets.provider.vault.addr", "http://127.0.0.1:8200")
            vault_token = getContextEnvironment("secrets.provider.vault.token", os.environ.get("VAULT_TOKEN", ""))

            client = hvac.Client(url=vault_addr, token=vault_token)
            if client.is_authenticated():
                for key, value in getContextEnvironments().items():
                    self.resolve(key, value, client)
                reload_envs()
            else:
                logger.error("Failed to authenticate with Vault, check your credentials and Vault server status")

            AutoConfigurationProviders._PROVIDERS[VAULT_PROVIDER_PREFIX] = self
        except ImportError as ex:
            logger.error("Could not import hvac, install hvac python package")
            raise ex

    def resolve(self, key, value, client):
        if value.startswith(VAULT_PROVIDER_PREFIX):
            secret_ref = value[len(VAULT_PROVIDER_PREFIX):]
            mount_point, path, key_ref = secret_ref.split(" ")

            read_response = client.secrets.kv.read_secret_version(mount_point=mount_point, path=path)

            if read_response and 'data' in read_response:
                value = read_response['data']['data'][key_ref]
                os.environ[RCN_ENVS_CONFIG + '.' + key] = value
            else:
                logger.warning(f"Secret not found at path: {mount_point}")