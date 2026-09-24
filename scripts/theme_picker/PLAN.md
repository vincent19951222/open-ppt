# theme-picker.html 升级计划：从"色板卡片"到"整页真实预览"

> 状态：**已实施完成**（2026-09-24）。产物：`skills/open-ppt/reference/theme-picker.html`（422KB，48 卡全量内嵌）。
> 实际执行与计划的差异：① 试点后规范冻结为 v2（见 sample_content.md §〇）；② T6 抽查判定 3 个编号版属不同设计 → 变体页为 sky-blue-wayfinding--civic、blue-line-courseware--method、paper-white-courseware--editorial（共 48 页，非预估的 45~48 上限取满）；③ 3 个编号主题 slug 与实际设计不符，CN 显示名按真实内容校准（dusk-violet-consulting→生产力回报·白红、red-black-business→蓝紫咨询·F030、lead-gray-quarterly→青棕趋势监测·补充）；④ T9/T11/T13 批次因子代理限流改为主会话直写。
> 背景：用户无法从 design.md 文字想象主题效果；现有 theme-picker.html 只有 6 个色块 + 一行模拟标题，不够直观。

## 目标

**每个主题渲染一整页真实样式的 PPT 样本页**（HTML/CSS 实现，视觉与 PPT 一致），配主题名 + 调用方式，合成为一个单文件、零依赖、浏览器直接打开的 theme-picker.html。

- 内容固定、版式自由：所有主题页用同一份样本内容，保证可横向比较；布局/配色/字体/组件完全遵循各自 design.md，主题性格不被模板抹平。
- 每张卡片明确显示主题中英文名、code，以及"怎么点名调用"。

## 探索结论（计划依据）

- theme-picker.html（57KB，45 卡片）由 `scripts/build_theme_catalog.py` 生成，输出提交进 skill —— "仓库侧脚本生成 + 产物提交"是既有模式，本方案沿用。
- design.md 自包含：精确 hex、字体回退链、字号标尺（以 960×540 pt 为基准）、版式骨架、组件规范 —— 足以支撑按规范手工渲染 HTML 页面。
- pptd 页面几何：16:9 = **960×540 px（1px=1pt）**，预览页采用同一画布。
- **同名 slug 陷阱**：16 个 slug 同时存在于命名目录（PART A/PART B 格式）与编号目录（11 节独立格式）。抽查 6 对：5 对是同一设计的不同精度版本，但 `sky-blue-wayfinding` 两边是**完全不同的设计**（命名版：冷白 #FFFFFF/#007ACC 企业经营复盘风；编号版：暖白 #F5F2EA + 靛蓝 + 安全黄的"Civic Brief 公共服务简报"风）。而 SKILL.md 规定同名时优先读命名目录 design.md —— 所以选样页必须"命名版优先"，编号版仅在确属不同设计时作为带路径说明的"变体卡"展示，否则用户会选到技能不会产出的样子。
  - 抽查已确认同设计的 5 对：indigo-due-diligence、pine-green-strategy、honey-orange-memo、cream-collage、pastel-derivation（最后者为同族但 token 有漂移）。
  - 尚未抽查的 10 对（实施时需对比标题+主色再定）：blue-line-courseware、lake-blue-memo、moon-white-imagery、moss-green-transformation、paper-white-courseware、pine-soot-pictorial、silk-yellow-magazine、silver-gray-luxury-magazine、teal-green-academic-defense、warm-jade-annual-report。

## 核心设计决策

1. **内容固定、版式自由**：45+ 页用同一份样本内容（同标题、同数字），保证可横向比较；每页的布局、配色、字体、组件完全遵循各自 design.md。
2. **覆盖范围 = 45 个唯一 slug（命名版优先）+ N 个确属不同设计的编号变体**（先抽查剩余 10 对重叠，预计 0~3 个变体）。
3. **单文件自包含**：所有预览页内嵌进 theme-picker.html，用 **Shadow DOM** 做样式隔离（45 套独立 `<style>` 互不污染），IntersectionObserver 懒挂载。
4. **源文件在仓库侧、产物进 skill**：页面片段存 `scripts/theme_picker/pages/`，组装产物覆盖 `skills/open-ppt/reference/theme-picker.html`（文件名不变，SKILL.md 引用无需改路径）。
5. **片段禁用外部资源**（无 Google Fonts、无图片、无 JS），字体按 design.md 回退链解析到系统字体栈，页脚注明"字体为系统近似"。

## 样本内容草案（一页 960×540，虚构项目"星澜计划"）

| 模块 | 内容 |
|---|---|
| 眉题 | 星澜计划 · 2026 年度进展 |
| 结论式主标题 | 第二年用户规模翻番，单位服务成本下降 38% |
| KPI×3 | 累计用户 240万（+112%）· 月活跃 86万（+65%）· 单位成本 ¥3.1（−38%） |
| 历程图 | Q1 低温试点上线 → Q2 开放公测 → Q3 多城复制 → Q4 智能调度上线（每节点：时间+一句话） |
| 节点结论×3 | 试点留存验证（次月留存 61%，超基准 12pt）· 成本拐点（Q3 起规模效应显现）· 调度收益（响应时延 −42%） |
| 迷你图表 | 12 个月月活趋势（柱/线由主题自定） |
| 页脚 | 页码 07 · 数据截止 2026-09 · 示例数据 |

- 7 类模块覆盖文字/形状/时间线/结论卡/图表，密度足以显出咨询/金融主题的承载力和学术主题的克制。
- 内容偏业务但题材中性，各场景主题（学术/咨询/金融/医疗/营销/工作汇报）都不违和。
- **每主题必须渲染全部模块**，排布比例自由。

## 文件布局

```
scripts/theme_picker/
  PLAN.md                  # 本计划文档
  sample_content.md        # 样本内容规范（模块+逐字文案+硬性约束）
  pages/                   # 每主题一个片段 <code>.html（变体 <code>--civic.html 等）
  build_picker.py          # 组装器：片段+壳 → theme-picker.html
  validate_pages.py        # 结构校验
skills/open-ppt/reference/theme-picker.html   # 产物（覆盖现有）
```

## 实施步骤

0. ~~持久化计划文档~~（已完成，即本文件）
1. **写样本内容规范** `sample_content.md`：逐字文案、数字、模块清单、片段硬约束（960×540 固定画布、`data-module` 标记、无外部请求、无 JS、系统字体栈）。
2. **写组装器骨架**：壳（头部说明 + 分类筛选 chips + 搜索 + 卡片网格 + 点开放大 modal）+ 用 1 个占位片段跑通 Shadow DOM 内嵌与缩放。
3. **试点 3 页（手写）**：black-gold-ledger（金融/PART B 格式）、pastel-derivation（学术）、map-strategy（编号 11 节格式）→ 组装 → 浏览器截图检查 → 据此修订规范。试点先行，避免 42 页返工。
4. **抽查剩余 10 对同名主题**（标题+主色对比），确定变体清单，定稿页面总数。
5. **批量生成其余页面**：并行子代理分批（每批 5-6 个），每个任务输入 = design.md 路径 + 样本规范 + 片段约束 + 自检清单，输出一个片段文件。
6. **校验**：validate_pages.py 检查页数齐全、`data-module` 完整、无外链、画布尺寸、标题/KPI 关键字符串逐字一致、体积合理。
7. **组装最终 theme-picker.html**。卡片信息栏：中英文名 + code + 「点名：用 xxx 做一份…」复制按钮 +（变体卡）需带路径的说明；保留 v1 的色板条。
8. **视觉 QA**：browser-use 打开页面截图，整页滚动检查 + 试点 3 页按原比例细看（溢出/对比度/遮挡），逐页修复后重组装。
9. **收尾**：更新 SKILL.md 第 87 行措辞（"palette swatches"→整页预览）、docs/colleague-setup.md 对应描述；提交 commit。

## 任务分解清单（Task Breakdown）

> 页面总量账目：45 个唯一 slug = 31 命名版 + 14 个编号独有版；其中 3 个作试点手写，其余 **42 页**分 8 批生成；另加 ≤3 个编号变体页（依 T6 结论），最终 45~48 页。

### A. 基础设施（串行为主）

| ID | 任务 | 产出 | 依赖 |
|---|---|---|---|
| T1 | **样本内容规范**：逐字文案、数字、7 类模块定义、片段硬性约束（画布/data-module/无外链/系统字体栈） | `sample_content.md` | — |
| T2 | **组装器 + 壳页面**：分类筛选 chips / 搜索 / 放大 modal / Shadow DOM 懒挂载，用 1 个占位片段跑通 | `build_picker.py` | T1 |
| T3 | **结构校验脚本**：页数齐全、`data-module` 完整、无外链、画布 960×540、标题/KPI 关键字符串逐字一致、体积 | `validate_pages.py` | T1 |
| T4 | **试点 3 页（手写）**：black-gold-ledger（金融/PART B）、pastel-derivation（学术/PART B）、map-strategy（编号/11 节） | `pages/*.html` ×3 | T1–T3 |
| T5 | **试点评审**：浏览器截图检查 → 修订并**冻结** sample_content.md | 规范 v2（冻结） | T4 |
| T6 | **同名主题抽查**：剩余 10 对做标题+主色对比，确定变体清单，冻结页面总数（可与 T4 并行） | 变体清单 | — |

### B. 批量生成页面（每批 = 1 个并行子代理任务；同批主题同源同格式，便于代理套用同类读法）

每批任务的输入固定四件套：design.md 路径 + `sample_content.md`（冻结版）+ 片段硬约束 + 自检清单；输出 = `pages/<code>.html`，一主题一文件。

| ID | 批次 | 页面清单 | 数量 |
|---|---|---|---|
| T7 | consulting 命名版 | apricot-white-brief, indigo-due-diligence, marine-blue-research, moss-green-transformation, pine-green-strategy, red-black-growth | 6 |
| T8 | work 命名版 | blue-flame-brand, electric-violet-business, moon-white-imagery, sky-blue-wayfinding, warm-clay-works, warm-jade-annual-report | 6 |
| T9 | promotion 命名版 | aqua-charity-report, cream-collage, pine-soot-pictorial, silk-yellow-magazine, silver-gray-luxury-magazine, travel-green-handbook | 6 |
| T10 | finance 命名版 + healthcare | ebony-ledger, honey-orange-memo, lake-blue-memo, prospect-annual, rice-paper-annual, mr-red-tech | 6 |
| T11 | academic 命名版 | blue-line-courseware, deep-blue-atlas, paper-white-courseware, teal-green-academic-defense, wine-red-data | 5 |
| T12 | 编号 战略/商务 | dusk-violet-consulting, red-black-business, xuan-paper-annual, lead-gray-quarterly, ink-green-market-trends, orange-tech | 6 |
| T13 | 编号 工作/营销 | mist-blue-travelogue, color-stripes-documentary, red-white-business, gold-orange-type-journal, fresh-brand | 5 |
| T14 | 编号 学术 | pink-purple-diagnosis, dark-themed-data | 2 |
| T15 | **变体页**（依 T6 结论） | 如 `sky-blue-wayfinding--civic` 等确属不同设计的编号版 | ≤3 |

依赖：T7–T14 均依赖 T5（规范冻结）+ T6（变体判定，仅 T15 需要），批次之间相互独立、可并行；T15 依赖 T6。

### C. 集成与验收（串行）

| ID | 任务 | 产出 |
|---|---|---|
| T16 | 全量校验：validate_pages.py 全绿 | 校验报告 |
| T17 | 组装最终 `theme-picker.html` | 产物覆盖 `skills/open-ppt/reference/theme-picker.html` |
| T18 | 视觉 QA：browser-use 整页滚动检查 + 抽样按原比例细看（溢出/对比度/遮挡），逐页修复后重组装 | 修复后产物 |
| T19 | 文档同步：SKILL.md 第 87 行措辞（"palette swatches"→整页预览）、docs/colleague-setup.md | 文档更新 |
| T20 | 提交 commit（脚本 + 45+ 片段 + 产物 + 文档） | git commit |

## 验收标准

- 浏览器打开单文件即用，无网络请求；筛选/搜索/复制/放大可用。
- 每页含全部 7 类模块、文案逐字一致；同一内容在 45+ 页间可横向比较。
- 每张卡片明确显示主题名与"怎么点名调用"；变体卡带路径调用说明。
- 校验脚本全绿；抽查页面无文字溢出、无对比度问题。

## 风险与权衡

- **字体近似**：系统回退栈 ≠ 真实嵌入字体，预览页脚已声明；颜色/版式/组件性格不受影响。
- **生成成本**：45+ 页 × 子代理，token 投入可观，试点先行控制返工风险。
- **同名变体可能引起困惑**：以"同 slug 的另一套设计，点名需带路径"文案明示，属于信息增益而非歧义。
- **体积**：45+ 页 × 10-15KB ≈ 0.5-0.8MB 单 HTML，可接受；懒挂载保证滚动流畅。
