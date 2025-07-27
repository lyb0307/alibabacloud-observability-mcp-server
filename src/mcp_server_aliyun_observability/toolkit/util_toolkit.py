from datetime import datetime

from mcp.server.fastmcp import Context, FastMCP

from mcp_server_aliyun_observability import utils


class UtilToolkit:
    def __init__(self, server: FastMCP):
        self.server = server
        self._register_common_tools()

    def _register_common_tools(self):
        """register common tools functions"""

        @self.server.tool()
        def sls_get_regions(ctx: Context) -> dict:
            """获取阿里云的部分区域列表。

            ## 功能概述

            该工具用于获取阿里云的部分区域列表，便于在执行SLS查询时指定区域。

            ## 使用场景

            - 当需要获取阿里云的部分区域列表时
            - 当需要根据区域进行SLS查询时
            - 当用户没有明确指定区域ID 时，可以调用该工具获取区域列表，并要求用户进行选择

            ## 返回数据格式

            返回包含区域列表的字典，每个字典包含region_id和region_name。

            ## 查询示例

            - "获取阿里云的部分区域列表"
            """
            return [  
                    {"RegionName": "华北1（青岛）", "RegionId": "cn-qingdao"},  
                    {"RegionName": "华北2（北京）", "RegionId": "cn-beijing"},
                    {"RegionName": "华北3（张家口）", "RegionId": "cn-zhangjiakou"},
                    {"RegionName": "华北5（呼和浩特）", "RegionId": "cn-huhehaote"},
                    {"RegionName": "华北6（乌兰察布）", "RegionId": "cn-wulanchabu"},
                    {"RegionName": "华东1（杭州）", "RegionId": "cn-hangzhou"},  
                    {"RegionName": "华东2（上海）", "RegionId": "cn-shanghai"},  
                    {"RegionName": "华东5（南京-本地地域）", "RegionId": "cn-nanjing"},  
                    {"RegionName": "华东6（福州-本地地域）", "RegionId": "cn-fuzhou"},  
                    {"RegionName": "华南1（深圳）", "RegionId": "cn-shenzhen"},  
                    {"RegionName": "华南2（河源）", "RegionId": "cn-heyuan"},  
                    {"RegionName": "华南3（广州）", "RegionId": "cn-guangzhou"},  
                    {"RegionName": "西南1（成都）", "RegionId": "cn-chengdu"},  
                ]
            
        @self.server.tool()
        def sls_get_current_time(ctx: Context) -> dict:
            """获取当前时间。

            ## 功能概述
            1. 获取当前时间，会返回当前时间字符串和当前时间戳(毫秒)

            ## 使用场景
            1. 只有当无法从聊天记录里面获取到当前时间时候才可以调用该工具
            """
            return utils.get_current_time()
