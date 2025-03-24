from mcp.server.fastmcp import Context
from mcp.types import TextContent
from toolloader import tool


@tool()
def demo_tool(ctx: Context, a: int, b: int) -> int:
    """
    calculate the sum of two integers
    """
    sls_client = ctx.request_context.lifespan_context["sls_client"].chooseRegion(
        "cn-shanghai"
    )

    return a + b
