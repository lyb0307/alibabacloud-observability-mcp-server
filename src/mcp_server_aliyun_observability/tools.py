# 在 src/mcp_server_aliyun_observability/tools.py 中创建 ToolManager 类

import logging
from datetime import datetime
from typing import Any, Dict, List

from alibabacloud_arms20190808.client import Client as ArmsClient
from alibabacloud_arms20190808.models import (
    SearchTraceAppByPageRequest,
    SearchTraceAppByPageResponse,
    SearchTraceAppByPageResponseBodyPageBean,
)
from alibabacloud_sls20201230.client import Client
from alibabacloud_sls20201230.models import (
    CallAiToolsRequest,
    CallAiToolsResponse,
    GetIndexResponse,
    GetIndexResponseBody,
    GetLogsRequest,
    GetLogsResponse,
    GetProjectResponse,
    IndexKey,
    ListLogStoresRequest,
    ListLogStoresResponse,
    ListProjectRequest,
    ListProjectResponse,
)
from alibabacloud_tea_util import models as util_models
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from mcp_server_aliyun_observability.utils import (
    get_arms_user_trace_log_store,
    parse_json_keys,
)

# 配置日志
logger = logging.getLogger(__name__)


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
        self._register_arms_tools()

    def _register_sls_tools(self):
        """register sls related tools functions"""

        @self.server.tool()
        def sls_list_projects(
            ctx: Context,
            project_name_query: str = Field(
                None, description="project name,fuzzy search"
            ),
            limit: int = Field(
                default=10, description="limit,max is 100", ge=1, le=100
            ),
            region_id: str = Field(default=..., description="aliyun region id"),
        ) -> list[dict[str, Any]]:
            """
            list all projects in the region,support fuzzy search by project name, if you don't provide the project name,the tool will return all projects in the region
            instructions:
            1. you can use this tool to answer the question
                1. like "有没有叫 XXX 的 project"
            """
            sls_client: Client = ctx.request_context.lifespan_context[
                "sls_client"
            ].with_region(region_id)
            request: ListProjectRequest = ListProjectRequest(
                project_name=project_name_query,
                size=limit,
            )
            response: ListProjectResponse = sls_client.list_project(request)
            return [
                {
                    "project_name": project.project_name,
                    "description": project.description,
                    "region_id": project.region,
                }
                for project in response.body.projects
            ]

        @self.server.tool()
        @retry(
            stop=stop_after_attempt(2),
            wait=wait_fixed(1),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        def sls_list_logstores(
            ctx: Context,
            project: str = Field(..., description="sls project name,must exact match"),
            log_store: str = Field(None, description="log store name,fuzzy search"),
            limit: int = Field(10, description="limit,max is 100", ge=1, le=100),
            log_store_type: str = Field(
                None,
                description="log store type,default is logs,should be logs,metrics",
            ),
            region_id: str = Field(default=..., description="aliyun region id"),
        ) -> list[str]:
            """
            1. list all log stores in the project,support fuzzy search by log store name, if you don't provide the log store name,the tool will return all log stores in the project
            instructions:
            1. you can use this tool to answer the question
                1. like "我想查询有没有 XXX 的日志库"
                2. like "某个 project 有哪些 log store"
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
        @retry(
            stop=stop_after_attempt(2),
            wait=wait_fixed(1),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        def sls_describe_logstore(
            ctx: Context,
            project: str = Field(
                ..., description="sls project name,must exact match,not fuzzy search"
            ),
            log_store: str = Field(
                ..., description="sls log store name,must exact match,not fuzzy search"
            ),
            region_id: str = Field(default=..., description="aliyun region id"),
        ) -> dict:
            """
            describe the log store schema or index info
            instructions:
            1. you can use this tool to answer the question
                1. like "我想查询 XXX 的日志库的 schema"
                2. like "我想查询 XXX 的日志库的 index"
                3. like "我想查询 XXX 的日志库的 结构信息"
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
        @retry(
            stop=stop_after_attempt(2),
            wait=wait_fixed(1),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        def sls_execute_query(
            ctx: Context,
            project: str = Field(..., description="sls project name"),
            log_store: str = Field(..., description="sls log store name"),
            query: str = Field(..., description="query"),
            from_timestamp: int = Field(
                ..., description="from timestamp,unit is second"
            ),
            to_timestamp: int = Field(..., description="to timestamp,unit is second"),
            limit: int = Field(10, description="limit,max is 100", ge=1, le=100),
            region_id: str = Field(default=..., description="aliyun region id"),
        ) -> dict:
            """
            1. execute the sls query on the log store
            2. the tool will return the query result
            3. if you don't konw the log store schema,you can use the get_log_store_index tool to get the index of the log store
            <important>
            1. you can use this tool to answer the question
                1. like "帮我查询下 XXX 的日志信息"
            2. the query should be a sls valid query,not a natural language text
            </important>
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
            runtime: util_models.RuntimeOptions = util_models.RuntimeOptions()
            runtime.read_timeout = 60000
            runtime.connect_timeout = 60000
            response: GetLogsResponse = sls_client.get_logs_with_options(
                project, log_store, request, headers={}, runtime=runtime
            )
            response_body: List[Dict[str, Any]] = response.body
            return response_body

        @self.server.tool()
        @retry(
            stop=stop_after_attempt(2),
            wait=wait_fixed(1),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        def sls_translate_natural_language_to_query(
            ctx: Context,
            text: str = Field(
                ...,
                description="the natural language text to generate sls log store query",
            ),
            project: str = Field(..., description="sls project name"),
            log_store: str = Field(..., description="sls log store name"),
            region_id: str = Field(default=..., description="aliyun region id"),
        ) -> str:
            """
            Can translate the natural language text to sls query or sql, can use to generate sls query or sql from natural language on log store search
            <important>
            1. you can only answer the question about generate sls query,not commond db sql like mysql,postgresql,elasticsearch,etc.
            2. you return the sls query,not the query result ,should use the sls_execute_query tool to get the query result
            3. if user question about arms application,you should use the arms_generate_trace_query tool first
            4. you can use this tool to answer the question
                1. like "帮我生成下 XXX 的日志查询语句"
            5. the text should be a natural language text,must be clear and concise,you can ask user to provide more information if you need
            6. the text should not include project or log store name
            7. you can ask user to provide query time range,if you need
            8. the query result you generate maybe not execute success at first time,you should try to generate the query again,and ask the user to provide more information about the error
            </important>
            """
            return text_to_sql(ctx, text, project, log_store, region_id)

    def _register_arms_tools(self):
        """register arms related tools functions"""

        @self.server.tool()
        def arms_search_apps(
            ctx: Context,
            app_name_query: str = Field(..., description="app name query"),
            region_id: str = Field(..., description="region id"),
            page_size: int = Field(
                20, description="page size,max is 100", ge=1, le=100
            ),
            page_number: int = Field(1, description="page number,default is 1", ge=1),
        ) -> list[dict[str, Any]]:
            """
            search the arms app by app name
            1. app_name_query is required,and should be part of the app name
            2. the tool will return the app name,pid,type
            3. the pid is unique id of the app,can be used to other arms tools
            <important>
            1. you can use this tool to answer the question
                1. like "帮我查询下 XXX 的应用"
            2. the app_name_query should be a part of the app name,not a natural language text
            3. the tool will return the app name,pid,type
            4. if the question about the arms app,you should use this tool to get the app info
            </important>
            """
            arms_client: ArmsClient = ctx.request_context.lifespan_context[
                "arms_client"
            ].with_region(region_id)
            request: SearchTraceAppByPageRequest = SearchTraceAppByPageRequest(
                trace_app_name=app_name_query,
                region_id=region_id,
                page_size=page_size,
                page_number=page_number,
            )
            response: SearchTraceAppByPageResponse = (
                arms_client.search_trace_app_by_page(request)
            )
            page_bean: SearchTraceAppByPageResponseBodyPageBean = (
                response.body.page_bean
            )
            result = {
                "total": page_bean.total_count,
                "page_size": page_bean.page_size,
                "page_number": page_bean.page_number,
                "trace_apps": [],
            }
            if page_bean:
                result["trace_apps"] = [
                    {
                        "app_name": app.app_name,
                        "pid": app.pid,
                        "user_id": app.user_id,
                        "type": app.type,
                    }
                    for app in page_bean.trace_apps
                ]

            return result

        @self.server.tool()
        @retry(
            stop=stop_after_attempt(2),
            wait=wait_fixed(1),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        def arms_generate_trace_query(
            ctx: Context,
            user_id: int = Field(..., description="user aliyun account id"),
            pid: str = Field(..., description="pid,the pid of the app"),
            region_id: str = Field(..., description="region id"),
            question: str = Field(
                ..., description="question,the question to query the trace"
            ),
        ) -> dict:
            """
            Generate the trace query by the natural language tex,you should use this tool to answer any question about application trace query,if you find any application info from context
            <important>
            1. you can use this tool to answer the question
                1. like "帮我查询下 XXX 的 trace 信息"
            2. the question should be a natural language text,must be clear and concise,you can ask user to provide more information if you need
            3. you can answer the arms application trace info query,if abount trace query,you should use this tool to generate the trace query,not the sls_translate_natural_language_to_query tool
            4. you just generate the trace query,not the query result,you should use the sls_execute_query tool to get the query result
            </important>
            """

            data: dict[str, str] = get_arms_user_trace_log_store(user_id, region_id)
            instructions = [
                "1. pid为" + pid,
                "2. 响应时间字段为 duration,单位为纳秒，转换成毫秒",
                "3. 注意因为保存的是每个 span 记录,如果是耗时，需要对所有符合条件的span 耗时做求和",
                "4. 涉及到接口服务等字段,使用 serviceName字段",
            ]
            instructions_str = "\n".join(instructions)
            prompt = f"""
            问题:
            {question}
            补充信息:
            {instructions_str}
            请根据以上信息生成sls查询语句
            """
            sls_text_to_query = text_to_sql(
                ctx, prompt, data["project"], data["log_store"], region_id
            )
            return {
                "sls_query": sls_text_to_query,
                "project": data["project"],
                "log_store": data["log_store"],
            }

    def _register_common_tools(self):
        """register common tools functions"""

        @self.server.tool()
        def sls_get_current_time(ctx: Context) -> dict:
            """
            Get the current time for execute the sls query
            """
            return {
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "current_timestamp": int(datetime.now().timestamp()),
            }


@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(1),
    retry=retry_if_exception_type(Exception),
    reraise=True,
    before_sleep=lambda retry_state: logger.warning(
        f"调用SLS AI工具失败，正在重试第{retry_state.attempt_number}次... 异常: {retry_state.outcome.exception()}"
    ),
)
def text_to_sql(
    ctx: Context, text: str, project: str, log_store: str, region_id: str
) -> str:
    try:
        sls_client: Client = ctx.request_context.lifespan_context[
            "sls_client"
        ].with_region("cn-shanghai")
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
    except Exception as e:
        logger.error(f"调用SLS AI工具失败: {str(e)}")
        raise  # 重新抛出异常以触发重试机制
