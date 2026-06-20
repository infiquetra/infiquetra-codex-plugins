# GEMINI.md

## Purpose

`infiquetra-codex-plugins` is the Codex-native adapter repo for selected Infiquetra
plugins. This is primarily a Codex surface; the authoritative agent instructions live
in [AGENTS.md](AGENTS.md), which Gemini should read and follow here. See
[README.md](README.md) for the plugin/version table and layout.

## Commands

```bash
python3 scripts/validate_codex_plugins.py
python3 -m pytest
```

## Repo-Specific Rules

- This repo is the source of truth after validation and cutover; do NOT edit installed
  Codex cache copies (`.codex/...`) as maintained source.
- `mission-control` is a vendored copy from `infiquetra-claude-plugins` (canonical) —
  script/config changes belong in the canonical repo first and must stay in sync across
  all vendored copies.
- Full agent guidance, the complete command set, and the canon links are in
  [AGENTS.md](AGENTS.md).

## Canon

- Context-audit standard: <https://github.com/infiquetra/infiquetra-context-library/blob/main/docs/ai-context/context-audit-standard.md>
