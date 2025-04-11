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
from Tea.exceptions import TeaException
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from mcp_server_aliyun_observability.utils import (
    get_arms_user_trace_log_store,
    handle_tea_exception,
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
            """列出阿里云日志服务中的所有项目。

            ## 功能概述

            该工具可以列出指定区域中的所有SLS项目，支持通过项目名进行模糊搜索。如果不提供项目名称，则返回该区域的所有项目。

            ## 使用场景

            - 当需要查找特定项目是否存在时
            - 当需要获取某个区域下所有可用的SLS项目列表时
            - 当需要根据项目名称的部分内容查找相关项目时

            ## 返回数据结构

            返回的项目信息包含：
            - project_name: 项目名称
            - description: 项目描述
            - region_id: 项目所在区域

            ## 查询示例

            - "有没有叫 XXX 的 project"
            - "列出所有SLS项目"

            Args:
                ctx: MCP上下文，用于访问SLS客户端
                project_name_query: 项目名称查询字符串，支持模糊搜索
                limit: 返回结果的最大数量，范围1-100，默认10
                region_id: 阿里云区域ID,region id format like "xx-xxx",like "cn-hangzhou"

            Returns:
                包含项目信息的字典列表，每个字典包含project_name、description和region_id
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
            region_id: str = Field(
                default=...,
                description="aliyun region id,region id format like 'xx-xxx',like 'cn-hangzhou'",
            ),
        ) -> list[str]:
            """列出SLS项目中的日志库。

            ## 功能概述

            该工具可以列出指定SLS项目中的所有日志库，支持通过日志库名称进行模糊搜索。如果不提供日志库名称，则返回项目中的所有日志库。

            ## 使用场景

            - 当需要查找特定项目下是否存在某个日志库时
            - 当需要获取项目中所有可用的日志库列表时
            - 当需要根据日志库名称的部分内容查找相关日志库时

            ## 数据类型筛选

            可以通过指定log_store_type参数来筛选日志库类型：
            - logs: 普通日志类型日志库
            - metrics: 指标类型日志库

            ## 查询示例

            - "我想查询有没有 XXX 的日志库"
            - "某个 project 有哪些 log store"

            Args:
                ctx: MCP上下文，用于访问SLS客户端
                project: SLS项目名称，必须精确匹配
                log_store: 日志库名称，支持模糊搜索
                limit: 返回结果的最大数量，范围1-100，默认10
                log_store_type: 日志库类型，可选值为logs或metrics，默认为logs
                region_id: 阿里云区域ID

            Returns:
                日志库名称的字符串列表
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
            return {
                "total": response.body.total,
                "logstores": response.body.logstores,
            }

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
            region_id: str = Field(
                default=...,
                description="aliyun region id,region id format like 'xx-xxx',like 'cn-hangzhou'",
            ),
        ) -> dict:
            """获取SLS日志库的结构信息。

            ## 功能概述

            该工具用于获取指定SLS项目中日志库的索引信息和结构定义，包括字段类型、别名、是否大小写敏感等信息。

            ## 使用场景

            - 当需要了解日志库的字段结构时
            - 当需要获取日志库的索引配置信息时
            - 当构建查询语句前需要了解可用字段时
            - 当需要分析日志数据结构时

            ## 返回数据结构

            返回一个字典，键为字段名，值包含以下信息：
            - alias: 字段别名
            - sensitive: 是否大小写敏感
            - type: 字段类型
            - json_keys: JSON字段的子字段信息

            ## 查询示例

            - "我想查询 XXX 的日志库的 schema"
            - "我想查询 XXX 的日志库的 index"
            - "我想查询 XXX 的日志库的结构信息"

            Args:
                ctx: MCP上下文，用于访问SLS客户端
                project: SLS项目名称，必须精确匹配
                log_store: SLS日志库名称，必须精确匹配
                region_id: 阿里云区域ID

            Returns:
                包含日志库结构信息的字典
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
        @handle_tea_exception
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
            region_id: str = Field(
                default=...,
                description="aliyun region id,region id format like 'xx-xxx',like 'cn-hangzhou'",
            ),
        ) -> dict:
            """执行SLS日志查询。

            ## 功能概述

            该工具用于在指定的SLS项目和日志库上执行查询语句，并返回查询结果。查询将在指定的时间范围内执行。

            ## 使用场景

            - 当需要根据特定条件查询日志数据时
            - 当需要分析特定时间范围内的日志信息时
            - 当需要检索日志中的特定事件或错误时
            - 当需要统计日志数据的聚合信息时



            ## 查询语法

            查询必须使用SLS有效的查询语法，而非自然语言。如果不了解日志库的结构，可以先使用sls_describe_logstore工具获取索引信息。

            ## 时间范围

            查询必须指定时间范围：
            - from_timestamp: 开始时间戳（秒）
            - to_timestamp: 结束时间戳（秒）

            ## 查询示例

            - "帮我查询下 XXX 的日志信息"
            - "查找最近一小时内的错误日志"

            ## 错误处理
            - Column xxx can not be resolved 如果是 sls_translate_natural_language_to_query 工具生成的查询语句 可能存在查询列未开启统计，可以提示用户增加相对应的信息，或者调用 sls_describe_logstore 工具获取索引信息之后，要用户选择正确的字段或者提示用户对列开启统计。当确定列开启统计之后，可以再次调用sls_translate_natural_language_to_query 工具生成查询语句

            Args:
                ctx: MCP上下文，用于访问SLS客户端
                project: SLS项目名称
                log_store: SLS日志库名称
                query: SLS查询语句
                from_timestamp: 查询开始时间戳（秒）
                to_timestamp: 查询结束时间戳（秒）
                limit: 返回结果的最大数量，范围1-100，默认10
                region_id: 阿里云区域ID

            Returns:
                查询结果列表，每个元素为一条日志记录
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
            result = {
                "data": response_body,
                "message": "success"
                if response_body
                else "Not found data by query,you can try to change the query or time range",
            }
            return result

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
            region_id: str = Field(
                default=...,
                description="aliyun region id,region id format like 'xx-xxx',like 'cn-hangzhou'",
            ),
        ) -> str:
            """将自然语言转换为SLS查询语句。

            ## 功能概述

            该工具可以将自然语言描述转换为有效的SLS查询语句，便于用户使用自然语言表达查询需求。

            ## 使用场景

            - 当用户不熟悉SLS查询语法时
            - 当需要快速构建复杂查询时
            - 当需要从自然语言描述中提取查询意图时

            ## 使用限制

            - 仅支持生成SLS查询，不支持其他数据库的SQL如MySQL、PostgreSQL等
            - 生成的是查询语句，而非查询结果，需要配合sls_execute_query工具使用
            - 如果查询涉及ARMS应用，应优先使用arms_generate_trace_query工具
            - 需要对应的 log_sotre 已经设定了索引信息，如果生成的结果里面有字段没有索引或者开启统计，可能会导致查询失败，需要友好的提示用户增加相对应的索引信息

            ## 最佳实践

            - 提供清晰简洁的自然语言描述
            - 不要在描述中包含项目或日志库名称
            - 如有需要，指定查询的时间范围
            - 首次生成的查询可能不完全符合要求，可能需要多次尝试

            ## 查询示例

            - "帮我生成下 XXX 的日志查询语句"
            - "查找最近一小时内的错误日志"

            Args:
                ctx: MCP上下文，用于访问SLS客户端
                text: 用于生成查询的自然语言文本
                project: SLS项目名称
                log_store: SLS日志库名称
                region_id: 阿里云区域ID

            Returns:
                生成的SLS查询语句
            """
            return text_to_sql(ctx, text, project, log_store, region_id)

    def _register_arms_tools(self):
        """register arms related tools functions"""

        @self.server.tool()
        def arms_search_apps(
            ctx: Context,
            app_name_query: str = Field(..., description="app name query"),
            region_id: str = Field(
                ...,
                description="region id,region id format like 'xx-xxx',like 'cn-hangzhou'",
            ),
            page_size: int = Field(
                20, description="page size,max is 100", ge=1, le=100
            ),
            page_number: int = Field(1, description="page number,default is 1", ge=1),
        ) -> list[dict[str, Any]]:
            """搜索ARMS应用。

            ## 功能概述

            该工具用于根据应用名称搜索ARMS应用，返回应用的基本信息，包括应用名称、PID、用户ID和类型。

            ## 使用场景

            - 当需要查找特定名称的应用时
            - 当需要获取应用的PID以便进行其他ARMS操作时
            - 当需要检查用户拥有的应用列表时

            ## 搜索条件

            - app_name_query必须是应用名称的一部分，而非自然语言
            - 搜索结果将分页返回，可以指定页码和每页大小

            ## 返回数据结构

            返回一个字典，包含以下信息：
            - total: 符合条件的应用总数
            - page_size: 每页大小
            - page_number: 当前页码
            - trace_apps: 应用列表，每个应用包含app_name、pid、user_id和type

            ## 查询示例

            - "帮我查询下 XXX 的应用"
            - "找出名称包含'service'的应用"

            Args:
                ctx: MCP上下文，用于访问ARMS客户端
                app_name_query: 应用名称查询字符串
                region_id: 阿里云区域ID
                page_size: 每页大小，范围1-100，默认20
                page_number: 页码，默认1

            Returns:
                包含应用信息的字典
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
            region_id: str = Field(
                ...,
                description="region id,region id format like 'xx-xxx',like 'cn-hangzhou'",
            ),
            question: str = Field(
                ..., description="question,the question to query the trace"
            ),
        ) -> dict:
            """生成ARMS应用的调用链查询语句。

            ## 功能概述

            该工具用于将自然语言描述转换为ARMS调用链查询语句，便于分析应用性能和问题。

            ## 使用场景

            - 当需要查询应用的调用链信息时
            - 当需要分析应用性能问题时
            - 当需要跟踪特定请求的执行路径时
            - 当需要分析服务间调用关系时

            ## 查询处理

            工具会将自然语言问题转换为SLS查询，并返回：
            - 生成的SLS查询语句
            - 存储调用链数据的项目名
            - 存储调用链数据的日志库名

            ## 查询上下文

            查询会考虑以下信息：
            - 应用的PID
            - 响应时间以纳秒存储，需转换为毫秒
            - 数据以span记录存储，查询耗时需要对符合条件的span进行求和
            - 服务相关信息使用serviceName字段
            - 如果用户明确提出要查询 trace信息，则需要在查询问题上question 上添加说明返回trace信息

            ## 查询示例

            - "帮我查询下 XXX 的 trace 信息"
            - "分析最近一小时内响应时间超过1秒的调用链"

            Args:
                ctx: MCP上下文，用于访问ARMS和SLS客户端
                user_id: 用户阿里云账号ID
                pid: 应用的PID
                region_id: 阿里云区域ID
                question: 查询调用链的自然语言问题

            Returns:
                包含查询信息的字典，包括sls_query、project和log_store
            """

            data: dict[str, str] = get_arms_user_trace_log_store(user_id, region_id)
            instructions = [
                "1. pid为" + pid,
                "2. 响应时间字段为 duration,单位为纳秒，转换成毫秒",
                "3. 注意因为保存的是每个 span 记录,如果是耗时，需要对所有符合条件的span 耗时做求和",
                "4. 涉及到接口服务等字段,使用 serviceName字段",
                "5. 如果用户明确提出要查询 trace信息，则需要返回 trace_id",
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
            """获取当前时间信息。

            ## 功能概述

            该工具用于获取当前的时间戳和格式化的时间字符串，便于在执行SLS查询时指定时间范围。

            ## 使用场景

            - 当需要获取当前时间以设置查询的结束时间
            - 当需要获取当前时间戳进行时间计算
            - 在构建查询时间范围时使用当前时间作为参考点

            ## 返回数据格式

            返回包含两个字段的字典：
            - current_time: 格式化的时间字符串 (YYYY-MM-DD HH:MM:SS)
            - current_timestamp: 整数形式的Unix时间戳（秒）

            Args:
                ctx: MCP上下文

            Returns:
                包含当前时间信息的字典
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
        f"调用失败，正在重试第{retry_state.attempt_number}次... 异常: {retry_state.outcome.exception()}"
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
        raise
