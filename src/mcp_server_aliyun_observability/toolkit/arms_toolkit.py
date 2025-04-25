import logging
from typing import Any

from alibabacloud_arms20190808.client import Client as ArmsClient
from alibabacloud_sls20201230.client import Client
from alibabacloud_arms20190808.models import (
    SearchTraceAppByPageRequest,
    SearchTraceAppByPageResponse,
    SearchTraceAppByPageResponseBodyPageBean,
)
from alibabacloud_tea_util import models as util_models
from alibabacloud_sls20201230.models import CallAiToolsRequest, CallAiToolsResponse
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from mcp_server_aliyun_observability.utils import (
    get_arms_user_trace_log_store,
    text_to_sql,
)

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
                "sls_query": sls_text_to_query["data"],
                "requestId": sls_text_to_query["requestId"],
                "project": data["project"],
                "log_store": data["log_store"],
            }

        @self.server.tool()
        def arms_profile_flame_analysis(
                ctx: Context,
                service_name: str = Field(..., description="arms service name"),
                start_ms: str = Field(..., description="profile start ms"),
                end_ms: str = Field(..., description="profile end ms"),
                profile_type = Field(..., description="profile type, like 'cpu' 'alloc_in_new_tlab_bytes'"),
                ip: str = Field(..., description="arms service host ip"),
                language: str = Field(..., description="arms service language, like 'java' 'go'"),
                thread: str = Field(..., description="arms service thread id"),
                thread_group: str = Field(..., description="arms service thread group"),
                region_id: str = Field(default=...,
                    description="aliyun region id,region id format like 'xx-xxx',like 'cn-hangzhou'",
                ),
        ) -> dict:
            """分析ARMS应用火焰图性能热点。

            ## 功能概述

            当应用存在性能问题且开启持续剖析时，可以调用该工具对ARMS应用火焰图性能热点进行分析，生成分析结果。分析结果会包含火焰图的性能热点问题、优化建议等信息。

            ## 使用场景

            - 当需要分析ARMS应用火焰图性能问题时

            ## 查询示例

            - "帮我分析下应用 XXX 的火焰图性能热点"

            Args:
                ctx: MCP上下文，用于访问SLS客户端
                service_name: ARMS应用监控服务名称，可以通过arms_search_apps工具获取
                start_ms: 分析的开始时间，通过get_current_time工具获取毫秒级时间戳
                end_ms: 分析的结束时间，通过get_current_time工具获取毫秒级时间戳
                profile_type: Profile类型，用于选择需要分析的Profile指标，支持CPU热点和内存热点，如'cpu'、'alloc_in_new_tlab_bytes'
                language: ARMS服务的编程语言，如'java'、'go'等
                ip: ARMS应用服务主机地址，非必要参数，用于选择所在的服务机器，如有多个填写时以英文逗号","分隔，如'192.168.0.1,192.168.0.2'，不填写默认查询服务所在的所有IP
                thread: 服务线程名称，非必要参数，用于选择对应线程，如有多个填写时以英文逗号","分隔，如'C1 CompilerThre,C2 CompilerThre'，不填写默认查询服务所有线程
                thread_group: 服务聚合线程组名称，非必要参数，用于选择对应线程组，如有多个填写时以英文逗号","分隔，如'http-nio-*-exec-*,http-nio-*-ClientPoller-*'，不填写默认查询服务所有聚合线程组
                region_id: 阿里云区域ID，如'cn-hangzhou'、'cn-shanghai'等
            """
            # Validate language parameter
            if language not in ['java', 'golang']:
                raise ValueError(f"暂不支持的语言类型: {language}. 当前仅支持 'java' 或 'go'")

            try:
                sls_client: Client = ctx.request_context.lifespan_context[
                    "sls_client"
                ].with_region("cn-shanghai")
                request: CallAiToolsRequest = CallAiToolsRequest()
                request.tool_name = "profile_flame_analysis"
                request.region_id = region_id
                params: dict[str, Any] = {
                    "serviceName": service_name,
                    "startMs": start_ms,
                    "endMs": end_ms,
                    "profileType": profile_type,
                    "ip": ip,
                    "language": language,
                    "thread": thread,
                    "threadGroup": thread_group,
                    "sys.query": f"帮我分析下应用 {service_name} 的火焰图性能热点问题",
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
                logger.error(f"调用火焰图数据性能热点AI工具失败: {str(e)}")
                raise