import os

import dotenv
from alibabacloud_sls20201230.client import Client as SLSClient
from alibabacloud_sls20201230.models import CallAiToolsRequest, CallAiToolsResponse
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

dotenv.load_dotenv()
from mcp_server_aliyun_observability.server import SLSClientWrapper

if __name__ == "__main__":
    project = "sls-console-log"
    logstore = "cn-service-ml-access"
    print(os.getenv("ALIYUN_ACCESS_KEY_ID"))
    client = SLSClientWrapper(
        access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID"),
        access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
    ).with_region("cn-hangzhou", "cn-hangzhou.log.aliyuncs.com")
    response = client.get_index(project, logstore)
    print(response)
    client = SLSClientWrapper(
        access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID"),
        access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
    ).with_region("cn-hangzhou", "pub-cn-hangzhou-staging-share.log.aliyuncs.com")
    request = CallAiToolsRequest()
    request.tool_name = "text_to_sql"
    request.region_id = "cn-hangzhou"
    request.params = {
        "project": project,
        "logstore": logstore,
        "sys.query": "帮我统计下 status 是 200 同比昨天的增量",
    }
    runtime: util_models.RuntimeOptions = util_models.RuntimeOptions()
    runtime.read_timeout = 60000
    runtime.connect_timeout = 60000
    tool_response: CallAiToolsResponse = client.call_ai_tools_with_options(
        request=request, headers={}, runtime=runtime
    )
    response = tool_response.body
    if "------answer------\n" in response:
        data = response.split("------answer------\n")[1]
    print(data)
