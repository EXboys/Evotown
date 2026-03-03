#!/usr/bin/env python3
"""
HTTP Request Skill - 发起 HTTP 网络请求
优化版：支持旧版 SSL 服务器、浏览器级 User-Agent、重试逻辑、HTML→Markdown 转换
"""

import json
import re
import ssl
import sys
import time

# html2text：HTML 转 Markdown，默认用于网页内容，降低 token 消耗
try:
    import html2text
    HAS_HTML2TEXT = True
except ImportError:
    HAS_HTML2TEXT = False

# 优先使用 requests（更稳健），fallback 到 urllib
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import urllib.parse
    import urllib.error


# 浏览器级 User-Agent，减少 503/反爬拦截
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Wikimedia/Wikipedia API 要求：必须使用描述性 User-Agent，否则返回 403 Too Many Requests
# 参见 https://meta.wikimedia.org/wiki/User-Agent_policy
WIKIMEDIA_USER_AGENT = (
    "SkillLite/1.0 (https://github.com/EXboys/skilllite; skilllite-http-request)"
)

# 默认请求头，模拟真实浏览器
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _is_wikimedia_url(url: str) -> bool:
    """判断是否为 Wikipedia/Wikimedia 域名，需使用合规 User-Agent"""
    if not url:
        return False
    return "wikipedia.org" in url or "wikimedia.org" in url or "wikidata.org" in url


def _is_wttr_url(url: str) -> bool:
    """wttr.in 对浏览器 UA 返回 HTML，需用 curl UA 才能拿到 JSON (format=j1)"""
    return url and "wttr.in" in url


# wttr.in 检测浏览器 UA 会返回 HTML；curl UA 才能拿到 JSON
WTTR_USER_AGENT = "curl/8.0"


def _looks_like_html(body: str, headers: dict) -> bool:
    """判断响应是否为 HTML"""
    if not body or not isinstance(body, str):
        return False
    ct = ""
    for k, v in (headers or {}).items():
        if k.lower() == "content-type":
            ct = str(v).lower()
            break
    if "text/html" in ct or "application/xhtml" in ct:
        return True
    stripped = body.strip()
    return stripped.startswith("<!") or stripped.lower().startswith("<html")


def _convert_html(body: str, extract_mode: str) -> str:
    """将 HTML 转为 Markdown 或纯文本"""
    if extract_mode == "raw":
        return body
    if extract_mode == "text":
        # 纯文本：去除标签
        return re.sub(r"<[^>]+>", "", body).strip()
    # extract_mode == "markdown"（默认）
    if HAS_HTML2TEXT:
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0  # 不自动换行
        return h.handle(body).strip()
    # 无 html2text 时退化为纯文本
    return re.sub(r"<[^>]+>", "", body).strip()


def _create_ssl_context_legacy():
    """创建支持旧版 SSL 服务器的上下文（解决 UNSAFE_LEGACY_RENEGOTIATION_DISABLED）"""
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    # OP_LEGACY_SERVER_CONNECT = 0x4，允许连接不支持 RFC 5746 安全重协商的旧服务器
    if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
        ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
    else:
        ctx.options |= 0x4  # OpenSSL 常量，兼容旧版 Python
    return ctx


def _create_http_adapter(use_legacy_ssl=True):
    """创建 HTTP Adapter：支持旧版 SSL + 重试"""
    class LegacySSLAdapter(HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            if use_legacy_ssl:
                kwargs["ssl_context"] = _create_ssl_context_legacy()
            return super().init_poolmanager(*args, **kwargs)

    retry = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[502, 503, 504],
        allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"],
    )
    return LegacySSLAdapter(max_retries=retry)


def _normalize_headers(headers_raw):
    """解析 headers：支持 dict 或 JSON 字符串（Agent 可能传字符串）"""
    if headers_raw is None:
        return {}
    if isinstance(headers_raw, dict):
        return dict(headers_raw)
    if isinstance(headers_raw, str):
        try:
            parsed = json.loads(headers_raw)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _normalize_timeout(timeout_raw):
    """将 timeout 转为 int/float，Agent 可能传字符串如 "30" """
    if timeout_raw is None:
        return 30
    if isinstance(timeout_raw, (int, float)):
        return timeout_raw
    if isinstance(timeout_raw, str):
        try:
            return int(float(timeout_raw))
        except (ValueError, TypeError):
            return 30
    return 30


def _normalize_params(params_raw):
    """解析 params：支持 dict 或 JSON 字符串（Agent 可能传 params: "{\"q\": \"...\"}"）"""
    if params_raw is None:
        return {}
    if isinstance(params_raw, dict):
        return dict(params_raw)
    if isinstance(params_raw, str):
        try:
            parsed = json.loads(params_raw)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _fix_wikipedia_api_params(url: str, params: dict) -> dict:
    """
    Agent 常传 params={"q": "..."}，但 MediaWiki API 需要 action=query&list=search&srsearch=...
    自动转换为合规格式，避免 403 / 无效请求。
    """
    if not _is_wikimedia_url(url) or "/api.php" not in url:
        return params
    if "action" in params:
        return params  # 已是正确格式
    q = params.get("q") or params.get("query") or params.get("search")
    if q is None:
        return params
    q_str = str(q).strip() if q else ""
    if not q_str:
        return params
    return {
        "action": "query",
        "list": "search",
        "srsearch": q_str,
        "format": "json",
        "srlimit": "5",
    }


def _request_with_requests(input_data):
    """使用 requests 库发起请求"""
    url = input_data.get("url")
    method = input_data.get("method", "GET").upper()
    headers = _normalize_headers(input_data.get("headers"))
    body = input_data.get("body")
    params = _normalize_params(input_data.get("params"))
    params = _fix_wikipedia_api_params(url, params)
    timeout = _normalize_timeout(input_data.get("timeout"))
    use_legacy_ssl = input_data.get("use_legacy_ssl", True)  # 默认启用，兼容旧服务器

    if "User-Agent" not in headers:
        if _is_wikimedia_url(url):
            headers["User-Agent"] = WIKIMEDIA_USER_AGENT
        elif _is_wttr_url(url):
            headers["User-Agent"] = WTTR_USER_AGENT  # wttr.in 对浏览器 UA 返回 HTML
        else:
            headers["User-Agent"] = DEFAULT_USER_AGENT
    for k, v in DEFAULT_HEADERS.items():
        if k not in headers:
            headers[k] = v

    # Wikimedia API 连续请求易触发 403，间隔 2.5 秒降低限流概率
    if _is_wikimedia_url(url):
        time.sleep(2.5)

    session = requests.Session()
    adapter = _create_http_adapter(use_legacy_ssl=use_legacy_ssl)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        if body is not None and method in ["POST", "PUT", "PATCH"]:
            resp = session.request(
                method, url, json=body, params=params, headers=headers, timeout=timeout
            )
        else:
            resp = session.request(
                method, url, params=params, headers=headers, timeout=timeout
            )

        # 尝试解析 JSON
        try:
            response_json = resp.json()
            body_out = response_json
        except Exception:
            body_out = resp.text

        # 4xx/5xx 视为失败（与旧版行为一致）
        if resp.status_code >= 400:
            out = {
                "success": False,
                "status_code": resp.status_code,
                "error": resp.reason or f"HTTP {resp.status_code}",
                "body": body_out,
            }
            if resp.status_code == 403 and _is_wikimedia_url(url):
                out["hint"] = "Wikipedia 403: IP 可能被临时限流，请 5–10 分钟后再试或换网络；或改用 Wikipedia REST API: https://en.wikipedia.org/api/rest_v1/page/summary/Chiang_Mai"
            return out
        return {
            "success": True,
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body": body_out,
            "is_json": isinstance(body_out, dict),
        }

    except requests.exceptions.SSLError as e:
        # SSL 错误时，若未用 legacy，可提示尝试 use_legacy_ssl
        return {
            "success": False,
            "error": f"SSL Error: {str(e)}",
            "hint": "部分旧版服务器需 use_legacy_ssl: true（已默认启用）",
        }
    except requests.exceptions.ConnectionError as e:
        err_msg = str(e)
        if "nodename nor servname" in err_msg or "Name or service not known" in err_msg:
            return {"success": False, "error": "DNS 解析失败，请检查域名或网络"}
        return {"success": False, "error": f"Connection Error: {err_msg}"}
    except requests.exceptions.Timeout:
        return {"success": False, "error": f"请求超时（{timeout} 秒）"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def _request_with_urllib(input_data):
    """使用 urllib 发起请求（无 requests 时的 fallback）"""
    url = input_data.get("url")
    method = input_data.get("method", "GET").upper()
    headers = _normalize_headers(input_data.get("headers"))
    body = input_data.get("body")
    params = _normalize_params(input_data.get("params"))
    params = _fix_wikipedia_api_params(url, params)
    timeout = _normalize_timeout(input_data.get("timeout"))

    if "User-Agent" not in headers:
        if _is_wikimedia_url(url):
            headers["User-Agent"] = WIKIMEDIA_USER_AGENT
        elif _is_wttr_url(url):
            headers["User-Agent"] = WTTR_USER_AGENT
        else:
            headers["User-Agent"] = DEFAULT_USER_AGENT

    if _is_wikimedia_url(url):
        time.sleep(2.5)
    for k, v in DEFAULT_HEADERS.items():
        if k not in headers:
            headers[k] = v

    if params:
        from urllib.parse import urlencode, urlparse, parse_qs
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{urlencode(params)}"

    data = None
    if body is not None and method in ["POST", "PUT", "PATCH"]:
        data = json.dumps(body).encode("utf-8")
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    ctx = _create_ssl_context_legacy()

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            resp_body = resp.read().decode("utf-8")
            try:
                body_out = json.loads(resp_body)
            except json.JSONDecodeError:
                body_out = resp_body
            return {
                "success": True,
                "status_code": resp.status,
                "headers": dict(resp.headers),
                "body": body_out,
                "is_json": isinstance(body_out, dict),
            }
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            pass
        return {
            "success": False,
            "status_code": e.code,
            "error": str(e.reason),
            "body": err_body,
        }
    except urllib.error.URLError as e:
        err = str(e.reason)
        if "UNSAFE_LEGACY_RENEGOTIATION" in err:
            return {"success": False, "error": f"SSL 错误: {err}", "hint": "建议安装 requests 库以获得更好兼容性"}
        if "nodename nor servname" in err or "Name or service not known" in err:
            return {"success": False, "error": "DNS 解析失败，请检查域名或网络"}
        return {"success": False, "error": f"URL Error: {err}"}
    except TimeoutError:
        return {"success": False, "error": f"请求超时（{timeout} 秒）"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    try:
        _main_inner()
    except Exception as e:
        # 防御性：任何未捕获异常也输出合法 JSON，避免沙箱解析失败
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))


def _main_inner():
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"Invalid JSON input: {e}"}))
        return

    url = input_data.get("url")
    if not url:
        print(json.dumps({"success": False, "error": "URL is required"}))
        return

    if HAS_REQUESTS:
        result = _request_with_requests(input_data)
    else:
        result = _request_with_urllib(input_data)

    # HTML 响应时转换为 Markdown（默认）或纯文本，降低 token 消耗
    extract_mode = input_data.get("extract_mode", "markdown")
    if (
        result.get("success")
        and not result.get("is_json")
        and isinstance(result.get("body"), str)
        and _looks_like_html(result["body"], result.get("headers", {}))
    ):
        result["body"] = _convert_html(result["body"], extract_mode)
        result["extract_mode"] = extract_mode

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
