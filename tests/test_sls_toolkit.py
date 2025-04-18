import os
from datetime import datetime

import dotenv
import pytest
from mcp.server.fastmcp import Context, FastMCP
from mcp.shared.context import RequestContext

from mcp_server_aliyun_observability.server import create_lifespan
from mcp_server_aliyun_observability.toolkit.sls_toolkit import SLSToolkit
from mcp_server_aliyun_observability.utils import SLSClientWrapper

dotenv.load_dotenv()

import logging

logger = logging.getLogger(__name__)


@pytest.fixture
def mcp_server():
    """创建模拟的FastMCP服务器实例"""
    mcp_server = FastMCP(
        name="mcp_aliyun_observability_server",
        lifespan=create_lifespan(
            os.getenv("ALIYUN_ACCESS_KEY_ID"), os.getenv("ALIYUN_ACCESS_KEY_SECRET")
        ),
    )
    return mcp_server


@pytest.fixture
def mock_request_context():
    """创建模拟的RequestContext实例"""
    context = Context(
        request_context=RequestContext(
            request_id="test_request_id",
            meta=None,
            session=None,
            lifespan_context={
                "sls_client": SLSClientWrapper(
                    os.getenv("ALIYUN_ACCESS_KEY_ID"),
                    os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
                ),
            },
        )
    )
    return context


@pytest.fixture
def tool_manager(mcp_server):
    """创建ToolManager实例"""
    return SLSToolkit(mcp_server)


@pytest.mark.asyncio
async def test_sls_execute_query_success(
    tool_manager: SLSToolkit,
    mcp_server: FastMCP,
    mock_request_context: Context,
):
    """测试SLS查询执行成功的情况"""
    tool = mcp_server._tool_manager.get_tool("sls_execute_query")
    text = await tool.run(
        {
            "project": os.getenv("TEST_PROJECT"),
            "log_store": os.getenv("TEST_LOG_STORE"),
            "query": "pid:aokcdqn3ly@b57c445b5d36e86 | SELECT serviceName, SUM(duration)/1000000 AS total_duration_ms FROM log GROUP BY serviceName ORDER BY total_duration_ms DESC LIMIT 10",
            "from_timestamp": int(datetime.now().timestamp()) - 3600,
            "to_timestamp": int(datetime.now().timestamp()),
            "limit": 10,
            "region_id": os.getenv("TEST_REGION"),
        },
        context=mock_request_context,
    )
    logger.info(text)
    assert text["data"] is not None
    assert text["message"] == "success"
