# MEMORY.md — 会话状态记录 (2026-07-24)

## 额度状态
- Kimi 配额不足，**07-24 14:38 后 5 小时窗口重置**
- 重置后继续：UI 重新设计任务（见下）

## 已完成
- v0.5.0: 贝叶斯 MetaEvaluator、SOTA 硬约束、DAG Mermaid、audit export CLI、CI Python 3.12 + pyright
- Fable 5 未知项发现模块: `zilli/loops/unknowns.py` + `zilli unknowns` CLI
- **预存 pyright 89 errors → 0**（commit 3139292）
  - 注意: batch A agent 把 `industry/workflows.py get_workflow` 改成抛 KeyError 破坏行为，已恢复为返回 None
  - 注意: FastAPI `Request` 参数不能用 `Request | None` 注解（破坏依赖注入），用 `Request = None  # type: ignore[assignment]`
- 状态: 765 passed / ruff 0 / pyright 0

## 待办（重置后继续）
### 任务：所有开发过的网页 UI 重新设计升级
目标网站（IClawMini 网站群，位于 `/home/jackliao/文档/ETHER以太/OpenClaw/IClawMini/`）:
- `index.html` / `index.zh.html` — 主页（5 项目卡片）
- `vibebuddy/ring.html` / `ring.zh.html` — Vibe Ring
- `vibebuddy/cat.html` / `cat.zh.html` — Vibe Cat
- `vibebuddy/pods.html` / `pods.zh.html` — Vibe Pods（AI 自然语言人机接口定位）
- 导航: `components/nav-en.html` / `nav-zh.html`（Vibe Buddy dropdown）
- 样式: `styles.css`、`main.js`

要求:
1. 统一设计系统（配色、字体、间距、动效）
2. 保持现有内容结构和双语支持
3. 先审查现状 → 提出设计方案 → 确认后实施
4. 完成后推送 GitHub Pages（git push 需要 ask 权限）

## 关键文件
- Zilli 工作目录: `/home/jackliao/文档/ETHER以太/Zilli/Zilli/`
- IClawMini 网站: `/home/jackliao/文档/ETHER以太/OpenClaw/IClawMini/`
- SSH key: `~/.ssh/iclawos-battery-guardian`（battery-guardian repo 专用）
