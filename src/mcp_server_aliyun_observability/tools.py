# 在 src/mcp_server_aliyun_observability/tools.py 中创建 ToolManager 类

from datetime import datetime
from typing import Any, Dict, List

from alibabacloud_sls20201230.client import Client
from alibabacloud_sls20201230.models import (
    CallAiToolsRequest,
    CallAiToolsResponse,
    GetIndexResponse,
    GetIndexResponseBody,
    GetLogsRequest,
    GetLogsResponse,
    IndexKey,
    ListAllProjectsRequest,
    ListAllProjectsResponse,
    ListLogStoresRequest,
    ListLogStoresResponse,
)
from alibabacloud_tea_util import models as util_models
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

from mcp_server_aliyun_observability.utils import parse_json_keys


class ToolManager:
    """aliyun observability tools manager"""

    def __init__(self, server: FastMCP):
        """
        initialize the tools manager

        Args:
            server: FastMCP server instance
        """
        self.server = server
        self._register_tools()

    def _register_tools(self):
        """register all tools functions to the FastMCP server"""
        self._register_sls_tools()
        self._register_common_tools()

    def _register_sls_tools(self):
        """register sls related tools functions"""

        @self.server.tool()
        def sls_list_projects(
            ctx: Context,
            project_name_query: str = Field(
                None, description="project name,fuzzy search"
            ),
            region_id: str = Field(..., description="region id"),
            content: str = Field(
                ..., description="content,the content of the chat history"
            ),
            limit: int = Field(10, description="limit,max is 100", ge=1, le=100),
        ) -> list[dict[str, Any]]:
            """
            list all projects in the region,support fuzzy search by project name, if you don't provide the project name,the tool will return all projects in the region
            """
            sls_client: Client = ctx.request_context.lifespan_context[
                "sls_client"
            ].with_region(region_id)
            request: ListAllProjectsRequest = ListAllProjectsRequest(
                project_name=project_name_query,
                region_id=region_id,
                size=limit,
            )
            response: ListAllProjectsResponse = sls_client.list_all_projects(request)
            return [
                {
                    "project_name": project.project_name,
                    "description": project.description,
                }
                for project in response.body.projects
            ]

        @self.server.tool()
        def sls_list_logstores(
            ctx: Context,
            project: str = Field(..., description="sls project name"),
            region_id: str = Field(..., description="region id"),
            log_store: str = Field(None, description="log store name,fuzzy search"),
            limit: int = Field(10, description="limit,max is 100", ge=1, le=100),
            log_store_type: str = Field(
                None,
                description="log store type,default is logs,should be logs,metrics",
            ),
        ) -> list[str]:
            """
            list all log stores in the project,support fuzzy search by log store name, if you don't provide the log store name,the tool will return all log stores in the project
            """
            sls_client: Client = ctx.request_context.lifespan_context[
                "sls_client"
            ].with_region(region_id)
            request: ListLogStoresRequest = ListLogStoresRequest(
                logstore_name=log_store,
                size=limit,
                telemetry_type=log_store_type,
            )
            response: ListLogStoresResponse = sls_client.list_log_stores(
                project, request
            )
            return response.body.logstores

        @self.server.tool()
        def sls_describe_logstore(
            ctx: Context,
            project: str = Field(..., description="sls project name"),
            log_store: str = Field(..., description="sls log store name"),
            region_id: str = Field(..., description="region id"),
        ) -> dict:
            """
            describe the log store schema or index info
            """
            sls_client: Client = ctx.request_context.lifespan_context[
                "sls_client"
            ].with_region(region_id)
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

        @self.server.tool()
        def sls_execute_query(
            ctx: Context,
            project: str = Field(..., description="sls project name"),
            log_store: str = Field(..., description="sls log store name"),
            region_id: str = Field(..., description="region id"),
            query: str = Field(..., description="query"),
            from_timestamp: int = Field(
                ..., description="from timestamp,unit is second"
            ),
            to_timestamp: int = Field(..., description="to timestamp,unit is second"),
            limit: int = Field(10, description="limit,max is 100", ge=1, le=100),
        ) -> dict:
            """
            1. execute the sls query on the log store
            2. the tool will return the query result
            3. if you don't konw the log store schema,you can use the get_log_store_index tool to get the index of the log store
            """
            sls_client: Client = ctx.request_context.lifespan_context[
                "sls_client"
            ].with_region(region_id)
            request: GetLogsRequest = GetLogsRequest(
                query=query,
                from_=from_timestamp,
                to=to_timestamp,
                line=limit,
            )
            response: GetLogsResponse = sls_client.get_logs(project, log_store, request)
            response_body: List[Dict[str, Any]] = response.body
            return response_body

        @self.server.tool()
        def sls_text_to_query(
            ctx: Context,
            text: str = Field(
                ...,
                description="the natural language text to generate sls log store query",
            ),
            region_id: str = Field(..., description="region id"),
            project: str = Field(..., description="sls project name"),
            log_store: str = Field(..., description="sls log store name"),
        ) -> str:
            """
            1.Can translate the natural language text to sls query, can use to generate sls query from natural language on log store search
            """
            sls_client: Client = ctx.request_context.lifespan_context[
                "sls_client"
            ].with_region(
                region_id, endpoint="pub-cn-hangzhou-staging-share.log.aliyuncs.com"
            )
            request: CallAiToolsRequest = CallAiToolsRequest()
            request.tool_name = "text_to_sql"
            request.region_id = region_id
            params: dict[str, Any] = {
                "project": project,
                "logstore": log_store,
                "sys.query": text,
            }
            request.params = params
            runtime: util_models.RuntimeOptions = util_models.RuntimeOptions()
            runtime.read_timeout = 60000
            runtime.connect_timeout = 60000
            tool_response: CallAiToolsResponse = sls_client.call_ai_tools_with_options(
                request=request, headers={}, runtime=runtime
            )
            data = tool_response.body
            if "------answer------\n" in data:
                data = data.split("------answer------\n")[1]
            return data

    def _register_common_tools(self):
        """register common tools functions"""

        @self.server.tool()
        def list_all_regions(ctx: Context) -> str:
            """
            1. Sample some regions,not all regions
            """
            try:
                return {
                    "cn-hangzhou": "杭州",
                    "cn-beijing": "北京",
                    "cn-shanghai": "上海",
                    "cn-shenzhen": "深圳",
                    "cn-qingdao": "青岛",
                    "cn-guangzhou": "广州",
                    "cn-zhangjiakou": "张家口",
                }
            except Exception as e:
                print(f"get regions list failed: {str(e)}")
                return {}
