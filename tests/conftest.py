from unittest.mock import Mock

import pytest
from mcp.server.fastmcp import Context, FastMCP


@pytest.fixture(scope="session")
def mock_sls_client():
    """创建模拟的SLS客户端"""
    return Mock()

@pytest.fixture(scope="session")
def mock_arms_client():
    """创建模拟的ARMS客户端"""
    return Mock()

@pytest.fixture(scope="session")
def mock_context(mock_sls_client, mock_arms_client):
    """创建模拟的Context实例"""
    context = Mock(spec=Context)
    context.request_context = Mock()
    context.request_context.lifespan_context = {
        "sls_client": mock_sls_client,
        "arms_client": mock_arms_client
    }
    return context

@pytest.fixture(scope="session")
def mock_server():
    """创建模拟的FastMCP服务器实例"""
    return Mock(spec=FastMCP) 