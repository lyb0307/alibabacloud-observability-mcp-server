from typing import Optional

from alibabacloud_cms20240330.client import (
    Client as CMSClient,
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


def parse_json_keys(json_keys: dict[str, IndexJsonKey]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for key, value in json_keys.items():
        result[key] = {
            "alias": value.alias,
            "sensitive": value.case_sensitive,
            "type": value.type,
        }
    return result
