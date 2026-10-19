# Mode 3: Normalize an existing deck to Mindray Red

Keep the supplied deck's content and make its visual presentation consistent with the fixed [MR Red Tech design system](../design_system/healthcare/mr-red-tech/design.md). “麦瑞红” is treated as the user's spelling of “迈瑞红”, not a separate theme.

Do not load the creation or translation workflows by default. This task has no outline approval, no theme picker, and no default translation/research. Preserve slide count, order, language, business text, numbers, units, tables, chart data, citations, images, and notes. Do not manufacture assertion titles or bottom takeaways to meet the design guide's narrative suggestions. Source-content preservation takes precedence over those suggestions. Reordering, splitting/merging pages, substantial rewriting, or dropping business content needs user authorization.

## Fixed visual system

- Use a 960 × 540 (16:9) canvas; brand red `#C8102E`, deep red `#8F0C20`, white, near-black, and neutral grays. Red is for titles/emphasis, not every body-page background.
- Covers/closing pages: deep-red field, large white original title and restrained supporting text. Classify these from the source; do not turn the first data page into a cover automatically. Preserve meaningful imagery even if that needs a content-page layout rather than a conventional cover.
- Body pages: white background, one red ❯ marker at the top left, original title in red (typically 24–28 pt), a thin gray header rule, consistent safe margins and columns. Align/reorganize the existing evidence rather than placing arbitrary original content into decorative cards.
- Use square modules where content grouping warrants them, red-header tables, and consistent process/architecture layouts. Keep fonts legible: normal body 12–14 pt, sources/footnotes 8–9 pt. Use Segoe UI / Microsoft YaHei; do not introduce MiSans or embed fonts by default.
- Place the bundled genuine logo at bottom right on light pages, with page number to its left. The asset is [mindray-lockup-wide.png](../design_system/healthcare/mr-red-tech/assets/mindray-lockup-wide.png). Do not redraw or distort it. Omit the red logo on a red cover unless the user supplies an approved white version.
- Preserve real colors in product photographs, medical imagery, evidence screenshots, and semantically coded plots. Ordinary native charts can be recolored red/gray after checking their legends; never erase diagnostic or risk distinctions just to satisfy a palette.

## 1. Inspect the original

Use the bundled `scripts/restyle_pptx.py`. Input is `.pptx`; legacy `.ppt` needs real conversion first. The native helper requires Python 3 and `python-pptx`. Check `python -c "import pptx"`; if missing, install with that interpreter's `python -m pip install python-pptx`. Do not install unrelated browser tooling for this path.

```bash
python /absolute/skill/scripts/restyle_pptx.py inspect /absolute/source.pptx \
  --output /absolute/work/restyle-plan.json
```

Read every slide's source shape inventory, tables, chart context, inherited layout/master candidates, and extracted `source-media/`. When a local native renderer is available, render and inspect the original first. Source inventories are audit artifacts, not an outline for user approval. Do not claim they are screenshots or that text extraction alone reveals the visual hierarchy.

## 2. Prepare the page layout plan

The helper produces a JSON plan. Keep source hashes, `source_shapes`, slide numbers, and original order intact; edit only the layout decisions. Defaults fit existing content into a common body region, which is **a starting point, not proof of a finished redesign**. The agent must choose appropriate page roles, identify titles, and improve individual placements when the original layout is poor.

For each slide:

- `page_type`: `cover`, `content`, `divider`, or `closing`, chosen from the actual content.
- `title_shape_id`: an existing text shape ID. The helper recognizes real title placeholders; choose a suitable existing text object for unstructured sources. Do not invent a title or use a table/image as a title. If the source has no suitable title, preserve the content and report the header decision rather than fabricating a claim.
- `placements`: per-object overrides by stable `shape_id`. `bounds` uses `[x, y, width, height]` on the 960 × 540 canvas; `font_size_pt` can adjust the text. Reflow content to solve density, not universal tiny fonts. Pictures and groups must retain their aspect ratios.
- `preserve_style`: preserve a particular evidence object or color-coded diagram. Pictures automatically retain their pixels; native charts keep their palette by default. For ordinary bar/line charts that can safely adopt the brand palette, set `preserve_style: false` and review point/marker/legend styles after applying.
- `decorative_shape_ids`: explicitly identified text-free old decoration or old logo objects only, with `decoration_reason`. Never classify a product photo/evidence screenshot as decoration. The helper refuses text, tables, charts, groups, and animation/connector targets in this list. It does not remove business text to make a page fit.
- `hide_master_shapes`: set true only after confirming inherited master graphics are decoration, and record `hide_master_shapes_reason`. Shared layers can contain real content. If they do, preserve them or materialize their content in a capable native editor before hiding them; do not silently discard inherited business content.

Example of a placement inside one slide's plan (not a complete plan):

```json
{
  "slide": 2,
  "page_type": "content",
  "title_shape_id": 2,
  "placements": [
    {"shape_id": 3, "bounds": [48, 110, 380, 350], "font_size_pt": 14},
    {"shape_id": 4, "bounds": [460, 110, 452, 350], "preserve_style": true}
  ]
}
```

## 3. Apply to a separate native PPTX

```bash
python /absolute/skill/scripts/restyle_pptx.py apply /absolute/source.pptx \
  --plan /absolute/work/restyle-plan.json --output /absolute/source-mindray-red.pptx
```

The helper moves/styles existing native objects, adds the header/footer/logo, and checks unchanged source text before saving. It preserves tables and charts as native objects and checks protected media, embedded workbooks, and notes. It does not route the source through the creation compiler, convert every page into a screenshot, or automatically add animations. Existing unsupported objects remain native; they may still need manual styling.

Fonts are not embedded by default. If a source has meaningful symbol-font glyphs, verify their rendering before removing its fonts; either replace them with verified native/vector symbols or use `--keep-source-fonts` when explicitly needed. That option retains existing embedding only, and may increase file size.

## 4. Verify content and appearance

- Check the `.restyle-report.json`, page count/order, original shape texts, every number/unit, table values/merges, chart series/categories, citations, hyperlinks, pictures/crops, and notes. Review removal/hiding decisions against the original.
- Inspect the native output: the candidate helper cannot determine overflow or attractive layouts. Render with PowerPoint, LibreOffice, or another capable local renderer when available. Check the header, safe margins, footer/logo, text fit, image ratio, connector relationships, chart palettes, and light/dark contrast on every page. Iterate the layout plan and write a new candidate filename until resolved.
- A native object remaining in the package is not proof it is visible or fits its new bounds. Complex SmartArt, inherited content, uncommon charts, OLE/media, animations, symbol fonts, and tightly packed pages need explicit inspection. Do not flatten these objects merely to hide a conversion limitation.
- If no native renderer is available, report structural checks separately and describe the output as awaiting visual review; do not claim full visual acceptance or PowerPoint/WPS playback validation.

Deliver the new PPTX, the layout plan, and the report when it contains actionable warnings. Preserve the source file. No PPTD project or content-outline confirmation is required for this native restyle path.
