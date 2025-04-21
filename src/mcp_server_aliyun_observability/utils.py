import hashlib
import logging
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

from alibabacloud_arms20190808.client import Client as ArmsClient
from alibabacloud_credentials.client import Client as CredClient
from alibabacloud_sls20201230.client import Client
from alibabacloud_sls20201230.client import Client as SLSClient
from alibabacloud_sls20201230.models import (CallAiToolsRequest,
                                             CallAiToolsResponse, IndexJsonKey)
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from mcp.server.fastmcp import Context
from Tea.exceptions import TeaException

from mcp_server_aliyun_observability.api_error import TEQ_EXCEPTION_ERROR

logger = logging.getLogger(__name__)

class CredentialWrapper:
    """
    A wrapper for aliyun credentials
    """

    access_key_id: str
    access_key_secret: str

    def __init__(self, access_key_id: str, access_key_secret: str):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
    
    
    
class SLSClientWrapper:
    """
    A wrapper for aliyun client
    """

    def __init__(self, credential: Optional[CredentialWrapper] = None):
        self.credential = credential
    

    def with_region(
        self, region: str = None, endpoint: Optional[str] = None
    ) -> SLSClient:
        if self.credential:
            config = open_api_models.Config(
                access_key_id=self.credential.access_key_id,
                access_key_secret=self.credential.access_key_secret,
            )
        else:
            credentialsClient = CredClient()
            config = open_api_models.Config(credential=credentialsClient)
        config.endpoint = f"{region}.log.aliyuncs.com"
        return SLSClient(config)


class ArmsClientWrapper:
    """
    A wrapper for aliyun arms client
    """

    def __init__(self, credential: Optional[CredentialWrapper] = None):
        self.credential = credential

    def with_region(self, region: str, endpoint: Optional[str] = None) -> ArmsClient:
        if self.credential:
            config = open_api_models.Config(
                access_key_id=self.credential.access_key_id,
                access_key_secret=self.credential.access_key_secret,
            )
        else:
            credentialsClient = CredClient()
            config = open_api_models.Config(credential=credentialsClient)
        config.endpoint = endpoint or f"arms.{region}.aliyuncs.com"
        return ArmsClient(config)


def parse_json_keys(json_keys: dict[str, IndexJsonKey]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for key, value in json_keys.items():
        result[key] = {
            "alias": value.alias,
            "sensitive": value.case_sensitive,
            "type": value.type,
        }
    return result


def get_arms_user_trace_log_store(user_id: int, region: str) -> dict[str, str]:
    """
    get the log store name of the user's trace
    """
    # project是基于 user_id md5,proj-xtrace-xxx-cn-hangzhou
    if "finance" in region:
        text = str(user_id) + region
        project = f"proj-xtrace-{md5_string(text)}"
    else:
        text = str(user_id)
        project = f"proj-xtrace-{md5_string(text)}-{region}"
    # logstore-xtrace-1277589232893727-cn-hangzhou
    log_store = "logstore-tracing"
    return {"project": project, "log_store": log_store}


def md5_string(origin: str) -> str:
    """
    计算字符串的MD5值，与Java实现对应

    Args:
        origin: 要计算MD5的字符串

    Returns:
        MD5值的十六进制字符串
    """
    buf = origin.encode()

    md5 = hashlib.md5()

    md5.update(buf)

    tmp = md5.digest()

    sb = []
    for b in tmp:
        hex_str = format(b & 0xFF, "x")
        sb.append(hex_str)

    return "".join(sb)


T = TypeVar("T")


def handle_tea_exception(func: Callable[..., T]) -> Callable[..., T]:
    """
    装饰器：处理阿里云 SDK 的 TeaException 异常

    Args:
        func: 被装饰的函数

    Returns:
        装饰后的函数，会自动处理 TeaException 异常
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except TeaException as e:
            for error in TEQ_EXCEPTION_ERROR:
                if e.code == error["errorCode"]:
                    return cast(
                        T,
                        {
                            "solution": error["solution"],
                            "message": error["errorMessage"],
                        },
                    )
            raise e

    return wrapper


def text_to_sql(
    ctx: Context, text: str, project: str, log_store: str, region_id: str
) -> str:
    try:
        sls_client: Client = ctx.request_context.lifespan_context[
            "sls_client"
        ].with_region("cn-shanghai")
        request: CallAiToolsRequest = CallAiToolsRequest()
        request.tool_name = "text_to_sql"
        request.region_id = region_id
        params: dict[str, Any] = {
            "project": project,
            "logstore": log_store,
            "sys.query": text,
        }
        request.params = params
        runtime: util_models.RuntimeOptions = util_models.RuntimeOptions()
        runtime.read_timeout = 60000
        runtime.connect_timeout = 60000
        tool_response: CallAiToolsResponse = sls_client.call_ai_tools_with_options(
            request=request, headers={}, runtime=runtime
        )
        data = tool_response.body
        if "------answer------\n" in data:
            data = data.split("------answer------\n")[1]
        return data
    except Exception as e:
        logger.error(f"调用SLS AI工具失败: {str(e)}")
        raise

