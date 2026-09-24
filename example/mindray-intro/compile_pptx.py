#!/usr/bin/env python3
"""Direct OOXML PPTX builder for mindray-intro PPTD."""

import html
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

EMU_PER_PX = 12700
SLIDE_WIDTH = 12192000
SLIDE_HEIGHT = 6858000

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

ICON_MAP = {
    "fas:heart-pulse": "♥",
    "fas:vial": "🧪",
    "fas:x-ray": "🔬",
}

def parse_color(c: str, theme_colors: Dict[str, str]) -> Tuple[str, Optional[int]]:
    if not c:
        return "FFFFFF", None
    if c.startswith("$"):
        c = theme_colors.get(c[1:], "#FFFFFF")
    c = c.lstrip("#")
    if len(c) == 8:
        return c[:6].upper(), int(int(c[6:], 16) / 255.0 * 100000)
    elif len(c) == 6:
        return c.upper(), None
    elif len(c) == 3:
        return (c[0]*2 + c[1]*2 + c[2]*2).upper(), None
    return "FFFFFF", None

def make_solid_fill(hex6: str, alpha: Optional[int] = None) -> str:
    if alpha is not None:
        return f'<a:solidFill><a:srgbClr val="{hex6}"><a:alpha val="{alpha}"/></a:srgbClr></a:solidFill>'
    return f'<a:solidFill><a:srgbClr val="{hex6}"/></a:solidFill>'

def clean_html_tags(text: str) -> List[Tuple[str, Dict[str, Any]]]:
    paragraphs = []
    # handle <li> tags
    text = text.replace("<li>", "<p>• ").replace("</li>", "</p>")
    text = re.sub(r'</?ul[^>]*>', '', text)
    p_blocks = re.split(r'</?p[^>]*>', text)
    for block in p_blocks:
        block = block.strip()
        if not block:
            continue
        runs = []
        tokens = re.split(r'(<[^>]+>)', block)
        cur_style = {}
        for token in tokens:
            if not token:
                continue
            if token.startswith('<span'):
                m_style = re.search(r'style="([^"]+)"', token)
                if m_style:
                    for part in m_style.group(1).split(';'):
                        if ':' in part:
                            k, v = part.split(':', 1)
                            cur_style[k.strip()] = v.strip()
            elif token == '</span>':
                cur_style = {}
            elif token.startswith('<strong'):
                cur_style['font-weight'] = '700'
            elif token == '</strong>':
                cur_style.pop('font-weight', None)
            elif not token.startswith('<'):
                raw_text = html.unescape(token)
                runs.append((raw_text, dict(cur_style)))
        if runs:
            paragraphs.append(runs)
    return paragraphs

def build_shape_xml(
    el: Dict[str, Any],
    el_id: int,
    theme_colors: Dict[str, str],
    text_styles: Dict[str, Any],
    slide_rels: Dict[str, str],
    base_dir: Path,
) -> str:
    bounds = el.get("bounds", [0, 0, 100, 100])
    x = int(bounds[0] * EMU_PER_PX)
    y = int(bounds[1] * EMU_PER_PX)
    w = int(bounds[2] * EMU_PER_PX)
    h = int(bounds[3] * EMU_PER_PX)
    el_type = el.get("elementType")

    shape_name = el.get("shapeName", "rect")
    shape_map = {
        "rect": "rect",
        "roundRect": "roundRect",
        "ellipse": "ellipse",
        "chevron": "chevron",
        "rightArrow": "rightArrow",
        "triangle": "triangle",
    }
    prst = shape_map.get(shape_name, "rect")

    fill_obj = el.get("fill")
    if fill_obj and fill_obj.get("type") == "solid":
        f_hex, f_alpha = parse_color(fill_obj.get("color", "#FFFFFF"), theme_colors)
        fill_xml = make_solid_fill(f_hex, f_alpha)
    else:
        fill_xml = "<a:noFill/>"

    border_obj = el.get("border")
    if border_obj:
        b_width = int(border_obj.get("width", 1) * EMU_PER_PX)
        b_hex, b_alpha = parse_color(border_obj.get("color", "#000000"), theme_colors)
        ln_fill = make_solid_fill(b_hex, b_alpha)
        ln_xml = f'<a:ln w="{b_width}">{ln_fill}</a:ln>'
    else:
        ln_xml = "<a:ln><a:noFill/></a:ln>"

    if el_type == "image":
        src = el.get("src", "")
        img_name = Path(src).name
        rel_id = f"rIdImg_{len(slide_rels) + 1}"
        slide_rels[rel_id] = img_name
        return f"""
        <p:pic>
          <p:nvPicPr>
            <p:cNvPr id="{el_id}" name="{html.escape(el.get('elementId', f'pic-{el_id}'))}"/>
            <p:cNvPicPr/>
            <p:nvPr/>
          </p:nvPicPr>
          <p:blipFill>
            <a:blip r:embed="{rel_id}"/>
            <a:stretch><a:fillRect/></a:stretch>
          </p:blipFill>
          <p:spPr>
            <a:xfrm>
              <a:off x="{x}" y="{y}"/>
              <a:ext cx="{w}" cy="{h}"/>
            </a:xfrm>
            <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
            {ln_xml}
          </p:spPr>
        </p:pic>
        """

    # If it's a chart, draw a simple OOXML representation (columns + labels)
    if el_type == "chart":
        # Draw 3 bars + values + x-labels as native vector shapes
        chart_data = el.get("data", {})
        rows = chart_data.get("rows", [])
        if rows:
            max_val = max(r[1] for r in rows if isinstance(r[1], (int, float))) or 1.0
            num_bars = len(rows)
            gap = int(w * 0.08)
            bar_w = int((w - gap * (num_bars + 1)) / num_bars)
            bars_xml = []
            f_hex, f_alpha = parse_color("$primary", theme_colors)
            b_fill = make_solid_fill(f_hex, f_alpha)
            for idx, r in enumerate(rows):
                val = r[1]
                year = str(r[0])
                bar_h = int((val / max_val) * (h * 0.75))
                bar_x = x + gap + idx * (bar_w + gap)
                bar_y = y + h - bar_h - int(24 * EMU_PER_PX)
                bars_xml.append(f"""
                <p:sp>
                  <p:nvSpPr>
                    <p:cNvPr id="{el_id * 100 + idx}" name="bar-{idx}"/>
                    <p:cNvSpPr txBox="0"/>
                    <p:nvPr/>
                  </p:nvSpPr>
                  <p:spPr>
                    <a:xfrm><a:off x="{bar_x}" y="{bar_y}"/><a:ext cx="{bar_w}" cy="{bar_h}"/></a:xfrm>
                    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                    {b_fill}
                    <a:ln><a:noFill/></a:ln>
                  </p:spPr>
                  <p:txBody>
                    <a:bodyPr lIns="0" rIns="0" tIns="0" bIns="0" wrap="none" anchor="ctr"/>
                    <a:lstStyle/>
                    <a:p>
                      <a:pPr algn="ctr"/>
                      <a:r>
                        <a:rPr lang="zh-CN" sz="1000" b="1">
                          <a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>
                          <a:ea typeface="Microsoft YaHei"/>
                        </a:rPr>
                        <a:t>{val}</a:t>
                      </a:r>
                    </a:p>
                  </p:txBody>
                </p:sp>
                <p:sp>
                  <p:nvSpPr>
                    <p:cNvPr id="{el_id * 100 + idx + 50}" name="lbl-{idx}"/>
                    <p:cNvSpPr txBox="1"/>
                    <p:nvPr/>
                  </p:nvSpPr>
                  <p:spPr>
                    <a:xfrm><a:off x="{bar_x}" y="{y + h - int(20 * EMU_PER_PX)}"/><a:ext cx="{bar_w}" cy="{int(18 * EMU_PER_PX)}"/></a:xfrm>
                    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                    <a:noFill/><a:ln><a:noFill/></a:ln>
                  </p:spPr>
                  <p:txBody>
                    <a:bodyPr lIns="0" rIns="0" tIns="0" bIns="0" wrap="none" anchor="t"/>
                    <a:lstStyle/>
                    <a:p>
                      <a:pPr algn="ctr"/>
                      <a:r>
                        <a:rPr lang="zh-CN" sz="900">
                          <a:solidFill><a:srgbClr val="595959"/></a:solidFill>
                          <a:ea typeface="Microsoft YaHei"/>
                        </a:rPr>
                        <a:t>{year}</a:t>
                      </a:r>
                    </a:p>
                  </p:txBody>
                </p:sp>
                """)
            return "".join(bars_xml)

    tx_body_xml = ""
    if el_type == "text":
        fill_xml = "<a:noFill/>"
        ln_xml = "<a:ln><a:noFill/></a:ln>"
        content = el.get("content", {})
        style_ref = content.get("style", "")
        base_style = {}
        if style_ref.startswith("$"):
            base_style = text_styles.get(style_ref[1:], {})

        align = content.get("align", ["left", "top"])
        h_align = align[0]
        v_align = align[1] if len(align) > 1 else "top"
        algn_val = "ctr" if h_align == "center" else ("r" if h_align == "right" else "l")
        anchor_val = "ctr" if v_align == "middle" else ("b" if v_align == "bottom" else "t")

        raw_text = content.get("text", "")
        paragraphs = clean_html_tags(raw_text)
        if not paragraphs:
            paragraphs = [[(raw_text, {})]]

        default_sz = int(content.get("fontSize", base_style.get("fontSize", 12)) * 100)
        default_color = content.get("color", base_style.get("color", "#1A1A1A"))
        default_bold = content.get("bold", base_style.get("bold", False))

        p_xml_list = []
        for p_runs in paragraphs:
            runs_xml = []
            for r_text, r_style in p_runs:
                sz = default_sz
                if "font-size" in r_style:
                    try:
                        sz = int(float(r_style["font-size"].replace("px", "").replace("pt", "")) * 100)
                    except ValueError:
                        pass
                c_val = r_style.get("color", default_color)
                r_hex, r_alpha = parse_color(c_val, theme_colors)
                color_xml = make_solid_fill(r_hex, r_alpha)
                b_val = "1" if (r_style.get("font-weight") in ("700", "800", "bold") or default_bold) else "0"
                escaped_text = html.escape(r_text)
                runs_xml.append(f"""
                <a:r>
                  <a:rPr lang="zh-CN" altLang="en-US" sz="{sz}" b="{b_val}">
                    {color_xml}
                    <a:latin typeface="Segoe UI"/>
                    <a:ea typeface="Microsoft YaHei"/>
                  </a:rPr>
                  <a:t>{escaped_text}</a:t>
                </a:r>
                """)
            p_xml_list.append(f"""
            <a:p>
              <a:pPr algn="{algn_val}"/>
              {''.join(runs_xml)}
            </a:p>
            """)

        tx_body_xml = f"""
        <p:txBody>
          <a:bodyPr lIns="20000" rIns="20000" tIns="10000" bIns="10000" wrap="square" anchor="{anchor_val}"/>
          <a:lstStyle/>
          {''.join(p_xml_list)}
        </p:txBody>
        """

    elif el_type == "icon":
        icon_name = el.get("iconName", "")
        symbol = ICON_MAP.get(icon_name, "◆")
        f_color = el.get("fill", {}).get("color", "$primary")
        f_hex, f_alpha = parse_color(f_color, theme_colors)
        color_xml = make_solid_fill(f_hex, f_alpha)
        tx_body_xml = f"""
        <p:txBody>
          <a:bodyPr lIns="0" rIns="0" tIns="0" bIns="0" wrap="none" anchor="ctr"/>
          <a:lstStyle/>
          <a:p>
            <a:pPr algn="ctr"/>
            <a:r>
              <a:rPr sz="1800" b="1">
                {color_xml}
                <a:latin typeface="Segoe UI Symbol"/>
                <a:ea typeface="Segoe UI Symbol"/>
              </a:rPr>
              <a:t>{symbol}</a:t>
            </a:r>
          </a:p>
        </p:txBody>
        """

    return f"""
    <p:sp>
      <p:nvSpPr>
        <p:cNvPr id="{el_id}" name="{html.escape(el.get('elementId', f'sp-{el_id}'))}"/>
        <p:cNvSpPr txBox="{'1' if el_type == 'text' else '0'}"/>
        <p:nvPr/>
      </p:nvSpPr>
      <p:spPr>
        <a:xfrm>
          <a:off x="{x}" y="{y}"/>
          <a:ext cx="{w}" cy="{h}"/>
        </a:xfrm>
        <a:prstGeom prst="{prst}">
          <a:avLst/>
        </a:prstGeom>
        {fill_xml}
        {ln_xml}
      </p:spPr>
      {tx_body_xml}
    </p:sp>
    """

def build_slide_xml(
    page_data: Dict[str, Any],
    theme_colors: Dict[str, str],
    text_styles: Dict[str, Any],
    base_dir: Path,
) -> Tuple[str, Dict[str, str]]:
    slide_rels = {}
    bg_obj = page_data.get("background", {})
    bg_color = bg_obj.get("color", "#FFFFFF")
    bg_hex, bg_alpha = parse_color(bg_color, theme_colors)
    bg_xml = make_solid_fill(bg_hex, bg_alpha)

    elements = page_data.get("elements", [])
    shapes_xml = []
    el_id = 2
    for el in elements:
        shapes_xml.append(build_shape_xml(el, el_id, theme_colors, text_styles, slide_rels, base_dir))
        el_id += 1

    slide_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:cSld>
    <p:bg>
      <p:bgPr>
        {bg_xml}
      </p:bgPr>
    </p:bg>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id="1" name=""/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x="0" y="0"/>
          <a:ext cx="0" cy="0"/>
          <a:chOff x="0" y="0"/>
          <a:chExt cx="0" cy="0"/>
        </a:xfrm>
      </p:grpSpPr>
      {''.join(shapes_xml)}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr>
    <a:masterClrMapping/>
  </p:clrMapOvr>
  <p:transition spd="fast" advClick="1"><p:fade/></p:transition>
</p:sld>
"""
    return slide_xml, slide_rels

def compile_pptd(pptd_path: Path, output_pptx: Path, template_pptx: Path) -> None:
    manifest = yaml.safe_load(pptd_path.read_text(encoding="utf-8"))
    theme = manifest.get("theme", {})
    theme_colors = theme.get("colors", {})
    text_styles = theme.get("textStyles", {})
    page_files = manifest.get("pages", [])

    base_dir = pptd_path.parent
    media_dir = base_dir / "media"
    slides_xml = []
    all_slide_rels = []
    used_images = set()

    for rel_path in page_files:
        full_path = base_dir / rel_path
        page_data = yaml.safe_load(full_path.read_text(encoding="utf-8"))
        slide_content, slide_rels = build_slide_xml(page_data, theme_colors, text_styles, base_dir)
        slides_xml.append(slide_content)
        all_slide_rels.append(slide_rels)
        for img_name in slide_rels.values():
            used_images.add(img_name)

    num_slides = len(slides_xml)

    with zipfile.ZipFile(template_pptx, "r") as src, zipfile.ZipFile(output_pptx, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            filename = item.filename
            if filename.startswith("ppt/slides/"):
                continue
            data = src.read(filename)
            if filename == "[Content_Types].xml":
                ct_root = ET.fromstring(data)
                has_png = any(c.attrib.get("Extension") == "png" for c in ct_root)
                if not has_png:
                    def_png = ET.SubElement(ct_root, "Default")
                    def_png.set("Extension", "png")
                    def_png.set("ContentType", "image/png")
                to_remove = [c for c in ct_root if c.attrib.get("PartName", "").startswith("/ppt/slides/slide")]
                for r in to_remove:
                    ct_root.remove(r)
                for i in range(1, num_slides + 1):
                    ov = ET.SubElement(ct_root, "Override")
                    ov.set("PartName", f"/ppt/slides/slide{i}.xml")
                    ov.set("ContentType", "application/vnd.openxmlformats-officedocument.presentationml.slide+xml")
                data = ET.tostring(ct_root, encoding="utf-8", xml_declaration=True)
            elif filename == "ppt/presentation.xml":
                p_root = ET.fromstring(data)
                sldIdLst = p_root.find(f"{{{P_NS}}}sldIdLst")
                if sldIdLst is not None:
                    sldIdLst.clear()
                    for i in range(1, num_slides + 1):
                        sldId = ET.SubElement(sldIdLst, f"{{{P_NS}}}sldId")
                        sldId.set("id", str(255 + i))
                        sldId.set(f"{{{R_NS}}}id", f"rId{2 + i}")
                data = ET.tostring(p_root, encoding="utf-8", xml_declaration=True)
            elif filename == "ppt/_rels/presentation.xml.rels":
                r_root = ET.fromstring(data)
                to_remove = [c for c in r_root if c.attrib.get("Type", "").endswith("/slide")]
                for r in to_remove:
                    r_root.remove(r)
                for i in range(1, num_slides + 1):
                    rel = ET.SubElement(r_root, "Relationship")
                    rel.set("Id", f"rId{2 + i}")
                    rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide")
                    rel.set("Target", f"slides/slide{i}.xml")
                data = ET.tostring(r_root, encoding="utf-8", xml_declaration=True)

            dst.writestr(item, data)

        for i in range(1, num_slides + 1):
            dst.writestr(f"ppt/slides/slide{i}.xml", slides_xml[i - 1].encode("utf-8"))
            rels_elements = [
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
            ]
            for rel_id, img_name in all_slide_rels[i - 1].items():
                rels_elements.append(
                    f'<Relationship Id="{rel_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/{img_name}"/>'
                )
            slide_rels_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {''.join(rels_elements)}
</Relationships>
"""
            dst.writestr(f"ppt/slides/_rels/slide{i}.xml.rels", slide_rels_xml.encode("utf-8"))

        for img_name in used_images:
            local_path = media_dir / img_name
            if local_path.exists():
                dst.writestr(f"ppt/media/{img_name}", local_path.read_bytes())

    print(f"OK: generated {output_pptx} ({output_pptx.stat().st_size} bytes)")

if __name__ == "__main__":
    pptd = Path("example/mindray-intro/mindray-intro.pptd")
    out = Path("example/mindray-intro/mindray-intro.pptx")
    tmpl = Path("example/dji-pocket4/DJI Osmo Pocket 4 产品深度解读.pptx")
    compile_pptd(pptd, out, tmpl)
