# DDC Skills — Upstream

This directory vendors the skill catalog from:

- **Source:** https://github.com/datadrivenconstruction/DDC_Skills_for_AI_Agents_in_Construction
- **Pinned commit:** `34e0d78332ce6a510706703dcb61793ee85e4aed`
- **License:** MIT (see `LICENSE`)

## What was copied

- `1_DDC_Toolkit/` — production-ready tools (CWICR, CAD converters, analytics)
- `2_DDC_Book/` — skills mapped to book chapters
- `3_DDC_Insights/` — n8n / agent workflows
- `4_DDC_Curated/` — document generation
- `5_DDC_Innovative/` — CV, IoT, digital twins
- `README.md`, `GETTING_STARTED.md`, `LICENSE`

## What was excluded

- `Books/` (~348 MB) and the 11 MB GuideBook PDF — fetch from upstream if needed
- `publish_*.ps1`, `publish_log.txt`, `update_all_skills.py` — upstream maintenance scripts

## Refresh procedure

```bash
git clone --depth 1 https://github.com/datadrivenconstruction/DDC_Skills_for_AI_Agents_in_Construction.git /tmp/ddc-skills
rm -rf .claude/skills/ddc/{1_DDC_Toolkit,2_DDC_Book,3_DDC_Insights,4_DDC_Curated,5_DDC_Innovative}
cp -r /tmp/ddc-skills/{1_DDC_Toolkit,2_DDC_Book,3_DDC_Insights,4_DDC_Curated,5_DDC_Innovative,README.md,GETTING_STARTED.md,LICENSE} .claude/skills/ddc/
# Update pinned commit above
```

## Note on Claude Code skill discovery

These 221 skills are stored under a nested folder (`ddc/<category>/<skill>/SKILL.md`)
rather than the flat `.claude/skills/<skill>/SKILL.md` layout that Claude Code
auto-discovers. They serve as a **reference library** that an AI agent (or human)
can browse and load on demand — not as auto-loaded skills. To promote any single
skill to auto-discoverable, symlink or copy its folder up to `.claude/skills/`.
