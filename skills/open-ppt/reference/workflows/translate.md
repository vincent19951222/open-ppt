# Mode 2: Translate an existing PPTX

Translate the text of an existing deck while retaining its slide count/order, objects, geometry, backgrounds, media, masters, relationships, and animations. Modify a copy of the original PPTX; do not convert through PPTD or invoke the creation compiler. No outline approval is required.

The quality levels, glossary-first analysis, and staged review approach are informed by [baoyu-translate](https://github.com/JimLiu/baoyu-skills/blob/main/skills/baoyu-translate/SKILL.md). This workflow adapts those ideas to slides; it does not require that skill, its runtime, or its preference files.

## 1. Establish scope and inspect

- Determine source file, target language, requested page range, and terminology from the request and materials. Default Chinese-to-English company decks to `en-US`, concise business/technical English. Respect a different specified locale or audience. Ask only if the target or intended preservation is genuinely unclear.
- Use user-provided glossaries and established product names first. Do not require a setup questionnaire or create global preferences.
- Input must be `.pptx`. Legacy `.ppt`, encrypted files, or damaged packages need conversion/repair before this helper can operate; do not rename their extensions and claim support.
- Use Python 3 and the bundled `scripts/translate_pptx.py` (standard library only). The agent supplies translations; the script extracts and safely writes them, without calling an external translation service.

```bash
python /absolute/skill/scripts/translate_pptx.py extract /absolute/source.pptx \
  --output /absolute/work/source.json --to en-US
# Optional range (1-based presentation order): --slides 3-8,10
```

Read the extracted units in slide order and inspect the deck's visual context if a local renderer is available. Table cells and grouped shapes are included as editable paragraphs. The helper identifies areas needing separate handling: pictures, native charts and their workbooks, SmartArt, embedded objects, slide fields, and shared master/layout text. Speaker notes are unchanged. Never claim these areas were translated automatically.

## 2. Translate with consistent context

| Quality | Selection | Language work |
| --- | --- | --- |
| `quick` | Explicit “快翻 / quick” | Direct translation with terminology and factual checks. |
| `normal` | Default | Analyze the whole deck, establish glossary, translate by slide, then check accuracy and consistency. |
| `refined` | “精翻 / refined / 正式对外 / 审校润色” | Analyze, draft, critique against source, revise, and polish before writing the final PPTX. |

All levels require coverage and package integrity checks. They differ in linguistic review, not in whether content may be skipped.

- For normal/refined, save `analysis.md` containing the audience/style, merged terminology table, abbreviations, and ambiguous passages. Resolve material ambiguities from supplied context or flag them; do not silently guess technical meanings. Research terminology only when needed, rather than expanding slide content.
- For long decks, translate batches of complete slides using the same glossary and adjacent-page context. Never split arbitrary character counts or translate styled runs independently of their full paragraph.
- Translate titles, bullets, captions, and table text in their original roles. Use natural target-language phrasing without adding claims, explanations, parenthetical definitions, translator notes, or extra slides. Preserve medical/performance qualifiers, negation, units, model identifiers, and trademark spelling.
- For refined, retain a draft JSON and save `review.md` with issues located by unit ID/slide: accuracy, terminology, qualifiers, naturalness, and text expansion. Revise the translation JSON from that review; improve language without changing meaning or evidence strength.

Copy `source.json` to `translation.json`. Keep its metadata, IDs, `source_runs`, and `source_text` intact. For each unit fill `target_runs` with a list of translated strings of the **same length** as `source_runs`. Translate the complete paragraph first, then assign its translated phrases to existing runs so emphasis and hyperlink-bearing runs continue to cover appropriate words. Keep the existing explicit line-break boundaries in mind; use ordinary spaces for natural English spacing. Unchanged numbers/brands can have identical source and target strings; an untranslated required unit must not be left null.

```json
{
  "id": "ppt/slides/slide1.xml#p0",
  "source_text": "提高检测效率",
  "source_runs": ["提高", "检测效率"],
  "target_runs": ["Improve ", "testing efficiency"]
}
```

This is one unit, not a complete translation file. Do not discard the surrounding manifest. The ID and source fingerprint prevent applying translations to a different or edited source file.

## 3. Write back and fit the translation

```bash
python /absolute/skill/scripts/translate_pptx.py apply /absolute/source.pptx \
  --translations /absolute/work/translation.json \
  --output /absolute/source-en.pptx
```

- The helper patches only text bytes inside selected slide XML parts. Unchanged ZIP entries are copied without modifying their payload; it does not add transitions or re-embed fonts.
- Existing paragraphs, runs, bullets, colors, links, positions, and media stay in place. Use concise equivalent phrasing first when English expands. Do not abbreviate away substantive facts to make text fit.
- Font size adjustments are optional and explicit: a unit may provide `font_sizes_pt`, a list matching `source_runs`, with `null` to retain each run's size or a positive point size for a necessary adjustment. Existing font properties remain otherwise intact. Use small, consistent changes after inspecting the slide; never apply a universal tiny font. The helper does not measure text fit or move text boxes.
- For further positioning/wrapping work, use a capable native PPTX editor and review the affected pages. Do not rebuild the entire deck to fix a few overflows. If no renderer/editor is available, preserve geometry and clearly report that fit was not visually verified.
- Output must be a new file. If a previous output already exists, choose a new filename instead of overwriting it or the source.

## 4. Validate and deliver

Inspect the generated `.translation-report.json`, and verify:

1. Every selected editable paragraph has an intentional target; source text/IDs still match. Check glossary consistency, values/units, qualifiers, and untranslated source-language text in target runs.
2. Slide count/order and non-target package entries remain unchanged. Compare changed XML to ensure only selected text and explicitly requested font sizes changed. A ZIP/XML check alone is not a PowerPoint playback or layout test.
3. If local PowerPoint, LibreOffice, or another suitable renderer is available, render original and translated copies and compare affected pages for overflow, wrapping, missing glyphs, overlapping content, and table fit. The creation workflow's Kimi/PPTD image exporter is not a native-PPTX verifier for this mode.
4. Review images and unsupported objects for source-language text. List specific slide/object candidates for further localization. Preserve originals and disclose unresolved content; only describe the deck as fully translated when all in-scope material was actually handled.

Deliver the translated `.pptx` and a short summary of language pair, page range, quality level, terminology choices, validation performed, and remaining issues. Link the report when it contains actionable limitations; retain working JSON and analysis alongside the output for follow-up. No PPTD project, outline, theme picker, or browser preview is required.

If the user later requests “继续润色”, reuse the original source and the current translation JSON, perform critique/revision/polish, and write a new output copy; no repeated scope questionnaire is needed.
