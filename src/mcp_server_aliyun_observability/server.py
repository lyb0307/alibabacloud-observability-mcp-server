from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server import FastMCP
from mcp.server.fastmcp import FastMCP

from mcp_server_aliyun_observability.tools import ToolManager
from mcp_server_aliyun_observability.utils import (
    ArmsClientWrapper,
    SLSClientWrapper,
)


def create_lifespan(access_key_id: str, access_key_secret: str):
    @asynccontextmanager
    async def lifespan(fastmcp: FastMCP) -> AsyncIterator[dict]:
        sls_client = SLSClientWrapper(access_key_id, access_key_secret)
        arms_client = ArmsClientWrapper(access_key_id, access_key_secret)
        yield {
            "sls_client": sls_client,
            "arms_client": arms_client,
        }

    return lifespan


def init_server(
    access_key_id: str,
    access_key_secret: str,
    log_level: str = "INFO",
    transport_port: int = 8000,
):
    """initialize the global mcp server instance"""
    mcp_server = FastMCP(
        name="mcp_aliyun_observability_server",
        lifespan=create_lifespan(access_key_id, access_key_secret),
        log_level=log_level,
        port=transport_port,
    )
    ToolManager(mcp_server)
    return mcp_server


def server(
    access_key_id: str,
    access_key_secret: str,
    transport: str,
    log_level: str,
    transport_port: int,
):
    server: FastMCP = init_server(
        access_key_id, access_key_secret, log_level, transport_port
    )
    server.run(transport)
