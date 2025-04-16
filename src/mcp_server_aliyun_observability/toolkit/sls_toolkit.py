import logging
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
    handle_tea_exception,
    parse_json_keys,
    text_to_sql,
)

# 配置日志
logger = logging.getLogger(__name__)


class SLSToolkit:
    """aliyun observability tools manager"""

    def __init__(self, server: FastMCP):
        """
        initialize the tools manager

        Args:
            server: FastMCP server instance
        """
        self.server = server
        self._register_sls_tools()

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

        @self.server.tool()
        def sls_diagnose_query(
            ctx: Context,
            query: str = Field(..., description="sls query"),
            error_message: str = Field(..., description="error message"),
            project: str = Field(..., description="sls project name"),
            log_store: str = Field(..., description="sls log store name"),
            region_id: str = Field(
                default=...,
                description="aliyun region id,region id format like 'xx-xxx',like 'cn-hangzhou'",
            ),
        ) -> dict:
            """诊断SLS查询语句。

            ## 功能概述

            当 SLS 查询语句执行失败时，可以调用该工具，根据错误信息，生成诊断结果。诊断结果会包含查询语句的正确性、性能分析、优化建议等信息。

            ## 使用场景

            - 当需要诊断SLS查询语句的正确性时
            - 当 SQL 执行错误需要查找原因时

            ## 查询示例

            - "帮我诊断下 XXX 的日志查询语句"
            - "帮我分析下 XXX 的日志查询语句"

            Args:
                ctx: MCP上下文，用于访问SLS客户端
                query: SLS查询语句
                error_message: 错误信息
                project: SLS项目名称
                log_store: SLS日志库名称
                region_id: 阿里云区域ID
            """
            try:
                sls_client: Client = ctx.request_context.lifespan_context[
                    "sls_client"
                ].with_region("cn-shanghai")
                request: CallAiToolsRequest = CallAiToolsRequest()
                request.tool_name = "diagnosis_sql"
                request.region_id = region_id
                params: dict[str, Any] = {
                    "project": project,
                    "logstore": log_store,
                    "sys.query": f"帮我诊断下 {query} 的日志查询语句,错误信息为 {error_message}",
                }
                request.params = params
                runtime: util_models.RuntimeOptions = util_models.RuntimeOptions()
                runtime.read_timeout = 60000
                runtime.connect_timeout = 60000
                tool_response: CallAiToolsResponse = (
                    sls_client.call_ai_tools_with_options(
                        request=request, headers={}, runtime=runtime
                    )
                )
                data = tool_response.body
                if "------answer------\n" in data:
                    data = data.split("------answer------\n")[1]
                return data
            except Exception as e:
                logger.error(f"调用SLS AI工具失败: {str(e)}")
                raise
