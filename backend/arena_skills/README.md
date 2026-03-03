# EvoTown Arena 默认技能种子

新建 Agent 时，会从此目录复制以下技能到 agent 的 `.skills/`：

| 技能 | 用途 |
|------|------|
| **http-request** | HTTP 请求、API 调用、网页抓取、搜索 |
| **agent-browser** | 浏览器自动化（打开网页、填表、点击、截图） |
| **skill-creator** | 创建/设计/打包新 Skill |
| **calculator** | 数学计算 |
| **find-skills** | 发现并安装 agent skills（来自 vercel-labs/skills） |

> `list_skills` 和 `get_skill_info` 是 SkillLite 内置工具，无需单独 skill。

如需修改默认技能集，在此目录增删技能目录，并更新 `.skilllite-manifest.json`。
