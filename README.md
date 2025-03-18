## Aliyun Observability MCP Server

### Introduction

This is a MCP server that can be used to connect to aliyun observability. Include Aliyun SLS(Simple Log Service) and Aliyun Arms Monitor and Aliyun Cloud Watch.


### Tools

#### Metadata Tools

- `get sls index`
    - Get the index info of aliyun sls logstore
    - Input:
        - `project` (string): The project name of aliyun sls
        - `logstore` (string): The logstore name of aliyun sls

#### Generate Tools

- `text to sql`
    - Convert a natural language query to a sls sql query
    - Input:
        - `query` (string): The natural language query
        - `project` (string): The project name of aliyun sls
        - `logstore` (string): The logstore name of aliyun sls
    - Returns:
        - `sql` (string): The sql query

#### Query Tools
- `execute sls query`
    - Execute a query on aliyun sls
    - Input:
        - `query` (string): The query to execute
        - `project` (string): The project name of aliyun sls
        - `logstore` (string): The logstore name of aliyun sls
    - Returns:
        - `result` (string): The data of the query


#### Analyze Tools

- `analyze observability trace `
    - Analyze a trace
    - Input:
        - `trace_id` (string): The trace id of the trace to analyze
        - `type` (string): slow or error trace analysis
    - Returns:
        - `result` (string): The result of the analysis
