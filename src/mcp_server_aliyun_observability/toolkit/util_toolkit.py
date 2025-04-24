import logging
from datetime import datetime

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger(__name__)


class UtilToolkit:
    def __init__(self, server: FastMCP):
        self.server = server
        self._register_common_tools()

    def _register_common_tools(self):
        """register common tools functions"""

        # @self.server.tool()
        # def sls_get_current_time(ctx: Context) -> dict:
        #     """获取当前时间信息。

        #     ## 功能概述

        #     该工具用于获取当前的时间戳和格式化的时间字符串，便于在执行SLS查询时指定时间范围。

        #     ## 使用场景

        #     - 当需要获取当前时间以设置查询的结束时间
        #     - 当需要获取当前时间戳进行时间计算
        #     - 在构建查询时间范围时使用当前时间作为参考点

        #     ## 返回数据格式

        #     返回包含两个字段的字典：
        #     - current_time: 格式化的时间字符串 (YYYY-MM-DD HH:MM:SS)
        #     - current_timestamp: 整数形式的Unix时间戳（秒）

        #     Args:
        #         ctx: MCP上下文

        #     Returns:
        #         包含当前时间信息的字典
        #     """
        #     return {
        #         "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        #         "current_timestamp": int(datetime.now().timestamp()),
        #     }
