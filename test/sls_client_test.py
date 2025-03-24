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
    client = SLSClient(config)
    response = client.list_ai_tools()
    print(response)
    request = CallAiToolsRequest()
    request.tool_name = "text_to_sql"
    request.region_id = "cn-chengdu"
    request.params = {
        "project": "copilot-sql-generator-eval",
        "logstore": "copilot-sql-generator-eval-log",
        "sys.query": "* and __topic__: oss_access_log and bucket: hgame-va | select client_ip, count(client_ip) as ip_num group by client_ip order by ip_num desc  在此基础上，按天显示",
    }
    response = client.call_ai_tools(request)
    print(response)
