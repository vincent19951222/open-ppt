#!/usr/bin/env python3
"""Assemble skills/open-ppt/reference/theme-picker.html from per-theme preview fragments.

Repo-side maintenance tool (stdlib only). Inputs:
  scripts/theme_picker/pages/<code>.html       one fragment per theme (style + .tp-slide)
  scripts/theme_picker/pages/<code>--<v>.html  variant fragments (same slug, divergent design)
  skills/open-ppt/reference/design_system/...  palette + signature parsed from design specs

Output overwrites skills/open-ppt/reference/theme-picker.html (committed into the skill).
"""
import html
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DS = ROOT / "skills/open-ppt/reference/design_system"
PAGES = Path(__file__).resolve().parent / "pages"
OUT = ROOT / "skills/open-ppt/reference/theme-picker.html"

# ---------------------------------------------------------------------------
# Theme registry — the 45 unique slugs (named-dir version preferred) + variants.
# kind: named = folder with design.md | extra = numbered-dir only slug | variant = numbered
#       version of a duplicated slug that is a genuinely different design (T6 verdict).
# ---------------------------------------------------------------------------
CAT_ZH_NAMED = {
    "academic": "学术", "consulting": "咨询", "finance": "金融",
    "healthcare": "医疗", "promotion": "营销", "work": "工作汇报",
}
CAT_ZH_NUM = {
    "01_strategy": "战略·补充", "02_business": "商务·补充", "03_work": "工作·补充",
    "04_promotion": "营销·补充", "05_academic": "学术·补充",
}

NAMED = [
    ("academic", "blue-line-courseware", "蓝线课件"),
    ("academic", "deep-blue-atlas", "深蓝图集"),
    ("academic", "paper-white-courseware", "纸白课件"),
    ("academic", "pastel-derivation", "粉彩推导"),
    ("academic", "teal-green-academic-defense", "青绿答辩"),
    ("academic", "wine-red-data", "酒红数据"),
    ("consulting", "apricot-white-brief", "杏白简报"),
    ("consulting", "indigo-due-diligence", "靛蓝尽调"),
    ("consulting", "marine-blue-research", "海蓝研究"),
    ("consulting", "moss-green-transformation", "苔绿转型"),
    ("consulting", "pine-green-strategy", "松绿战略"),
    ("consulting", "red-black-growth", "红黑增长"),
    ("finance", "black-gold-ledger", "黑金账本"),
    ("finance", "ebony-ledger", "乌木账本"),
    ("finance", "honey-orange-memo", "蜜橙备忘"),
    ("finance", "lake-blue-memo", "湖蓝备忘"),
    ("finance", "prospect-annual", "前景年报"),
    ("finance", "rice-paper-annual", "宣纸年报"),
    ("healthcare", "mr-red-tech", "迈瑞红科技"),
    ("promotion", "aqua-charity-report", "水色公益报告"),
    ("promotion", "cream-collage", "奶油拼贴"),
    ("promotion", "pine-soot-pictorial", "松烟画报"),
    ("promotion", "silk-yellow-magazine", "丝黄杂志"),
    ("promotion", "silver-gray-luxury-magazine", "银灰奢华杂志"),
    ("promotion", "travel-green-handbook", "旅行绿手册"),
    ("work", "blue-flame-brand", "蓝焰品牌"),
    ("work", "electric-violet-business", "电紫商务"),
    ("work", "moon-white-imagery", "月白影像"),
    ("work", "sky-blue-wayfinding", "天蓝导引"),
    ("work", "warm-clay-works", "暖陶作品"),
    ("work", "warm-jade-annual-report", "暖玉年报"),
]
NAMED_CAT_DIR = {"academic": "academic", "consulting": "consulting", "finance": "finance",
                 "healthcare": "healthcare", "promotion": "promotion", "work": "work"}

EXTRA = [  # (numbered dir, slot, slug, cn) — cn labels verified against each spec's actual
           # content (T6/H1 audit): three slugs misleadingly describe their source design.
    ("01_strategy", "01", "dusk-violet-consulting", "生产力回报·白红"),
    ("01_strategy", "04", "red-black-business", "蓝紫咨询·F030"),
    ("01_strategy", "06", "map-strategy", "地图战略"),
    ("02_business", "03", "xuan-paper-annual", "宣纸年报·补充"),
    ("02_business", "04", "lead-gray-quarterly", "青棕趋势监测·补充"),
    ("02_business", "05", "ink-green-market-trends", "墨绿市场趋势"),
    ("02_business", "06", "orange-tech", "橙色科技"),
    ("03_work", "02", "mist-blue-travelogue", "雾蓝游记"),
    ("03_work", "04", "color-stripes-documentary", "彩条纪实"),
    ("03_work", "06", "red-white-business", "红白商务"),
    ("04_promotion", "04", "gold-orange-type-journal", "金橙字体期刊"),
    ("04_promotion", "06", "fresh-brand", "清新品牌"),
    ("05_academic", "01", "pink-purple-diagnosis", "粉紫诊断"),
    ("05_academic", "06", "dark-themed-data", "暗色数据"),
]

# Variants confirmed by T6 audit: (code, variant suffix, cn label, numbered source path)
VARIANTS = [
    ("sky-blue-wayfinding", "civic", "天蓝导引·公共服务版",
     "03_work/01/en/sky-blue-wayfinding.md", "Civic Brief · Public Service Brief"),
    ("blue-line-courseware", "method", "蓝线课件·实验方法论版",
     "05_academic/05/en/blue-line-courseware.md", "Blue-Line Experiment Methodology Courseware"),
    ("paper-white-courseware", "editorial", "纸白课件·编辑成长版",
     "05_academic/04/en/paper-white-courseware.md", "Editorial Growth Courseware"),
]

def registry():
    items = []
    for cat, code, cn in NAMED:
        src = f"design_system/{NAMED_CAT_DIR[cat]}/{code}/design.md"
        items.append(dict(code=code, cn=cn, cat=CAT_ZH_NAMED[cat], kind="named", src=src))
    for ndir, slot, code, cn in EXTRA:
        src = f"design_system/{ndir}/{slot}/en/{code}.md"
        items.append(dict(code=code, cn=cn, cat=CAT_ZH_NUM[ndir], kind="extra", src=src))
    for code, suffix, cn, src, en in VARIANTS:
        items.append(dict(code=f"{code}--{suffix}", cn=cn, en=en, cat="变体", kind="variant",
                          src=f"design_system/{src}",
                          call=f"用 reference/design_system/{src} 这套风格"))
    return items

# ---------------------------------------------------------------------------
def parse_palette(src_path: Path):
    try:
        text = src_path.read_text(encoding="utf-8")
    except OSError:
        return [], ""
    hexes = re.findall(r"#[0-9A-Fa-f]{6}\b", text)
    ordered = [h.upper() for h in dict.fromkeys(hexes)]
    counts = Counter(h.upper() for h in hexes)
    ordered.sort(key=lambda h: -counts[h])
    sig_m = re.search(r"One-line style signature:\s*(.+)", text)
    sig = sig_m.group(1).strip() if sig_m else ""
    return ordered[:6], sig

def esc(s):
    return html.escape(s, quote=True)

# ---------------------------------------------------------------------------
SHELL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>open-ppt 主题选样页 · 共 __TOTAL__ 套</title>
<style>
  :root { --ink:#1c1917; --muted:#78716c; --line:#e7e5e4; --bg:#f5f5f4; --card:#ffffff; --accent:#0f766e; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font-family:system-ui,-apple-system,"Segoe UI","Microsoft YaHei",sans-serif; }
  header { max-width:1400px; margin:0 auto; padding:28px 24px 10px; }
  header h1 { font-size:22px; margin:0 0 6px; }
  header p { margin:0; color:var(--muted); font-size:13px; line-height:1.7; }
  .toolbar { position:sticky; top:0; z-index:20; background:rgba(245,245,244,.94);
             backdrop-filter:blur(6px); border-bottom:1px solid var(--line); }
  .toolbar-in { max-width:1400px; margin:0 auto; padding:10px 24px; display:flex;
                gap:10px; flex-wrap:wrap; align-items:center; }
  #filter { flex:1 1 220px; max-width:340px; padding:7px 12px; border:1px solid var(--line);
            border-radius:8px; font-size:13px; background:#fff; }
  .chips { display:flex; gap:6px; flex-wrap:wrap; }
  .chip { padding:5px 11px; border:1px solid var(--line); border-radius:999px; background:#fff;
          font-size:12.5px; cursor:pointer; color:var(--muted); user-select:none; }
  .chip.on { background:var(--ink); color:#fff; border-color:var(--ink); }
  .grid { max-width:1400px; margin:0 auto; padding:18px 24px 60px; display:grid;
          gap:22px; grid-template-columns:repeat(auto-fill,minmax(430px,1fr)); }
  .card { background:var(--card); border:1px solid var(--line); border-radius:12px;
          overflow:hidden; display:flex; flex-direction:column;
          transition:box-shadow .15s; cursor:zoom-in; }
  .card:hover { box-shadow:0 4px 18px rgba(0,0,0,.08); }
  .card.hide { display:none; }
  .viewport { aspect-ratio:16/9; background:#e7e5e4; position:relative; overflow:hidden; }
  .viewport .ph { position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
                  color:#a8a29e; font-size:12px; }
  .scaler { position:absolute; top:0; left:0; transform-origin:0 0; }
  .meta { padding:12px 14px 13px; border-top:1px solid var(--line); display:flex;
          flex-direction:column; gap:7px; }
  .meta .r1 { display:flex; align-items:baseline; gap:8px; flex-wrap:wrap; }
  .meta .cn { font-weight:700; font-size:15.5px; }
  .meta .en { color:var(--muted); font-size:12px; }
  .meta .cat { margin-left:auto; font-size:11px; color:var(--muted);
               border:1px solid var(--line); border-radius:999px; padding:2px 8px; white-space:nowrap; }
  .swatches { display:flex; gap:4px; }
  .sw { width:17px; height:17px; border-radius:4px; border:1px solid rgba(0,0,0,.08); }
  .meta .r2 { display:flex; align-items:center; gap:8px; }
  .meta code { font-family:Consolas,Menlo,monospace; font-size:12.5px; background:#f5f5f4;
               padding:2px 7px; border-radius:5px; }
  .copy { border:1px solid var(--line); background:#fff; border-radius:6px; font-size:11.5px;
          padding:2px 9px; cursor:pointer; color:var(--muted); }
  .copy:hover { border-color:var(--ink); color:var(--ink); }
  .hint { font-size:11.5px; color:var(--muted); line-height:1.55; }
  .hint b { color:var(--ink); font-weight:600; }
  .sig { font-size:11px; color:#a8a29e; line-height:1.5; display:-webkit-box;
         -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
  .modal { position:fixed; inset:0; z-index:50; display:none; align-items:center;
           justify-content:center; background:rgba(28,25,23,.72); }
  .modal.open { display:flex; }
  .modal-box { background:#fff; border-radius:14px; padding:16px; max-width:94vw; max-height:92vh;
               display:flex; flex-direction:column; gap:12px; }
  .modal-head { display:flex; align-items:baseline; gap:10px; flex-wrap:wrap; }
  .modal-head .cn { font-weight:700; font-size:17px; }
  .modal-head .en { color:var(--muted); font-size:12.5px; }
  .modal-head .close { margin-left:auto; cursor:pointer; border:1px solid var(--line);
                       background:#fff; border-radius:8px; padding:4px 12px; font-size:13px; }
  #modal-viewport { overflow:hidden; position:relative; background:#eee; }
  footer { max-width:1400px; margin:0 auto; padding:0 24px 40px; color:var(--muted); font-size:12px; }
</style>
</head>
<body>
<header>
  <h1>open-ppt 主题选样页 · 共 __TOTAL__ 套</h1>
  <p>每个主题用<b>同一份样本内容</b>渲染一整页真实版式（眉题 · 结论式标题 · KPI · 历程图 · 节点结论 · 趋势图 · 页脚），
     横向对比即可看出各主题的性格。点击卡片放大；预览字体为系统近似，实际 PPT 以 design.md 嵌入字体为准。</p>
</header>
<div class="toolbar"><div class="toolbar-in">
  <input id="filter" type="search" placeholder="搜索：名称 / 拼音 code，如 黑金、ledger">
  <div class="chips" id="chips"></div>
</div></div>
<div class="grid" id="grid"></div>
<footer>选定后在对话里点名即可，例如：「用 black-gold-ledger（黑金账本）风格做一份 PPT」。变体主题需按卡片提示带路径点名。</footer>
<div class="modal" id="modal">
  <div class="modal-box">
    <div class="modal-head" id="modal-head"></div>
    <div id="modal-viewport"></div>
  </div>
</div>
__TEMPLATES__
<script>
(function () {
  var THEMES = __THEMES_JSON__;
  var grid = document.getElementById('grid');
  var chipsBox = document.getElementById('chips');
  var filter = document.getElementById('filter');
  var modal = document.getElementById('modal');
  var modalHead = document.getElementById('modal-head');
  var modalVp = document.getElementById('modal-viewport');
  var activeCat = '全部';

  function tpl(code) {
    var t = document.querySelector('template[data-code="' + code + '"]');
    return t || null;
  }
  function mountShadow(host, code, scale) {
    var t = tpl(code);
    if (!t) return null;
    var root = host.attachShadow({ mode: 'open' });
    root.appendChild(t.content.cloneNode(true));
    var slide = root.querySelector('.tp-slide');
    var scaler = document.createElement('div');
    // inline styles: outer-document CSS does not reach inside a shadow root
    scaler.style.cssText = 'position:absolute;top:0;left:0;width:960px;height:540px;transform-origin:0 0;';
    if (slide) { slide.style.margin = '0'; scaler.appendChild(slide); }
    root.appendChild(scaler);
    applyScale(scaler, scale || host.clientWidth / 960);
    return scaler;
  }
  function applyScale(scaler, s) {
    scaler.style.transform = 'scale(' + s + ')';
    var host = scaler.getRootNode().host;
    if (host) host.style.height = (540 * s) + 'px';
  }

  THEMES.forEach(function (th) {
    var card = document.createElement('article');
    card.className = 'card';
    card.setAttribute('data-code', th.code);
    card.setAttribute('data-cat', th.cat);
    card.setAttribute('data-search', (th.code + ' ' + th.cn + ' ' + th.en).toLowerCase());
    var callText = th.call || th.code;
    card.innerHTML =
      '<div class="viewport"><div class="ph">加载预览…</div></div>' +
      '<div class="meta">' +
        '<div class="r1"><span class="cn">' + th.cn + '</span><span class="en">' + th.en + '</span>' +
          '<span class="cat">' + th.cat + '</span></div>' +
        '<div class="swatches">' + th.palette.map(function (c) {
            return '<span class="sw" style="background:' + c + '" title="' + c + '"></span>'; }).join('') +
        '</div>' +
        '<div class="r2"><code>' + th.code + '</code>' +
          '<button class="copy" data-copy="' + encodeURIComponent(callText) + '">复制点名</button></div>' +
        '<div class="hint">' + th.hint + '</div>' +
        (th.sig ? '<div class="sig">' + th.sig + '</div>' : '') +
      '</div>';
    grid.appendChild(card);

    var vp = card.querySelector('.viewport');
    var mounted = false;
    var io = new IntersectionObserver(function (ents) {
      ents.forEach(function (e) {
        if (e.isIntersecting && !mounted) {
          mounted = true;
          if (tpl(th.code)) {
            vp.innerHTML = '';
            mountShadow(vp, th.code);
          } else {
            vp.querySelector('.ph').textContent = '预览生成中…';
          }
          io.unobserve(vp);
        }
      });
    }, { rootMargin: '300px' });
    io.observe(vp);

    card.addEventListener('click', function (ev) {
      if (ev.target.classList.contains('copy')) return;
      openModal(th);
    });
  });

  function fitModal(code) {
    var s = Math.min((window.innerWidth * 0.9) / 960, (window.innerHeight * 0.78) / 540);
    modalVp.style.width = (960 * s) + 'px';
    modalVp.style.height = (540 * s) + 'px';
    var t = tpl(code);
    if (!t) return;
    modalVp.innerHTML = '';
    var host = document.createElement('div');
    host.style.width = '960px';
    host.style.height = '540px';
    host.style.transformOrigin = '0 0';
    host.style.transform = 'scale(' + s + ')';
    var root = host.attachShadow({ mode: 'open' });
    root.appendChild(t.content.cloneNode(true));
    modalVp.appendChild(host);
  }
  function openModal(th) {
    modalHead.innerHTML = '<span class="cn">' + th.cn + '</span>' +
      '<span class="en">' + th.en + ' · ' + th.code + '</span>' +
      '<button class="close">关闭 ✕</button>';
    fitModal(th.code);
    modal.classList.add('open');
    modalHead.querySelector('.close').onclick = function () { modal.classList.remove('open'); };
  }
  modal.addEventListener('click', function (e) { if (e.target === modal) modal.classList.remove('open'); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') modal.classList.remove('open'); });
  window.addEventListener('resize', function () {
    if (modal.classList.contains('open')) {
      var code = modalHead.querySelector('.en').textContent.split(' · ').pop();
      fitModal(code);
    }
  });

  // category chips
  var cats = ['全部'];
  THEMES.forEach(function (t) { if (cats.indexOf(t.cat) < 0) cats.push(t.cat); });
  cats.forEach(function (c) {
    var n = c === '全部' ? THEMES.length : THEMES.filter(function (t) { return t.cat === c; }).length;
    var b = document.createElement('button');
    b.className = 'chip' + (c === activeCat ? ' on' : '');
    b.textContent = c + ' ' + n;
    b.addEventListener('click', function () {
      activeCat = c;
      chipsBox.querySelectorAll('.chip').forEach(function (x) { x.classList.remove('on'); });
      b.classList.add('on');
      applyFilter();
    });
    chipsBox.appendChild(b);
  });

  function applyFilter() {
    var q = filter.value.trim().toLowerCase();
    grid.querySelectorAll('.card').forEach(function (card) {
      var okCat = activeCat === '全部' || card.getAttribute('data-cat') === activeCat;
      var okQ = !q || card.getAttribute('data-search').indexOf(q) >= 0;
      card.classList.toggle('hide', !(okCat && okQ));
    });
  }
  filter.addEventListener('input', applyFilter);

  // copy-to-clipboard with fallback for file:// usage
  grid.addEventListener('click', function (ev) {
    var btn = ev.target.closest ? ev.target.closest('.copy') : null;
    if (!btn) return;
    ev.stopPropagation();
    var text = decodeURIComponent(btn.getAttribute('data-copy'));
    function done() { btn.textContent = '已复制'; setTimeout(function () { btn.textContent = '复制点名'; }, 1200); }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallback(); });
    } else fallback();
    function fallback() {
      var ta = document.createElement('textarea');
      ta.value = text; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); done(); } catch (e) {}
      document.body.removeChild(ta);
    }
  });
})();
</script>
</body>
</html>
"""

def build():
    themes = registry()
    codes = {t["code"] for t in themes}
    fragments = {p.stem: p for p in PAGES.glob("*.html")}
    unknown = sorted(set(fragments) - codes)
    missing = sorted(c for c in codes if c not in fragments)
    if unknown:
        sys.exit(f"ERROR: fragments without registry entry: {unknown}")
    if missing:
        print(f"NOTE: {len(missing)} themes not yet rendered: {missing}")

    cards, templates = [], []
    for t in themes:
        palette, sig = parse_palette(ROOT / "skills/open-ppt/reference" / t["src"])
        if t["kind"] == "variant":
            hint = f"<b>同名另一套设计</b>：点名需带路径「{t['call']}」"
        else:
            hint = f"点名：<b>用 {t['code']}（{t['cn']}）风格做一份 PPT</b>"
        cards.append(dict(code=t["code"], cn=t["cn"], en=t.get("en", t["code"]), cat=t["cat"],
                          palette=palette, sig=esc(sig), hint=hint, call=t.get("call", t["code"])))
        fp = fragments.get(t["code"])
        if fp:
            templates.append(f'<template data-code="{t["code"]}">\n{fp.read_text(encoding="utf-8").strip()}\n</template>')

    page = SHELL.replace("__TOTAL__", str(len(themes)))
    page = page.replace("__THEMES_JSON__",
                        __import__("json").dumps(cards, ensure_ascii=False))
    page = page.replace("__TEMPLATES__", "\n".join(templates))
    OUT.write_text(page, encoding="utf-8")
    print(f"OK: wrote {OUT} ({OUT.stat().st_size/1024:.0f} KB, "
          f"{len(cards)} cards, {len(templates)} fragments embedded)")

if __name__ == "__main__":
    build()
