from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from alibabacloud_credentials.client import Client as CredClient
from mcp.server import FastMCP
from mcp.server.fastmcp import FastMCP

from mcp_server_aliyun_observability.toolkit.arms_toolkit import ArmsToolkit
from mcp_server_aliyun_observability.toolkit.sls_toolkit import SLSToolkit
from mcp_server_aliyun_observability.toolkit.cms_toolkit import CMSToolkit
from mcp_server_aliyun_observability.toolkit.util_toolkit import UtilToolkit
from mcp_server_aliyun_observability.utils import (
    ArmsClientWrapper,
    CredentialWrapper,
    SLSClientWrapper,
)


def create_lifespan(credential: Optional[CredentialWrapper] = None):
    @asynccontextmanager
    async def lifespan(fastmcp: FastMCP) -> AsyncIterator[dict]:
        sls_client = SLSClientWrapper(credential)
        arms_client = ArmsClientWrapper(credential)
        cms_client = SLSClientWrapper(credential)
        yield {
            "sls_client": sls_client,
            "arms_client": arms_client,
            "cms_client": cms_client,
        }

    return lifespan


def init_server(
    credential: Optional[CredentialWrapper] = None,
    log_level: str = "INFO",
    transport_port: int = 8000,
    host: str = "0.0.0.0",
):
    """initialize the global mcp server instance"""
    mcp_server = FastMCP(
        name="mcp_aliyun_observability_server",
        lifespan=create_lifespan(credential),
        log_level=log_level,
        port=transport_port,
        host=host,
    )
    SLSToolkit(mcp_server)
    UtilToolkit(mcp_server)
    ArmsToolkit(mcp_server)
    CMSToolkit(mcp_server)
    return mcp_server


def server(
    credential: Optional[CredentialWrapper] = None,
    transport: str = "stdio",
    log_level: str = "INFO",
    transport_port: int = 8000,
    host: str = "0.0.0.0",
):
    server: FastMCP = init_server(credential, log_level, transport_port, host)
    server.run(transport)
