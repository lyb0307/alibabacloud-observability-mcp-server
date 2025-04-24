import logging
from typing import Any

from alibabacloud_arms20190808.client import Client as ArmsClient
from alibabacloud_arms20190808.models import (
    SearchTraceAppByPageRequest, SearchTraceAppByPageResponse,
    SearchTraceAppByPageResponseBodyPageBean)
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from tenacity import (retry, retry_if_exception_type, stop_after_attempt,
                      wait_fixed)

from mcp_server_aliyun_observability.utils import (
    get_arms_user_trace_log_store, text_to_sql)

logger = logging.getLogger(__name__)


class ArmsToolkit:
    def __init__(self, server: FastMCP):
        self.server = server
        self._register_tools()

    def _register_tools(self):
        """register arms related tools functions"""

        @self.server.tool()
        def arms_search_apps(
            ctx: Context,
            appNameQuery: str = Field(..., description="app name query"),
            regionId: str = Field(
                ...,
                description="region id,region id format like 'xx-xxx',like 'cn-hangzhou'",
            ),
            pageSize: int = Field(
                20, description="page size,max is 100", ge=1, le=100
            ),
            pageNumber: int = Field(1, description="page number,default is 1", ge=1),
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
            ].with_region(regionId)
            request: SearchTraceAppByPageRequest = SearchTraceAppByPageRequest(
                traceAppName=appNameQuery,
                regionId=regionId,
                pageSize=pageSize,
                pageNumber=pageNumber,
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
                        "appName": app.app_name,
                        "pid": app.pid,
                        "userId": app.user_id,
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
            userId: int = Field(..., description="user aliyun account id"),
            pid: str = Field(..., description="pid,the pid of the app"),
            regionId: str = Field(
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

            data: dict[str, str] = get_arms_user_trace_log_store(userId, regionId)
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
                ctx, prompt, data["project"], data["logStore"], regionId
            )
            return {
                "slsQuery": sls_text_to_query,
                "project": data["project"],
                "logStore": data["logStore"],
            }
