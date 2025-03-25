import argparse
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Literal, Optional

import mcp
from alibabacloud_cms20240330.client import (
    Client as CMSClient,
)
from alibabacloud_sls20201230.client import (
    Client as SLSClient,
)
from alibabacloud_tea_openapi import models as open_api_models
from mcp.server import FastMCP
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

from mcp_server_aliyun_observability.toolloader import ToolLoader


class SLSClientWrapper:
    """
    A wrapper for aliyun client
    """

    def __init__(self, access_key_id: str, access_key_secret: str):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret

    def with_region(self, region: str, endpoint: Optional[str] = None) -> SLSClient:
        config = open_api_models.Config(
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret,
        )
        config.endpoint = endpoint or f"{region}.log.aliyuncs.com"
        print("jheee")
        return SLSClient(config)


class CMSClientWrapper:
    """
    A wrapper for aliyun client
    """

    def __init__(self, access_key_id: str, access_key_secret: str):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret

    def with_region(self, region: str) -> CMSClient:
        config = open_api_models.Config(
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret,
        )
        config.endpoint = "cms-pre.cn-hangzhou.aliyuncs.com"
        return CMSClient(config)


def create_parser() -> argparse.ArgumentParser:
    """create command line argument parser"""
    parser = argparse.ArgumentParser(description="aliyun observability mcp server")
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "sse"],
        default="stdio",
        help="transport type. stdio or sse",
    )
    parser.add_argument(
        "--access-key-id", type=str, help="aliyun access key id", default=None
    )
    parser.add_argument(
        "--access-key-secret", type=str, help="aliyun access key secret", default=None
    )
    parser.add_argument(
        "--env-file",
        type=str,
        help="environment variable file path (.env)",
        default=None,
    )
    return parser


def load_env_file(env_file: str) -> dict:
    """load config from environment variable file"""
    env_vars = {}
    try:
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    except Exception as e:
        print(f"警告: 无法加载环境变量文件 {env_file}: {e}")
    return env_vars


def get_credentials(args: argparse.Namespace) -> tuple[Optional[str], Optional[str]]:
    """get credentials, priority: command line arguments > environment variable file > environment variables"""
    import os

    access_key_id = None
    access_key_secret = None

    # 1. check command line arguments first
    if args.access_key_id and args.access_key_secret:
        return args.access_key_id, args.access_key_secret

    # 2. check environment variable file
    if args.env_file:
        env_vars = load_env_file(args.env_file)
        if (
            "ALIYUN_ACCESS_KEY_ID" in env_vars
            and "ALIYUN_ACCESS_KEY_SECRET" in env_vars
        ):
            return env_vars["ALIYUN_ACCESS_KEY_ID"], env_vars[
                "ALIYUN_ACCESS_KEY_SECRET"
            ]

    # 3. check environment variables
    access_key_id = os.environ.get("ALIYUN_ACCESS_KEY_ID")
    access_key_secret = os.environ.get("ALIYUN_ACCESS_KEY_SECRET")

    return access_key_id, access_key_secret


def create_lifespan(access_key_id: str, access_key_secret: str):
    @asynccontextmanager
    async def lifespan(fastmcp: FastMCP) -> AsyncIterator[dict]:
        sls_client = SLSClientWrapper(access_key_id, access_key_secret)
        cms_client = CMSClientWrapper(
            access_key_id, access_key_secret=access_key_secret
        )
        yield {
            "sls_client": sls_client,
            "cms_client": cms_client,
        }

    return lifespan


def server(
    access_key_id: str,
    access_key_secret: str,
    transport: str,
    log_level: str,
    transport_port: int,
):
    if not access_key_id or not access_key_secret:
        raise ValueError(
            "need to set aliyun access credentials. you can set it in one of the following ways:\n"
            "1. command line arguments: --access-key-id and --access-key-secret\n"
        )
    # create server instance and run
    mcp = FastMCP(
        name="mcp_aliyun_observability_server",
        lifespan=create_lifespan(access_key_id, access_key_secret),
        log_level=log_level,
        port=transport_port,
    )
    # 使用工具加载器
    loader = ToolLoader(mcp)
    loader.load_tools()
    mcp.run(transport)
