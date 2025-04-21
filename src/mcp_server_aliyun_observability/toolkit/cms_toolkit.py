import logging
from typing import Any, Dict, List

from alibabacloud_sls20201230.client import Client
from alibabacloud_sls20201230.models import CallAiToolsRequest, CallAiToolsResponse
from alibabacloud_tea_util import models as util_models
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

# 配置日志
logger = logging.getLogger(__name__)


class CMSToolkit:
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
        """register cms and prometheus related tools functions"""

        @self.server.tool()
        @retry(
            stop=stop_after_attempt(2),
            wait=wait_fixed(1),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        def prom_translate_natural_language_to_query(
            ctx: Context,
            text: str = Field(
                ...,
                description="the natural language text to generate promql",
            ),
            project: str = Field(..., description="sls project name"),
            metric_store: str = Field(..., description="sls metric store name"),
            region_id: str = Field(
                default=...,
                description="aliyun region id,region id format like 'xx-xxx',like 'cn-hangzhou'",
            ),
        ) -> str:
            """将自然语言转换为Prometheus PromQL查询语句。

            ## 功能概述

            该工具可以将自然语言描述转换为有效的PromQL查询语句，便于用户使用自然语言表达查询需求。

            ## 使用场景

            - 当用户不熟悉PromQL查询语法时
            - 当需要快速构建复杂查询时
            - 当需要从自然语言描述中提取查询意图时

            ## 使用限制

            - 仅支持生成PromQL查询
            - 生成的是查询语句，而非查询结果

            ## 最佳实践

            - 提供清晰简洁的自然语言描述
            - 不要在描述中包含项目或时序库名称
            - 首次生成的查询可能不完全符合要求，可能需要多次尝试

            ## 查询示例

            - "帮我生成 XXX 的PromQL查询语句"
            - "查询每个namespace下的Pod数量"

            Args:
                ctx: MCP上下文，用于访问SLS客户端
                text: 用于生成查询的自然语言文本
                project: SLS项目名称
                metric_store: SLS时序库名称
                region_id: 阿里云区域ID

            Returns:
                生成的PromQL查询语句
            """
            try:
                prom_client: Client = ctx.request_context.lifespan_context[
                    "cms_client"
                ].with_region("cn-shanghai")
                request: CallAiToolsRequest = CallAiToolsRequest()
                request.tool_name = "text_to_promql"
                request.region_id = region_id
                params: dict[str, Any] = {
                    "project": project,
                    "metricstore": metric_store,
                    "sys.query": text,
                }
                request.params = params
                runtime: util_models.RuntimeOptions = util_models.RuntimeOptions()
                runtime.read_timeout = 60000
                runtime.connect_timeout = 60000
                tool_response: CallAiToolsResponse = (
                    prom_client.call_ai_tools_with_options(
                        request=request, headers={}, runtime=runtime
                    )
                )
                data = tool_response.body
                if "------answer------\n" in data:
                    data = data.split("------answer------\n")[1]
                return data
            except Exception as e:
                logger.error(f"调用Prom AI工具失败: {str(e)}")
                raise
