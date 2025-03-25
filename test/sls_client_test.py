import os

import dotenv
from alibabacloud_sls20201230.client import Client as SLSClient
from alibabacloud_sls20201230.models import CallAiToolsRequest
from alibabacloud_tea_openapi import models as open_api_models

dotenv.load_dotenv()

if __name__ == "__main__":
    config = open_api_models.Config(
        access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID"),
        access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
    )
    config.endpoint = "pub-cn-hangzhou-staging-share.log.aliyuncs.com"

    project = "sls-console-log"
    logstore = "cn-service-ml-access"
    client = SLSClient(config)
    response = client.list_ai_tools()
    print(response)
    request = CallAiToolsRequest()
    request.tool_name = "text_to_sql"
    request.region_id = "cn-hangzhou"
    request.params = {
        "project": project,
        "logstore": logstore,
        "sys.query": "帮我统计下 status 是 200 同比昨天的增量",
    }
    response = client.call_ai_tools(request).body
    if "------answer------\n" in response:
        data = response.split("------answer------\n")[1]
    print(data)
