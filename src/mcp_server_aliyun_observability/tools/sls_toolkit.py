from typing import Any, Dict, List

from alibabacloud_sls20201230.client import Client
from alibabacloud_sls20201230.models import (
    CallAiToolsRequest,
    CallAiToolsResponse,
    GetIndexResponse,
    GetIndexResponseBody,
    GetLogsRequest,
    GetLogsResponse,
    IndexJsonKey,
    IndexKey,
)
from alibabacloud_tea_openapi import models as open_api_models
from mcp.server.fastmcp import Context
from mcp.types import TextContent
from pydantic import Field
from toolloader import ToolConfig, tool

"""
get_log_store_index
"""


@tool()
def get_log_store_schema(
    ctx: Context,
    project: str = Field(..., description="sls project name"),
    log_store: str = Field(..., description="sls log store name"),
    region_id: str = Field(..., description="region id"),
) -> dict:
    """
    get the index of the log store,which is the schema of the log store
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
    """
    1. execute the sls query on the log store
    2. the tool will return the query result
    3. if you don't konw the log store schema,you can use the get_log_store_index tool to get the index of the log store
    """
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


@tool()
def text_to_sls_query(
    ctx: Context,
    text: str = Field(
        ..., description="the natural language text to generate sls query"
    ),
    region_id: str = Field(..., description="region id"),
    project: str = Field(..., description="sls project name"),
    log_store: str = Field(..., description="sls log store name"),
) -> str:
    """
    1. Convert the natural language text to sls query, can use to generate sls query from natural language on log store search
    2. please note the tool not support cms query generation,only support sls query generation
    3. the tool will return the sls query string, you can use the execute_sls_query tool to execute the query
    """
    sls_client: Client = ctx.request_context.lifespan_context["sls_client"].with_region(
        region_id
    )
    request: CallAiToolsRequest = CallAiToolsRequest()
    request.tool_name = "text_to_sql"
    request.region_id = region_id
    params: dict[str, Any] = {
        "project": project,
        "log_store": log_store,
        "sys.query": text,
    }
    request.params = params
    tool_response: CallAiToolsResponse = sls_client.call_ai_tools(request)
    data = tool_response.body
    """
     "------response------\n{\n  \"type\":\"sql\",\n  \"answer\": \"${answer}\",\n  \"nextActions\": [],\n  \"scene_sql\":\"${sql}\",\n  \"scene_message\":\"${message}\",\n  \"scene_from_time\":\"${from_time}\",\n  \"scene_to_time\":\"${to_time}\"\n}\n------answer------\n此查询执行以下步骤：<br>1. 筛选出主题为'oss_access_log'且桶(bucket)为'hgame-va'的日志。<br>2. 按天对齐时间字段，并按client_ip分组。<br>3. 计算每天每个client_ip的数量。<br>4. 按天和ip_num降序排序。<br>注意，SLS默认限制输出结果100行，您可以通过添加LIMIT N来限制最大结果行数。\n------sql------\n* | SELECT date_trunc('day', __time__) AS day, client_ip, COUNT(client_ip) AS ip_num FROM log WHERE __topic__ = 'oss_access_log' AND bucket = 'hgame-va' GROUP BY day, client_ip ORDER BY day, ip_num DESC\n------message------\n此查询执行以下步骤：<br>1. 筛选出主题为'oss_access_log'且桶(bucket)为'hgame-va'的日志。<br>2. 按天对齐时间字段，并按client_ip分组。<br>3. 计算每天每个client_ip的数量。<br>4. 按天和ip_num降序排序。<br>注意，SLS默认限制输出结果100行，您可以通过添加LIMIT N来限制最大结果行数。\n------from_time------\n1742806350\n------to_time------\n1742807250\n------end------"
    """
    if "------answer------\n" in data:
        data = data.split("------answer------\n")[1]
    return data
