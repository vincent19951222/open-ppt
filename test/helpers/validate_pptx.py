#!/usr/bin/env python3
"""Structural smoke validator for compiled PPTX files.

Catches the two defect classes found in lib/compile-pptx.py:
1. OPC parts rewritten without namespace (breaks PowerPoint/python-pptx open).
2. Animation <p:spTgt spid> referencing shape ids absent from the slide spTree.

Usage: validate_pptx.py <file.pptx> <expected-slide-count>
"""

import posixpath
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
CT_NS = "{http://schemas.openxmlformats.org/package/2006/content-types}"
P_NS = "{http://schemas.openxmlformats.org/presentationml/2006/main}"

SLIDE_RE = re.compile(r"ppt/slides/slide\d+\.xml$")


def fail(message: str) -> None:
    print(f"VALIDATE FAIL: {message}")
    sys.exit(1)


def main() -> None:
    path = sys.argv[1]
    expect_slides = int(sys.argv[2])

    archive = zipfile.ZipFile(path)
    if archive.testzip() is not None:
        fail("zip integrity check failed")
    names = set(archive.namelist())

    for name in names:
        if name.endswith((".xml", ".rels")):
            try:
                ET.fromstring(archive.read(name))
            except ET.ParseError as error:
                fail(f"{name} is not well-formed XML: {error}")

    # Every child of a .rels root must live in the relationships namespace;
    # a non-namespaced child silently breaks consumers (python-pptx, PowerPoint).
    for name in sorted(part for part in names if part.endswith(".rels")):
        root = ET.fromstring(archive.read(name))
        if root.tag != f"{REL_NS}Relationships":
            fail(f"{name}: unexpected root {root.tag}")
        for child in root:
            if child.tag != f"{REL_NS}Relationship":
                fail(f"{name}: non-namespaced child {child.tag}")
        base = posixpath.dirname(posixpath.dirname(name))
        for rel in root.findall(f"{REL_NS}Relationship"):
            if rel.get("TargetMode") == "External":
                continue
            target = posixpath.normpath(posixpath.join(base, rel.get("Target")))
            if target not in names:
                fail(f"{name}: unresolved target {rel.get('Target')} -> {target}")

    ct_root = ET.fromstring(archive.read("[Content_Types].xml"))
    if ct_root.tag != f"{CT_NS}Types":
        fail(f"[Content_Types].xml: unexpected root {ct_root.tag}")
    for child in ct_root:
        if not child.tag.startswith(CT_NS):
            fail(f"[Content_Types].xml: non-namespaced child {child.tag}")
        part = child.get("PartName")
        if part and part[1:] not in names:
            fail(f"[Content_Types].xml: override without part {part}")

    slides = sorted(name for name in names if SLIDE_RE.match(name))
    if len(slides) != expect_slides:
        fail(f"expected {expect_slides} slides, package has {len(slides)}")

    presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
    slide_id_list = presentation.find(f"{P_NS}sldIdLst")
    if slide_id_list is None or len(slide_id_list) != expect_slides:
        fail("presentation.xml sldIdLst does not match expected slide count")

    for slide in slides:
        xml_text = archive.read(slide).decode("utf-8")
        body = xml_text[: xml_text.find("</p:spTree>")]
        shape_ids = set(re.findall(r'cNvPr id="(\d+)"', body))
        for spid in set(re.findall(r'spTgt spid="(\d+)"', xml_text)):
            if spid not in shape_ids:
                fail(f"{slide}: animation targets missing shape id {spid}")

    print(f"VALIDATE OK: {len(slides)} slides")


if __name__ == "__main__":
    main()
