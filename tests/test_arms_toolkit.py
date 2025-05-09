import os
from datetime import datetime

import dotenv
import pytest
from mcp.server.fastmcp import Context, FastMCP
from mcp.shared.context import RequestContext

from mcp_server_aliyun_observability.server import create_lifespan
from mcp_server_aliyun_observability.toolkit.arms_toolkit import ArmsToolkit
from mcp_server_aliyun_observability.utils import (ArmsClientWrapper,
                                                   CredentialWrapper,
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
                "arms_client": ArmsClientWrapper(
                    credential=CredentialWrapper(
                        access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID"),
                        access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
                    ),
                ),
                "sls_client": SLSClientWrapper(
                    credential=CredentialWrapper(
                        access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID"),
                        access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
                    ),
                ),
            },
        )
    )
    return context


@pytest.fixture
def tool_manager(mcp_server):
    """创建ToolManager实例"""
    return ArmsToolkit(mcp_server)

@pytest.mark.asyncio
async def test_arms_profile_flame_analysis_success(
    tool_manager: ArmsToolkit,
    mcp_server: FastMCP,
    mock_request_context: Context,
):
    """测试arms_profile_flame_analysis成功的情况"""
    tool = mcp_server._tool_manager.get_tool("arms_profile_flame_analysis")
    result_data = await tool.run(
        {
            "pid": "test_pid",
            "startMs": "1609459200000",
            "endMs": "1609545600000",
            "profileType": "cpu",
            "ip": "127.0.0.1",
            "thread": "main-thread",
            "threadGroup": "default-group",
            "regionId": "cn-hangzhou",
        },
        context=mock_request_context,
    )
    assert result_data is not None

@pytest.mark.asyncio
async def test_arms_diff_flame_analysis_success(
    tool_manager: ArmsToolkit,
    mcp_server: FastMCP,
    mock_request_context: Context,
):
    """测试arms_diff_flame_analysis成功的情况"""
    tool = mcp_server._tool_manager.get_tool("arms_diff_profile_flame_analysis")
    result_data = await tool.run(
        {
            "pid": "test_pid",
            "startMs": "1609459200000",
            "endMs": "1609462800000",
            "baseStartMs": "1609545600000",
            "baseEndMs": "1609549200000",
            "profileType": "cpu",
            "ip": "127.0.0.1",
            "thread": "main-thread",
            "threadGroup": "default-group",
            "regionId": "cn-hangzhou",
        },
        context=mock_request_context,
    )
    assert result_data is not None

@pytest.mark.asyncio
async def test_arms_trace_quality_analysis(
    tool_manager: ArmsToolkit,
    mcp_server: FastMCP,
    mock_request_context: Context,
):
    """测试arms_trace_quality_analysis成功的情况"""
    tool = mcp_server._tool_manager.get_tool("arms_trace_quality_analysis")
    result_data = await tool.run(
        {
            "traceId": "test_trace_id",
            "startMs": 1746686989000,
            "endMs": 1746690589507,
            "regionId": "cn-hangzhou",
        },
        context=mock_request_context,
    )
    assert result_data is not None

@pytest.mark.asyncio
async def test_arms_slow_trace_analysis(
    tool_manager: ArmsToolkit,
    mcp_server: FastMCP,
    mock_request_context: Context,
):
    """测试arms_slow_trace_analysis成功的情况"""
    tool = mcp_server._tool_manager.get_tool("arms_slow_trace_analysis")
    result_data = await tool.run(
        {
            "traceId": "test_trace_id",
            "startMs": 1746686989000,
            "endMs": 1746690589507,
            "regionId": "cn-hangzhou",
        },
        context=mock_request_context,
    )
    assert result_data is not None

@pytest.mark.asyncio
async def test_arms_error_trace_analysis(
    tool_manager: ArmsToolkit,
    mcp_server: FastMCP,
    mock_request_context: Context,
):
    """测试arms_error_trace_analysis成功的情况"""
    tool = mcp_server._tool_manager.get_tool("arms_error_trace_analysis")
    result_data = await tool.run(
        {
            "traceId": "test_trace_id",
            "startMs": 1746686989000,
            "endMs": 1746690589507,
            "regionId": "cn-hangzhou",
        },
        context=mock_request_context,
    )
    assert result_data is not None