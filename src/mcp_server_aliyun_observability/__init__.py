import os
import sys

from alibabacloud_credentials.provider import StaticAKCredentialsProvider, EcsRamRoleCredentialsProvider, \
    RamRoleArnCredentialsProvider, OIDCRoleArnCredentialsProvider, StaticSTSCredentialsProvider
from alibabacloud_credentials.exceptions import CredentialException
from alibabacloud_credentials import provider

def _get_credentials_provider(self, config, profile_name):
        if profile_name is None or profile_name == '':
            raise CredentialException('invalid profile name')

        profiles = config.get('profiles', [])

        if not profiles:
            raise CredentialException(f"unable to get profile with '{profile_name}' form cli credentials file.")

        for profile in profiles:
            if profile.get('name') is not None and profile['name'] == profile_name:
                mode = profile.get('mode')
                if mode == "AK":
                    return StaticAKCredentialsProvider(
                        access_key_id=profile.get('access_key_id'),
                        access_key_secret=profile.get('access_key_secret')
                    )
                elif mode == "StsToken" or mode == "CloudSSO":
                    return StaticSTSCredentialsProvider(
                        access_key_id=profile.get('access_key_id'),
                        access_key_secret=profile.get('access_key_secret'),
                        security_token=profile.get('sts_token')
                    )
                elif mode == "RamRoleArn":
                    pre_provider = StaticAKCredentialsProvider(
                        access_key_id=profile.get('access_key_id'),
                        access_key_secret=profile.get('access_key_secret')
                    )
                    return RamRoleArnCredentialsProvider(
                        credentials_provider=pre_provider,
                        role_arn=profile.get('ram_role_arn'),
                        role_session_name=profile.get('ram_session_name'),
                        duration_seconds=profile.get('expired_seconds'),
                        policy=profile.get('policy'),
                        external_id=profile.get('external_id'),
                        sts_region_id=profile.get('sts_region'),
                        enable_vpc=profile.get('enable_vpc'),
                    )
                elif mode == "EcsRamRole":
                    return EcsRamRoleCredentialsProvider(
                        role_name=profile.get('ram_role_name')
                    )
                elif mode == "OIDC":
                    return OIDCRoleArnCredentialsProvider(
                        role_arn=profile.get('ram_role_arn'),
                        oidc_provider_arn=profile.get('oidc_provider_arn'),
                        oidc_token_file_path=profile.get('oidc_token_file'),
                        role_session_name=profile.get('role_session_name'),
                        duration_seconds=profile.get('expired_seconds'),
                        policy=profile.get('policy'),
                        sts_region_id=profile.get('sts_region'),
                        enable_vpc=profile.get('enable_vpc'),
                    )
                elif mode == "ChainableRamRoleArn":
                    previous_provider = self._get_credentials_provider(config, profile.get('source_profile'))
                    return RamRoleArnCredentialsProvider(
                        credentials_provider=previous_provider,
                        role_arn=profile.get('ram_role_arn'),
                        role_session_name=profile.get('ram_session_name'),
                        duration_seconds=profile.get('expired_seconds'),
                        policy=profile.get('policy'),
                        external_id=profile.get('external_id'),
                        sts_region_id=profile.get('sts_region'),
                        enable_vpc=profile.get('enable_vpc'),
                    )
                else:
                    raise CredentialException(f"unsupported profile mode '{mode}' form cli credentials file.")

        raise CredentialException(f"unable to get profile with '{profile_name}' form cli credentials file.")

provider.cli_profile.CLIProfileCredentialsProvider._get_credentials_provider = _get_credentials_provider

import click
import dotenv
from typing import Dict

from mcp_server_aliyun_observability.server import server
from mcp_server_aliyun_observability.utils import CredentialWrapper
dotenv.load_dotenv()


@click.command()
@click.option(
    "--access-key-id",
    type=str,
    help="aliyun access key id",
    required=False,
    envvar="ALIBABA_CLOUD_ACCESS_KEY_ID",
)
@click.option(
    "--access-key-secret",
    type=str,
    help="aliyun access key secret",
    required=False,
    envvar="ALIBABA_CLOUD_ACCESS_KEY_SECRET",
)
@click.option(
    "--security-token",
    type=str,
    help="aliyun security token (for temporary credentials)",
    required=False,
    envvar="ALIBABA_CLOUD_SECURITY_TOKEN",
)
@click.option(
    "--knowledge-config",
    type=str,
    help="knowledge config file path",
    required=False,
)
@click.option("--host", type=str, help="host", default="0.0.0.0")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    help="transport type: stdio or sse or streamable-http",
    default="stdio",
)
@click.option("--log-level", type=str, help="log level", default="INFO")
@click.option("--transport-port", type=int, help="transport port", default=8000)
def main(
    access_key_id,
    access_key_secret,
    security_token,
    knowledge_config,
    transport,
    log_level,
    transport_port,
    host,
):
    
    if access_key_id and access_key_secret:
        credential = CredentialWrapper(
            access_key_id, access_key_secret, knowledge_config, security_token
        )
    else:
        credential = None

    server(credential, transport, log_level, transport_port, host=host)
