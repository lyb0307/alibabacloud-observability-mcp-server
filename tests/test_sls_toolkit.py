import os
from datetime import datetime

import dotenv
import pytest
from mcp.server.fastmcp import Context, FastMCP
from mcp.shared.context import RequestContext

from mcp_server_aliyun_observability.server import create_lifespan
from mcp_server_aliyun_observability.toolkit.sls_toolkit import SLSToolkit
from mcp_server_aliyun_observability.utils import (CredentialWrapper,
                                                   SLSClientWrapper)

dotenv.load_dotenv()

import logging

logger = logging.getLogger(__name__)


@pytest.fixture
def mcp_server():
    """创建模拟的FastMCP服务器实例"""
    mcp_server = FastMCP(
        name="mcp_aliyun_observability_server",
        lifespan=create_lifespan(
            credential=CredentialWrapper(
                access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID"),
                access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
                knowledge_config=None
            ),
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
                    credential=CredentialWrapper(
                        access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID"),
                        access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
                        knowledge_config=None
                    ),
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
    tool = mcp_server._tool_manager.get_tool("sls_execute_sql_query")
    text = await tool.run(
        {
            "project": os.getenv("TEST_PROJECT"),
            "logStore": os.getenv("TEST_LOG_STORE"),
            "query": "* | select count(*) as total",
            "fromTimestampInSeconds": int(datetime.now().timestamp()) - 3600,
            "toTimestampInSeconds": int(datetime.now().timestamp()),
            "limit": 10,
            "regionId": os.getenv("TEST_REGION"),
        },
        context=mock_request_context,
    )
    assert text["data"] is not None
    """
     response_body: List[Dict[str, Any]] = response.body
            result = {
                "data": response_body,
    """
    print(text)
    item = text["data"][0]
    assert item["total"] is not None
    assert text["message"] == "success"


@pytest.mark.asyncio
async def test_sls_list_projects_success(
    tool_manager: SLSToolkit,
    mcp_server: FastMCP,
    mock_request_context: Context,
):
    """测试SLS列出项目成功的情况"""
    tool = mcp_server._tool_manager.get_tool("sls_list_projects")
    text = await tool.run(
        {
            "projectName": "",
            "limit": 10,
            "regionId": os.getenv("TEST_REGION"),
        },
        context=mock_request_context,
    )
    assert len(text) > 0

@pytest.mark.asyncio
async def test_sls_list_logstores_success(
    tool_manager: SLSToolkit,
    mcp_server: FastMCP,
    mock_request_context: Context,
):
    """测试SLS列出日志库成功的情况"""
    tool = mcp_server._tool_manager.get_tool("sls_list_logstores")
    text = await tool.run(
        {
            "project": os.getenv("TEST_PROJECT"),
            "regionId": os.getenv("TEST_REGION"),
            "limit": 10,
        },
        context=mock_request_context,
    )
    assert len(text["logstores"]) > 0


@pytest.mark.asyncio
async def test_sls_list_metric_store_success(
    tool_manager: SLSToolkit,
    mcp_server: FastMCP,
    mock_request_context: Context,
):
    """测试SLS列出日志库成功的情况"""
    tool = mcp_server._tool_manager.get_tool("sls_list_logstores")
    text = await tool.run(
        {
            "project": os.getenv("TEST_PROJECT"),
            "logStore": "",
            "limit": 10,
            "isMetricStore": True,
            "regionId": os.getenv("TEST_REGION"),
        },
        context=mock_request_context,
    )
    assert len(text["logstores"]) >= 0

@pytest.mark.asyncio
async def test_sls_describe_logstore_success(
    tool_manager: SLSToolkit,
    mcp_server: FastMCP,
    mock_request_context: Context,
):
    """测试SLS描述日志库成功的情况"""
    tool = mcp_server._tool_manager.get_tool("sls_describe_logstore")
    text = await tool.run(
        {
            "project": os.getenv("TEST_PROJECT"),
            "logStore": os.getenv("TEST_LOG_STORE"),
            "regionId": os.getenv("TEST_REGION"),
        },
        context=mock_request_context,
    )
    assert text is not None


@pytest.mark.asyncio
async def test_sls_translate_text_to_sql_query_success(
    tool_manager: SLSToolkit,
    mcp_server: FastMCP,
    mock_request_context: Context,
):
    """测试SLS自然语言转换为查询语句成功的情况"""
    tool = mcp_server._tool_manager.get_tool("sls_translate_text_to_sql_query")
    text = await tool.run(
        {
            "project": os.getenv("TEST_PROJECT"),
            "logStore": os.getenv("TEST_LOG_STORE"),
            "text": "我想查询最近10分钟内，所有日志库的日志数量",
            "regionId": os.getenv("TEST_REGION"),
        },
        context=mock_request_context,
    )
    assert text is not None
    assert "select" in text["data"] or "SELECT" in text["data"]
