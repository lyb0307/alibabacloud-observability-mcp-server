## 阿里云可观测MCP服务

### 简介

阿里云可观测 MCP服务，提供了一系列访问阿里云可观测各产品的工具能力，覆盖产品包含阿里云日志服务SLS、阿里云应用实时监控服务ARMS、阿里云云监控等，任意支持 MCP 协议的智能体助手都可快速接入。

目前提供的 MCP 工具以阿里云日志服务为主，其他产品会陆续支持，工具详细如下:


### 工具列表

#### SLS 日志服务相关

- `sls_describe_logstore`
    - 获取 SLS Logstore 的索引信息
    - 输入:
        - `project` (string): SLS Project 名称
        - `logstore` (string): SLS Logstore 名称
    - 返回:
        - 日志存储的索引信息

- `sls_list_projects`
    - 获取 SLS Project 列表
    - 输入:
        - `region_id` (string): SLS 区域ID
    - 返回:
        - SLS Project 列表

- `sls_list_logstores`
    - 获取 SLS Logstore 列表
    - 输入:
        - `project` (string): SLS Project 名称
    - 返回:
        - SLS Logstore 列表

- `sls_execute_query`
    - 执行SLS 日志查询
    - 输入:
        - `project` (string): SLS Project 名称
        - `logstore` (string): SLS Logstore 名称
        - `query` (string): 查询语句
    - 返回:
        - 日志查询结果

- `sls_text_to_query`
    - 将自然语言转换为 SLS 日志查询语句
    - 输入:
        - `text` (string): 自然语言文本
        - `project` (string): SLS Project 名称
        - `logstore` (string): SLS Logstore 名称
    - 返回:
        - 日志查询语句


### 使用说明

在使用 MCP Server 之前，需要先获取阿里云的 AccessKeyId 和 AccessKeySecret，请参考 [阿里云 AccessKey 管理](https://help.aliyun.com/document_detail/53045.html)


#### 使用 pip 安装

直接使用 pip 安装即可，安装命令如下：

```bash
pip install mcp-server-aliyun-observability
```
安装之后，直接运行即可，运行命令如下：

```bash
python -m mcp_server_aliyun_observability --transport sse --access-key-id <your_access_key_id> --access-key-secret <your_access_key_secret>
```
可通过命令行传递指定参数:
- `--transport` 指定传输方式，可选值为 `sse` 或 `stdio`，默认值为 `stdio`
- `--access-key-id` 指定阿里云 AccessKeyId
- `--access-key-secret` 指定阿里云 AccessKeySecret
- `--log-level` 指定日志级别，可选值为 `DEBUG`、`INFO`、`WARNING`、`ERROR`，默认值为 `INFO`
- `--transport-port` 指定传输端口，默认值为 `8000`,仅当 `--transport` 为 `sse` 时有效


### 使用uv安装

```bash
uv install mcp-server-aliyun-observability
```

安装之后，直接运行即可，运行命令如下：

```bash
uv run mcp-server-aliyun-observability --transport sse --access-key-id <your_access_key_id> --access-key-secret <your_access_key_secret>
```






