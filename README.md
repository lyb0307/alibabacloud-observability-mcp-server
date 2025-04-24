## 阿里云可观测MCP服务
<p align="center">
  <a href="./README.md"><img alt="中文自述文件" src="https://img.shields.io/badge/简体中文-d9d9d9""></a>
  <a href="./README_EN.md"><img alt="英文自述文件" src="https://img.shields.io/badge/English-d9d9d9")
</p>

### 简介

阿里云可观测 MCP服务，提供了一系列访问阿里云可观测各产品的工具能力，覆盖产品包含阿里云日志服务SLS、阿里云应用实时监控服务ARMS、阿里云云监控等，任意支持 MCP 协议的智能体助手都可快速接入。支持的产品如下:

- [阿里云日志服务SLS](https://help.aliyun.com/zh/sls/product-overview/what-is-log-service)
- [阿里云应用实时监控服务ARMS](https://help.aliyun.com/zh/arms/?scm=20140722.S_help@@%E6%96%87%E6%A1%A3@@34364._.RL_arms-LOC_2024NSHelpLink-OR_ser-PAR1_215042f917434789732438827e4665-V_4-P0_0-P1_0)

目前提供的 MCP 工具以阿里云日志服务为主，其他产品会陆续支持，工具详细如下:

### 版本记录
可以查看 [CHANGELOG.md](./CHANGELOG.md)

### 常见问题
可以查看 [FAQ.md](./FAQ.md)

##### 场景举例

- 场景一: 快速查询某个 logstore 相关结构
    - 使用工具:
        - `sls_list_logstores`
        - `sls_describe_logstore`
    ![image](./images/search_log_store.png)


- 场景二: 模糊查询最近一天某个 logstore下面访问量最高的应用是什么
    - 分析:
        - 需要判断 logstore 是否存在
        - 获取 logstore 相关结构
        - 根据要求生成查询语句(对于语句用户可确认修改)
        - 执行查询语句
        - 根据查询结果生成响应
    - 使用工具:
        - `sls_list_logstores`
        - `sls_describe_logstore`
        - `sls_translate_natural_language_to_query`
        - `sls_execute_query`
    ![image](./images/fuzzy_search_and_get_logs.png)

    
- 场景三: 查询 ARMS 某个应用下面响应最慢的几条 Trace
    - 分析:
        - 需要判断应用是否存在
        - 获取应用相关结构
        - 根据要求生成查询语句(对于语句用户可确认修改)
        - 执行查询语句
        - 根据查询结果生成响应
    - 使用工具:
        - `arms_search_apps`
        - `arms_generate_trace_query`
        - `sls_translate_natural_language_to_query`
        - `sls_execute_query`
    ![image](./images/find_slowest_trace.png)


### 权限要求

为了确保 MCP Server 能够成功访问和操作您的阿里云可观测性资源，您需要配置以下权限：

1.  **阿里云访问密钥 (AccessKey)**：
    *   服务运行需要有效的阿里云 AccessKey ID 和 AccessKey Secret。
    *   获取和管理 AccessKey，请参考 [阿里云 AccessKey 管理官方文档](https://help.aliyun.com/document_detail/53045.html)。
  
2. 当你初始化时候不传入 AccessKey 和 AccessKey Secret 时，会使用[默认凭据链进行登录](https://www.alibabacloud.com/help/zh/sdk/developer-reference/v2-manage-python-access-credentials#62bf90d04dztq)
   1. 如果环境变量 中的ALIBABA_CLOUD_ACCESS_KEY_ID 和 ALIBABA_CLOUD_ACCESS_KEY_SECRET均存在且非空，则使用它们作为默认凭据。
   2. 如果同时设置了ALIBABA_CLOUD_ACCESS_KEY_ID、ALIBABA_CLOUD_ACCESS_KEY_SECRET和ALIBABA_CLOUD_SECURITY_TOKEN，则使用STS Token作为默认凭据。
   
3.  **RAM 授权 (重要)**：
    *   与 AccessKey 关联的 RAM 用户或角色**必须**被授予访问相关云服务所需的权限。
    *   **强烈建议遵循"最小权限原则"**：仅授予运行您计划使用的 MCP 工具所必需的最小权限集，以降低安全风险。
    *   根据您需要使用的工具，参考以下文档进行权限配置：
        *   **日志服务 (SLS)**：如果您需要使用 `sls_*` 相关工具，请参考 [日志服务权限说明](https://help.aliyun.com/zh/sls/overview-8)，并授予必要的读取、查询等权限。
        *   **应用实时监控服务 (ARMS)**：如果您需要使用 `arms_*` 相关工具，请参考 [ARMS 权限说明](https://help.aliyun.com/zh/arms/security-and-compliance/overview-8?scm=20140722.H_74783._.OR_help-T_cn~zh-V_1)，并授予必要的查询权限。
    *   请根据您的实际应用场景，精细化配置所需权限。

### 安全与部署建议

请务必关注以下安全事项和部署最佳实践：

1.  **密钥安全**：
    *   本 MCP Server 在运行时会使用您提供的 AccessKey 调用阿里云 OpenAPI，但**不会以任何形式存储您的 AccessKey**，也不会将其用于设计功能之外的任何其他用途。

2.  **访问控制 (关键)**：
    *   当您选择通过 **SSE (Server-Sent Events) 协议** 访问 MCP Server 时，**您必须自行负责该服务接入点的访问控制和安全防护**。
    *   **强烈建议**将 MCP Server 部署在**内部网络或受信环境**中，例如您的私有 VPC (Virtual Private Cloud) 内，避免直接暴露于公共互联网。
    *   推荐的部署方式是使用**阿里云函数计算 (FC)**，并配置其网络设置为**仅 VPC 内访问**，以实现网络层面的隔离和安全。
    *   **注意**：**切勿**在没有任何身份验证或访问控制机制的情况下，将配置了您 AccessKey 的 MCP Server SSE 端点暴露在公共互联网上，这会带来极高的安全风险。

### 使用说明


在使用 MCP Server 之前，需要先获取阿里云的 AccessKeyId 和 AccessKeySecret，请参考 [阿里云 AccessKey 管理](https://help.aliyun.com/document_detail/53045.html)


#### 使用 pip 安装
> ⚠️ 需要 Python 3.10 及以上版本。

直接使用 pip 安装即可，安装命令如下：

```bash
pip install mcp-server-aliyun-observability
```
1. 安装之后，直接运行即可，运行命令如下：

```bash
python -m mcp_server_aliyun_observability --transport sse --access-key-id <your_access_key_id> --access-key-secret <your_access_key_secret>
```
可通过命令行传递指定参数:
- `--transport` 指定传输方式，可选值为 `sse` 或 `stdio`，默认值为 `stdio`
- `--access-key-id` 指定阿里云 AccessKeyId，不指定时会使用环境变量中的ALIBABA_CLOUD_ACCESS_KEY_ID
- `--access-key-secret` 指定阿里云 AccessKeySecret，不指定时会使用环境变量中的ALIBABA_CLOUD_ACCESS_KEY_SECRET
- `--log-level` 指定日志级别，可选值为 `DEBUG`、`INFO`、`WARNING`、`ERROR`，默认值为 `INFO`
- `--transport-port` 指定传输端口，默认值为 `8000`,仅当 `--transport` 为 `sse` 时有效

2. 使用uv 命令启动
   可以指定下版本号，会自动拉取对应依赖，默认是 studio 方式启动
```bash
uvx --from 'mcp-server-aliyun-observability==0.2.1' mcp-server-aliyun-observability 
```

3. 使用 uvx 命令启动

```bash
uvx run mcp-server-aliyun-observability
```

### 从源码安装

```bash

# clone 源码
git clone git@github.com:aliyun/alibabacloud-observability-mcp-server.git
# 进入源码目录
cd alibabacloud-observability-mcp-server
# 安装
pip install -e .
# 运行
python -m mcp_server_aliyun_observability --transport sse --access-key-id <your_access_key_id> --access-key-secret <your_access_key_secret>
```


### AI 工具集成

> 以 SSE 启动方式为例,transport 端口为 8888,实际使用时需要根据实际情况修改

#### Cursor，Cline 等集成
1. 使用 SSE 启动方式
```json
{
  "mcpServers": {
    "alibaba_cloud_observability": {
      "url": "http://localhost:7897/sse"
        }
  }
}
```
2. 使用 stdio 启动方式
   直接从源码目录启动,注意
    1. 需要指定 `--directory` 参数,指定源码目录，最好是绝对路径
    2. uv命令 最好也使用绝对路径，如果使用了虚拟环境，则需要使用虚拟环境的绝对路径
```json
{
  "mcpServers": {
    "alibaba_cloud_observability": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/your/alibabacloud-observability-mcp-server",
        "run",
        "mcp-server-aliyun-observability"
      ],
      "env": {
        "ALIBABA_CLOUD_ACCESS_KEY_ID": "<your_access_key_id>",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "<your_access_key_secret>"
      }
    }
  }
}
```
1. 使用 stdio 启动方式-从 module 启动
```json
{
  "mcpServers": {
    "alibaba_cloud_observability": {
      "command": "uv",
      "args": [
        "run",
        "mcp-server-aliyun-observability"
      ],
      "env": {
        "ALIBABA_CLOUD_ACCESS_KEY_ID": "<your_access_key_id>",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "<your_access_key_secret>"
      }
    }
  }
}
```

#### Cherry Studio集成

![image](./images/cherry_studio_inter.png)

![image](./images/cherry_studio_demo.png)


#### Cursor集成

![image](./images/cursor_inter.png)

![image](./images/cursor_tools.png)

![image](./images/cursor_demo.png)


#### ChatWise集成

![image](./images/chatwise_inter.png)

![image](./images/chatwise_demo.png)

