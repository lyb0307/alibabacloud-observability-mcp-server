from mcp.types import TextContent
from mcp.server.fastmcp import Context
from alibabacloud_cms20240330.client import Client
from functools import wraps

from toolloader import ToolConfig, tool


@tool()
def execute_sls_query(
    ctx: Context,
    logstore: str,
    query: str,
    start_time: str,
    end_time: str,
    offset: int = 0,
    size: int = 20
) -> TextContent:
    """
    执行SLS日志查询
    
    Args:
        ctx: 上下文对象
        logstore: 日志库名称
        query: 查询语句
        start_time: 开始时间，格式为ISO8601
        end_time: 结束时间，格式为ISO8601
        offset: 分页偏移量，默认为0
        size: 返回结果数量，默认为20
        
    Returns:
        查询结果
    """
    # 从上下文中获取SLS客户端
    sls_client = ctx.request_context.lifespan_context.get("sls_client")
    if not sls_client:
        return TextContent("SLS客户端未初始化")
    
    try:
        # 执行查询并获取结果
        result = sls_client.get_logs(logstore, query, start_time, end_time, offset, size)
        
        # 处理查询结果
        if not result or not hasattr(result, 'body'):
            return TextContent("查询未返回结果")
        
        # 格式化返回结果
        formatted_result = format_sls_result(result.body)
        return TextContent(formatted_result)
    except Exception as e:
        return TextContent(f"查询执行出错: {str(e)}")

def format_sls_result(result_body):
    """格式化SLS查询结果"""
    if not result_body or not hasattr(result_body, 'logs'):
        return "无查询结果"
    
    logs = result_body.logs
    if not logs:
        return "查询结果为空"
    
    # 格式化日志内容
    formatted_logs = []
    for log in logs:
        formatted_logs.append(str(log))
    
    return "\n".join(formatted_logs)