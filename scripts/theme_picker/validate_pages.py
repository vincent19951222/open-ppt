#!/usr/bin/env python3
"""Structural validator for theme-picker preview fragments (scripts/theme_picker/pages/*.html).

Checks per PLAN.md T3: canvas size, data-module completeness, verbatim sample strings,
forbidden external resources / JS, size budget. Exit 1 on any failure.
"""
import re
import sys
from pathlib import Path

PAGES = Path(__file__).resolve().parent / "pages"

MODULES = ["eyebrow", "headline", "kpi", "timeline", "conclusions", "chart", "footer"]

VERBATIM = [
    # eyebrow / headline / footer
    "星澜计划 · 2026 年度进展",
    "第二年用户规模翻番，单位服务成本下降 38%",
    "07 · 数据截止 2026-09 · 示例数据",
    # KPI values + deltas
    "240万", "+112%", "86万", "+65%", "¥3.1", "−38%",
    # timeline node titles
    "低温试点上线", "开放公测", "多城复制", "智能调度上线",
    # conclusions
    "试点留存验证", "61%", "超基准 12 个百分点", "成本拐点", "规模效应显现", "调度收益", "−42%",
    # chart
    "月活趋势（万人）", "86",
]

FORBIDDEN = [
    ("http://", "external URL"), ("https://", "external URL"),
    ("@import", "CSS import"), ("url(", "CSS url()"),
    ("<img", "img tag"), ("<link", "link tag"), ("<iframe", "iframe tag"),
    ("<script", "script tag"), ("onclick=", "inline JS"), ("onload=", "inline JS"),
    ("<!DOCTYPE", "doctype"), ("<html", "html tag"), ("<body", "body tag"),
]

def check(fp: Path) -> list[str]:
    issues = []
    text = fp.read_text(encoding="utf-8")
    code = fp.stem

    if len(text.encode("utf-8")) > 30 * 1024:
        issues.append(f"file too large: {len(text.encode('utf-8'))/1024:.0f}KB > 30KB")

    # root slide + size
    if 'class="tp-slide"' not in text and "class='tp-slide'" not in text:
        issues.append("missing root element .tp-slide")
    m = re.search(r'class="tp-slide"[^>]*data-theme="([^"]+)"', text)
    if not m:
        issues.append("root .tp-slide missing data-theme attribute")
    elif m.group(1) != code:
        issues.append(f'data-theme="{m.group(1)}" != filename "{code}"')
    if not re.search(r"width\s*:\s*960px", text):
        issues.append("no `width: 960px` rule found")
    if not re.search(r"height\s*:\s*540px", text):
        issues.append("no `height: 540px` rule found")
    if not re.search(r"overflow\s*:\s*hidden", text):
        issues.append("no `overflow: hidden` on canvas")

    # modules exactly once
    for mod in MODULES:
        n = len(re.findall(f'data-module="{mod}"', text))
        if n != 1:
            issues.append(f'data-module="{mod}" found {n}x (want exactly 1)')

    # verbatim strings — matched against tag-stripped text so inline emphasis
    # spans (theme-colored keywords) don't break contiguity
    stripped = re.sub(r"<[^>]+>", "", text)
    for s in VERBATIM:
        if s not in stripped:
            issues.append(f"missing verbatim string: {s!r}")

    # forbidden patterns
    for pat, why in FORBIDDEN:
        if pat.lower() in text.lower():
            # url( check: allow none; report first occurrence line
            ln = text.lower().index(pat.lower()) 
            line = text[:ln].count("\n") + 1
            issues.append(f"forbidden {why} ({pat!r}) at line {line}")

    # style block present
    if "<style" not in text:
        issues.append("no <style> block")

    return issues

def main():
    files = sorted(PAGES.glob("*.html"))
    if len(sys.argv) > 1:
        wanted = set(sys.argv[1:])
        files = [f for f in files if f.stem in wanted]
    if not files:
        sys.exit(f"no fragments found in {PAGES}")
    failed = 0
    for fp in files:
        issues = check(fp)
        if issues:
            failed += 1
            print(f"FAIL {fp.name}")
            for i in issues:
                print(f"     - {i}")
        else:
            print(f"OK   {fp.name}")
    print(f"\n{len(files) - failed}/{len(files)} fragments pass")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
