from typing import Any, Dict, List

from alibabacloud_sls20201230.client import Client
from alibabacloud_sls20201230.models import (
    GetIndexResponse,
    GetIndexResponseBody,
    GetLogsRequest,
    GetLogsResponse,
    IndexJsonKey,
    IndexKey,
)
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from toolloader import ToolConfig, tool

"""
get_log_store_index
"""


@tool()
def get_log_store_index(
    ctx: Context,
    project: str = Field(..., description="sls project name"),
    log_store: str = Field(..., description="sls log store name"),
    region_id: str = Field(..., description="region id"),
) -> dict:
    """
    get the index of the log store
    """
    sls_client: Client = ctx.request_context.lifespan_context["sls_client"].with_region(
        region_id
    )
    response: GetIndexResponse = sls_client.get_index(project, log_store)
    response_body: GetIndexResponseBody = response.body
    keys: dict[str, IndexKey] = response_body.keys
    index_dict: dict[str, dict[str, str]] = {}
    for key, value in keys.items():
        index_dict[key] = {
            "alias": value.alias,
            "sensitive": value.case_sensitive,
            "type": value.type,
            "json_keys": parse_json_keys(value.json_keys),
        }
    return index_dict


@tool()
def execute_sls_query(
    ctx: Context,
    project: str = Field(..., description="sls project name"),
    log_store: str = Field(..., description="sls log store name"),
    region_id: str = Field(..., description="region id"),
    query: str = Field(..., description="query"),
    from_timestamp: int = Field(..., description="from timestamp,unit is second"),
    to_timestamp: int = Field(..., description="to timestamp,unit is second"),
    limit: int = Field(..., description="limit,max is 100", ge=1, le=100),
) -> dict:
    sls_client: Client = ctx.request_context.lifespan_context["sls_client"].with_region(
        region_id
    )
    ##如果是毫秒，则转换为秒
    request: GetLogsRequest = GetLogsRequest(
        query=query,
        from_=from_timestamp,
        to=to_timestamp,
        line=limit,
    )
    response: GetLogsResponse = sls_client.get_logs(project, log_store, request)
    response_body: List[Dict[str, Any]] = response.body
    return response_body


def parse_json_keys(json_keys: dict[str, IndexJsonKey]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for key, value in json_keys.items():
        result[key] = {
            "alias": value.alias,
            "sensitive": value.case_sensitive,
            "type": value.type,
        }
    return result
