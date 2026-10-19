"""Behavioral checks for loss-minimizing native PPTX text translation."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "translate_pptx.py"
spec = importlib.util.spec_from_file_location("translate_pptx", SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

A = helper.A
P = helper.P
R = helper.R


def slide(body):
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}"
 xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
 xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main" mc:Ignorable="p14">
<p:cSld><p:spTree>{body}</p:spTree></p:cSld>
<p:transition><p:fade/></p:transition><p:timing/><p:extLst><p14:creationId val="123"/></p:extLst>
</p:sld>'''.encode("utf-8")


class TranslationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.pptx"
        self.manifest = self.root / "source.json"
        self.translations = self.root / "translation.json"
        self.output = self.root / "english.pptx"
        first = slide('''<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title" descr="a > b"/></p:nvSpPr>
<p:spPr><a:xfrm><a:off x="100" y="200"/><a:ext cx="300" cy="400"/></a:xfrm></p:spPr>
<p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:pPr lvl="1"><a:buChar char="•"/></a:pPr>
<a:r><a:rPr b="1" sz="2400"><a:solidFill><a:srgbClr val="C8102E"/></a:solidFill>
<a:hlinkClick r:id="hyper1"/></a:rPr><a:t>提高</a:t></a:r>
<a:r><a:t>检测效率</a:t></a:r></a:p></p:txBody></p:sp>
<p:grpSp><p:sp><p:txBody><a:p><a:r><a:t>分组文本</a:t></a:r><a:br/>
<a:r><a:t>第二行</a:t></a:r></a:p></p:txBody></p:sp></p:grpSp>
<p:graphicFrame><a:tbl><a:tr><a:tc><a:txBody><a:p><a:r><a:t>表格内容</a:t></a:r>
</a:p></a:txBody></a:tc></a:tr></a:tbl></p:graphicFrame>
<p:sp><p:txBody><a:p><a:fld id="field1" type="slidenum"><a:t>1</a:t></a:fld></a:p></p:txBody></p:sp>''')
        second = slide('<p:sp><p:txBody><a:p><a:r><a:t>第二页</a:t></a:r></a:p></p:txBody></p:sp>')
        self.parts = {
            "[Content_Types].xml": b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
            "ppt/presentation.xml": f'<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst><p:sldId id="256" r:id="r1"/><p:sldId id="257" r:id="r2"/></p:sldIdLst></p:presentation>'.encode(),
            "ppt/_rels/presentation.xml.rels": f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="{R}/slide" Target="slides/slide9.xml"/><Relationship Id="r2" Type="{R}/slide" Target="/ppt/slides/slide2.xml"/></Relationships>'.encode(),
            "ppt/slides/slide9.xml": first,
            "ppt/slides/slide2.xml": second,
            "ppt/slides/_rels/slide9.xml.rels": f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="hyper1" Type="{R}/hyperlink" Target="https://example.com" TargetMode="External"/><Relationship Id="chart1" Type="{R}/chart" Target="../charts/chart1.xml"/><Relationship Id="pic1" Type="{R}/image" Target="../media/image1.png"/><Relationship Id="smart1" Type="{R}/diagramData" Target="../diagrams/data1.xml"/></Relationships>'.encode(),
            "ppt/charts/chart1.xml": b'<chart>unchanged labels and values</chart>',
            "ppt/diagrams/data1.xml": b'<diagram>unchanged smart art</diagram>',
            "ppt/media/image1.png": b'original picture bytes',
            "ppt/embeddings/data.xlsx": b'original embedded workbook',
            "ppt/slideMasters/slideMaster1.xml": f'<p:sldMaster xmlns:p="{P}" xmlns:a="{A}"><a:t>共享标题</a:t></p:sldMaster>'.encode(),
            "ppt/notesSlides/notesSlide1.xml": f'<p:notes xmlns:p="{P}" xmlns:a="{A}"><a:t>备注</a:t></p:notes>'.encode(),
        }
        with zipfile.ZipFile(self.source, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.comment = b"original ZIP comment"
            for name, content in self.parts.items():
                archive.writestr(name, content)
        self.original_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def draft(self, slides=None):
        helper.extract(self.source, self.manifest, "en-US", slides)
        document = json.loads(self.manifest.read_text(encoding="utf-8"))
        mapping = {"提高": "Improve ", "检测效率": "testing efficiency & quality <verified>",
                   "分组文本": "Grouped text", "第二行": "Second line", "表格内容": "Table content", "第二页": "Second page"}
        for unit in document["units"]:
            unit["target_runs"] = [mapping[text] for text in unit["source_runs"]]
        return document

    def save(self, document):
        self.translations.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")

    def test_extract_follows_presentation_order_and_finds_tables_groups_and_fields(self):
        document = self.draft()
        self.assertEqual([u["slide"] for u in document["units"]], [1, 1, 1, 2])
        self.assertEqual(document["units"][0]["part"], "ppt/slides/slide9.xml")
        self.assertEqual(document["units"][1]["source_text"], "分组文本\n第二行")
        self.assertEqual(document["units"][2]["source_text"], "表格内容")
        self.assertEqual(document["units"][0]["run_properties"][0]["b"], "1")
        self.assertTrue({"field", "image", "chart", "diagramData", "shared_text"}.issubset({w["kind"] for w in document["warnings"]}))

    def test_apply_preserves_objects_styles_relationships_and_unselected_slides(self):
        document = self.draft("1")
        self.save(document)
        helper.apply(self.source, self.translations, self.output)
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.comment, b"original ZIP comment")
            self.assertEqual(set(archive.namelist()), set(self.parts))
            for name, content in self.parts.items():
                if name != "ppt/slides/slide9.xml":
                    self.assertEqual(archive.read(name), content, name)
            translated = archive.read("ppt/slides/slide9.xml")
        expected = self.parts["ppt/slides/slide9.xml"]
        for unit in document["units"]:
            for original, target in zip(unit["source_runs"], unit["target_runs"]):
                expected = expected.replace(original.encode(), helper.escape(target).encode())
        self.assertEqual(translated, expected)
        root = ET.fromstring(translated)
        self.assertEqual(root.find(f".//{{{A}}}rPr").get("b"), "1")
        self.assertIn("testing efficiency & quality <verified>", [t.text for t in root.iter(f"{{{A}}}t")])
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.original_hash)
        report = json.loads(self.output.with_suffix(".translation-report.json").read_text(encoding="utf-8"))
        self.assertTrue(report["other_parts_unchanged"])
        self.assertEqual(report["visual_validation"], "not_performed")

    def test_font_adjustment_preserves_bold_link_and_inherited_run_properties(self):
        document = self.draft("1")
        document["units"][0]["font_sizes_pt"] = [22, 20]
        self.save(document)
        helper.apply(self.source, self.translations, self.output)
        with zipfile.ZipFile(self.output) as archive:
            root = ET.fromstring(archive.read("ppt/slides/slide9.xml"))
        runs = root.find(f".//{{{P}}}txBody/{{{A}}}p").findall(f"{{{A}}}r")
        self.assertEqual([r.find(f"{{{A}}}rPr").get("sz") for r in runs], ["2200", "2000"])
        self.assertEqual(runs[0].find(f"{{{A}}}rPr").get("b"), "1")
        self.assertIsNotNone(runs[0].find(f"{{{A}}}rPr/{{{A}}}hlinkClick"))

    def test_missing_duplicate_unknown_and_stale_units_fail_without_output(self):
        baseline = self.draft()
        variants = []
        for change in ("missing", "duplicate", "unknown", "stale", "null", "wrong_count", "empty", "bad_xml", "bad_size"):
            doc = json.loads(json.dumps(baseline))
            if change == "missing":
                doc["units"].pop()
            elif change == "duplicate":
                doc["units"].append(doc["units"][0])
            elif change == "unknown":
                doc["units"][0]["id"] = "unknown"
            elif change == "stale":
                doc["units"][0]["source_runs"][0] = "wrong source"
            elif change == "null":
                doc["units"][0]["target_runs"] = None
            elif change == "wrong_count":
                doc["units"][0]["target_runs"] = ["one"]
            elif change == "empty":
                doc["units"][0]["target_runs"] = ["", ""]
            elif change == "bad_xml":
                doc["units"][0]["target_runs"][0] = "bad\x01text"
            elif change == "bad_size":
                doc["units"][0]["font_sizes_pt"] = [float("nan"), None]
            variants.append((change, doc))
        for name, document in variants:
            with self.subTest(name=name):
                self.save(document)
                with self.assertRaises(ValueError):
                    helper.apply(self.source, self.translations, self.output)
                self.assertFalse(self.output.exists())
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.original_hash)

    def test_stale_source_and_overwrite_are_rejected(self):
        document = self.draft()
        document["source_sha256"] = "wrong"
        self.save(document)
        with self.assertRaisesRegex(ValueError, "source file changed"):
            helper.apply(self.source, self.translations, self.output)
        document["source_sha256"] = self.original_hash
        self.save(document)
        with self.assertRaisesRegex(ValueError, "distinct"):
            helper.apply(self.source, self.translations, self.source)
        self.output.write_bytes(b"existing result")
        with self.assertRaisesRegex(ValueError, "already exists"):
            helper.apply(self.source, self.translations, self.output)
        self.assertEqual(self.output.read_bytes(), b"existing result")

    def test_page_selection_is_validated_and_output_is_not_replaced(self):
        self.assertEqual(helper.select_slides("2,1-2", 2), [1, 2])
        for value in ("0", "3", "2-1", "1,", "all"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                helper.select_slides(value, 2)
        self.draft("2")
        self.assertEqual([u["slide"] for u in json.loads(self.manifest.read_text(encoding="utf-8"))["units"]], [2])
        with self.assertRaises(FileExistsError):
            helper.extract(self.source, self.manifest, "en-US")

    def test_literal_linebreaks_and_xml_entities_roundtrip_as_text(self):
        text = "Spacing & signs < >\nSecond line\rThird line"
        encoded = helper.xml_text(text)
        self.assertEqual(ET.fromstring(b"<text>" + encoded + b"</text>").text, text)
        content = slide('<p:sp><p:txBody><a:p><a:r><a:t><![CDATA[原文 & 数值]]></a:t></a:r></a:p></p:txBody></p:sp>')
        self.assertEqual(helper.paragraphs(content)[0]["pieces"], ["原文 & 数值"])


if __name__ == "__main__":
    unittest.main()
