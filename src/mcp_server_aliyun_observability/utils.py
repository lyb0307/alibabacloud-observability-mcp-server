import hashlib
from typing import Optional

from alibabacloud_arms20190808.client import (
    Client as ArmsClient,
)
from alibabacloud_sls20201230.client import (
    Client as SLSClient,
)
from alibabacloud_sls20201230.models import (
    IndexJsonKey,
)
from alibabacloud_tea_openapi import models as open_api_models


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
        return SLSClient(config)


class ArmsClientWrapper:
    """
    A wrapper for aliyun arms client
    """

    def __init__(self, access_key_id: str, access_key_secret: str):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret

    def with_region(self, region: str, endpoint: Optional[str] = None) -> ArmsClient:
        config = open_api_models.Config(
            access_key_id=self.access_key_id,
            access_key_secret=self.access_key_secret,
        )
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
    text = (str(user_id) + region).encode()
    if "finance" in region:
        project = f"proj-xtrace-{hashlib.md5(text).hexdigest()}"
    else:
        project = f"proj-xtrace-{hashlib.md5(text).hexdigest()}"
    # logstore-xtrace-1277589232893727-cn-hangzhou
    log_store = f"logstore-xtrace-{user_id}-{region}"
    return {"project": project, "log_store": log_store}
