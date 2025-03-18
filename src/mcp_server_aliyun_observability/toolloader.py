from dataclasses import dataclass
from functools import wraps
from typing import List, Optional, Set
import pkgutil
import importlib
from mcp.server import FastMCP
import inspect
import sys
import os

# 自定义tool装饰器
def tool():
    """自定义工具装饰器，用于标记函数为MCP工具"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}
        # 添加__mcp_tool__属性，使ToolLoader能够识别
        wrapper.__mcp_tool__ = True
        return wrapper
    return decorator

@dataclass
class ToolConfig:
    """工具配置"""
    enabled: bool = True
    categories: List[str] = None
    requires_auth: bool = False

#从.tools包中加载所有工具，并注册到mcp_server中
class ToolLoader:
    def __init__(self, mcp_server: FastMCP):
        self.mcp_server = mcp_server
        # 初始化已加载工具集合
        self.loaded_tools = set()

    def load_tools(self):
        # 从tools包中加载所有工具
        tools_package = importlib.import_module('tools')
        for _, name, is_pkg in pkgutil.iter_modules(tools_package.__path__):
            if name.startswith('_'):
                continue
            
            module_name = f"{tools_package.__name__}.{name}"
            module = importlib.import_module(module_name)
            
            # 检查模块级配置
            config = getattr(module, 'TOOL_CONFIG', ToolConfig())
            if not config.enabled:
                continue

            # 加载工具
            for attr_name, attr_value in inspect.getmembers(module):
                if (
                    inspect.isfunction(attr_value)
                    and hasattr(attr_value, "__mcp_tool__")
                    and attr_name not in self.loaded_tools
                ):
                    self.mcp_server.add_tool(attr_value)
                    self.loaded_tools.add(attr_name)
                    print(f"已加载工具: {attr_name}")
                    
                    
