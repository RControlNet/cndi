from cndi.autoconfiguration.configure import AutoConfigurationProviders
from cndi.consts import RCN_ENABLE_VAULT_PROVIDER
from cndi.env import RCN_ENVS_CONFIG, getContextEnvironment
from cndi.initializers import AppInitializer
import os
from testcontainers.vault import VaultContainer
import hvac

ASSERT_VALUE = "test_key"
if __name__ == '__main__':
    with VaultContainer("hashicorp/vault:1.16.1") as vault_container:
        client = hvac.Client(url=vault_container.get_connection_url(), token=vault_container.root_token)
        assert client.is_authenticated()

        client.sys.enable_secrets_engine(
            backend_type='kv',
            path='secrets/iorcloud',
        )
        client.secrets.kv.v2.create_or_update_secret(
            mount_point='secrets/iorcloud',
            path='commons',
            secret=dict(llm_proxy_virtual_key=ASSERT_VALUE)
        )

        os.environ[RCN_ENVS_CONFIG + '.' + RCN_ENABLE_VAULT_PROVIDER] = "true"
        os.environ[RCN_ENVS_CONFIG + '.' + "secrets.provider.vault.addr"] = vault_container.get_connection_url()
        os.environ[RCN_ENVS_CONFIG + '.' + "secrets.provider.vault.token"] = vault_container.root_token
        os.environ[RCN_ENVS_CONFIG + '.' + 'SECRET_VALUE'] = "vault://secrets/iorcloud commons llm_proxy_virtual_key"

        app_initializer = AppInitializer()
        app_initializer.componentScan("cndi.secrets")
        app_initializer.run()
        print(AutoConfigurationProviders._PROVIDERS)
        print(getContextEnvironment('SECRET_VALUE'))

        assert getContextEnvironment('SECRET_VALUE') == ASSERT_VALUE