# P0 synthetic fixtures

`sample.{pdf,docx,pptx,xlsx,html,csv,txt}` are self-created, non-personal samples
licensed under this repository's MIT license. Each contains the known marker
`EverythingMarkdown P0 sample`; TXT and HTML also contain `한글 확인`.

Regenerate from the repository root with:

```sh
uv run --locked python scripts/create_fixtures.py
```

Generated Office ZIP timestamps/metadata may differ on regeneration; tests verify
semantic content, not binary identity. These minimal fixtures do not establish
real-world document fidelity, OCR support, parser security, or network isolation.
