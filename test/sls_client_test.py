import os

import dotenv
from alibabacloud_sls20201230.client import Client as SLSClient
from alibabacloud_sls20201230.models import GetAgentConfigRequest
from alibabacloud_tea_openapi import models as open_api_models

dotenv.load_dotenv()

if __name__ == "__main__":
    config = open_api_models.Config(
        access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID"),
        access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
    )
    config.endpoint = "pub-cn-hangzhou-staging-share.log.aliyuncs.com"
    client = SLSClient(config)
    response = client.list_ai_tools()
    print(response)
