#!/usr/bin/env python3
"""Generate reference/theme-picker.html from design_system specs.

Extracts real hex colors and the style signature line from every theme's
design.md so users can eyeball all presets in a browser and name the one
they want. Repo-side maintenance tool; output is committed into the skill.
"""

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESIGN_SYSTEM = ROOT / "skills" / "open-ppt" / "reference" / "design_system"
OUTPUT = ROOT / "skills" / "open-ppt" / "reference" / "theme-picker.html"

CATEGORY_ZH = {
    "academic": "学术教育",
    "consulting": "咨询",
    "finance": "财经",
    "healthcare": "医疗科技",
    "promotion": "品牌推广",
    "work": "工作汇报",
    "01_strategy": "战略",
    "02_business": "商务",
    "03_work": "工作汇报",
    "04_promotion": "品牌推广",
    "05_academic": "学术教育",
}

HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}\b")


def luminance(hex6: str) -> float:
    r, g, b = (int(hex6[i : i + 2], 16) for i in (1, 3, 5))
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def parse_design_md(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    h1 = text.splitlines()[0].lstrip("# ").strip()
    name = re.split(r"\s+[—··]\s+|\s+·\s+", h1)[0].replace(" STYLE DESIGN SYSTEM", "").strip()

    hexes = [h.upper() for h in HEX_RE.findall(text)]
    counts = Counter(hexes)
    ordered = []
    for h in hexes:
        if h not in ordered:
            ordered.append(h)
    ordered.sort(key=lambda h: -counts[h])
    primary = ordered[0] if ordered else "#4A5568"

    signature = ""
    m = re.search(r"One-line style signature:\s*(.+)", text)
    if m:
        signature = m.group(1).strip()

    return {"name": name, "hexes": ordered[:6], "primary": primary, "signature": signature}


def collect_themes() -> list:
    themes, seen_names = [], set()

    for design_md in sorted(DESIGN_SYSTEM.glob("*/*/design.md")):
        folder = design_md.parent.name
        category = CATEGORY_ZH.get(design_md.parent.parent.name, design_md.parent.parent.name)
        info = parse_design_md(design_md)
        info.update(code=folder, category=category)
        themes.append(info)
        seen_names.add(folder)

    for numbered in sorted(DESIGN_SYSTEM.glob("0*/*/en/*.md")):
        stem = numbered.stem
        if stem in seen_names:
            continue
        category = CATEGORY_ZH.get(numbered.parts[-4], numbered.parts[-4])
        info = parse_design_md(numbered)
        info.update(code=stem, category=f"{category}·补充")
        themes.append(info)
        seen_names.add(stem)

    return themes


def render_card(theme: dict) -> str:
    swatches = "".join(
        f'<div class="sw" style="background:{h}" title="{h}"><span>{h}</span></div>'
        for h in theme["hexes"]
    ) or '<div class="sw" style="background:#CBD5E0"><span>—</span></div>'
    sig = f'<p class="sig">{theme["signature"]}</p>' if theme["signature"] else ""
    name_attr = theme["name"].replace('"', "&quot;")
    code_attr = theme["code"].replace('"', "&quot;")
    return f"""<article class="card" data-name="{name_attr}" data-code="{code_attr}">
  <div class="head" style="background:{theme['primary']}">
    <h2>{theme["name"]}</h2><span class="cat">{theme["category"]}</span>
  </div>
  <div class="swatches">{swatches}</div>
  <div class="mock">
    <p class="mock-title" style="color:{theme['primary']}">❯ 页标题是一句完整结论</p>
    <p class="mock-body">正文 12–14pt 黑体，数据大字用主色。</p>
  </div>
  {sig}
  <p class="code">点名：<code>{theme["code"]}</code><button class="copy" data-code="{code_attr}">复制</button></p>
</article>"""


def main() -> None:
    themes = collect_themes()
    cards = "\n".join(render_card(t) for t in themes)
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>open-ppt 主题选样页 · 共 {len(themes)} 套</title>
<style>
  * {{ box-sizing: border-box; margin: 0; }}
  body {{ font-family: "Microsoft YaHei", "PingFang SC", sans-serif; background:#F1F5F9; padding:24px; }}
  header {{ max-width:1280px; margin:0 auto 16px; }}
  h1 {{ font-size:20px; color:#1A202C; }}
  header p {{ color:#4A5568; font-size:13px; margin-top:4px; }}
  #filter {{ margin-top:10px; padding:8px 12px; width:320px; border:1px solid #CBD5E0; border-radius:6px; font-size:14px; }}
  main {{ max-width:1280px; margin:0 auto; display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:16px; }}
  .card {{ background:#fff; border:1px solid #E2E8F0; border-radius:8px; overflow:hidden; }}
  .head {{ padding:12px 14px; color:#fff; display:flex; justify-content:space-between; align-items:baseline; gap:8px; }}
  .head h2 {{ font-size:15px; }}
  .cat {{ font-size:11px; opacity:.85; white-space:nowrap; }}
  .swatches {{ display:flex; }}
  .sw {{ flex:1; height:26px; position:relative; }}
  .sw span {{ position:absolute; inset:0; display:flex; align-items:center; justify-content:center; font-size:9px; color:#fff; text-shadow:0 0 3px rgba(0,0,0,.6); opacity:0; transition:opacity .15s; }}
  .sw:hover span {{ opacity:1; }}
  .mock {{ padding:14px; }}
  .mock-title {{ font-size:15px; font-weight:700; }}
  .mock-body {{ font-size:12px; color:#4A5568; margin-top:6px; }}
  .sig {{ padding:0 14px; font-size:11px; color:#718096; line-height:1.5; }}
  .code {{ padding:10px 14px 14px; font-size:12px; color:#2D3748; }}
  .code code {{ background:#EDF2F7; padding:2px 6px; border-radius:4px; font-size:12px; }}
  .copy {{ margin-left:8px; border:1px solid #CBD5E0; background:#fff; border-radius:4px; font-size:11px; padding:2px 8px; cursor:pointer; }}
  .copy:hover {{ background:#EDF2F7; }}
</style>
</head>
<body>
<header>
  <h1>open-ppt 主题选样页 · 共 {len(themes)} 套</h1>
  <p>挑一个顺眼的，点「复制」把名字发给 AI：「用 &lt;名字&gt; 风格做一份 PPT，主题是 …」。色块悬停可看色值。</p>
  <input id="filter" placeholder="筛选：医疗 / 咨询 / 深红 / academic …">
</header>
<main>
{cards}
</main>
<script>
const f = document.getElementById('filter');
f.addEventListener('input', () => {{
  const q = f.value.trim().toLowerCase();
  document.querySelectorAll('.card').forEach(c => {{
    c.style.display = (!q || c.dataset.name.toLowerCase().includes(q) || c.dataset.code.includes(q)) ? '' : 'none';
  }});
}});
document.addEventListener('click', e => {{
  const btn = e.target.closest('.copy');
  if (!btn) return;
  navigator.clipboard.writeText(btn.dataset.code);
  btn.textContent = '已复制';
  setTimeout(() => btn.textContent = '复制', 1200);
}});
</script>
</body>
</html>
"""
    OUTPUT.write_text(html, encoding="utf-8")
    print(f"OK: {OUTPUT} ({len(themes)} themes)")


if __name__ == "__main__":
    main()
