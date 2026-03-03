---
name: http-request
description: 发起 HTTP 网络请求，支持 GET、POST、PUT、DELETE、PATCH 方法。当用户需要调用 API、获取网页内容、发送数据到服务器时使用。
license: MIT
compatibility: Python 3.x，推荐 requests + html2text（无 html2text 时 HTML 退化为纯文本），需网络权限
metadata:
  author: skillLite
  version: "1.0"
---

# HTTP Request Skill

一个通用的 HTTP 网络请求技能，支持常见的 RESTful API 调用。

## 功能特性

- 支持 GET、POST、PUT、DELETE、PATCH 方法
- 支持自定义请求头
- 支持 JSON 请求体
- 支持 URL 查询参数
- 支持超时设置
- **旧版 SSL 兼容**：支持连接使用旧版 TLS 的服务器（如部分政府/教育网站）
- **浏览器级 User-Agent**：减少 503/反爬拦截
- **Wikipedia/Wikimedia 合规**：访问 wikipedia.org / wikimedia.org / wikidata.org 时自动使用合规 User-Agent（否则易 403），并加 1.5 秒间隔降低限流
- **自动重试**：对 502/503/504 自动重试 2 次
- **HTML→Markdown**：网页响应自动转为 Markdown（默认），降低 token 消耗

## 使用示例

### GET 请求
```json
{
  "url": "https://httpbin.org/get",
  "method": "GET",
  "params": {"name": "test"}
}
```

### POST 请求
```json
{
  "url": "https://httpbin.org/post",
  "method": "POST",
  "headers": {"Content-Type": "application/json"},
  "body": {"message": "hello world"}
}
```

### 天气查询（推荐 Open-Meteo，免费无 key）
```json
{
  "url": "https://api.open-meteo.com/v1/forecast",
  "method": "GET",
  "params": {
    "latitude": 18.7883,
    "longitude": 98.9853,
    "daily": "temperature_2m_max,temperature_2m_min,weathercode",
    "timezone": "Asia/Bangkok",
    "forecast_days": 2
  }
}
```
清迈坐标 18.7883,98.9853。返回 JSON 含 daily.time、temperature_2m_max/min、weathercode。

wttr.in 亦可用：`https://wttr.in/Chiang_Mai?format=j1`，skill 会自动用 curl UA 以获取 JSON。

### Wikipedia 获取城市/地点摘要（推荐，限流较宽松）
```json
{
  "url": "https://en.wikipedia.org/api/rest_v1/page/summary/Chiang_Mai",
  "method": "GET"
}
```
或 `.../page/summary/Bangkok`。返回 JSON 含 extract、description、title 等。

### Wikipedia 搜索 API（params 可用 q，skill 会自动转为 action=query&list=search）
```json
{
  "url": "https://en.wikipedia.org/w/api.php",
  "method": "GET",
  "params": {"q": "Chiang Mai tourism"}
}
```

## Runtime

```yaml
entry_point: scripts/main.py
language: python
network:
  enabled: true
  outbound:
    - "*:80"
    - "*:443"
  block_private_ips: false
input_schema:
  type: object
  properties:
    url:
      type: string
      description: 请求的完整 URL
    method:
      type: string
      description: HTTP 请求方法
      enum:
        - GET
        - POST
        - PUT
        - DELETE
        - PATCH
      default: GET
    headers:
      type: object
      description: 自定义请求头
      additionalProperties:
        type: string
    body:
      type: object
      description: 请求体数据，用于 POST/PUT/PATCH，将以 JSON 格式发送
    params:
      type: object
      description: URL 查询参数
      additionalProperties: true
    timeout:
      type: number
      description: 请求超时时间（秒），默认 30 秒
      default: 30
    use_legacy_ssl:
      type: boolean
      description: 是否启用旧版 SSL 兼容（连接 cscse.edu.cn、lxgz.org.cn 等旧服务器时需 true）
      default: true
    extract_mode:
      type: string
      description: HTML 响应提取模式，markdown=转为 Markdown（默认），text=纯文本，raw=原始 HTML
      enum:
        - markdown
        - text
        - raw
      default: markdown
  required:
    - url
```
