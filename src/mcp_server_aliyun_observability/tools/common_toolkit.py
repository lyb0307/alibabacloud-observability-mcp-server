from datetime import datetime

from mcp.server.fastmcp import Context, FastMCP
from toolloader import tool


@tool()
def list_all_regions(ctx: Context) -> str:
    """
    list all regions
    """
    try:
        # 这里可以扩展为实际调用API获取区域列表
        return {
            "cn-hangzhou": "杭州",
            "cn-beijing": "北京",
            "cn-shanghai": "上海",
            "cn-shenzhen": "深圳",
        }
    except Exception as e:
        print(f"获取区域列表失败: {str(e)}")
        return {"cn-hangzhou": "杭州"}


@tool()
def get_current_time(ctx: Context) -> str:
    """
    Get current time,format: YYYY-MM-DD HH:MM:SS
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
