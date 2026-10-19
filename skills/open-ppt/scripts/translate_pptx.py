#!/usr/bin/env python3
"""Extract slide paragraphs and patch agent-supplied translations into a PPTX copy.

Uses byte-range XML patches so namespaces, unsupported objects, and all unrelated
package parts remain untouched. This helper does not translate or render text.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import posixpath
import re
import tempfile
import xml.etree.ElementTree as ET
from xml.parsers import expat
from xml.sax.saxutils import escape
import zipfile


A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CJK = re.compile(r"[\u3400-\u9fff]")


def read_package(path):
    if path.suffix.lower() != ".pptx":
        raise ValueError("input must be an unencrypted .pptx file")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(set(names)) != len(names):
            raise ValueError("duplicate ZIP entry names are not supported")
        if archive.testzip():
            raise ValueError("PPTX contains a corrupt ZIP entry")
        parts = {name: archive.read(name) for name in names}
    if "ppt/presentation.xml" not in parts:
        raise ValueError("missing ppt/presentation.xml")
    return parts


def slide_parts(parts):
    root = ET.fromstring(parts["ppt/presentation.xml"])
    rels = ET.fromstring(parts["ppt/_rels/presentation.xml.rels"])
    targets = {rel.attrib["Id"]: rel for rel in rels}
    slides = []
    for slide in root.findall(f"{{{P}}}sldIdLst/{{{P}}}sldId"):
        rel = targets[slide.attrib[f"{{{R}}}id"]]
        target = rel.attrib["Target"]
        if rel.get("TargetMode") == "External" or "\\" in target:
            raise ValueError("unsupported slide relationship target")
        part = posixpath.normpath(target.lstrip("/") if target.startswith("/")
                                  else posixpath.join("ppt", target))
        if part not in parts or not part.startswith("ppt/slides/"):
            raise ValueError(f"missing or invalid slide part: {part}")
        slides.append(part)
    if not slides or len(set(slides)) != len(slides):
        raise ValueError("presentation must contain unique slide parts")
    return slides


def select_slides(spec, count):
    if not spec:
        return list(range(1, count + 1))
    selected = set()
    for item in spec.split(","):
        match = re.fullmatch(r"\s*(\d+)(?:-(\d+))?\s*", item)
        if not match:
            raise ValueError("slides must be a range such as 3-8,10")
        start = int(match[1])
        end = int(match[2] or start)
        if not 1 <= start <= end <= count:
            raise ValueError(f"slide range outside 1-{count}: {item}")
        selected.update(range(start, end + 1))
    return sorted(selected)


def paragraphs(data):
    """Return paragraph text plus original byte spans for text/run properties."""
    if b"\x00" in data or re.search(br"encoding\s*=\s*['\"](?!UTF-8|utf-8)[^'\"]+", data[:150]):
        raise ValueError("slide XML must use UTF-8")
    parser = expat.ParserCreate(namespace_separator="|")
    result = []
    current = None
    run = None
    text = None
    index = -1

    def opening_end(offset):
        quote = None
        for position in range(offset, len(data)):
            char = data[position]
            if quote is not None:
                if char == quote:
                    quote = None
            elif char in (34, 39):
                quote = char
            elif char == 62:
                return position + 1
        raise ValueError("unterminated XML opening tag")

    def start(name, attrs):
        nonlocal current, run, text, index
        offset = parser.CurrentByteIndex
        end = opening_end(offset)
        if name == A + "|p":
            index += 1
            current = {"index": index, "segments": [], "pieces": [], "field": False}
        elif current is not None:
            if name == A + "|fld":
                current["field"] = True
            elif name == A + "|br":
                current["pieces"].append("\n")
            elif name == A + "|r":
                tag = data[offset:end].split(None, 1)[0].rstrip(b">/")
                prefix = tag[1:].rsplit(b":", 1)[0] + b":" if b":" in tag else b""
                run = {"insert": end, "prefix": prefix, "properties": {}, "property_span": None}
            elif name == A + "|rPr" and run is not None:
                run["property_span"] = (offset, end)
                run["properties"] = dict(attrs)
            elif name == A + "|t" and run is not None and not data[offset:end].endswith(b"/>"):
                text = {"start": end, "text": "", "run": run}

    def chars(value):
        if text is not None:
            text["text"] += value

    def finish(name):
        nonlocal current, run, text
        if name == A + "|t" and text is not None:
            text["end"] = parser.CurrentByteIndex
            current["segments"].append(text)
            current["pieces"].append(text["text"])
            text = None
        elif name == A + "|r":
            run = None
        elif name == A + "|p" and current is not None:
            if current["segments"] or current["field"]:
                result.append(current)
            current = None

    def reject_doctype(*_args):
        raise ValueError("DOCTYPE is not supported in slide XML")

    parser.StartElementHandler = start
    parser.EndElementHandler = finish
    parser.CharacterDataHandler = chars
    parser.StartDoctypeDeclHandler = reject_doctype
    parser.Parse(data, True)
    return result


def inventory(parts, slides, selected):
    units = []
    warnings = []
    for number in selected:
        part = slides[number - 1]
        for paragraph in paragraphs(parts[part]):
            unit_id = f"{part}#p{paragraph['index']}"
            if paragraph["field"]:
                warnings.append({"slide": number, "id": unit_id, "kind": "field",
                                 "detail": "Dynamic field paragraph retained unchanged."})
                continue
            if not "".join(paragraph["pieces"]).strip():
                continue
            units.append({"id": unit_id, "slide": number, "part": part,
                          "source_text": "".join(paragraph["pieces"]),
                          "source_runs": [s["text"] for s in paragraph["segments"]],
                          "run_properties": [s["run"]["properties"] for s in paragraph["segments"]],
                          "target_runs": None})
        rel_part = posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")
        if rel_part in parts:
            for rel in ET.fromstring(parts[rel_part]):
                kind = rel.get("Type", "").rsplit("/", 1)[-1]
                if kind in {"image", "chart", "chartEx", "diagramData", "oleObject", "package"}:
                    warnings.append({"slide": number, "kind": kind, "target": rel.get("Target"),
                                     "detail": "Content not translated by this helper; inspect separately."})
    for part, data in parts.items():
        if re.fullmatch(r"ppt/slide(?:Masters|Layouts)/[^/]+\.xml", part):
            texts = [node.text for node in ET.fromstring(data).iter(f"{{{A}}}t") if node.text]
            if any(CJK.search(value) for value in texts):
                warnings.append({"part": part, "kind": "shared_text",
                                 "detail": "Shared master/layout contains Chinese text; retained unchanged."})
    return units, warnings


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def extract(source, output, target, spec=None):
    if not target.strip():
        raise ValueError("target language must not be empty")
    parts = read_package(source)
    slides = slide_parts(parts)
    selected = select_slides(spec, len(slides))
    units, warnings = inventory(parts, slides, selected)
    document = {"schema_version": 1, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "source_name": source.name, "target_language": target, "slide_count": len(slides),
                "selected_slides": selected, "units": units, "warnings": warnings}
    write_json(output, document)
    return {"output": str(output), "units": len(units), "warnings": len(warnings)}


def xml_text(value):
    if any(ord(c) < 32 and c not in "\t\n\r" or 0xD800 <= ord(c) <= 0xDFFF
           or ord(c) in {0xFFFE, 0xFFFF} for c in value):
        raise ValueError("translation contains characters invalid in XML 1.0")
    return escape(value).replace("\r", "&#13;").encode("utf-8")


def font_patch(segment, size):
    if isinstance(size, bool) or not isinstance(size, (int, float)) or not math.isfinite(size) or not 1 <= size <= 400:
        raise ValueError("font sizes must be finite values between 1 and 400 points")
    value = str(round(size * 100)).encode("ascii")
    run = segment["run"]
    if run["property_span"] is None:
        position = run["insert"]
        return position, position, b"<" + run["prefix"] + b'rPr sz="' + value + b'"/>'
    return (*run["property_span"], value)


def apply(source, translations, output):
    if output.suffix.lower() != ".pptx":
        raise ValueError("output must have the .pptx extension")
    report_path = output.with_suffix(".translation-report.json")
    paths = [source.resolve(), translations.resolve(), output.resolve(), report_path.resolve()]
    if len(set(paths)) != len(paths):
        raise ValueError("source, translations, output, and report must be distinct files")
    if output.exists() or report_path.exists():
        raise ValueError("output/report already exists; choose a new output filename")
    document = json.loads(translations.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1:
        raise ValueError("unsupported translation manifest version")
    if document.get("source_sha256") != hashlib.sha256(source.read_bytes()).hexdigest():
        raise ValueError("source file changed or translations belong to another PPTX")
    parts = read_package(source)
    slides = slide_parts(parts)
    if document.get("slide_count") != len(slides):
        raise ValueError("slide count does not match source")
    if not isinstance(document.get("target_language"), str) or not document["target_language"].strip():
        raise ValueError("target language must not be empty")
    selected = document.get("selected_slides")
    if not isinstance(selected, list) or not selected or any(type(n) is not int for n in selected):
        raise ValueError("selected_slides must be a nonempty list of slide numbers")
    if selected != sorted(set(selected)) or not all(1 <= n <= len(slides) for n in selected):
        raise ValueError("invalid selected_slides")
    expected, warnings = inventory(parts, slides, selected)
    supplied = document.get("units")
    if not isinstance(supplied, list) or any(not isinstance(u, dict) for u in supplied):
        raise ValueError("units must be a list of translation objects")
    lookup = {u.get("id"): u for u in supplied}
    if len(lookup) != len(supplied) or set(lookup) != {u["id"] for u in expected}:
        raise ValueError("translation units are missing, duplicated, or unknown")
    patches = {}
    changed_units = []
    resized_units = []
    remaining_chinese = []
    positions = {part: {p["index"]: p for p in paragraphs(parts[part])}
                 for part in {u["part"] for u in expected}}
    for original in expected:
        unit = lookup[original["id"]]
        for key in ("source_text", "source_runs", "part", "slide"):
            if unit.get(key) != original[key]:
                raise ValueError(f"{original['id']}: original {key} does not match")
        targets = unit.get("target_runs")
        if not isinstance(targets, list) or len(targets) != len(original["source_runs"]) or any(not isinstance(t, str) for t in targets):
            raise ValueError(f"{original['id']}: target_runs must contain one string per source run")
        if not "".join(targets).strip():
            raise ValueError(f"{original['id']}: translation must not remove all paragraph text")
        sizes = unit.get("font_sizes_pt", [None] * len(targets))
        if not isinstance(sizes, list) or len(sizes) != len(targets):
            raise ValueError(f"{original['id']}: font_sizes_pt must match source_runs length")
        part = original["part"]
        paragraph = positions[part][int(original["id"].rsplit("#p", 1)[1])]
        for segment, translated, size in zip(paragraph["segments"], targets, sizes):
            encoded = xml_text(translated)
            if translated != segment["text"]:
                patches.setdefault(part, []).append((segment["start"], segment["end"], encoded))
            if size is not None:
                start, end, value = font_patch(segment, size)
                if start != end:
                    tag = parts[part][start:end]
                    pattern = br"\bsz\s*=\s*(['\"])[^'\"]*\1"
                    attr = b'sz="' + value + b'"'
                    value = re.sub(pattern, lambda _m: attr, tag) if re.search(pattern, tag) else re.sub(br"(/?>)$", lambda m: b" " + attr + m[1], tag)
                patches.setdefault(part, []).append((start, end, value))
        if targets != original["source_runs"]:
            changed_units.append(original["id"])
        if any(size is not None for size in sizes):
            resized_units.append(original["id"])
        if CJK.search("".join(targets)):
            remaining_chinese.append(original["id"])
    replacements = {}
    for part, changes in patches.items():
        data = parts[part]
        previous = len(data) + 1
        for start, end, value in sorted(changes, reverse=True):
            if end > previous:
                raise ValueError(f"overlapping XML patches in {part}")
            data = data[:start] + value + data[end:]
            previous = start
        ET.fromstring(data)
        replacements[part] = data
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".translate-", suffix=".pptx", dir=output.parent)
    os.close(descriptor)
    try:
        with zipfile.ZipFile(source) as src, zipfile.ZipFile(temporary, "w") as dst:
            dst.comment = src.comment
            for info in src.infolist():
                dst.writestr(info, replacements.get(info.filename, parts[info.filename]))
        with zipfile.ZipFile(temporary) as check:
            if check.testzip() or set(check.namelist()) != set(parts):
                raise ValueError("output package integrity check failed")
            for name, value in parts.items():
                if check.read(name) != replacements.get(name, value):
                    raise ValueError(f"output part mismatch: {name}")
        # Exclusive creation also prevents accidentally replacing an output created meanwhile.
        with output.open("xb") as handle, open(temporary, "rb") as staged:
            while chunk := staged.read(1024 * 1024):
                handle.write(chunk)
    finally:
        Path(temporary).unlink(missing_ok=True)
    report = {"source": str(source.resolve()), "output": str(output.resolve()),
              "target_language": document.get("target_language"), "slide_count": len(slides),
              "selected_slides": selected, "covered_units": len(expected),
              "changed_units": changed_units, "font_adjusted_units": resized_units,
              "changed_parts": sorted(replacements), "other_parts_unchanged": True,
              "visual_validation": "not_performed", "speaker_notes": "unchanged", "warnings": warnings,
              "target_units_containing_chinese": remaining_chinese}
    write_json(report_path, report)
    return {"output": str(output), "report": str(report_path), "changed_units": len(changed_units)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    get = commands.add_parser("extract", help="extract editable paragraphs to JSON")
    get.add_argument("source", type=Path)
    get.add_argument("--output", required=True, type=Path)
    get.add_argument("--to", default="en-US")
    get.add_argument("--slides")
    put = commands.add_parser("apply", help="write translated runs to a new PPTX")
    put.add_argument("source", type=Path)
    put.add_argument("--translations", required=True, type=Path)
    put.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "extract":
            result = extract(args.source, args.output, args.to, args.slides)
        else:
            result = apply(args.source, args.translations, args.output)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, ET.ParseError, expat.ExpatError) as error:
        parser.exit(1, f"translation helper: {error}\n")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
