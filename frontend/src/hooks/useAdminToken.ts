/**
 * Admin Token 管理
 *
 * token 存于 sessionStorage（关 Tab 自动清除，不进 JS bundle）。
 * 调用 adminFetch() 时若无 token 会弹出原生 prompt 要求输入。
 * 写操作统一走 adminFetch，GET 请求继续用普通 fetch。
 */

const SESSION_KEY = "evotown_admin_token";

/** 从 sessionStorage 读取 token */
export function getAdminToken(): string {
  return sessionStorage.getItem(SESSION_KEY) ?? "";
}

/** 保存 token 到 sessionStorage */
export function setAdminToken(token: string): void {
  if (token) {
    sessionStorage.setItem(SESSION_KEY, token);
  } else {
    sessionStorage.removeItem(SESSION_KEY);
  }
}

/** 清除 token（退出管理模式） */
export function clearAdminToken(): void {
  sessionStorage.removeItem(SESSION_KEY);
}

/**
 * 带 Admin Token 的 fetch 封装。
 *
 * - 若 sessionStorage 中无 token，弹出 prompt 要求输入。
 * - 若服务端返回 403，清除本地 token 并提示重新输入。
 * - 用法与普通 fetch 相同，仅适用于写操作（POST / PUT / DELETE / PATCH）。
 *
 * @example
 * const res = await adminFetch("/dispatcher/start", { method: "POST" });
 */
export async function adminFetch(
  url: string,
  init: RequestInit = {}
): Promise<Response> {
  let token = getAdminToken();

  if (!token) {
    const input = window.prompt(
      "🔑 请输入 Admin Token（仅本次会话保存，关闭 Tab 后自动清除）："
    );
    if (!input) {
      // 用户取消输入 → 返回一个假的 401 Response，不发网络请求
      return new Response(JSON.stringify({ detail: "No token provided" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }
    token = input.trim();
    setAdminToken(token);
  }

  const headers = new Headers(init.headers);
  headers.set("X-Admin-Token", token);
  headers.set("Content-Type", headers.get("Content-Type") ?? "application/json");

  const res = await fetch(url, { ...init, headers });

  if (res.status === 403) {
    // token 错误，清除并提示
    clearAdminToken();
    window.alert("❌ Admin Token 错误，已清除。请重试并输入正确的 Token。");
  }

  return res;
}

