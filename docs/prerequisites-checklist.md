# open-kimi-ppt 环境自检清单

分享给同事前的环境确认表。五项硬条件全过，再执行安装；任何一项不过，按「解决办法」处理后再继续。

## 一、硬条件自检（缺一不可）

| # | 检查项 | 为什么需要 | 自检命令 | 通过标准 |
|---|--------|-----------|----------|----------|
| 1 | Node.js 18+ | 安装 skill、起本地编辑器、驱动浏览器自动化 | `node --version` | 输出版本 ≥ v18 |
| 2 | npm / npx | 随 Node 附带，装 skill 和 agent-browser 用 | `npm --version` | 输出版本号 |
| 3 | Python 3 + pip（在 PATH 中） | **本地直出 PPTX 的核心依赖**（编译器 + 质检脚本） | `python -V` | 打印 `Python 3.x`（见坑 1） |
| 4 | Chromium 系浏览器 | 预览画布、视觉质检、可选的官方导出用（无 Chrome 自动回退 Edge）。**本地直出 PPTX 不需要浏览器** | 看机器上有没有 Chrome / Edge | 有其一即可 |
| 5 | 网络可达 Kimi 公开资源 | 预览编辑器内核和字体资源实时从线上加载；可选官方导出也需要。**本地直出 PPTX 完全离线可用** | `curl -I https://www.kimi.com` 和 `curl -I https://statics.moonshot.cn` | 都返回 HTTP 状态码 |

## 二、会自动安装的依赖（不用手动装，但要满足前提）

| 依赖 | 触发时机 | 前提 |
|------|----------|------|
| PyYAML / Pillow / websocket-client | 首次运行导出/质检脚本时自动 `pip --user install` | pip 可用，**能访问 PyPI**（公司内网需配镜像源） |
| agent-browser ≥ 0.33.2 | 首次导出时自动 `npm install -g` | **能访问 npm registry**（内网需配镜像） |

## 三、安装

```bash
npx open-kimi-ppt-skill@latest install -y
```

默认装到共享目录 `~/.agents/skills/open-kimi-ppt`（Windows 为 `%USERPROFILE%\.agents\skills\open-kimi-ppt`），Kimi Code / Codex / Claude Code / Cursor 装一次即可发现。WorkBuddy 发现不了共享目录，需要单独指定：

```bash
# Windows
npx open-kimi-ppt-skill@latest install --target %USERPROFILE%\.workbuddy\skills
```

## 四、装完后端到端验证

1. 对 Agent 说：`用 open-kimi-ppt 做一个介绍咖啡的 PPT，3 页，深色科技风`
2. 确认产出：项目目录里有 `.pptd` 清单 + `pages/` + 本地编译出的 `.pptx`（默认路径，无需浏览器和网络）
3. 可选：跑 `npx open-kimi-ppt-skill preview <项目目录>`，浏览器打开 <http://127.0.0.1:55173/> 能进入编辑器；手动导出也可用 `npx open-kimi-ppt-skill compile <项目目录>`

## 五、常见坑（出问题先看这里）

**坑 1：Windows 的 python 是应用商店占位 stub**
表现：`python -V` 无输出或弹商店。解决：从 [python.org](https://www.python.org/downloads/) 安装，**勾选 "Add python.exe to PATH"**；装完重开终端再自检。

**坑 2：导出卡在加载编辑器**
多为网络问题：确认能访问 `www.kimi.com` 和 `statics.moonshot.cn`；公司代理环境先配代理。

**坑 3：Windows 上多出一个常驻浏览器进程**
这是**设计如此**：导出用的调试浏览器（9337 端口、独立配置目录 `%TEMP%\okp-cdp-profile`、窗口在屏幕外），导完保留供下次复用。不是病毒，不用杀；杀掉也行，下次导出会自动重开。macOS / Linux 无此行为。

**坑 4：pip / npm 安装依赖失败**
内网环境检查 PyPI 和 npm 镜像源配置。

## 六、风险提示（分享给同事时请告知）

本项目是逆向实现的**非官方**兼容层，不是 Kimi 官方 SDK。Kimi 更新前端资源哈希、PPTD 格式或通信协议后，导出功能可能暂时失效，需等项目同步升级。适合学习研究和内部快速出稿，不要作为长期稳定依赖写进正式流程。
