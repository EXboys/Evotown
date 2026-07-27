import { useEffect, useState } from "react";

/** Logo 组件：优先显示系统配置中上传的 logo.png，加载失败时回退到首字母图标 */
export function SystemLogo({
  className = "",
  fallbackLetter = "E",
  cacheBuster = 0,
}: {
  className?: string;
  fallbackLetter?: string;
  cacheBuster?: number;
}) {
  const [failed, setFailed] = useState(false);

  // 当 cacheBuster 变化时重置 failed 状态（例如上传新 logo 后）
  useEffect(() => {
    setFailed(false);
  }, [cacheBuster]);

  if (failed) {
    return (
      <span
        className={`flex items-center justify-center bg-slate-950 text-sm font-semibold text-white ${className}`}
      >
        {fallbackLetter}
      </span>
    );
  }

  return (
    <img
      src={`/system/logo.png?t=${Date.now()}&v=${cacheBuster}`}
      alt="Logo"
      className={`object-contain ${className}`}
      onError={() => setFailed(true)}
    />
  );
}
