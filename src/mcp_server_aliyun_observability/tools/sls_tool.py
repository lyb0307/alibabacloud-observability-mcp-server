


import mcp
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool
from mcp.server.fastmcp import Context, FastMCP
from alibabacloud_cms20240330.client import Client

from server import mcp

@mcp.tool(name="execute_sls_query", description="Execute a query on Aliyun SLS")
def execute_sls_query(ctx: Context,logstore: str,query: str,start_time: str,end_time: str,offset: int,size: int):
    sls_client = ctx.request_context.lifespan_context["sls_client"]
    result = sls_client.get_logs(logstore,query,start_time,end_time,offset,size)
    return "execute_sls_query"