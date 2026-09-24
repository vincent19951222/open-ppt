# open-ppt 技能 · 发给同事的安装说明

> 给完全不懂技术的同事看。他只需要：装一次 Python → 把文件夹放对位置 → 对 AI 说一句话。

---

## 一、前提：电脑要有 Python 3（只装一次）

1. 打开 https://www.python.org/downloads/ ，下载安装
2. **安装第一屏务必勾选 "Add python.exe to PATH"**（最容易漏的一步）
3. 装完重开终端，输入 `python -V`，显示 `Python 3.x` 就成功了

> 没有 Python，AI 只能生成 PPTD 工程目录，出不了 .pptx 文件。

## 二、安装（二选一）

### 方法一：让 AI 帮你装（推荐）

把压缩包发给同事，让同事把下面这句原话发给他的 AI 助手（Kimi Code / Claude Code / Cursor 等都行）：

```
请把压缩包里的 open-ppt 文件夹解压到 C:\Users\你的用户名\.agents\skills\ 下面，
没有这个目录就创建，装完告诉我装到了哪里。
```

### 方法二：手动放

1. 解压 `open-ppt-skill.zip`
2. 把 **open-ppt 整个文件夹**复制到：`C:\Users\你的用户名\.agents\skills\` 下面
   - `.agents` 文件夹在用户主目录里，可能是隐藏的；没有就新建
3. 装好后最终位置应该长这样：`C:\Users\你的用户名\.agents\skills\open-ppt\SKILL.md`
4. Mac 同理：`~/.agents/skills/open-ppt/`

> WorkBuddy 用户例外：要放到 `C:\Users\你的用户名\.workbuddy\skills\` 下面。

## 三、装好后怎么验证

对 AI 说：

```
用 open-ppt 做一个介绍咖啡的 PPT，3 页，深色科技风
```

AI 会生成一个项目文件夹，里面有 `.pptd` 清单、`pages/` 页面、以及编译好的 `.pptx` —— 能打开 .pptx 就说明装好了。

之后正常使用就是这种话术：

```
用 open-ppt 做一份《XX产品介绍》PPT，10 页，用 mr-red-tech 医疗科技风
```

**不知道用哪个主题？** 双击打开 `open-ppteference	heme-picker.html`（浏览器直接开），
45 套主题的配色一目了然，点「复制」拿到名字，告诉 AI「用 xx 风格」即可。

## 四、常见问题

| 现象 | 解决 |
|------|------|
| 提示找不到 python | 重装 Python，勾选 Add python.exe to PATH，重开终端 |
| 提示装 PyYAML 失败（公司内网） | 让 AI 执行：`python -m pip install --user pyyaml -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| AI 说找不到这个技能 | 检查文件夹位置：必须是 `.agents\skills\open-ppt\SKILL.md` 这个层级 |

## 五、给分享者（你）的备注

- 要分享的包：仓库根目录运行打包，或直接用现成的 `dist/open-ppt-skill.zip`
- 包里只有 `open-ppt/` 一个文件夹 + 本说明，共约 8MB
- 仓库里其余目录（bin/lib/editor/docs/example 等）**不需要发给同事**，也不影响使用
- 技能升级后重新打一次包发给同事，让他覆盖 `open-ppt` 文件夹即可
