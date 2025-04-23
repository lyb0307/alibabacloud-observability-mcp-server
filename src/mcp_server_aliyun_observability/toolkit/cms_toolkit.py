import logging
from typing import Any, Dict, List

from alibabacloud_sls20201230.client import Client
from alibabacloud_sls20201230.models import CallAiToolsRequest, CallAiToolsResponse
from alibabacloud_sls20201230.models import (
    CallAiToolsRequest,
    CallAiToolsResponse,
    GetLogsRequest,
    GetLogsResponse,
    ListLogStoresRequest,
    ListLogStoresResponse,
    ListProjectRequest,
    ListProjectResponse,
)
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
        def cms_summarize_alert_events(
            ctx: Context,
            from_timestamp: int = Field(
                ..., description="from timestamp,unit is second, like 1745384910"
            ),
            to_timestamp: int = Field(
                ..., description="to timestamp,unit is second, like 1745388510"
            ),
            limit: int = Field(10, description="limit,max is 100", ge=1, le=100),
            region_id: str = Field(
                default=...,
                description="aliyun region id,region id format like 'xx-xxx',like 'cn-hangzhou'",
            ),
        ) -> dict:
            """获取CMS中的告警事件。

            ## 功能概述

            该工具可以获取CMS中的告警事件信息，并对告警事件进行基本分析
            在告警规则维度进行分析，给出高频出现的告警规则和对应的告警规则内容信息rule_query信息
            在资源维度进行分析，给出高频出现的资源的信息
            对返回的数据进行总结分析，根据告警规则和资源维度的信息给出简单的告警规则调整建议

            ## 使用场景

            - 当需要查看当前有多少告警事件、有多少告警规则触发
            - 当需要查看当前告警事件的严重等级分布
            - 当需要查看告警事件在规则维度的信息
            - 当需要查看告警事件按照资源维度的信息

            ## 查询示例

            - "某个 region 有多少告警事件"

            ## 输出示例

            1. 总共触发了xxx次告警事件，涉及xxx条告警规则。
            2. critical 占比 xxx，warning 占比 xxx。
            3. 触发告警事件的规则占比主要有
                a. 集群ETCD服务不可用有xx条: 占比xxx。
                   告警规则为："duration":180,"expr":"((sum(up{job="ack-kube-controller-manager"}) <= 0) or (absent(sum(up{job="ack-kube-controller-manager"})))) > 0","type":"PROMQL_QUERY"
                b. 集群cloud-controller-manager服务不可用有xx条: 占比xxx。
                   告警规则为："duration":60,"expr":"((sum(up{job="ack-scheduler"}) <= 0) or (absent(sum(up{job="ack-scheduler"})))) > 0","type":"PROMQL_QUERY"
            4. 触发告警事件的资源占比主要有
                a. pod:otel-demo-opensearch-0,实体id为e33136c8bff0bfe5ddf1fc4404a7d795，有xx条
                b. instance:10.206.180.153:9100，实体id为d782274eb3167ca58e96e96a6be2d400，有xx条
                c. xxx
            5. 这些告警主要集中在集群的关键组件上，建议检查相关服务的状态和健康状况。如果属于误告警，请调整规则阈值。

            Args:
                ctx: MCP上下文，用于访问SLS客户端
                from_timestamp: 查询开始时间戳（秒）
                to_timestamp: 查询结束时间戳（秒）
                limit: 返回结果的最大数量，范围1-100，默认10
                region_id: 阿里云区域ID

            Returns:
                日志库名称的告警事件信息字典
            """
            try:
                # get project and logstore
                cms_client: Client = ctx.request_context.lifespan_context[
                    "cms_client"
                ].with_region(region_id)
                request: ListProjectRequest = ListProjectRequest(
                    project_name="cms-alert-center",
                    size=100,
                )
                response: ListProjectResponse = cms_client.list_project(request)
                projects = [
                    {
                        "project_name": project.project_name,
                        "description": project.description,
                        "region_id": project.region,
                    }
                    for project in response.body.projects
                    if project.project_name.endswith(region_id)
                ]
                project = projects[0]["project_name"]

                request: ListLogStoresRequest = ListLogStoresRequest(
                    logstore_name="alert-rule-event-default",
                    size=limit,
                )
                response: ListLogStoresResponse = cms_client.list_log_stores(
                    project, request
                )
                log_store_list = [
                    log_store
                    for log_store in response.body.logstores
                    if log_store.endswith(region_id)
                ]

                log_store = log_store_list[0]

                runtime: util_models.RuntimeOptions = util_models.RuntimeOptions()
                runtime.read_timeout = 60000
                runtime.connect_timeout = 60000

                # 获取告警总揽信息
                request: GetLogsRequest = GetLogsRequest(
                    query="* | SELECT  COUNT(CASE WHEN type = 'ALERT' THEN 1 END) AS alert_events ,COUNT(DISTINCT CASE WHEN type = 'ALERT' AND status != 'RECOVERED' THEN source END) AS alert_rules FROM log",
                    from_=from_timestamp,
                    to=to_timestamp,
                    line=limit,
                )
                response: GetLogsResponse = cms_client.get_logs_with_options(
                    project, log_store, request, headers={}, runtime=runtime
                )
                alert_event_total: List[Dict[str, Any]] = response.body
                print(alert_event_total)

                # 获取告警按照严重等级信息
                request: GetLogsRequest = GetLogsRequest(
                    query="* | SELECT severity, COUNT(*) AS alert_count FROM log GROUP BY severity order by alert_count desc",
                    from_=from_timestamp,
                    to=to_timestamp,
                    line=limit,
                )
                response: GetLogsResponse = cms_client.get_logs_with_options(
                    project, log_store, request, headers={}, runtime=runtime
                )
                alert_severity_info: List[Dict[str, Any]] = response.body
                print(alert_severity_info)

                # 获取告警事件按照告警规则维度的信息
                request: GetLogsRequest = GetLogsRequest(
                    query="type:alert | set session mode=scan;  SELECT subject,json_extract_scalar(data, '$.rule.query') as rule_query,  COUNT(*) AS count, COUNT(*) * 100.0 / (SELECT COUNT(*) FROM log) AS percentage FROM log GROUP BY (subject,rule_query) ORDER BY percentage DESC limit 10",
                    from_=from_timestamp,
                    to=to_timestamp,
                    line=limit,
                )
                response: GetLogsResponse = cms_client.get_logs_with_options(
                    project, log_store, request, headers={}, runtime=runtime
                )
                alert_rule_info: List[Dict[str, Any]] = response.body
                print(alert_rule_info)

                # 获取告警事件按照资源维度的信息
                request: GetLogsRequest = GetLogsRequest(
                    query="type:alert | set session mode=scan;  SELECT json_extract(resource, '$.entity') as entity, COUNT(*) AS count, COUNT(*) * 100.0 / (SELECT COUNT(*) FROM log) AS percentage FROM log GROUP BY (entity) ORDER BY count DESC limit 100",
                    from_=from_timestamp,
                    to=to_timestamp,
                    line=limit,
                )
                response: GetLogsResponse = cms_client.get_logs_with_options(
                    project, log_store, request, headers={}, runtime=runtime
                )
                alert_resource_info: List[Dict[str, Any]] = response.body

                print(alert_resource_info)
                result = {
                    "alert_event_total": alert_event_total,
                    "alert_severity_info": alert_severity_info,
                    "alert_rule_percent": alert_rule_info,
                    "alert_resource_info": alert_resource_info,
                }
                return result
            except Exception as e:
                logger.error(f"调用CMS AI工具失败: {str(e)}")
                raise

        @self.server.tool()
        @retry(
            stop=stop_after_attempt(2),
            wait=wait_fixed(1),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )
        def cms_translate_natural_language_to_promql(
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
            - 禁止使用sls_execute_query工具执行，两者接口不兼容

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
                cms_client: Client = ctx.request_context.lifespan_context[
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
                    cms_client.call_ai_tools_with_options(
                        request=request, headers={}, runtime=runtime
                    )
                )
                data = tool_response.body
                if "------answer------\n" in data:
                    data = data.split("------answer------\n")[1]
                return data
            except Exception as e:
                logger.error(f"调用CMS AI工具失败: {str(e)}")
                raise
