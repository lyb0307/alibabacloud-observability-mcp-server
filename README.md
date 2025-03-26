## Aliyun Observability MCP Server

### Introduction

This is a MCP server that can be used to connect to aliyun observability. Include Aliyun SLS(Simple Log Service) and Aliyun Arms Monitor and Aliyun Cloud Watch.


### Tools

#### SLS Tools
Tookit for sls service

- `get_sls_logstore_index`
    - Get the index info of aliyun sls logstore
    - Input:
        - `project` (string): The project name of aliyun sls
        - `logstore` (string): The logstore name of aliyun sls

- `execute_log_store_query`
    - Execute a query on aliyun sls logstore
    - Input:
        - `project` (string): The project name of aliyun sls
        - `logstore` (string): The logstore name of aliyun sls
        - `query` (string): The query to execute

- `text_to_sls_log_store_query`
    - Convert the natural language text to sls log store query
    - Input:
        - `text` (string): The natural language text to generate sls log store query
        - `region_id` (string): The region id of aliyun sls
        - `project` (string): The project name of aliyun sls
        - `logstore` (string): The logstore name of aliyun sls

#### CMS Tools
Toolkit for cms2.0

- `list_cms_user_workspaces`
    - Get the workspace list of aliyun cms
    - Input:
        - `region_id` (string): The region id of aliyun cms
    - Returns:
        - `workspaces` (list): The workspace list of aliyun cms

- `execute_cms_query`
    - Execute a query on aliyun cms
    - Input:
        - `workspace_name` (string): The workspace name of aliyun cms
        - `from_timestamp` (int): The from timestamp of the query
        - `to_timestamp` (int): The to timestamp of the query
        - `query` (string): The query to execute
        - `region_id` (string): The region id of aliyun cms
    - Returns:
        - `result` (string): The data of the query


### Common Tools

- `list_all_regions`
    - Get the all region list of aliyun
    - Returns:
        - `regions` (list): The region list of aliyun






### How to run
Current,the mcp server not deploy to pip,so you need to run it from source code.

#### Install dependencies

```bash
pip install poetry
poetry update
```


#### SSE Mode

```bash
python -m mcp_server_aliyun_observability.server --transport sse --access-key-id <your_access_key_id> --access-key-secret <your_access_key_secret> --transport-port <port>
```

#### Stdio Mode

```bash
python -m mcp_server_aliyun_observability.server --transport stdio --access-key-id <your_access_key_id> --access-key-secret <your_access_key_secret>
```


