---
name: open-ppt
description: Create, edit, replicate, translate, restyle, read, and export presentations. New decks first deliver a Markdown content draft for approval, then editable PPTD and native PPTX. Translate existing PPTX copies while preserving their design, with glossary and review options. Restyle existing decks into fixed Mindray Red (迈瑞红/麦瑞红) while retaining content and native objects. Use for PowerPoint, PPT/PPTX, slide decks, PPTD, infographics, and posters.
---

# open-ppt

Choose the workflow from the user's intent, then read **only that workflow** and its relevant references. Modes are natural-language routing rules, not CLI subcommands.

| Mode | Trigger and boundary | Workflow |
| --- | --- | --- |
| 1 · Create | Create a new deck from a topic, document, outline, template, or visual reference; existing PPTD edits and faithful replication also use this workflow. “Create an English PPT from this report” is creation. | [Create](reference/workflows/create.md) |
| 2 · Translate | Translate/localize an existing PPTX while retaining its pages, objects, and overall design. “把这份中文 PPT 翻成英文，保留格式” and “translate slides 3–8” select this mode. | [Translate](reference/workflows/translate.md) |
| 3 · Restyle | Normalize an existing PPTX into fixed Mindray Red while keeping its content. “统一成迈瑞红 / 麦瑞红”, “Mindray Red”, “mr-red-tech”, or “Mode 3” with an existing deck select this workflow. | [Restyle](reference/workflows/restyle.md) |

- Explicit mode selection takes priority when consistent with the task. Otherwise infer intent; ask only when ambiguity affects preservation or content changes.
- An attached PPTX alone does not select translation: it can be a template for a new deck. Mentioning English alone does not select translation either.
- A request for a new Mindray-style deck from a topic/document remains Mode 1. Mode 3 requires an existing deck whose content is to be retained; it is not a request to invent a new proposal.
- For a clear request, state the selected mode briefly and proceed; do not require a mode-selection menu.
- For a request combining translation and redesign, clarify the preservation requirement if unclear. Do not silently rebuild a deck that was meant to keep its format.
- Creation-specific outline approval, PPTD delivery, theme choice, and default transitions **do not apply to translation or native PPTX restyling**. Translation quality levels (`quick`, `normal`, `refined`) are options within Mode 2, not additional top-level modes.

Shared requirements:

- Preserve user originals and unrelated changes; write derived decks to separate files.
- Preserve facts, numbers, units, product names, and links. Do not invent missing material or claim success for skipped content.
- Deliver absolute local file links and describe what was verified and what still needs review.
- Resolve script paths from this skill's actual installation directory, never from a workflow reference directory.
