import os
import sys

import click
import dotenv

from mcp_server_aliyun_observability.server import server
from mcp_server_aliyun_observability.utils import CredentialWrapper

dotenv.load_dotenv()


@click.command()
@click.option(
    "--access-key-id",
    type=str,
    help="aliyun access key id",
    required=False,
)
@click.option(
    "--access-key-secret",
    type=str,
    help="aliyun access key secret",
    required=False,
)
@click.option(
    "--transport", type=str, help="transport type. stdio or sse", default="stdio"
)
@click.option("--log-level", type=str, help="log level", default="INFO")
@click.option("--transport-port", type=int, help="transport port", default=8000)
def main(access_key_id, access_key_secret, transport, log_level, transport_port):
    if access_key_id and access_key_secret:
        credential = CredentialWrapper(access_key_id, access_key_secret)
    else:
        credential = None
    server(credential, transport, log_level, transport_port)
