from alibabacloud_cms20240330.client import Client
from alibabacloud_cms20240330.models import (
    GetEntityStoreDataRequest,
    GetEntityStoreDataResponse,
    GetEntityStoreDataResponseBody,
    GetEntityStoreResponseBody,
    ListWorkspacesRequest,
    ListWorkspacesResponse,
    ListWorkspacesResponseBody,
    ListWorkspacesResponseBodyWorkspaces,
)
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from toolloader import tool

"""
get user workspace
"""


@tool()
def list_user_workspaces(
    ctx: Context, region_id: str = Field(..., description="region id")
) -> list[str]:
    """
    list all workspaces of the user
    """
    try:
        request = ListWorkspacesRequest(region=region_id)
        cms_client: Client = ctx.request_context.lifespan_context[
            "cms_client"
        ].with_region(region_id)
        response: ListWorkspacesResponse = cms_client.list_workspaces(request)
        workspaces: ListWorkspacesResponseBodyWorkspaces = response.body.workspaces
        workspace_list: list[str] = []
        for workspace in workspaces:
            workspace_list.append(workspace.workspace_name)
        return workspace_list
    except Exception as e:
        return f"获取工作空间列表失败: {str(e)}"


@tool()
def execute_cms_query(
    ctx: Context,
    workspace_name: str = Field(..., description="workspace name"),
    from_timestamp: int = Field(
        ..., description="from timestamp,should be unix timestamp seconds"
    ),
    to_timestamp: int = Field(
        ..., description="to timestamp,should be unix timestamp seconds"
    ),
    query: str = Field(..., description="query"),
    region_id: str = Field(..., description="region id"),
) -> str:
    """
    Execute cms query
    Args:
        workspace_name: str = Field(..., description="workspace name"),
        from_timestamp: int = Field(..., description="from timestamp,should be unix timestamp seconds"),
        to_timestamp: int = Field(..., description="to timestamp,should be unix timestamp seconds"),
        query: str = Field(..., description="query"),
    """
    try:
        request = GetEntityStoreDataRequest(
            workspace_name=workspace_name,
            from_=from_timestamp,
            to=to_timestamp,
            query=query,
        )
        cms_client: Client = ctx.request_context.lifespan_context[
            "cms_client"
        ].with_region(region_id)
        response: GetEntityStoreDataResponse = cms_client.get_entity_store_data(
            workspace=workspace_name, request=request
        )
        body: GetEntityStoreDataResponseBody = response.body
        return format_entity_data_to_text(body)
    except Exception as e:
        return f"执行cms查询失败,错误信息: {str(e)}"


def format_entity_data_to_text(data: GetEntityStoreDataResponseBody) -> str:
    """将 entity store 数据转换为易读的文本格式

    Args:
        data: 包含 header 和 data 的字典

    Returns:
        格式化后的文本
    """
    data = data.to_map()
    print(f"data: {data}")
    if not data or "header" not in data or "data" not in data:
        return "数据格式错误或为空"

    headers = data["header"]
    rows = data["data"]

    if not headers or not rows:
        return "数据为空"

    # 计算每列的最大宽度（考虑中文字符）
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                # 考虑中文字符宽度
                cell_width = sum(2 if ord(c) > 127 else 1 for c in str(cell))
                col_widths[i] = max(col_widths[i], cell_width)

    # 生成表头
    header_line = " | ".join(
        str(headers[i]).ljust(col_widths[i]) for i in range(len(headers))
    )
    separator = "-" * len(header_line)

    # 生成数据行
    result = [header_line, separator]
    for row in rows:
        row_str = " | ".join(
            str(row[i]).ljust(col_widths[i]) for i in range(min(len(row), len(headers)))
        )
        result.append(row_str)

    return "\n".join(result)


def format_entity_data_to_text(data: GetEntityStoreDataResponseBody) -> str:
    """将 entity store 数据转换为易读的文本格式

    Args:
        data: 包含 header 和 data 的字典

    Returns:
        格式化后的文本
    """
    data = data.to_map()
    print(f"data: {data}")
    if not data or "header" not in data or "data" not in data:
        return "数据格式错误或为空"

    headers = data["header"]
    rows = data["data"]

    if not headers or not rows:
        return "数据为空"

    # 计算每列的最大宽度（考虑中文字符）
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                # 考虑中文字符宽度
                cell_width = sum(2 if ord(c) > 127 else 1 for c in str(cell))
                col_widths[i] = max(col_widths[i], cell_width)

    # 生成表头
    header_line = " | ".join(
        str(headers[i]).ljust(col_widths[i]) for i in range(len(headers))
    )
    separator = "-" * len(header_line)

    # 生成数据行
    result = [header_line, separator]
    for row in rows:
        row_str = " | ".join(
            str(row[i]).ljust(col_widths[i]) for i in range(min(len(row), len(headers)))
        )
        result.append(row_str)

    return "\n".join(result)
